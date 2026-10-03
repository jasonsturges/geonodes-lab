"""Independent checks for assets/Vessels.blend. Never imports the builder.

The oracle transcribes three-low-poly vesselProfiles.ts to plain Python. Silhouettes, shells and liquid
sections are compared point for point; each shipped object is checked for closure, UVs and the exact
N-gon lathe volume; the bare Vessel group is composed with a user's own NURBS curve.

Run: python3 scripts/check.py vessels
"""
from pathlib import Path
import math
import sys
import bpy
import bmesh

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from authoring.checking import evaluate_object, fresh_session_with, report  # noqa: E402
from authoring.modifiers import get_input, set_input  # noqa: E402
from authoring.naming import PREFIX as P  # noqa: E402

TOL = 1e-4


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def florence(R=1.0, nr=0.2, nh=1.5, seg=32):
    top = math.asin(clamp(nr / R, 0, 1))
    pts = [(R * math.sin(math.pi - (math.pi - top) * i / seg), R * math.cos(math.pi - (math.pi - top) * i / seg) + R)
           for i in range(seg + 1)]
    return pts + [(nr, pts[-1][1] + nh)]


def erlenmeyer(R=1.0, nr=0.3, bh=2.5, nh=1.0):
    return [(0, 0), (R * .875, 0), (R, bh * .04), (nr, bh), (nr, bh + nh)]


def test_tube(r=0.2, h=3.0, seg=16):
    pts = [(r * math.sin(math.pi - math.pi / 2 * i / seg), r * math.cos(math.pi - math.pi / 2 * i / seg) + r)
           for i in range(seg + 1)]
    return pts + [(r, h)]


def graduated(r=0.35, h=3.0, frf=1.5, fhf=.08):
    fr, fh = r * frf, h * fhf
    return [(0, 0), (fr, 0), (fr, fh * .5), (r, fh), (r, h)]


def pipette(r=0.1, h=3.0, tf=.22):
    return [(0, 0), (r, h * tf), (r, h)]


def apothecary(R=1.5, bf=.8, nf=.4, h=3.5):
    return [(0, 0), (R * bf, 0), (R * .98, h * .25), (R, h * .5), (R * .74, h * .78), (R * nf, h)]


def potion(R=1.0, bf=.7, nf=.4, h=2.6):
    return [(0, 0), (R * bf, 0), (R, h * .45), (R * .7, h * .64), (R * nf, h * .8), (R * nf, h)]


def wine(R=.5, nr=.18, h=3.0, nh=.9, sh=.5, seg=6):
    top = max(0, h - nh - sh)
    pts = [(0, 0), (R, 0)]
    pts += [(nr + (R - nr) * math.cos(i / seg * math.pi / 2), top + sh * math.sin(i / seg * math.pi / 2))
            for i in range(seg + 1)]
    return pts + [(nr, h)]


def offset_inward(profile, t):
    out = []
    for i, (x, y) in enumerate(profile):
        px, py = profile[max(0, i - 1)]
        nx, ny = profile[min(len(profile) - 1, i + 1)]
        tx, ty = nx - px, ny - py
        length = math.hypot(tx, ty) or 1
        tx, ty = tx / length, ty / length
        # SDK clamps at 0.0005; the graph clamps at 0 and keeps axis points on the axis.
        out.append((0.0 if x <= 1e-6 else max(0.0, x - ty * t), y + tx * t))
    return out


def vessel_shell(sil, thickness=0.0, rim=0.1, rounded=True, seg=6):
    rx, ry = sil[-1]
    if thickness > 1e-6:
        t = min(thickness, rx * .8)
        inner = offset_inward(sil, t)
        bead = []
        if rounded:
            ix, iy = inner[-1]
            cx, cy = (rx + ix) / 2, (ry + iy) / 2
            r = math.hypot(rx - ix, ry - iy) / 2 or 1e-4
            a0 = math.atan2(ry - cy, rx - cx)
            bead = [(cx + r * math.cos(a0 + math.pi * i / seg), cy + r * math.sin(a0 + math.pi * i / seg))
                    for i in range(1, seg)]
        return sil + bead + inner[::-1]
    if rim <= 0:
        return sil[:-1] + [(rx, ry)]
    b = min(rim, .9) * rx / 2
    return sil[:-1] + [(rx - b + b * math.cos(math.pi * i / seg), ry + b * math.sin(math.pi * i / seg))
                       for i in range(seg + 1)]


def fill_profile(shell, fill, inset=.03):
    base, top = min(p[1] for p in shell), max(p[1] for p in shell)
    rmax = max(p[0] for p in shell)
    level = base + (top - base) * clamp(fill, 0, 1)
    if level <= base:
        return []
    inner = offset_inward(shell, clamp(inset, 0, .5) * (rmax or 1))
    if level <= inner[0][1] + 1e-6:
        return []
    pts = [(0, inner[0][1])] if inner[0][0] > 1e-6 else []
    for i, p in enumerate(inner):
        if p[1] <= level:
            pts.append(p)
            continue
        if i > 0:
            q = inner[i - 1]
            span = p[1] - q[1]
            if span > 1e-6:
                t = (level - q[1]) / span
                pts.append((q[0] + (p[0] - q[0]) * t, level))
        break
    if pts[-1][0] > 1e-6:
        pts.append((0, pts[-1][1]))
    return pts if len(pts) >= 2 else []


