"""GNL • Path Stations: evenly spaced stations along any curve (open or closed) or a straight run,
with tangent and side directions, optional jitter, and a drop onto a ground mesh. Shared by both fences."""
import math

import bpy

from authoring.graph import Graph
from authoring.naming import named
from common import rand, unit, foreach, generation, transform, rand1


def path_stations_group():
    """Evenly spaced stations along a curve (or a straight run), jittered and dropped onto ground."""
    G = Graph(named('Path Stations'))
    G.input('Path', 'NodeSocketGeometry', description='A curve (open or closed). Empty = a straight run along X.')
    G.input('Run Length', 'NodeSocketFloat', 9.0, .1, 500.0, 'Straight run length when Path is empty.')
    G.input('Spacing', 'NodeSocketFloat', 2.4, .05, 100.0, 'Target spacing; stations divide the path evenly.')
    G.input('Ground', 'NodeSocketGeometry', description='Optional mesh: each station drops straight down onto it.')
    G.input('Jitter', 'NodeSocketFloat', 0.0, 0.0, 10.0, 'Seeded stray along the run, and 0.6× across it.')
    G.input('Seed', 'NodeSocketInt', 0, 0, 65535)
    G.output('Stations')
    G.output('Closed', 'NodeSocketBool')
    G.output('Count', 'NodeSocketInt')
    G.finish_io()
    i = G.i
    line = G.n('GeometryNodeCurvePrimitiveLine', 'Straight run')
    half = G.mul(i['Run Length'], .5)
    G.link(G.xyz(G.mul(half, -1), 0, 0), line.inputs['Start'])
    G.link(G.xyz(half, 0, 0), line.inputs['End'])
    path = G.switch('GEOMETRY', G.m('GREATER_THAN', G.point_count(i['Path']), 0), line.outputs['Curve'], i['Path'])
    length = G.n('GeometryNodeCurveLength', 'Path length')
    G.link(path, length.inputs['Curve'])
    stat = G.n('GeometryNodeAttributeStatistic', 'Closed?', data_type='FLOAT', domain='CURVE')
    G.link(path, stat.inputs['Geometry'])
    G.link(G.n('GeometryNodeInputSplineCyclic', 'Cyclic').outputs[0], stat.inputs['Attribute'])
    closed = stat.outputs['Max']
    bays = G.hi(1, G.m('ROUND', G.div(length.outputs['Length'], i['Spacing'])))
    count = G.add(bays, G.sub(1, closed))          # a closed path shares its seam station
    resample = G.n('GeometryNodeResampleCurve', 'Even spacing')
    G.link(path, resample.inputs['Curve'])
    G.link(count, resample.inputs['Count'])
    to_points = G.n('GeometryNodeCurveToPoints', 'Stations', mode='EVALUATED')
    G.link(resample.outputs[0], to_points.inputs['Curve'])
    pts = to_points.outputs['Points']
    tangent = G.v('NORMALIZE', to_points.outputs['Tangent'])
    side = G.v('NORMALIZE', G.v('CROSS_PRODUCT', (0, 0, 1), tangent))
    pts = G.store(pts, 'tangent', tangent, kind='FLOAT_VECTOR')
    pts = G.store(pts, 'side', side, kind='FLOAT_VECTOR')
    idx = G.index
    stray = G.v('ADD', G.v('SCALE', G.named('tangent', 'FLOAT_VECTOR'), scale=G.mul(i['Jitter'], rand(G, idx, 1, i['Seed']))),
                G.v('SCALE', G.named('side', 'FLOAT_VECTOR'), scale=G.mul(G.mul(i['Jitter'], .6), rand(G, idx, 2, i['Seed']))))
    spot = G.v('ADD', G.position(), stray)
    ray = G.n('GeometryNodeRaycast', 'Drop onto ground')
    G.link(i['Ground'], ray.inputs['Target Geometry'])
    G.link(G.v('ADD', spot, (0, 0, 100)), ray.inputs['Source Position'])
    ray.inputs['Ray Direction'].default_value = (0, 0, -1)
    ray.inputs['Ray Length'].default_value = 1000
    sx, sy, sz = G.sep(spot)
    _, _, hz = G.sep(ray.outputs['Hit Position'])
    pts = G.set_position(pts, G.xyz(sx, sy, G.switch('FLOAT', ray.outputs['Is Hit'], sz, hz)))
    G.link(pts, G.o['Stations'])
    G.link(G.m('GREATER_THAN', closed, .5), G.o['Closed'])
    G.link(count, G.o['Count'])
    G.layout()
    G.g.description = ('Evenly spaced stations along any curve (open or closed) or a straight run; '
                      'stores tangent and side; optional jitter and ground drop.')
    return G.g


def stations(G, i, *, spacing, jitter, seed):
    """Feed this fence's Path / Ground objects to GNL • Path Stations; returns (points, closed 0/1)."""
    path = G.n('GeometryNodeObjectInfo', 'Your path', transform_space='RELATIVE')
    G.link(i['Path'], path.inputs['Object'])
    ground = G.n('GeometryNodeObjectInfo', 'Ground', transform_space='RELATIVE')
    G.link(i['Ground'], ground.inputs['Object'])
    node = G.group(G.stations_group, 'Path Stations')
    G.link(path.outputs['Geometry'], node.inputs['Path'])
    G.link(ground.outputs['Geometry'], node.inputs['Ground'])
    G.link(i['Run Length'], node.inputs['Run Length'])
    G.link(spacing, node.inputs['Spacing'])
    G.link(jitter, node.inputs['Jitter'])
    G.link(seed, node.inputs['Seed'])
    closed = G.m('MULTIPLY', node.outputs['Closed'], 1)
    return node.outputs['Stations'], closed
