"""GNL • Corner / Surface Molding: a named section extruded into a straight run, with UVs."""
import math

from authoring.naming import named
from authoring.nodes import socket
from graph import MoldingGraph as Graph, F, value, CORNER, SURFACE


def molding_group(profile, material, surface=False):
    title = 'Surface' if surface else 'Corner'
    h = Graph(named(title + ' Molding'))
    g = h.g
    g.is_modifier = True
    socket(g, 'Profile', 'NodeSocketMenu')
    socket(g, 'Length', 'NodeSocketFloat', 1.2, .05, 10.)
    socket(g, 'Height', 'NodeSocketFloat', .07 if surface else .09, .02, .3)
    socket(g, 'Projection', 'NodeSocketFloat', .028 if surface else .065, .005, .2)
    socket(g, 'Segments', 'NodeSocketInt', 6, 1, 16)
    if surface:
        socket(g, 'Reeds', 'NodeSocketInt', 4, 2, 8)
        socket(g, 'Reed Backing', 'NodeSocketFloat', .1, .02, .4)
    else:
        socket(g, 'Crown', 'NodeSocketBool', True, description='Hang down from origin; off rises as base molding.')
    socket(g, 'Material', 'NodeSocketMaterial', material)
    for name in ('Geometry', 'Profile'):
        socket(g, name, 'NodeSocketGeometry', direction='OUTPUT')
    o = h.n('NodeGroupInput', 'One configurable molding piece').outputs
    p = h.n('GeometryNodeGroup', 'Reusable named section')
    p.node_tree = profile
    for name in ('Profile', 'Height', 'Projection', 'Segments') + (('Reeds', 'Reed Backing') if surface else ()):
        h.link(o[name], p.inputs[name])
    fill = h.n('GeometryNodeFillCurve', 'Solid section')
    h.link(p.outputs[0], fill.inputs['Curve'])
    ex = h.n('GeometryNodeExtrudeMesh', 'Straight run')
    ex.mode = 'FACES'
    ex.inputs['Individual'].default_value = False
    ex.inputs['Offset Scale'].default_value = 1
    h.link(fill.outputs[0], ex.inputs['Mesh'])
    h.link(h.xyz(0, 0, o['Length']), ex.inputs['Offset'])
    flip = h.n('GeometryNodeFlipFaces', 'Start cap')
    h.link(fill.outputs[0], flip.inputs[0])
    geo = h.weld(h.join(ex.outputs[0], flip.outputs[0]))
    position = h.n('GeometryNodeInputPosition', 'Section and run coordinates').outputs[0]
    sep = h.n('ShaderNodeSeparateXYZ', 'Coordinates')
    h.link(position, sep.inputs[0])
    sign = 1 if surface else h.switch('FLOAT', o['Crown'], 1, -1)

    def orient(geometry):
        n = h.n('GeometryNodeSetPosition', 'X run, -Y projection, Z height')
        h.link(geometry, n.inputs[0])
        h.link(h.xyz(h.m('SUBTRACT', sep.outputs['Z'], h.m('MULTIPLY', o['Length'], .5)), h.m('MULTIPLY', sep.outputs['Y'], -1), h.m('MULTIPLY', sep.outputs['X'], sign)), n.inputs['Position'])
        return n.outputs[0]
    geo = orient(geo)
    if not surface:
        flip = h.n('GeometryNodeFlipFaces', 'Preserve crown winding')
        h.link(geo, flip.inputs[0])
        geo = h.switch('GEOMETRY', o['Crown'], geo, flip.outputs[0])
    normal = h.n('GeometryNodeInputNormal', 'UV projection').outputs[0]
    ns = h.n('ShaderNodeSeparateXYZ', 'Normal')
    h.link(normal, ns.inputs[0])
    ax = h.m('ABSOLUTE', ns.outputs['X'])
    ay = h.m('ABSOLUTE', ns.outputs['Y'])
    az = h.m('ABSOLUTE', ns.outputs['Z'])
    side = h.switch('VECTOR', h.m('GREATER_THAN', ax, ay), h.xyz(sep.outputs['X'], sep.outputs['Z']), h.xyz(sep.outputs['Y'], sep.outputs['Z']))
    uv = h.switch('VECTOR', h.m('GREATER_THAN', az, h.m('MAXIMUM', ax, ay)), side, h.xyz(sep.outputs['X'], sep.outputs['Y']))
    geo = h.store(geo, 'UVMap', uv, 'FLOAT2', 'CORNER')
    mat = h.n('GeometryNodeSetMaterial', 'Molding finish')
    h.link(geo, mat.inputs[0])
    h.link(o['Material'], mat.inputs['Material'])
    out = h.n('NodeGroupOutput', 'Straight piece and source section')
    h.link(mat.outputs[0], out.inputs['Geometry'])
    h.link(p.outputs[0], out.inputs['Profile'])
    next(s for s in g.interface.items_tree if s.name == 'Profile' and s.in_out == 'INPUT').default_value = 'Astragal' if surface else 'Ogee'
    h.layout()
    return g