ORACLES = {
    'Florence Flask': (florence, ['Body Radius', 'Neck Radius', 'Neck Height', 'Profile Segments'],
                       [(1.0, .2, 1.5, 32), (1.4, .35, .8, 12)]),
    'Erlenmeyer Flask': (erlenmeyer, ['Body Radius', 'Neck Radius', 'Body Height', 'Neck Height'],
                         [(1.0, .3, 2.5, 1.0), (.7, .15, 1.8, .6)]),
    'Test Tube': (test_tube, ['Radius', 'Height', 'Profile Segments'], [(.2, 3.0, 16), (.35, 2.0, 5)]),
    'Graduated Cylinder': (graduated, ['Radius', 'Height', 'Foot Radius Factor', 'Foot Height Factor'],
                           [(.35, 3.0, 1.5, .08), (.5, 4.0, 2.0, .05)]),
    'Pipette': (pipette, ['Radius', 'Height', 'Tip Length Factor'], [(.1, 3.0, .22), (.2, 2.0, .4)]),
    'Apothecary Jar': (apothecary, ['Radius', 'Base Radius Factor', 'Neck Radius Factor', 'Height'],
                       [(1.5, .8, .4, 3.5), (1.0, .6, .55, 2.2)]),
    'Potion Bottle': (potion, ['Radius', 'Base Radius Factor', 'Neck Radius Factor', 'Height'],
                      [(1.0, .7, .4, 2.6), (.8, .9, .3, 3.0)]),
    'Wine Bottle': (wine, ['Radius', 'Neck Radius', 'Height', 'Neck Height', 'Shoulder Height', 'Shoulder Segments'],
                    [(.5, .18, 3.0, .9, .5, 6), (.45, .15, 3.4, 1.1, .3, 1)]),
}


# ---------------------------------------------------------------------------
# Evaluate node groups in the saved study.
# ---------------------------------------------------------------------------

def section_points(chain):
    """Evaluate a chain of groups ending in a curve and return its (x, z) points in order."""
    g = bpy.data.node_groups.new('check probe', 'GeometryNodeTree')
    g.is_modifier = True
    g.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    previous = None
    for name, settings in chain:
        node = g.nodes.new('GeometryNodeGroup')
        node.node_tree = bpy.data.node_groups[name]
        for key, value in settings.items():
            node.inputs[key].default_value = value
        if previous is not None:
            g.links.new(previous, node.inputs[0])
        previous = node.outputs[0]
    points = g.nodes.new('GeometryNodeCurveToPoints')
    points.mode = 'EVALUATED'
    g.links.new(previous, points.inputs[0])
    verts = g.nodes.new('GeometryNodePointsToVertices')
    g.links.new(points.outputs[0], verts.inputs[0])
    g.links.new(verts.outputs[0], g.nodes.new('NodeGroupOutput').inputs[0])
    obj = bpy.data.objects.new('check probe', bpy.data.meshes.new('check probe'))
    bpy.context.scene.collection.objects.link(obj)
    obj.modifiers.new('probe', 'NODES').node_group = g
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    result = [(v.co.x, v.co.z) for v in mesh.vertices]
    assert all(abs(v.co.y) < 1e-6 for v in mesh.vertices), 'profile left the XZ plane'
    evaluated.to_mesh_clear()
    bpy.data.objects.remove(obj)
    bpy.data.node_groups.remove(g)
    return result


def same(actual, expected, what):
    assert len(actual) == len(expected), f'{what}: {len(actual)} points, expected {len(expected)}'
    for k, (a, e) in enumerate(zip(actual, expected)):
        assert math.dist(a, e) < TOL, f'{what}: point {k} {a} != {e}'


def lathe_volume(section, n):
    """Exact volume of a closed (radius, height) loop spun as an n-gon."""
    total = 0.0
    loop = section + [section[0]]
    for (r1, z1), (r2, z2) in zip(loop, loop[1:]):
        total += (z2 - z1) * (r1 * r1 + r1 * r2 + r2 * r2) / 3
    return total * n / 2 * math.sin(math.tau / n)


def mesh_report(obj):
    m = evaluate_object(obj)
    uvs = []
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    if mesh.uv_layers:
        uvs = [c for loop in mesh.uv_layers['UVMap'].data for c in loop.uv]
    evaluated.to_mesh_clear()
    return {'open': 0 if m.closed else 1, 'volume': m.volume, 'uv': m.uv_layers,
            'uv range': (min(uvs, default=0), max(uvs, default=0)), 'faces': m.faces}


