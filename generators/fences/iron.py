"""GNL • Iron Fence: iron posts and per-bay panels along any curve, raked to the slope, with seeded
derelict panels (NodesLab study 031; website graveyard Enclosure.ts)."""
import math

import bpy

from authoring.graph import Graph
from authoring.naming import named
from common import rand, unit, foreach, generation, transform, rand1
from stations import stations


IRON_SPEC = [
    ('Path', [('Path', 'NodeSocketObject', None, None, None, 'A curve object (open or closed). Empty = a straight run.'),
              ('Run Length', 'NodeSocketFloat', 9.0, .5, 200.0, 'Straight run length when no Path is set.'),
              ('Post Spacing', 'NodeSocketFloat', 3.0, .5, 20.0, 'Target spacing; posts divide the path evenly.'),
              ('Ground', 'NodeSocketObject', None, None, None, 'Optional mesh: posts and panels follow it.'),
              ('Follow Slope', 'NodeSocketBool', True, None, None, 'Rake panels between their posts; off = level steps.')]),
    ('Panels', [('Bar Height', 'NodeSocketFloat', 2.0, .3, 6.0, ''),
                ('Gap', 'NodeSocketFloat', .3, .0, 2.0, 'Clear air between pickets.'),
                ('Bar Radius', 'NodeSocketFloat', .05, .005, .3, ''),
                ('Sides', 'NodeSocketInt', 4, 3, 16, '4 = square tubing.'),
                ('Rings', 'NodeSocketBool', False, None, None, 'Fitted ring band under the top rail.'),
                ('Clearance', 'NodeSocketFloat', .12, .0, 1.0, 'Each panel is the bay minus this, so rails reach into the posts.')]),
    ('Posts', [('Post Above Panel', 'NodeSocketFloat', .3, .0, 2.0, 'Post shaft height above the bar height.'),
               ('Post Radius', 'NodeSocketFloat', .085, .01, .4, ''),
               ('Ball Radius', 'NodeSocketFloat', .13, .0, .6, ''),
               ('Collar', 'NodeSocketBool', True, None, None, '')]),
    ('Decay', [('Decay Seed', 'NodeSocketInt', 1, 0, 65535, 'Which panels are derelict, and how.'),
               ('Derelict Panels', 'NodeSocketFloat', 0.0, 0.0, 1.0, 'Chance a panel is derelict.'),
               ('Missing Pickets', 'NodeSocketFloat', .12, 0.0, 1.0, 'In a derelict panel.'),
               ('Bent Pickets', 'NodeSocketFloat', .25, 0.0, 1.0, 'In a derelict panel.'),
               ('Sag', 'NodeSocketFloat', 1.0, 0.0, 3.0, 'Scales the drop and lean of derelict panels (website: 0.08 m, 0.06 / 0.045 rad).')]),
    ('Surface', [('Iron', 'NodeSocketMaterial', None, None, None, ''),
                 ('Rust', 'NodeSocketMaterial', None, None, None, 'Derelict panels.')]),
]


