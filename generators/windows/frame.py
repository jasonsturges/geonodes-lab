"""Window frames: a bounded planar offset of the opening boundary, and the frame built from it."""
import math

import bpy

from authoring.naming import named
from authoring.nodes import socket
from graph import WindowGraph as Graph, opening_inputs, STYLES


def offset_group():
    h = Graph(named('Opening Boundary Offset'))
    g = h.g
    m = h.m
    socket(g, 'Outline', 'NodeSocketGeometry')
    socket(g, 'Distance', 'NodeSocketFloat', 0.)
    socket(g, 'Miter Limit', 'NodeSocketFloat', 6., 1., 10.)
    socket(g, 'Outline', 'NodeSocketGeometry', direction='OUTPUT')
    socket(g, 'Valid', 'NodeSocketBool', direction='OUTPUT')
    o = h.n('NodeGroupInput', 'Single closed opening in XZ').outputs
    source = h.n('GeometryNodeCurveToMesh', 'Polyline vertices')
    h.link(h.transform(o['Outline'], rotation=(-math.pi / 2, 0, 0)), source.inputs['Curve'])
    # Remove redundant points on straight runs before offsetting. Otherwise an
    # inset corner can pass those samples and create a false fold at a square head.
    raw = source
    rawsize = h.n('GeometryNodeAttributeDomainSize', 'Raw sample count')
    rawsize.component = 'MESH'
    h.link(raw.outputs[0], rawsize.inputs[0])
    rn = rawsize.outputs['Point Count']
    ri = h.n('GeometryNodeInputIndex', 'Raw corner').outputs[0]
    rp = h.n('GeometryNodeInputPosition', 'Raw position').outputs[0]

    def raw_sample(k):
        q = h.n('GeometryNodeSampleIndex', 'Adjacent raw sample')
        q.data_type = 'FLOAT_VECTOR'
        q.domain = 'POINT'
        h.link(raw.outputs[0], q.inputs['Geometry'])
        h.link(rp, q.inputs['Value'])
        h.link(k, q.inputs['Index'])
        return q.outputs['Value']

    def raw_vec(op, a, b=None):
        q = h.n('ShaderNodeVectorMath', op)
        q.operation = op
        h.link(a, q.inputs[0])
        if b is not None:
            h.link(b, q.inputs[1])
        return q.outputs['Value'] if op == 'DOT_PRODUCT' else q.outputs['Vector']
    a = raw_vec('NORMALIZE', raw_vec('SUBTRACT', rp, raw_sample(m('MODULO', m('ADD', ri, m('SUBTRACT', rn, 1)), rn))))
    b = raw_vec('NORMALIZE', raw_vec('SUBTRACT', raw_sample(m('MODULO', m('ADD', ri, 1), rn)), rp))
    # Cross-product magnitude avoids rounding nearly-collinear dot products to 1.
    cross = raw_vec('CROSS_PRODUCT', a, b)
    length = h.n('ShaderNodeVectorMath', 'Turn magnitude')
    length.operation = 'LENGTH'
    h.link(cross, length.inputs[0])
    straight = m('MULTIPLY', m('LESS_THAN', length.outputs['Value'], .000001), m('GREATER_THAN', raw_vec('DOT_PRODUCT', a, b), 0))
    delete = h.n('GeometryNodeDeleteGeometry', 'Dissolve straight-run curve samples')
    delete.domain = 'POINT'
    h.link(h.transform(o['Outline'], rotation=(-math.pi / 2, 0, 0)), delete.inputs['Geometry'])
    h.link(straight, delete.inputs['Selection'])
    source = h.n('GeometryNodeCurveToMesh', 'Essential boundary corners')
    h.link(delete.outputs[0], source.inputs['Curve'])
    size = h.n('GeometryNodeAttributeDomainSize', 'Boundary count')
    size.component = 'MESH'
    h.link(source.outputs[0], size.inputs[0])
    count = size.outputs['Point Count']
    pos = h.n('GeometryNodeInputPosition', 'Source positions').outputs[0]
    index = h.n('GeometryNodeInputIndex', 'Paired corner index').outputs[0]
    corner = m('FLOOR', m('DIVIDE', index, 2))

    def sample(i):
        n = h.n('GeometryNodeSampleIndex', 'Corner position')
        n.data_type = 'FLOAT_VECTOR'
        n.domain = 'POINT'
        h.link(source.outputs[0], n.inputs['Geometry'])
        h.link(pos, n.inputs['Value'])
        h.link(i, n.inputs['Index'])
        return n.outputs['Value']

    def v(op, a, b=None):
        n = h.n('ShaderNodeVectorMath', op)
        n.operation = op
        h.link(a, n.inputs[0])
        if b is not None:
            h.link(b, n.inputs['Scale'] if op == 'SCALE' else n.inputs[1])
        return n.outputs['Value'] if op in ('DOT_PRODUCT', 'LENGTH') else n.outputs['Vector']

    def split(a):
        n = h.n('ShaderNodeSeparateXYZ', 'XY')
        h.link(a, n.inputs[0])
        return n.outputs
    p = sample(corner)
    prev = sample(m('MODULO', m('ADD', corner, m('SUBTRACT', count, 1)), count))
    nxt = sample(m('MODULO', m('ADD', corner, 1), count))
    incoming = v('NORMALIZE', v('SUBTRACT', p, prev))
    outgoing = v('NORMALIZE', v('SUBTRACT', nxt, p))
    a = split(incoming)
    b = split(outgoing)
    na = h.xyz(a['Y'], m('MULTIPLY', a['X'], -1))
    nb = h.xyz(b['Y'], m('MULTIPLY', b['X'], -1))
    denominator = m('MAXIMUM', .000001, m('ADD', 1, v('DOT_PRODUCT', na, nb)))
    mit = v('SCALE', v('ADD', na, nb), m('DIVIDE', 1, denominator))
    ratio = v('LENGTH', mit)
    turn = m('SUBTRACT', m('MULTIPLY', a['X'], b['Y']), m('MULTIPLY', a['Y'], b['X']))
    # Bevel only expanding joins; contracting joins retain their shifted-line intersection.
    bevel = m('MULTIPLY', m('GREATER_THAN', m('MULTIPLY', turn, o['Distance']), 0), m('GREATER_THAN', ratio, o['Miter Limit']))
    normal = h.switch('VECTOR', m('GREATER_THAN', m('MODULO', index, 2), .5), na, nb)
    offset = v('ADD', p, v('SCALE', h.switch('VECTOR', bevel, mit, normal), o['Distance']))
    line = h.n('GeometryNodeMeshLine', 'Two vertices per potential bevel')
    h.link(m('MULTIPLY', count, 2), line.inputs['Count'])
    place = h.n('GeometryNodeSetPosition', 'Offset edge intersections')
    h.link(line.outputs[0], place.inputs[0])
    h.link(offset, place.inputs['Position'])
    # Symmetric pointed heads can consume several short edges during contraction.
    # Replace the crossed crown chain by the intersection at the symmetry axis.
    original = split(p)
    shifted = split(offset)
    right_bad = m('MULTIPLY', m('GREATER_THAN', original['X'], .000001), m('LESS_THAN', shifted['X'], 0))
    left_bad = m('MULTIPLY', m('LESS_THAN', original['X'], -.000001), m('GREATER_THAN', shifted['X'], 0))
    first = h.stats(place.outputs[0], h.switch('FLOAT', right_bad, 100000, index), 'Min')
    last = h.stats(place.outputs[0], h.switch('FLOAT', left_bad, -1, index), 'Max')

    def shifted_sample(i):
        n = h.n('GeometryNodeSampleIndex', 'Surviving tip edge')
        n.data_type = 'FLOAT_VECTOR'
        n.domain = 'POINT'
        h.link(place.outputs[0], n.inputs['Geometry'])
        h.link(pos, n.inputs['Value'])
        h.link(i, n.inputs['Index'])
        return split(n.outputs['Value'])
    a = shifted_sample(m('SUBTRACT', first, 1))
    b = shifted_sample(first)
    factor = m('DIVIDE', a['X'], m('SUBTRACT', a['X'], b['X']))
    apex = m('ADD', a['Y'], m('MULTIPLY', factor, m('SUBTRACT', b['Y'], a['Y'])))
    repair = m('MULTIPLY', m('LESS_THAN', o['Distance'], 0), m('GREATER_THAN', last, first))
    selected = m('MULTIPLY', repair, m('MULTIPLY', m('GREATER_THAN', index, m('SUBTRACT', first, .5)), m('LESS_THAN', index, m('ADD', last, .5))))
    tip = h.n('GeometryNodeSetPosition', 'Resolve consumed symmetric crown edges')
    h.link(place.outputs[0], tip.inputs[0])
    h.link(selected, tip.inputs['Selection'])
    h.link(h.xyz(0, apex, 0), tip.inputs['Position'])
    curve = h.n('GeometryNodeMeshToCurve', 'Offset polyline')
    h.link(h.weld(tip.outputs[0]), curve.inputs[0])
    cyclic = h.n('GeometryNodeSetSplineCyclic', 'Close offset')
    cyclic.inputs['Cyclic'].default_value = True
    h.link(curve.outputs[0], cyclic.inputs[0])
    # Reject non-adjacent edge intersections instead of emitting folded offsets.
    mesh = h.n('GeometryNodeCurveToMesh', 'Closed offset edges')
    h.link(cyclic.outputs[0], mesh.inputs['Curve'])
    size2 = h.n('GeometryNodeAttributeDomainSize', 'Offset vertex count')
    size2.component = 'MESH'
    h.link(mesh.outputs[0], size2.inputs[0])
    n = size2.outputs['Point Count']
    pairs = h.n('GeometryNodeMeshLine', 'All edge pairs')
    h.link(m('MULTIPLY', n, n), pairs.inputs['Count'])
    i = m('FLOOR', m('DIVIDE', index, n))
    j = m('MODULO', index, n)

    def at(k):
        q = h.n('GeometryNodeSampleIndex', 'Offset endpoint')
        q.data_type = 'FLOAT_VECTOR'
        q.domain = 'POINT'
        h.link(mesh.outputs[0], q.inputs['Geometry'])
        h.link(pos, q.inputs['Value'])
        h.link(k, q.inputs['Index'])
        return q.outputs['Value']
    pa = at(i)
    pb = at(m('MODULO', m('ADD', i, 1), n))
    pc = at(j)
    pd = at(m('MODULO', m('ADD', j, 1), n))

    def cross(a, b):
        aa = split(a)
        bb = split(b)
        return m('SUBTRACT', m('MULTIPLY', aa['X'], bb['Y']), m('MULTIPLY', aa['Y'], bb['X']))
    ab = v('SUBTRACT', pb, pa)
    cd = v('SUBTRACT', pd, pc)
    ac = v('SUBTRACT', pc, pa)
    det = cross(ab, cd)
    t = m('DIVIDE', cross(ac, cd), det)
    u = m('DIVIDE', cross(ac, ab), det)
    hit = m('MULTIPLY', m('GREATER_THAN', m('ABSOLUTE', det), 1e-10), m('MULTIPLY', m('MULTIPLY', m('GREATER_THAN', t, -.000001), m('LESS_THAN', t, 1.000001)), m('MULTIPLY', m('GREATER_THAN', u, -.000001), m('LESS_THAN', u, 1.000001))))
    distant = m('MULTIPLY', m('GREATER_THAN', j, m('ADD', i, 1)), m('LESS_THAN', m('SUBTRACT', j, i), m('SUBTRACT', n, 1)))
    valid = m('LESS_THAN', h.stats(pairs.outputs[0], m('MULTIPLY', hit, distant), 'Max'), .5)
    out = h.n('NodeGroupOutput', 'Offset opening')
    h.link(h.transform(cyclic.outputs[0], rotation=(math.pi / 2, 0, 0)), out.inputs['Outline'])
    h.link(valid, out.inputs['Valid'])
    h.layout()
    return g