def main():
    objects = [f'{P} {n}' for n in ORACLES] + [f'{P} Vessel From Curve', f'{P} Vase Profile']
    groups = [f'{P} Vessel', f'{P} Lathe', f'{P} Vessel Shell', f'{P} Liquid Fill'] + \
             [f'{P} Silhouette • {n}' for n in ORACLES]
    loaded = fresh_session_with('Vessels.blend', objects=objects, node_groups=groups)
    for name in objects:
        assert loaded[name].asset_data is not None, f'{name} is an asset'
    cases = 0

    # The public composition group is organised into panels.
    vessel = bpy.data.node_groups[f'{P} Vessel']
    panels = [i.name for i in vessel.interface.items_tree if i.item_type == 'PANEL']
    assert panels == ['Silhouette', 'Glass', 'Liquid', 'Detail'], panels
    outputs = [i.name for i in vessel.interface.items_tree if i.item_type == 'SOCKET' and i.in_out == 'OUTPUT']
    assert outputs == ['Geometry', 'Glass', 'Liquid', 'Glass Section', 'Liquid Section'], outputs
    cases += 1

    for name, (fn, keys, variants) in ORACLES.items():
        group = f'{P} Silhouette • {name}'
        for values in variants:
            settings = dict(zip(keys, values))
            sil = fn(*values)
            same(section_points([(group, settings)]), sil, f'{name} silhouette {values}')
            cases += 1
            for thickness, rim, rounded in [(0.0, .1, True), (.03, .1, True), (.03, .1, False)]:
                same(section_points([(group, settings), (f'{P} Vessel Shell',
                                                         {'Thickness': thickness, 'Rim': rim, 'Rounded Rim': rounded})]),
                     vessel_shell(sil, thickness, rim, rounded), f'{name} shell t={thickness}')
                cases += 1
            for fill in (0.0, .3, .7, 1.0):
                same(section_points([(group, settings), (f'{P} Liquid Fill', {'Fill': fill, 'Inset': .03})]),
                     fill_profile(sil, fill, .03), f'{name} fill={fill}')
                cases += 1

    # Each appended object at its shipped defaults.
    for name, (fn, keys, variants) in ORACLES.items():
        obj = bpy.data.objects[f'{P} {name}']
        mod = obj.modifiers[0]
        value = lambda socket: get_input(mod, socket)
        assert value('Glass Material') and value('Liquid Material'), f'{name}: materials not shipped'
        sil = fn(*[value(k) for k in keys])
        n = value('Radial Segments')
        expected = lathe_volume(vessel_shell(sil, value('Thickness'), value('Rim'), value('Rounded Rim')), n)
        expected += lathe_volume(fill_profile(sil, value('Fill'), value('Fill Inset')), n)
        r = mesh_report(obj)
        assert r['open'] == 0, f'{name}: {r["open"]} open edges'
        assert r['uv'] == ['UVMap'] and -1e-6 <= r['uv range'][0] and r['uv range'][1] <= 1 + 1e-6, f'{name}: {r}'
        assert abs(r['volume'] - expected) < 1e-3 * expected, f'{name}: volume {r["volume"]} != {expected}'
        cases += 1

    # Vessel From Curve with the shipped Bézier profile.
    host = bpy.data.objects[f'{P} Vessel From Curve']
    assert mesh_report(host)['faces'] == 0, 'no curve chosen yet: empty output expected'
    set_input(host.modifiers[0], 'Profile Curve', bpy.data.objects[f'{P} Vase Profile'])
    r = mesh_report(host)
    assert r['open'] == 0 and r['volume'] > 0, f'vessel from curve: {r}'
    cases += 1

    # The node group on its own: a user's mesh object + a user's own curve, composed in their graph.
    data = bpy.data.curves.new('My NURBS', 'CURVE')
    data.dimensions = '3D'
    spline = data.splines.new('NURBS')
    spline.points.add(4)
    for p, (x, z) in zip(spline.points, [(0, 0), (.5, 0), (.7, .8), (.3, 1.6), (.35, 2.0)]):
        p.co = (x, 0, z, 1)
    spline.use_endpoint_u = True
    mine = bpy.data.objects.new('My NURBS', data)
    bpy.context.scene.collection.objects.link(mine)
    g = bpy.data.node_groups.new('My graph', 'GeometryNodeTree')
    g.is_modifier = True
    g.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    info = g.nodes.new('GeometryNodeObjectInfo')
    info.inputs['Object'].default_value = mine
    v = g.nodes.new('GeometryNodeGroup')
    v.node_tree = vessel
    v.inputs['Fill'].default_value = .6
    g.links.new(info.outputs['Geometry'], v.inputs['Silhouette'])
    g.links.new(v.outputs['Glass'], g.nodes.new('NodeGroupOutput').inputs[0])
    obj = bpy.data.objects.new('My vessel', bpy.data.meshes.new('My vessel'))
    bpy.context.scene.collection.objects.link(obj)
    obj.modifiers.new('mine', 'NODES').node_group = g
    r = mesh_report(obj)
    assert r['open'] == 0 and r['volume'] > 0, f'composed NURBS vessel: {r}'
    cases += 1

    report('Vessels', cases)


main()
