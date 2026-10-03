"""Independent checks for assets/Timber.blend. Never imports build.py.

Appends from the saved asset file into a fresh session, then measures each warp exactly
(randomization off), the hewn timber's taper and frustum volume, seeds and the shipped objects.

Run: python3 scripts/check.py timber
"""
from pathlib import Path
import math
import bpy
import bmesh

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT))
from authoring.naming import PREFIX  # noqa: E402
ASSET = ROOT / 'assets/Timber.blend'
P = PREFIX


def evaluate(group, settings):
    """Run one member group with settings; return (vertex positions, closed?, volume, attribute names)."""
    g = bpy.data.node_groups.new('check probe', 'GeometryNodeTree')
    g.is_modifier = True
    g.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    node = g.nodes.new('GeometryNodeGroup')
    node.node_tree = bpy.data.node_groups[f'{P} {group}']
    for key, value in settings.items():
        node.inputs[key].default_value = value
    g.links.new(node.outputs[0], g.nodes.new('NodeGroupOutput').inputs[0])
    obj = bpy.data.objects.new('check probe', bpy.data.meshes.new('check probe'))
    bpy.context.scene.collection.objects.link(obj)
    obj.modifiers.new('probe', 'NODES').node_group = g
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    result = ([tuple(v.co) for v in mesh.vertices], all(e.is_manifold for e in bm.edges),
              bm.calc_volume(signed=True), {a.name for a in mesh.attributes})
    bm.free()
    evaluated.to_mesh_clear()
    bpy.data.objects.remove(obj)
    bpy.data.node_groups.remove(g)
    return result


FLAT = {'Edge Roughness': 0.0, 'End Skew': 0.0, 'Bow': 0.0, 'Crook': 0.0, 'Cup': 0.0, 'Twist': 0.0,
        'Surface': 0.0, 'Randomize Warp': False, 'Length': 2.0, 'Width': .4, 'Thickness': .1,
        'Length Segments': 20, 'Width Segments': 4}


def nearest(verts, target):
    return min(verts, key=lambda p: math.dist(p[:1], target[:1]) * 10 + math.dist(p[1:], target[1:]))


def check_plank():
    cases = 0
    verts, closed, volume, attrs = evaluate('Weathered Plank', FLAT)
    assert closed and abs(volume - 2 * .4 * .1) < 1e-6, f'flat board: closed={closed} volume={volume}'
    assert {'UVMap', 'grain'} <= attrs
    cases += 1
    # Each warp alone, measured where it is defined.
    for warp, amount, probe, axis, expected in [
            ('Bow', .12, (0, 0, .05), 2, .05 + .12),       # mid-length, top center rises by Bow
            ('Crook', .07, (0, .2, .05), 1, .2 + .07),      # mid-length, edge moves sideways by Crook
            ('Cup', .02, (0, .2, .05), 2, .05 + .02)]:      # mid-length edge lifts by Cup
        verts, closed, _, _ = evaluate('Weathered Plank', {**FLAT, warp: amount})
        # Find the vertex that started at `probe`: same X, and the extreme along the warp direction.
        column = [p for p in verts if abs(p[0] - probe[0]) < 1e-6]
        value = max(p[axis] for p in column)
        assert closed and abs(value - expected) < 1e-6, f'{warp}: {value} != {expected}'
        cases += 1
    twist = math.radians(30)
    verts, closed, _, _ = evaluate('Weathered Plank', {**FLAT, 'Twist': twist})
    end = [p for p in verts if abs(p[0] - 1.0) < 1e-6]
    # The end section is the original 5×2 grid of (y, z) rotated by half the twist.
    c, s_ = math.cos(twist / 2), math.sin(twist / 2)
    expected = [(y * c - z * s_, y * s_ + z * c) for y in (-.2, -.1, 0, .1, .2) for z in (-.05, .05)]
    got = [(y, z) for _, y, z in end]
    assert closed and len(got) == 10 and all(min(math.dist(e, g) for g in got) < 1e-6 for e in expected), \
        f'twist: {got}'
    cases += 1
    # Seeds: deterministic, distinct, and closed with everything on.
    a = evaluate('Weathered Plank', {'Seed': 5})
    b = evaluate('Weathered Plank', {'Seed': 5})
    c = evaluate('Weathered Plank', {'Seed': 6})
    assert a[0] == b[0] and a[0] != c[0] and a[1] and c[1], 'plank seeds'
    cases += 1
    return cases