def frame_group(opening, offset, material):
    h = Graph(named('Window Frame'))
    g = h.g
    g.is_modifier = True
    m = h.m
    opening_inputs(g)
    for name, default, lo, hi in [('Inset', .022, .001, .08), ('Outset', .0352, 0., .12), ('Depth', .0308, .002, .15)]:
        socket(g, name, 'NodeSocketFloat', default, lo, hi)
    socket(g, 'Material', 'NodeSocketMaterial', material)
    socket(g, 'Geometry', 'NodeSocketGeometry', direction='OUTPUT')
    socket(g, 'Valid', 'NodeSocketBool', direction='OUTPUT')
    o = h.n('NodeGroupInput', 'Opening and frame dimensions').outputs
    profile = h.n('GeometryNodeGroup', 'Shared opening')
    profile.node_tree = opening
    for name in ('Arch Style', 'Width', 'Springing Height', 'Rise', 'Arch Segments'):
        h.link(o[name], profile.inputs[name])
    curves = []
    validity = []
    for label, distance, limit in [('Outer', o['Outset'], 6), ('Inner', m('MULTIPLY', o['Inset'], -1), 2)]:
        n = h.n('GeometryNodeGroup', label + ' offset')
        n.node_tree = offset
        h.link(profile.outputs['Outline'], n.inputs['Outline'])
        h.link(distance, n.inputs['Distance'])
        n.inputs['Miter Limit'].default_value = limit
        curves.append(n.outputs['Outline'])
        validity.append(n.outputs['Valid'])
    fill = h.n('GeometryNodeFillCurve', 'Nested loops form a ring')
    h.link(h.transform(h.join(*curves), rotation=(-math.pi / 2, 0, 0)), fill.inputs['Curve'])
    ex = h.n('GeometryNodeExtrudeMesh', 'Frame depth')
    ex.mode = 'FACES'
    ex.inputs['Individual'].default_value = False
    ex.inputs['Offset Scale'].default_value = 1
    h.link(fill.outputs[0], ex.inputs['Mesh'])
    h.link(h.xyz(0, 0, o['Depth']), ex.inputs['Offset'])
    flip = h.n('GeometryNodeFlipFaces', 'Back closure')
    h.link(fill.outputs[0], flip.inputs[0])
    geo = h.weld(h.join(ex.outputs['Mesh'], flip.outputs[0]))
    geo = h.transform(geo, h.xyz(0, 0, m('MULTIPLY', o['Depth'], -.5)))
    pos = h.n('GeometryNodeInputPosition', 'UV coordinates').outputs[0]
    p = h.n('ShaderNodeSeparateXYZ', 'Position')
    h.link(pos, p.inputs[0])
    normal = h.n('GeometryNodeInputNormal', 'UV projection').outputs[0]
    n = h.n('ShaderNodeSeparateXYZ', 'Normal')
    h.link(normal, n.inputs[0])
    ax = m('ABSOLUTE', n.outputs['X'])
    ay = m('ABSOLUTE', n.outputs['Y'])
    az = m('ABSOLUTE', n.outputs['Z'])
    side = h.switch('VECTOR', m('GREATER_THAN', ax, ay), h.xyz(p.outputs['X'], p.outputs['Z']), h.xyz(p.outputs['Y'], p.outputs['Z']))
    uv = h.switch('VECTOR', m('GREATER_THAN', az, m('MAXIMUM', ax, ay)), side, h.xyz(p.outputs['X'], p.outputs['Y']))
    geo = h.store(geo, 'UVMap', uv, 'FLOAT2', 'CORNER')
    geo = h.transform(geo, rotation=(math.pi / 2, 0, 0))
    finish = h.n('GeometryNodeSetMaterial', 'Frame material')
    h.link(geo, finish.inputs[0])
    h.link(o['Material'], finish.inputs['Material'])
    out = h.n('NodeGroupOutput', 'Frame')
    valid = m('MULTIPLY', *validity)
    h.link(h.switch('GEOMETRY', valid, None, finish.outputs[0]), out.inputs['Geometry'])
    h.link(valid, out.inputs['Valid'])
    g.interface.items_tree['Arch Style'].default_value = 'Semicircle'
    h.layout()
    return g
