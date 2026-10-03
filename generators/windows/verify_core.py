"""Independent formulas and section integration for saved native window components."""
from pathlib import Path
import math, sys, json, struct
from collections import Counter, defaultdict
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from authoring.modifiers import set_input, get_input
from authoring.uv import audit_uv
STYLES = ['Square', 'Semicircle', 'Segmental', 'Horseshoe', 'Elliptical', 'Pointed', 'Ogee']


def boundary(style, w, h, r, n):
    a = w / 2
    if style == 'Square':
        r = 0
    elif style == 'Semicircle':
        r = a
    elif style == 'Segmental':
        r = min(a, r)
    elif style in ('Horseshoe', 'Pointed'):
        r = max(a, r)
    points = [(-a, 0), (a, 0)]
    for i in range(2 * n + 1):
        t = i / (2 * n)
        q = 2 * min(t, 1 - t)
        sign = 1 if t <= .5 else -1
        if style == 'Square':
            x, y = a * (1 - 2 * t), 0
        elif style == 'Elliptical':
            x, y = a * math.cos(math.pi * t), r * math.sin(math.pi * t)
        elif style == 'Pointed':
            off = (a * a - r * r) / (2 * a)
            rad = a - off
            angle = q * math.atan2(r, -off)
            x, y = sign * (off + rad * math.cos(angle)), rad * math.sin(angle)
        elif style == 'Ogee':
            controls = [(1, 0), (1, .4), (.45, .55)] if q <= .5 else [(.45, .55), (.175, .625), (0, 1)]
            u = q * 2 if q <= .5 else q * 2 - 1
            x = sign * a * sum(v[0] * k for v, k in zip(controls, ((1 - u)**2, 2 * u * (1 - u), u * u)))
            y = r * sum(v[1] * k for v, k in zip(controls, ((1 - u)**2, 2 * u * (1 - u), u * u)))
        else:
            rad = (a * a + r * r) / (2 * r)
            cy = r - rad
            lo = math.atan2(-cy, a)
            angle = lo + t * (math.pi - 2 * lo)
            x, y = rad * math.cos(angle), cy + rad * math.sin(angle)
        points.append((x, h + y))
    return points, r


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


def sample_output(core, output, values):
    g = bpy.data.node_groups.new('Temporary output', 'GeometryNodeTree')
    g.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    n = g.nodes.new('GeometryNodeGroup')
    n.node_tree = core
    for k, v in values.items():
        if k in n.inputs:
            n.inputs[k].default_value = v
    out = g.nodes.new('NodeGroupOutput')
    g.links.new(n.outputs[output], out.inputs[0])
    obj = bpy.data.objects.new('Temporary output', bpy.data.meshes.new('Temporary'))
    bpy.context.collection.objects.link(obj)
    obj.modifiers.new('Read', 'NODES').node_group = g
    result = data(obj)
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    bpy.data.node_groups.remove(g)
    return result


def crossings(poly, level):
    hits = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if (a[1] <= level < b[1]) or (b[1] <= level < a[1]):
            hits.append(a[0] + (b[0] - a[0]) * (level - a[1]) / (b[1] - a[1]))
    hits.sort()
    return hits


