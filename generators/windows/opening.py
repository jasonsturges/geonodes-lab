"""GNL • Opening Profile: one named opening (three-low-poly ArchProfile styles) as outline, filled
region and closed cutter, upright in XZ with the sill centre at the origin."""
import math

import bpy

from authoring.naming import named
from authoring.nodes import socket
from graph import WindowGraph as Graph, opening_inputs, STYLES


def opening_group():
    h = Graph(named('Opening Profile'))
    g = h.g
    m = h.m
    opening_inputs(g)
    socket(g, 'Cutter Depth', 'NodeSocketFloat', .3, .02, 2.)
    for name, kind in [('Outline', 'NodeSocketGeometry'), ('Region', 'NodeSocketGeometry'), ('Cutter', 'NodeSocketGeometry'), ('Resolved Rise', 'NodeSocketFloat')]:
        socket(g, name, kind, direction='OUTPUT')
    inp = h.n('NodeGroupInput', 'One opening description')
    o = inp.outputs
    half = m('MULTIPLY', o['Width'], .5)
    rise = h.menu('FLOAT', o['Arch Style'], [0, half, m('MINIMUM', o['Rise'], half), m('MAXIMUM', o['Rise'], half), o['Rise'], m('MAXIMUM', o['Rise'], half), o['Rise']])
    # Sampling retains sill corners, both springings, and the crown.
    count = m('ADD', m('MULTIPLY', o['Arch Segments'], 2), 3)
    line = h.n('GeometryNodeMeshLine', 'Closed opening vertices')
    h.link(count, line.inputs['Count'])
    index = h.n('GeometryNodeInputIndex', 'Boundary index').outputs[0]
    t = m('MINIMUM', 1, m('MAXIMUM', 0, m('DIVIDE', m('SUBTRACT', index, 2), m('MULTIPLY', o['Arch Segments'], 2))))
    angle = m('MULTIPLY', t, math.pi)
    ex = m('MULTIPLY', half, m('COSINE', angle))
    ey = m('MULTIPLY', rise, m('SINE', angle))
    safe = m('MAXIMUM', rise, .00001)
    radius = m('DIVIDE', m('ADD', m('MULTIPLY', half, half), m('MULTIPLY', safe, safe)), m('MULTIPLY', safe, 2))
    cy = m('SUBTRACT', safe, radius)
    a0 = m('ARCTAN2', m('MULTIPLY', cy, -1), half)
    ca = m('ADD', a0, m('MULTIPLY', t, m('SUBTRACT', math.pi, m('MULTIPLY', a0, 2))))
    cx = m('MULTIPLY', radius, m('COSINE', ca))
    cyval = m('ADD', cy, m('MULTIPLY', radius, m('SINE', ca)))
    # Each half of the pointed arch runs springing -> crown, mirrored on the left.
    q = m('MULTIPLY', m('MINIMUM', t, m('SUBTRACT', 1, t)), 2)
    sign = h.switch('FLOAT', m('GREATER_THAN', t, .5), 1, -1)
    offset = m('DIVIDE', m('SUBTRACT', m('MULTIPLY', half, half), m('MULTIPLY', rise, rise)), m('MULTIPLY', half, 2))
    pr = m('SUBTRACT', half, offset)
    pa = m('MULTIPLY', q, m('ARCTAN2', rise, m('MULTIPLY', offset, -1)))
    px = m('MULTIPLY', sign, m('ADD', offset, m('MULTIPLY', pr, m('COSINE', pa))))
    py = m('MULTIPLY', pr, m('SINE', pa))
    # Ogee: two tangent-continuous quadratics per half, normalized like the SDK.
    q2 = m('MULTIPLY', q, 2)
    second = m('GREATER_THAN', q, .5)
    u = h.switch('FLOAT', second, q2, m('SUBTRACT', q2, 1))
    v = m('SUBTRACT', 1, u)
    def bez(a, b, c): return m('ADD', m('ADD', m('MULTIPLY', a, m('MULTIPLY', v, v)), m('MULTIPLY', 2 * b, m('MULTIPLY', u, v))), m('MULTIPLY', c, m('MULTIPLY', u, u)))
    ox = m('MULTIPLY', m('MULTIPLY', sign, half), h.switch('FLOAT', second, bez(1, 1, .45), bez(.45, .175, 0)))
    oy = m('MULTIPLY', rise, h.switch('FLOAT', second, bez(0, .4, .55), bez(.55, .625, 1)))
    hx = h.menu('FLOAT', o['Arch Style'], [m('MULTIPLY', half, m('SUBTRACT', 1, m('MULTIPLY', t, 2))), cx, cx, cx, ex, px, ox])
    hy = h.menu('FLOAT', o['Arch Style'], [0, cyval, cyval, cyval, ey, py, oy])
    x = h.switch('FLOAT', m('LESS_THAN', index, 2), hx, h.switch('FLOAT', m('LESS_THAN', index, 1), half, m('MULTIPLY', half, -1)))
    y = h.switch('FLOAT', m('LESS_THAN', index, 2), m('ADD', o['Springing Height'], hy), 0)
    place = h.n('GeometryNodeSetPosition', 'Sill, jambs and named arch')
    h.link(line.outputs[0], place.inputs[0])
    h.link(h.xyz(x, y, 0), place.inputs['Position'])
    curve = h.n('GeometryNodeMeshToCurve', 'Boundary polyline')
    h.link(place.outputs[0], curve.inputs[0])
    cyclic = h.n('GeometryNodeSetSplineCyclic', 'Close at sill')
    cyclic.inputs['Cyclic'].default_value = True
    h.link(curve.outputs[0], cyclic.inputs['Geometry'])
    fill = h.n('GeometryNodeFillCurve', 'One shared opening region')
    h.link(cyclic.outputs[0], fill.inputs['Curve'])
    region = fill.outputs['Mesh']
    position = h.n('GeometryNodeInputPosition', 'Planar UV coordinates').outputs[0]
    region = h.store(region, 'UVMap', position, 'FLOAT2', 'CORNER')
    extrude = h.n('GeometryNodeExtrudeMesh', 'Cutter solid')
    extrude.mode = 'FACES'
    extrude.inputs['Individual'].default_value = False
    extrude.inputs['Offset Scale'].default_value = 1
    h.link(region, extrude.inputs['Mesh'])
    h.link(h.xyz(0, 0, o['Cutter Depth']), extrude.inputs['Offset'])
    flip = h.n('GeometryNodeFlipFaces', 'Back cap')
    h.link(region, flip.inputs['Mesh'])
    cutter = h.transform(h.weld(h.join(extrude.outputs['Mesh'], flip.outputs[0])), h.xyz(0, 0, m('MULTIPLY', o['Cutter Depth'], -.5)))
    # Public geometry is upright XZ, front faces toward -Y; origin is the sill center.
    out = h.n('NodeGroupOutput', 'Shared outline, region and cutter')
    for name, geo in [('Outline', cyclic.outputs[0]), ('Region', region), ('Cutter', cutter)]:
        h.link(h.transform(geo, rotation=(math.pi / 2, 0, 0)), out.inputs[name])
    h.link(rise, out.inputs['Resolved Rise'])
    g.interface.items_tree['Arch Style'].default_value = 'Semicircle'
    h.layout()
    return g