def iron_fence_group(panel, post, stations_group):
    G = Graph(named('Iron Fence'), modifier=True)
    G.stations_group = stations_group
    G.input('Geometry', 'NodeSocketGeometry')
    for _, items in IRON_SPEC:
        for name, kind, default, lo, hi, text in items:
            G.input(name, kind, default, lo, hi, text)
    G.output('Geometry')
    G.finish_io()
    i = G.i
    dseed = i['Decay Seed']

    # --- Stations: GNL • Path Stations, no jitter (ironwork is set out true). ---------------------
    posts, closed = stations(G, i, spacing=i['Post Spacing'], jitter=0.0, seed=0)

    # --- Posts: one shared post, instanced (they are identical, so instancing is right here). ----
    one = G.group(post, 'Post')
    G.link(G.add(i['Bar Height'], i['Post Above Panel']), one.inputs['Height'])
    G.link(i['Post Radius'], one.inputs['Radius'])
    G.link(i['Ball Radius'], one.inputs['Ball Radius'])
    G.link(i['Collar'], one.inputs['Collar'])
    inst = G.n('GeometryNodeInstanceOnPoints', 'A post at every station')
    G.link(posts, inst.inputs['Points'])
    G.link(one.outputs[0], inst.inputs['Instance'])
    real = G.n('GeometryNodeRealizeInstances', 'Real posts')
    G.link(inst.outputs[0], real.inputs['Geometry'])
    iron_posts = G.n('GeometryNodeSetMaterial', 'Iron')
    G.link(real.outputs[0], iron_posts.inputs['Geometry'])
    G.link(i['Iron'], iron_posts.inputs['Material'])

    # --- Panels: one per bay, each its own length, decay, rake and pose (For Each zone). ----------
    size = G.n('GeometryNodeAttributeDomainSize', 'Post count', component='POINTCLOUD')
    G.link(posts, size.inputs[0])
    count = size.outputs['Point Count']
    bay_points = G.points(G.sub(count, G.sub(1, closed)), (0, 0, 0))
    zin = G.n('GeometryNodeForeachGeometryElementInput', 'For each bay')
    zout = G.n('GeometryNodeForeachGeometryElementOutput', '… next bay')
    zin.pair_with_output(zout)
    zout.domain = 'POINT'
    G.link(bay_points, zin.inputs['Geometry'])
    k = zin.outputs['Index']
    pa = G.sample(posts, G.position(), k)
    pb = G.sample(posts, G.position(), G.m('FLOORED_MODULO', G.add(k, 1), count))
    ax, ay, az = G.sep(pa)
    bx, by, bz = G.sep(pb)
    dx, dy = G.sub(bx, ax), G.sub(by, ay)
    run = G.v('LENGTH', G.xyz(dx, dy, 0))
    yaw = G.m('ARCTAN2', dy, dx)
    derelict = G.m('LESS_THAN', unit(G, k, 1, dseed), i['Derelict Panels'])
    pan = G.group(panel, 'Panel')
    G.link(G.sub(run, i['Clearance']), pan.inputs['Length'])
    for name in ('Bar Height', 'Gap', 'Bar Radius', 'Sides', 'Rings'):
        G.link(i[name], pan.inputs[name])
    G.link(G.add(G.mul(dseed, 97), k), pan.inputs['Decay Seed'])
    G.link(G.mul(derelict, i['Missing Pickets']), pan.inputs['Missing Pickets'])
    G.link(G.mul(derelict, i['Bent Pickets']), pan.inputs['Bent Pickets'])
    geometry = pan.outputs['Mesh']
    # Rake: lift each vertex along the run so the panel meets both posts; pickets stay vertical.
    rise = G.sub(bz, az)
    x, y, z = G.sep(G.position())
    raked = G.xyz(x, y, G.add(z, G.mul(G.div(x, G.hi(run, 1e-6)), rise)))
    geometry = G.switch('GEOMETRY', i['Follow Slope'], geometry, G.set_position(geometry, raked))
    # Derelict pose (website Enclosure): dropped and leaning out, about the panel's own centre.
    sag = G.mul(derelict, i['Sag'])
    sign = G.switch('FLOAT', G.m('GREATER_THAN', rand(G, k, 2, dseed), 0), -1.0, 1.0)
    geometry = transform(G, geometry, translation=G.xyz(0, 0, G.mul(sag, -.08)),
                         rotation=G.xyz(G.mul(G.mul(sag, .06), sign), 0, G.mul(sag, .045)), label='Sag')
    base = G.switch('FLOAT', i['Follow Slope'], G.lo(az, bz), G.mul(G.add(az, bz), .5))
    geometry = transform(G, geometry, translation=G.xyz(G.mul(G.add(ax, bx), .5), G.mul(G.add(ay, by), .5), base),
                         rotation=G.xyz(0, 0, yaw), label='Into the bay')
    mat = G.n('GeometryNodeSetMaterial', 'Iron or rust')
    G.link(geometry, mat.inputs['Geometry'])
    G.link(G.switch('MATERIAL', derelict, i['Iron'], i['Rust']), mat.inputs['Material'])
    G.link(mat.outputs[0], next(s for s in zout.inputs if s.identifier == 'Generation_0'))
    panels = zout.outputs[2]

    G.link(G.join(iron_posts.outputs[0], panels), G.o['Geometry'])
    G.layout()
    for title, items in IRON_SPEC:
        group_panel = G.g.interface.new_panel(name=title, default_closed=title == 'Decay')
        for name, *_ in items:
            G.g.interface.move_to_parent(G.g.interface.items_tree[name], group_panel, 100)
    G.g.description = 'Wrought-iron fence along any curve: iron posts, raked panels, seeded derelict panels.'
    return G.g