def expected_bars(poly, w, h, r, angle, spacing, phase, width, depth, sides, *, families=None, full_section=False):
    # Candidate IDs depend on native float32 arithmetic at integer boundaries.
    f32 = lambda x: struct.unpack("f", struct.pack("f", x))[0]
    reach = f32(f32(f32(w) + f32(h)) + f32(f32(r) + 1))
    families = families or [(angle, spacing, phase), (-angle, spacing, phase)]
    steps = math.ceil(f32(reach / f32(min(v[1] for v in families))))
    per = 2 * steps + 1
    result = {}
    section = [(-depth / 2 * math.cos(math.pi / sides + i * math.tau / sides), width / 2 * math.sin(math.pi / sides + i * math.tau / sides)) for i in range(sides)]
    vmin = min(p[1] for p in section)
    vmax = max(p[1] for p in section)
    for family, (theta, spacing, phase) in enumerate(families):
        c, s = math.cos(theta), math.sin(theta)
        planar = [(x * c + y * s, -x * s + y * c) for x, y in poly]
        for j in range(per):
            off = (j - steps) * spacing + phase
            if full_section and (min(v for _, v in planar) > off + vmin + 2e-6 or max(v for _, v in planar) < off + vmax - 2e-6):
                continue
            breaks = sorted(set([vmin, vmax] + [v for _, v in section] + [v - off for _, v in planar if vmin < v - off < vmax]))
            ext = []
            # Axis range of the intersection of the boundary region with the section's lateral strip.
            for u, v in planar:
                if vmin - 1e-10 <= v - off <= vmax + 1e-10:
                    ext.append(u)
            for a, b in zip(planar, planar[1:] + planar[:1]):
                for edge in (off + vmin, off + vmax):
                    if min(a[1], b[1]) < edge < max(a[1], b[1]):
                        ext.append(a[0] + (b[0] - a[0]) * (edge - a[1]) / (b[1] - a[1]))
            if not ext or max(ext) - min(ext) <= width * 3 + 1e-8:
                continue

            def f(v):
                hits = crossings(planar, off + v)
                z = crossings(section, v)
                return sum(b - a for a, b in zip(hits[::2], hits[1::2])) * (max(z) - min(z) if z else 0)
            # Two Gauss points integrate the piecewise quadratic exactly, avoiding endpoint ambiguities.
            volume = 0
            for a, b in zip(breaks, breaks[1:]):
                mid = (a + b) / 2
                dx = (b - a) / 2
                volume += dx * (f(mid - dx / math.sqrt(3)) + f(mid + dx / math.sqrt(3)))
            if volume > 1e-10:
                result[family * per + j] = volume
    return result


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(ROOT / 'assets/Windows.blend'), link=False) as (src, dst):
        dst.objects = ['GNL • Diamond Lattice']
    obj = dst.objects[0]
    bpy.context.collection.objects.link(obj)
    mod = obj.modifiers[0]
    profile = bpy.data.node_groups['GNL • Opening Profile']
    report = []
    for style in STYLES:
        cases = [(.4, 12, 4, 1.2, 1.4, .67, .19, .023, .022, .035), (1., 24, 7, 1.2, 1.4, .67, .19, .023, .022, .035)]
        if style == 'Square':
            cases.append((.1, 4, 3, .8, .6, math.radians(15), .12, -.17, .03, .06))
        if style == 'Horseshoe':
            cases.append((1.4, 64, 16, .8, .7, math.radians(75), .2, .17, .025, .035))
        for r, n, sides, w, h, theta, spacing, phase, cw, cd in cases:
            values = {'Arch Style': style, 'Width': w, 'Springing Height': h, 'Rise': r, 'Arch Segments': n, 'Came Sides': sides, 'Angle': theta, 'Spacing': spacing, 'Phase': phase, 'Came Width': cw, 'Came Depth': cd, 'Fuse Crossings': False}
            for k, v in values.items():
                set_input(mod, k, v)
            poly, resolved = boundary(style, w, h, r, n)
            region = sample_output(profile, 'Region', values)
            assert len(region['vertices']) == len(poly), (style, len(region['vertices']), len(poly))
            for (x, y, z), (px, py) in zip(region['vertices'], poly):
                assert abs(x - px) < 3e-6 and abs(z - py) < 3e-6 and abs(y) < 1e-6
            assert region['uv']['present'] and region['uv']['finite'] and not region['uv']['zero_area_faces']
            cutter = sample_output(profile, 'Cutter', dict(values, **{'Cutter Depth': .4}))
            volume = shell(cutter)[0]
            assert abs(volume - area(poly) * .4) < 1e-5
            d = data(obj)
            volumes = shell(d, d['ids'])
            expected = expected_bars(poly, w, h, resolved, theta, spacing, phase, cw, cd, sides)
            assert set(volumes) == set(expected), (style, set(volumes) ^ set(expected))
            for key, v in volumes.items():
                assert abs(v - expected[key]) < max(2e-8, expected[key] * .002), (style, key, v, expected[key])
            assert d['uv']['present'] and d['uv']['finite'] and not d['uv']['zero_area_faces'], d['uv']
            report.append(dict(style=style, rise=r, resolved=resolved, segments=n, sides=sides, cames=len(volumes)))
            print('PASS', report[-1], flush=True)
            set_input(mod, 'Fuse Crossings', True)
            fused = data(obj)
            fv = shell(fused, allow_collinear=True)[0]
            assert 0 < fv <= sum(volumes.values()) + 1e-7
            assert fused['uv']['present'] and fused['uv']['finite'] and not fused['uv']['zero_area_faces']
    # Verify a standalone group on an arbitrary host and independent modifier values.
    sibling = bpy.data.objects.new('Independent consumer', bpy.data.meshes.new('Host'))
    bpy.context.collection.objects.link(sibling)
    sibling.modifiers.new('Native recipe', 'NODES').node_group = mod.node_group
    set_input(sibling.modifiers[0], 'Width', 2.)
    assert abs(get_input(mod, 'Width') - values['Width']) < 1e-6
    assert len(data(sibling)['vertices']) > 0
    print(f'PASS: {len(report)} named-profile/cutter/lattice cases, fused checks and independent consumer')