def check_timber():
    cases = 0
    flat = {'Facet Variation': 0.0, 'Irregularity': 0.0, 'Bow': 0.0, 'Twist': 0.0, 'Randomize Warp': False}
    for L, D, taper, facets, rings in [(2, .25, .1, 7, 8), (3.5, .4, 0, 4, 1), (1, .1, .5, 12, 3)]:
        s = {**flat, 'Length': L, 'Diameter': D, 'Taper': taper, 'Facets': facets, 'Rings': rings}
        verts, closed, volume, attrs = evaluate('Hewn Timber', s)
        assert closed and {'UVMap', 'grain'} <= attrs, s
        zs = sorted({round(z, 6) for _, _, z in verts})
        assert abs(zs[0]) < 1e-6 and abs(zs[-1] - L) < 1e-6 and len(zs) == rings + 1, (s, zs)
        for x, y, z in verts:
            r = D / 2 * (1 + taper * (1 - z / L))
            assert abs(math.hypot(x, y) - r) < 1e-5, (s, x, y, z)
        # Exact volume of a polygonal frustum.
        area = lambda R: facets / 2 * R * R * math.sin(math.tau / facets)
        a1, a2 = area(D / 2 * (1 + taper)), area(D / 2)
        assert abs(volume - L / 3 * (a1 + a2 + math.sqrt(a1 * a2))) < 1e-5, (s, volume)
        cases += 1
    bow = .2
    verts, _, _, _ = evaluate('Hewn Timber', {**flat, 'Bow': bow, 'Length': 2.0, 'Diameter': .2, 'Taper': 0.0})
    mid = [x for x, y, z in verts if abs(z - 1.0) < 1e-6]
    # A regular ring's vertices average to its center, so the mid-length ring's mean X is the bow.
    assert mid and abs(sum(mid) / len(mid) - bow) < 1e-5, mid
    cases += 1
    a, b, c = (evaluate('Hewn Timber', {'Seed': s}) for s in (3, 3, 4))
    assert a[0] == b[0] and a[0] != c[0] and a[1] and c[1], 'timber seeds'
    cases += 1
    return cases


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mine = bpy.data.objects.new('My object', bpy.data.meshes.new('mine'))
    bpy.context.scene.collection.objects.link(mine)
    with bpy.data.libraries.load(str(ASSET), link=False, assets_only=True) as (src, dst):
        assert sorted(src.objects) == [f'{P} Hewn Timber', f'{P} Weathered Plank'], src.objects
        assert {f'{P} Hewn Timber', f'{P} Weathered Plank'} <= set(src.node_groups), src.node_groups
        assert len(src.materials) == 3, src.materials
        dst.objects = list(src.objects)
        dst.node_groups = [f'{P} Hewn Timber', f'{P} Weathered Plank']
    for obj in dst.objects:
        bpy.context.scene.collection.objects.link(obj)
    assert bpy.data.objects.get(mine.name) is mine and not bpy.data.texts
    cases = 1
    for name in ('Weathered Plank', 'Hewn Timber'):
        group = bpy.data.node_groups[f'{P} {name}']
        panels = [i.name for i in group.interface.items_tree if i.item_type == 'PANEL']
        assert panels == ['Size', 'Resolution', 'Variation', 'Warp'], (name, panels)
        obj = bpy.data.objects[f'{P} {name}']
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        bm = bmesh.new()
        bm.from_mesh(mesh)
        assert all(e.is_manifold for e in bm.edges) and bm.calc_volume() > 0, name
        assert any(mesh.materials) and 'grain' in mesh.attributes, name
        bm.free()
        evaluated.to_mesh_clear()
        cases += 1
    cases += check_plank() + check_timber()
    print(f'Timber: {cases} cases passed')


main()
