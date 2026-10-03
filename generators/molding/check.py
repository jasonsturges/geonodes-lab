"""Independent checks for assets/Molding.blend: every named section against sampled three-low-poly
profile fixtures (sdk-reference.json), exact extrusion volumes, UVs and crown/base orientation; and
Molding Run against an independent miter oracle (three-low-poly MoldingGeometry: bisecting-plane joints).
Run: python3 scripts/check.py molding
"""
from pathlib import Path
import sys, json, math, struct
import bpy
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from authoring.modifiers import set_input, get_input
from authoring.uv import audit_uv
from collections import Counter, defaultdict
from mathutils import Vector


def area(poly): return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))) / 2


def data(obj):
    bpy.context.view_layer.update()
    e = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = e.to_mesh()
    try:
        me.calc_loop_triangles()
        return dict(vertices=[tuple(v.co) for v in me.vertices], faces=[list(p.vertices) for p in me.polygons], tris=[(list(t.vertices), t.polygon_index) for t in me.loop_triangles], uv=audit_uv(me), ids=[d.value for d in me.attributes['came_id'].data] if 'came_id' in me.attributes else None)
    finally:
        e.to_mesh_clear()


def shell(d, ids=None, allow_collinear=False):
    assert d['vertices'], 'Empty geometry'
    edges = Counter()
    direction = Counter()
    vol = defaultdict(float)
    face_areas = defaultdict(float)
    for i, f in enumerate(d['faces']):
        group = ids[i] if ids else 0
        for a, b in zip(f, f[1:] + f[:1]):
            edges[(group, *sorted((a, b)))] += 1
            direction[group, a, b] += 1
    assert all(n == 2 for n in edges.values()), 'Nonmanifold edges'
    assert all(n == direction[g, b, a] for (g, a, b), n in direction.items()), 'Winding'
    for tri, face in d['tris']:
        a, b, c = [Vector(d['vertices'][i]) for i in tri]
        twice_area = (b - a).cross(c - a).length
        face_areas[face] += twice_area
        assert twice_area > 1e-12 or (allow_collinear and len(d['faces'][face]) > 3)
        vol[ids[face] if ids else 0] += a.dot(b.cross(c)) / 6
    assert all(v > 1e-12 for v in face_areas.values()), 'Zero-area face'
    assert all(v > 0 for v in vol.values()), vol
    return vol


def reed(n, reeds=4, back=.1):
    points = [(0, 0), (1, 0), (1, back)]
    for j in range(reeds):
        for i in range(1, 2 * n + 1):
            t = i / (2 * n) * math.pi
            points.append((1 - (j + .5) / reeds + .5 / reeds * math.cos(t), back + (1 - back) * math.sin(t)))
    points.append((0, 0))
    return points


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objects = {}
    report = []
    for family in ('Corner', 'Surface'):
        with bpy.data.libraries.load(str(ROOT / 'assets/Molding.blend'), link=False) as (_, dst):
            dst.objects = ['GNL • ' + family + ' Molding']
        obj = dst.objects[0]
        bpy.context.collection.objects.link(obj)
        objects[family] = obj
    for case in json.loads((HERE / 'sdk-reference.json').read_text()):
        family, style, n = case['family'], case['style'], case['segments']
        obj = objects[family]
        mod = obj.modifiers[0]
        height, projection, length = .09, .065, 1.2
        for k, v in {'Profile': style, 'Segments': n, 'Height': height, 'Projection': projection, 'Length': length}.items():
            set_input(mod, k, v)
        points = reed(n) if style == 'Reed' else case['points']
        expected = area(points) * height * projection * length
        for crown in ([False, True] if family == 'Corner' else [False]):
            if family == 'Corner':
                set_input(mod, 'Crown', crown)
            d = data(obj)
            volume = shell(d, allow_collinear=True)[0]
            assert abs(volume - expected) < max(1e-9, expected * 1e-4), (family, style, n, volume, expected)
            assert d['uv']['present'] and d['uv']['finite'] and not d['uv']['zero_area_faces'], (family, style, n, d['uv'])
            for x, y, z in d['vertices']:
                assert abs(abs(x) - length / 2) < 1e-6
                assert min(((-z if crown else z) / height - a)**2 + (-y / projection - b)**2 for a, b in points) < 1e-9, (style, n, x, y, z)
            report.append(dict(family=family, style=style, segments=n, crown=crown, volume=volume))
            print('PASS', report[-1], flush=True)
    # Dimensions, reed count and backing all remain live and independently reusable.
    mod = objects['Surface'].modifiers[0]
    for k, v in {'Profile': 'Reed', 'Reeds': 8, 'Reed Backing': .25, 'Length': .55, 'Height': .16, 'Projection': .008, 'Segments': 2}.items():
        set_input(mod, k, v)
    assert abs(shell(data(objects['Surface']), allow_collinear=True)[0] - area(reed(2, 8, .25)) * .55 * .16 * .008) < 1e-8
    sibling = bpy.data.objects.new('Independent molding', bpy.data.meshes.new('Host'))
    bpy.context.collection.objects.link(sibling)
    sm = sibling.modifiers.new('Molding', 'NODES')
    sm.node_group = mod.node_group
    set_input(sm, 'Length', 2.)
    assert abs(get_input(mod, 'Length') - .55) < 1e-6 and data(sibling)['vertices']
    print(f'Molding: {len(report)} profile/mode cases passed, plus reed variation and an independent host')


