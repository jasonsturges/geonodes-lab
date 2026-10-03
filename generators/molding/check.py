"""Independent checks for assets/Molding.blend: every named section against sampled three-low-poly
profile fixtures (sdk-reference.json), exact extrusion volumes, UVs and crown/base orientation.
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


if __name__ == '__main__':
    main()
