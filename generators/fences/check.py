"""Independent checks for assets/Fences.blend. Never imports build.py.

Appends the three objects from the saved asset file into a fresh session (their dependencies come
with them) and repeats the studies' measurements: rustic fence islands (029), iron fence rake and
decay (031) and gateway composition (036), plus NL • Path Stations counts directly.

Run: python3 scripts/check.py fences
"""
from pathlib import Path
import math
import sys
import bpy
import bmesh

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from authoring.modifiers import set_input  # noqa: E402

RUSTIC = 'GNL • Rustic Fence'
RUSTIC_CALM = {'Jitter': 0.0, 'Lean': 0.0, 'Height Variation': 0.0, 'Rail Jitter': 0.0}


def rustic_islands(settings):
    obj = bpy.data.objects.new('check fence', bpy.data.meshes.new('check fence'))
    bpy.context.scene.collection.objects.link(obj)
    mod = obj.modifiers.new('fence', 'NODES')
    mod.node_group = bpy.data.node_groups[RUSTIC]
    for key, value in settings.items():
        set_input(mod, key, value)
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    assert all(e.is_manifold for e in bm.edges), 'every log must be closed'
    parent = list(range(len(bm.verts)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for e in bm.edges:
        a, b = find(e.verts[0].index), find(e.verts[1].index)
        parent[a] = b
    groups = {}
    for v in bm.verts:
        groups.setdefault(find(v.index), []).append(tuple(v.co))
    bm.free()
    evaluated.to_mesh_clear()
    bpy.data.objects.remove(obj)
    parts = list(groups.values())
    # Posts stand: their vertical extent beats their horizontal extent; rails lie down.
    def extent(part, axis):
        return max(p[axis] for p in part) - min(p[axis] for p in part)
    posts = [p for p in parts if extent(p, 2) > max(extent(p, 0), extent(p, 1))]
    rails = [p for p in parts if p not in posts]
    return posts, rails


def centre(part):
    return tuple(sum(p[k] for p in part) / len(part) for k in range(3))


def rustic_curve(points, cyclic):
    data = bpy.data.curves.new('check path', 'CURVE')
    data.dimensions = '3D'
    spline = data.splines.new('POLY')
    spline.points.add(len(points) - 1)
    for p, co in zip(spline.points, points):
        p.co = (*co, 1)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new('check path', data)
    bpy.context.scene.collection.objects.link(obj)
    return obj


IRON = 'GNL • Iron Fence'
TOP = 2.0 + .3 + .6 * .13 + .13          # default bar height + post above + ball settle + ball


def iron_parts(settings):
    obj = bpy.data.objects.new('check fence', bpy.data.meshes.new('check fence'))
    bpy.context.scene.collection.objects.link(obj)
    mod = obj.modifiers.new('fence', 'NODES')
    mod.node_group = bpy.data.node_groups[IRON]
    for key, value in settings.items():
        set_input(mod, key, value)
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    parent = list(range(len(bm.verts)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for e in bm.edges:
        parent[find(e.verts[0].index)] = find(e.verts[1].index)
    groups = {}
    for v in bm.verts:
        groups.setdefault(find(v.index), []).append(tuple(v.co))
    bm.free()
    evaluated.to_mesh_clear()
    bpy.data.objects.remove(obj)
    return list(groups.values())


def ext(part, axis):
    return max(p[axis] for p in part) - min(p[axis] for p in part)


def balls(ps, top=TOP):
    return [p for p in ps if abs(max(q[2] for q in p) - top) < 1e-4]


def rails(ps, min_len=1.0):
    return [p for p in ps if math.hypot(ext(p, 0), ext(p, 1)) > min_len]   # pickets and posts are narrow


def iron_ground(slope):
    obj = bpy.data.objects.new('check ground', bpy.data.meshes.new('check ground'))
    obj.data.from_pydata([(-30, -30, -30 * slope), (30, -30, 30 * slope), (30, 30, 30 * slope),
                          (-30, 30, -30 * slope)], [], [(0, 1, 2, 3)])
    bpy.context.scene.collection.objects.link(obj)
    return obj


def iron_path(points, cyclic):
    data = bpy.data.curves.new('check path', 'CURVE')
    data.dimensions = '3D'
    spline = data.splines.new('POLY')
    spline.points.add(len(points) - 1)
    for p, co in zip(spline.points, points):
        p.co = (*co, 1)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new('check path', data)
    bpy.context.scene.collection.objects.link(obj)
    return obj


GATEWAY = 'GNL • Gateway'
TOP = .5 + 2.6 + .3          # plinth + shaft + cap at the defaults


def gateway_eval(settings):
    obj = bpy.data.objects.new('check gateway', bpy.data.meshes.new('check gateway'))
    bpy.context.scene.collection.objects.link(obj)
    mod = obj.modifiers.new('gateway', 'NODES')
    mod.node_group = bpy.data.node_groups[GATEWAY]
    materials = {'Brick': 'GNL • Brick • Clay', 'Mortar': 'GNL • Mortar', 'Quoin': 'GNL • Stone • Dressed',
                 'Stone': 'GNL • Stone • Plinth and Cap', 'Iron': 'GNL • Iron • Forged', 'Rust': 'GNL • Iron • Rusted'}
    for key, name in materials.items():
        set_input(mod, key, bpy.data.materials[name])
    for key, value in settings.items():
        set_input(mod, key, value)
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    verts = [tuple(v.co) for v in mesh.vertices]
    mats = {mesh.materials[p.material_index].name for p in mesh.polygons if mesh.materials[p.material_index]}
    evaluated.to_mesh_clear()
    bpy.data.objects.remove(obj)
    return verts, mats


def check_stations():
    """Path Stations alone: counts for a straight run, an open path and a closed loop."""
    def count(settings, path=None):
        g = bpy.data.node_groups.new('probe', 'GeometryNodeTree')
        g.is_modifier = True
        g.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
        node = g.nodes.new('GeometryNodeGroup')
        node.node_tree = bpy.data.node_groups['GNL • Path Stations']
        for key, value in settings.items():
            node.inputs[key].default_value = value
        if path is not None:
            info = g.nodes.new('GeometryNodeObjectInfo')
            info.inputs['Object'].default_value = path
            g.links.new(info.outputs['Geometry'], node.inputs['Path'])
        verts = g.nodes.new('GeometryNodePointsToVertices')
        g.links.new(node.outputs['Stations'], verts.inputs[0])
        g.links.new(verts.outputs[0], g.nodes.new('NodeGroupOutput').inputs[0])
        obj = bpy.data.objects.new('probe', bpy.data.meshes.new('probe'))
        bpy.context.scene.collection.objects.link(obj)
        obj.modifiers.new('p', 'NODES').node_group = g
        bpy.context.view_layer.update()
        n = len(obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh().vertices)
        bpy.data.objects.remove(obj)
        bpy.data.node_groups.remove(g)
        return n
    assert count({'Run Length': 9.0, 'Spacing': 3.0}) == 4
    assert count({'Run Length': 10.0, 'Spacing': 2.4}) == 5
    assert count({'Spacing': 2.0}, rustic_curve([(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)], True)) == 12
    assert count({'Spacing': 2.0}, rustic_curve([(0, 0, 0), (4, 0, 0), (4, 4, 0)], False)) == 5
    return 4


def check_rustic():
    cases = 0

    # Straight runs: posts = bays + 1, rails = bays × count; exact stations and heights when calm.
    for run, bay, rails_n, height, bury in [(9.6, 2.4, 3, 1.65, .1), (10.0, 3.0, 2, 1.2, .3), (2.0, 2.4, 1, 1.0, 0.0)]:
        posts, rails = rustic_islands({**RUSTIC_CALM, 'Run Length': run, 'Bay Length': bay, 'Rail Count': rails_n,
                                'Post Height': height, 'Bury': bury})
        bays = max(1, round(run / bay))
        assert len(posts) == bays + 1 and len(rails) == bays * rails_n, (run, bay, len(posts), len(rails))
        xs = sorted(centre(p)[0] for p in posts)
        for k, x in enumerate(xs):
            assert abs(x - (-run / 2 + k * run / bays)) < .06, (run, k, x)   # timber bow shifts centroids slightly
        for p in posts:
            zs = [q[2] for q in p]
            assert abs(min(zs) + bury) < 1e-5 and abs(max(zs) - height) < 1e-5, (min(zs), max(zs))
        cases += 1

    # Closed path: no duplicate post at the seam, one bay per post.
    square = rustic_curve([(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)], True)
    posts, rails = rustic_islands({**RUSTIC_CALM, 'Path': square, 'Bay Length': 2.0, 'Rail Count': 2})
    assert len(posts) == 12 and len(rails) == 24, (len(posts), len(rails))
    for p in posts:
        x, y, _ = centre(p)
        assert abs(max(abs(x), abs(y)) - 3) < .06, (x, y)   # every post on the square
    cases += 1
    open_path = rustic_curve([(0, 0, 0), (4, 0, 0), (4, 4, 0)], False)
    posts, rails = rustic_islands({**RUSTIC_CALM, 'Path': open_path, 'Bay Length': 2.0, 'Rail Count': 3})
    assert len(posts) == 5 and len(rails) == 12, (len(posts), len(rails))
    cases += 1

    # Ground: every post bottom sits Bury below a plane at z = 0.7.
    plane = bpy.data.objects.new('check ground', bpy.data.meshes.new('check ground'))
    plane.data.from_pydata([(-20, -20, .7), (20, -20, .7), (20, 20, .7), (-20, 20, .7)], [], [(0, 1, 2, 3)])
    bpy.context.scene.collection.objects.link(plane)
    posts, _ = rustic_islands({**RUSTIC_CALM, 'Ground': plane, 'Bury': .2})
    assert posts and all(abs(min(q[2] for q in p) - .5) < 1e-5 for p in posts)
    cases += 1

    # Decay: rails vanish or drop; the intact layout never moves when only the decay changes.
    base_posts, base_rails = rustic_islands({})
    gone_posts, gone_rails = rustic_islands({'Missing Rails': 1.0})
    assert not gone_rails and gone_posts == base_posts, 'Missing 1.0 removes every rail, keeps posts'
    some_posts, some_rails = rustic_islands({'Missing Rails': .4, 'Decay Seed': 3})
    other_posts, other_rails = rustic_islands({'Missing Rails': .4, 'Decay Seed': 4})
    assert 0 < len(some_rails) < len(base_rails) and some_posts == other_posts == base_posts
    cases += 2
    _, dropped = rustic_islands({**RUSTIC_CALM, 'Dropped Rails': 1.0, 'Rail Diameter': .16})
    assert dropped and all(min(q[2] for q in r) < .16 for r in dropped), 'each dropped rail touches down'
    cases += 1

    # Seeds: the same seed reproduces; a new seed changes the logs and layout.
    a, b, c = rustic_islands({'Seed': 9}), rustic_islands({'Seed': 9}), rustic_islands({'Seed': 10})
    assert a == b and a != c
    cases += 1

    return cases


def check_iron():
    cases = 0
    # Straight runs: posts = bays + 1 at even stations; two rails per panel, each Clearance short.
    for run, spacing in [(9.0, 3.0), (10.0, 2.4), (2.0, 3.0)]:
        ps = iron_parts({'Run Length': run, 'Post Spacing': spacing})
        bays = max(1, round(run / spacing))
        b = balls(ps)
        assert len(b) == bays + 1, (run, len(b))
        xs = sorted(sum(q[0] for q in p) / len(p) for p in b)
        assert all(abs(x - (-run / 2 + k * run / bays)) < 1e-4 for k, x in enumerate(xs)), xs
        r = rails(ps, min_len=.5)
        assert len(r) == 2 * bays, (run, len(r))
        assert all(abs(ext(p, 0) - (run / bays - .12)) < 1e-4 for p in r), 'panel = bay − clearance'
        cases += 1
    # Closed square: one post per bay, no seam duplicate.
    square = iron_path([(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)], True)
    ps = iron_parts({'Path': square, 'Post Spacing': 2.0})
    assert len(balls(ps)) == 12 and len(rails(ps, .5)) == 24
    cases += 1
    # Rake vs step on a tilted plane (z = 0.2·x): raked rails rise with the ground; stepped ones are level.
    tilt = iron_ground(.2)
    raked = rails(iron_parts({'Ground': tilt, 'Run Length': 9.0, 'Post Spacing': 3.0}), .5)
    stepped = rails(iron_parts({'Ground': tilt, 'Run Length': 9.0, 'Post Spacing': 3.0, 'Follow Slope': False}), .5)
    run = 3.0
    panel = run - .12
    assert raked and all(abs(ext(p, 2) - (.1 + .2 * panel)) < 1e-4 for p in raked), [ext(p, 2) for p in raked]
    assert stepped and all(abs(ext(p, 2) - .1) < 1e-4 for p in stepped), [ext(p, 2) for p in stepped]
    for p in raked:   # each raked rail meets its two posts' ground heights (+ its own height above them)
        lo = min(p, key=lambda q: q[0])
        hi = max(p, key=lambda q: q[0])
        assert abs((hi[2] - lo[2]) - .2 * (hi[0] - lo[0])) < .02, 'rail follows the slope'
    cases += 2
    # Decay: derelict panels never move posts; with Derelict 0 nothing is derelict whatever the seed.
    base = iron_parts({})
    calm_a, calm_b = iron_parts({'Decay Seed': 3}), iron_parts({'Decay Seed': 9})
    assert calm_a == calm_b == base, 'no derelict panels: decay seed changes nothing'
    ruined = iron_parts({'Derelict Panels': 1.0, 'Decay Seed': 3})
    assert sorted(map(sorted, balls(ruined))) == sorted(map(sorted, balls(base))) and ruined != base
    cases += 2
    a, b = iron_parts({'Derelict Panels': .5, 'Decay Seed': 5}), iron_parts({'Derelict Panels': .5, 'Decay Seed': 5})
    assert a == b, 'decay is reproducible'
    cases += 1
    return cases


def check_gateway():
    cases = 0
    closed = {'Swing Left': 0.0, 'Swing Right': 0.0}
    for width, pier in ((3.0, .9), (4.2, 1.1), (2.0, .6)):
        verts, _ = gateway_eval({**closed, 'Opening Width': width, 'Pier Width': pier, 'Crown': 'None'})
        arch = [v for v in verts if v[2] > TOP + 1e-3]
        xs = [v[0] for v in arch]
        span = width + pier
        assert abs((max(xs) - min(xs)) - (span + 2 * .05)) < 1e-3, ('overthrow spans pier centres', width, max(xs) - min(xs))
        legs = [v for v in verts if abs(v[2] - TOP) < 1e-5 and abs(abs(v[0]) - span / 2) < .051]
        assert legs, 'the overthrow legs land on the pier tops'
        # Closed leaves stay between the pier faces, inset by their hinge gap.
        leaves = [v for v in verts if v[2] < 2.9 and abs(v[0]) < width / 2 + 1e-6 and abs(v[1]) < .2]
        assert leaves and max(abs(v[0]) for v in leaves) <= width / 2 - .02 + .05, 'leaves hang inside the opening'
        cases += 1
    # Swing: the free end of the left leaf turns about its hinge by exactly Swing Left.
    for angle in (20, 45, 80):
        verts, _ = gateway_eval({'Swing Left': math.radians(angle), 'Swing Right': 0.0})
        hinge = (-1.5, 0.0)
        left = [v for v in verts if v[2] < 2.9 and v[0] > -1.5 - 1e-6 and v[0] < 0 and v[1] > -.05 and abs(v[1]) < 1.6]
        tip = max(left, key=lambda v: math.hypot(v[0] - hinge[0], v[1] - hinge[1]))
        measured = math.degrees(math.atan2(tip[1] - hinge[1], tip[0] - hinge[0]))
        assert abs(measured - angle) < 2.0, ('leaf swings by its angle', angle, measured)
        cases += 1
    # Ruin 0: the decay seed changes nothing. Ruin: fewer bricks, rust, and the composition holds.
    a, _ = gateway_eval({'Decay Seed': 1})
    b, _ = gateway_eval({'Decay Seed': 9})
    assert a == b, 'no ruin: seed is inert'
    ruined, mats = gateway_eval({'Ruin': .9, 'Decay Seed': 3})
    _, fresh_mats = gateway_eval({})
    assert len(ruined) < len(a), 'ruin removes material'
    assert 'GNL • Iron • Rusted' in mats and 'GNL • Iron • Rusted' not in fresh_mats, 'ruined iron rusts'
    assert 'GNL • Iron • Forged' in fresh_mats and 'GNL • Brick • Clay' in fresh_mats
    cases += 2
    return cases


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mine = bpy.data.objects.new('My object', bpy.data.meshes.new('mine'))
    bpy.context.scene.collection.objects.link(mine)
    names = ['GNL • Rustic Fence', 'GNL • Iron Fence', 'GNL • Gateway']
    with bpy.data.libraries.load(str(ROOT / 'assets/Fences.blend'), link=False, assets_only=True) as (src, dst):
        assert sorted(src.objects) == sorted(names), src.objects
        assert {*names, 'GNL • Path Stations'} <= set(src.node_groups), src.node_groups
        dst.objects = list(names)
        dst.node_groups = ['GNL • Path Stations']
    for obj in dst.objects:
        bpy.context.scene.collection.objects.link(obj)
    assert bpy.data.objects.get(mine.name) is mine and not bpy.data.texts
    for dependency in ('GNL • Hewn Timber', 'GNL • Panel', 'GNL • Post', 'GNL • Overthrow', 'GNL • Brick Pier'):
        assert dependency in bpy.data.node_groups, f'{dependency} travels with the fences'
    cases = 1 + check_stations() + check_rustic() + check_iron() + check_gateway()
    print(f'Fences: {cases} cases passed')


main()