# --- Molding Run ---------------------------------------------------------------------------------------
PLANS = {   # name: (points, closed). Anticlockwise rooms, so Inward is the room side.
    'rectangle room': ([(-2, -1.5), (2, -1.5), (2, 1.5), (-2, 1.5)], True),
    'triangle': ([(0, 0), (3, 0), (1, 2)], True),
    'open L': ([(0, 0), (2, 0), (2, 1.5)], False),
    'chimney breast': ([(0, 0), (1, 0), (1, .4), (1.8, .4), (1.8, 0), (3, 0)], False),
    'shallow 30° and sharp 120°': ([(0, 0), (1.5, 0), (2.8, .75), (2.2, 1.9)], False),
}


def poly(name, points, closed):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    spline = curve.splines.new('POLY')
    spline.points.add(len(points) - 1)
    for p, (x, y) in zip(spline.points, points):
        p.co = (x, y, 0, 1)
    spline.use_cyclic_u = closed
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def straight_bezier(name, points, closed):
    """The plan as a Bézier whose handles sit on its sides: straight walls, many evaluated points."""
    curve = bpy.data.curves.new(name + ' (Bézier)', 'CURVE')
    curve.dimensions = '3D'
    spline = curve.splines.new('BEZIER')
    spline.resolution_u = 16
    spline.bezier_points.add(len(points) - 1)
    count = len(points)
    for k, (p, (x, y)) in enumerate(zip(spline.bezier_points, points)):
        p.co = (x, y, 0)
        p.handle_left_type = p.handle_right_type = 'FREE'
        (px, py) = points[(k - 1) % count] if closed or k > 0 else (2 * x - points[1][0], 2 * y - points[1][1])
        (nx, ny) = points[(k + 1) % count] if closed or k < count - 1 else (2 * x - points[-2][0], 2 * y - points[-2][1])
        p.handle_left = (x + (px - x) / 3, y + (py - y) / 3, 0)
        p.handle_right = (x + (nx - x) / 3, y + (ny - y) / 3, 0)
    spline.use_cyclic_u = closed
    obj = bpy.data.objects.new(name + ' (Bézier)', curve)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def miters(points, closed):
    """Oracle: each point's offset direction n (unit, bisecting the turn) and widening k = 1/cos(turn/2)."""
    out = []
    count = len(points)
    for i, (x, y) in enumerate(points):
        dirs = []
        for a, b in ((i - 1, i), (i, i + 1)):
            if not closed and (a < 0 or b >= count):
                continue
            (ax, ay), (bx, by) = points[a % count], points[b % count]
            length = math.hypot(bx - ax, by - ay)
            dirs.append(((bx - ax) / length, (by - ay) / length))
        perps = [(-dy, dx) for dx, dy in dirs]
        nx, ny = sum(p[0] for p in perps), sum(p[1] for p in perps)
        norm = math.hypot(nx, ny)
        n = (nx / norm, ny / norm)
        k = 1 / (n[0] * perps[0][0] + n[1] * perps[0][1])
        out.append((n, k))
    return out


def section_points(group, settings):
    from authoring.checking import evaluate_group
    mesh = evaluate_group(group, settings, as_points=True)
    return [(x, y) for x, y, _ in mesh.verts]


def verify_run():
    from authoring.checking import fresh_session_with, evaluate_object
    from mathutils.kdtree import KDTree
    loaded = fresh_session_with('Molding.blend', objects=['GNL • Molding Run'])
    obj = loaded['GNL • Molding Run']
    corner_styles = ['Cove', 'Ovolo', 'Chamfer', 'Ogee', 'Cyma', 'Scotia', 'Fillet', 'Step']
    cases = 0
    for p_index, (name, (points, closed)) in enumerate(PLANS.items()):
        path = poly(name, points, closed)
        frames = miters(points, closed)
        for r_index, run in enumerate(('Crown', 'Base', 'Chair Rail')):
            for outward in (False, True):
                style = corner_styles[(p_index * 6 + r_index * 2 + outward) % 8] if run != 'Chair Rail' else 'Astragal'
                size = {'Height': .14, 'Projection': .09, 'Segments': 5}
                settings = {'Path': path, 'Run': run, 'Outward': outward, **size,
                            ('Surface Profile' if run == 'Chair Rail' else 'Corner Profile'): style}
                mesh = evaluate_object(obj, settings)
                group = 'GNL • Surface Molding Profile' if run == 'Chair Rail' else 'GNL • Corner Molding Profile'
                section = section_points(group, {'Profile': style, **size})
                label = (name, run, 'outward' if outward else 'inward', style)
                assert mesh.closed and len(mesh.islands) == 1, label
                assert len(mesh.verts) == len(points) * len(section), (label, len(mesh.verts))
                assert 'UVMap' in mesh.uv_layers, label
                # Every vertex where the oracle puts it: path point + side·k·n·projection, height down or up.
                tree = KDTree(len(mesh.verts))
                for k_, v in enumerate(mesh.verts):
                    tree.insert(v, k_)
                tree.balance()
                side = -1 if outward else 1
                up = -1 if run == 'Crown' else 1
                for (px, py), ((nx, ny), k) in zip(points, frames):
                    for h, p in section:
                        expected = (px + side * k * nx * p, py + side * k * ny * p, up * h)
                        _, _, distance = tree.find(expected)
                        assert distance < 1e-5, (label, expected, distance)
                # Volume: section area × the length of its centroid line (exact for a mitered prism chain).
                area_, centroid = 0, 0
                for (h0, p0), (h1, p1) in zip(section, section[1:] + section[:1]):
                    cross = h0 * p1 - h1 * p0
                    area_ += cross / 2
                    centroid += (p0 + p1) * cross / 6
                c = centroid / area_
                ring = [(px + side * k * nx * c, py + side * k * ny * c) for (px, py), ((nx, ny), k) in zip(points, frames)]
                pairs = list(zip(ring, ring[1:] + ring[:1])) if closed else list(zip(ring, ring[1:]))
                expected_volume = abs(area_) * sum(math.dist(a, b) for a, b in pairs)
                assert mesh.volume > 0 and abs(mesh.volume - expected_volume) < 1e-6 + expected_volume * 1e-5, \
                    (label, mesh.volume, expected_volume)
                cases += 1
                # The same plan as a Bézier with straight segments (16 evaluated points per side) must give
                # exactly the poly result: collinear stations are dropped, so no inside miter can fold.
                mesh_b = evaluate_object(obj, {**settings, 'Path': straight_bezier(name, points, closed)})
                assert len(mesh_b.verts) == len(mesh.verts) and abs(mesh_b.volume - mesh.volume) < 1e-7, \
                    (label, 'Bézier', len(mesh_b.verts), len(mesh.verts), mesh_b.volume, mesh.volume)
                cases += 1
    # A Bézier path (evaluated points), and one path object holding two separate runs.
    bez = bpy.data.curves.new('bay', 'CURVE')
    bez.dimensions = '3D'
    spline = bez.splines.new('BEZIER')
    spline.bezier_points.add(3)
    for p, co in zip(spline.bezier_points, [(0, 0, 0), (1, .6, 0), (2, -.2, 0), (3, .5, 0)]):
        p.co = co
        p.handle_left_type = p.handle_right_type = 'AUTO'
    two = poly('two runs', [(0, 0), (1, 0)], False)
    extra = two.data.splines.new('POLY')
    extra.points.add(2)
    for p, (x, y) in zip(extra.points, [(0, 1), (1, 1), (1, 2)]):
        p.co = (x, y, 0, 1)
    for path, islands in ((bpy.data.objects.new('bay', bez), 1), (two, 2)):
        if path.name not in bpy.context.scene.objects:
            bpy.context.scene.collection.objects.link(path)
        for run in ('Crown', 'Base', 'Chair Rail'):
            for outward in (False, True):
                mesh = evaluate_object(obj, {'Path': path, 'Run': run, 'Outward': outward})
                assert mesh.closed and mesh.volume > 0 and len(mesh.islands) == islands, (path.name, run, outward)
                cases += 1
    # No path chosen: the sample room keeps a freshly appended object visible.
    mesh = evaluate_object(obj, {'Path': None})
    assert mesh.closed and mesh.volume > 0
    print(f'Molding Run: {cases + 1} path cases passed against the miter oracle')


if __name__ == '__main__':
    main()
    verify_run()
