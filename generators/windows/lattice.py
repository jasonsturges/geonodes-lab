"""GNL • Diamond Lattice and GNL • Gregorian Lattice: bar families fitted to a named opening."""
import math

import bpy

from authoring.naming import named
from authoring.nodes import socket
from graph import WindowGraph as Graph, opening_inputs, STYLES


def lattice_group(opening, material, *, gregorian=False):
    """Shared bar construction; each public lattice has its own pattern interface."""
    h = Graph(named('Gregorian Lattice') if gregorian else named('Diamond Lattice'))
    g = h.g
    g.is_modifier = True
    m = h.m
    opening_inputs(g)
    if gregorian:
        for name, default in [('Mullion Spacing', .24), ('Transom Spacing', .3)]:
            socket(g, name, 'NodeSocketFloat', default, .08, .6)
        for name in ('Mullion Phase', 'Transom Phase'):
            socket(g, name, 'NodeSocketFloat', 0., -1., 1.)
    else:
        socket(g, 'Spacing', 'NodeSocketFloat', .19, .08, .6)
        socket(g, 'Phase', 'NodeSocketFloat', 0., -1., 1.)
        socket(g, 'Angle', 'NodeSocketFloat', math.pi / 4, math.radians(15), math.radians(75), subtype='ANGLE')
    stock = 'Bar' if gregorian else 'Came'
    for suffix, default, lo, hi in [('Width', .03 if gregorian else .022, .01, .08), ('Depth', .03 if gregorian else .022, .01, .12)]:
        socket(g, f'{stock} {suffix}', 'NodeSocketFloat', default, lo, hi)
    socket(g, f'{stock} Sides', 'NodeSocketInt', 4, 3, 16)
    socket(g, 'Material', 'NodeSocketMaterial', material)
    socket(g, 'Fuse Crossings', 'NodeSocketBool', True, description='Union intersecting cames for a clean rendered surface. Off preserves individual closed bars.')
    for name, kind in [('Geometry', 'NodeSocketGeometry'), ('Outline', 'NodeSocketGeometry'), ('Region', 'NodeSocketGeometry'), ('Cutter', 'NodeSocketGeometry'), ('Resolved Rise', 'NodeSocketFloat'), (f'{stock} Count', 'NodeSocketInt')]:
        socket(g, name, kind, direction='OUTPUT')
    inp = h.n('NodeGroupInput', 'Standalone lattice controls')
    o = inp.outputs
    profile = h.n('GeometryNodeGroup', 'Shared named opening')
    profile.node_tree = opening
    for name in ('Arch Style', 'Width', 'Springing Height', 'Rise', 'Arch Segments'):
        h.link(o[name], profile.inputs[name])
    profile.inputs['Cutter Depth'].default_value = .5
    # Work in the opening plane until the final upright placement.
    cutter = h.transform(profile.outputs['Cutter'], rotation=(-math.pi / 2, 0, 0))
    reach = m('ADD', m('ADD', o['Width'], o['Springing Height']), m('ADD', profile.outputs['Resolved Rise'], 1))
    minimum_spacing = m('MINIMUM', o['Mullion Spacing'], o['Transom Spacing']) if gregorian else o['Spacing']
    steps = m('CEIL', m('DIVIDE', reach, minimum_spacing))
    per = m('ADD', m('MULTIPLY', steps, 2), 1)
    points = h.n('GeometryNodeMeshLine', 'Two families of parallel bars')
    h.link(m('MULTIPLY', per, 2), points.inputs['Count'])
    index = h.n('GeometryNodeInputIndex', 'Bar identity').outputs[0]
    family = m('FLOOR', m('DIVIDE', index, per))
    ordinal = m('SUBTRACT', m('MODULO', index, per), steps)
    second = m('GREATER_THAN', family, .5)
    if gregorian:
        angle = h.switch('FLOAT', second, math.pi / 2, 0)
        spacing = h.switch('FLOAT', second, o['Mullion Spacing'], o['Transom Spacing'])
        phase = h.switch('FLOAT', second, o['Mullion Phase'], o['Transom Phase'])
    else:
        angle = h.switch('FLOAT', second, o['Angle'], m('MULTIPLY', o['Angle'], -1))
        spacing = o['Spacing']
        phase = o['Phase']
    offset = m('ADD', m('MULTIPLY', ordinal, spacing), phase)
    end = h.n('GeometryNodeForeachGeometryElementOutput', 'Clip each member independently')
    end.domain = 'POINT'
    for kind, name in [('FLOAT', 'Angle'), ('FLOAT', 'Offset'), ('INT', 'ID'), ('INT', 'Family')]:
        end.input_items.new(kind, name)
    end.main_items.new('INT', 'Kept')
    start = h.n('GeometryNodeForeachGeometryElementInput', 'One bar')
    start.pair_with_output(end)
    h.link(points.outputs[0], start.inputs['Geometry'])
    for name, value in [('Angle', angle), ('Offset', offset), ('ID', index), ('Family', family)]:
        h.link(value, start.inputs[name])
    p = start.outputs
    c = m('COSINE', p['Angle'])
    s = m('SINE', p['Angle'])
    cylinder = h.n('GeometryNodeMeshCylinder', 'Polygonal came section')
    cylinder.fill_type = 'NGON'
    cylinder.inputs['Radius'].default_value = .5
    h.link(o[f'{stock} Sides'], cylinder.inputs['Vertices'])
    h.link(m('MULTIPLY', reach, 2), cylinder.inputs['Depth'])
    bar = h.transform(cylinder.outputs['Mesh'], rotation=h.xyz(0, 0, m('DIVIDE', math.pi, o[f'{stock} Sides'])))
    bar = h.transform(bar, scale=h.xyz(o[f'{stock} Depth'], o[f'{stock} Width'], 1))
    bar = h.transform(bar, h.xyz(m('MULTIPLY', m('MULTIPLY', s, -1), p['Offset']), m('MULTIPLY', c, p['Offset']), 0), h.xyz(0, math.pi / 2, p['Angle']))
    cut = h.n('GeometryNodeMeshBoolean', 'Both ends follow the full outline')
    cut.operation = 'INTERSECT'
    cut.solver = 'EXACT'
    h.link(bar, cut.inputs[1])
    h.link(cutter, cut.inputs[1])
    geo = h.weld(cut.outputs['Mesh'])
    pos = h.n('GeometryNodeInputPosition', 'Surface coordinates').outputs[0]
    sep = h.n('ShaderNodeSeparateXYZ', 'Surface')
    h.link(pos, sep.inputs[0])
    station = m('ADD', m('MULTIPLY', sep.outputs['X'], c), m('MULTIPLY', sep.outputs['Y'], s))
    # Reject short corner members. Boolean may retain separate portions for concave heads.
    length = m('SUBTRACT', h.stats(geo, station, 'Max'), h.stats(geo, station, 'Min'))
    keep = m('GREATER_THAN', length, m('MULTIPLY', o[f'{stock} Width'], 3))
    if gregorian:
        # Drop sections lying along an opening edge: they belong to the frame.
        lateral = m('ADD', m('MULTIPLY', sep.outputs['X'], m('MULTIPLY', s, -1)), m('MULTIPLY', sep.outputs['Y'], c))
        covers_min = m('LESS_THAN', h.stats(geo, lateral, 'Min'), m('ADD', h.stats(bar, lateral, 'Min'), .000002))
        covers_max = m('GREATER_THAN', h.stats(geo, lateral, 'Max'), m('SUBTRACT', h.stats(bar, lateral, 'Max'), .000002))
        keep = m('MULTIPLY', keep, m('MULTIPLY', covers_min, covers_max))
    normal = h.n('GeometryNodeInputNormal', 'Projection selection').outputs[0]
    ns = h.n('ShaderNodeSeparateXYZ', 'Normal')
    h.link(normal, ns.inputs[0])
    # Dominant-axis planar UVs provide finite, nondegenerate maps including end cuts.
    ax = m('ABSOLUTE', ns.outputs['X'])
    ay = m('ABSOLUTE', ns.outputs['Y'])
    az = m('ABSOLUTE', ns.outputs['Z'])
    side = h.switch('VECTOR', m('GREATER_THAN', ax, ay), h.xyz(sep.outputs['X'], sep.outputs['Z']), h.xyz(sep.outputs['Y'], sep.outputs['Z']))
    uv = h.switch('VECTOR', m('GREATER_THAN', az, m('MAXIMUM', ax, ay)), side, h.xyz(sep.outputs['X'], sep.outputs['Y']))
    geo = h.store(geo, 'UVMap', uv, 'FLOAT2', 'CORNER')
    geo = h.store(geo, 'came_id', p['ID'], 'INT')
    geo = h.store(geo, 'came_family', p['Family'], 'INT')
    finish = h.n('GeometryNodeSetMaterial', 'Came material')
    h.link(geo, finish.inputs[0])
    h.link(o['Material'], finish.inputs['Material'])
    h.link(h.switch('GEOMETRY', keep, None, finish.outputs[0]), end.inputs['Geometry'])
    h.link(keep, end.inputs['Kept'])
    out = h.n('NodeGroupOutput', 'Standalone leading and shared opening')
    raw = next(s for s in end.outputs if s.identifier == 'Generation_0')
    union = h.n('GeometryNodeMeshBoolean', 'Optional unified leadwork')
    union.operation = 'UNION'
    union.solver = 'EXACT'
    if gregorian:
        # Uprights and levels are each disjoint families. Union the two families as separate operands
        # instead of everything at once, which avoids self-intersection artifacts at every crossing.
        family = h.named('came_family', 'INT')
        separate = h.n('GeometryNodeSeparateGeometry', 'Separate upright and horizontal families', domain='FACE')
        h.link(raw, separate.inputs['Geometry'])
        h.link(family, separate.inputs['Selection'])
        h.link(separate.outputs['Selection'], union.inputs[1])
        h.link(separate.outputs['Inverted'], union.inputs[1])
        union.inputs['Self Intersection'].default_value = False
    else:
        union.inputs['Self Intersection'].default_value = True
        h.link(raw, union.inputs[1])
    result = h.switch('GEOMETRY', o['Fuse Crossings'], raw, h.weld(union.outputs['Mesh']))
    result = h.store(result, 'UVMap', uv, 'FLOAT2', 'CORNER')
    h.link(h.transform(result, rotation=(math.pi / 2, 0, 0)), out.inputs['Geometry'])
    for name in ('Outline', 'Region', 'Cutter', 'Resolved Rise'):
        h.link(profile.outputs[name], out.inputs[name])
    h.link(h.stats(end.outputs[0], end.outputs['Kept'], 'Sum'), out.inputs[f'{stock} Count'])
    g.interface.items_tree['Arch Style'].default_value = 'Semicircle'
    pattern = ('Mullion Spacing', 'Transom Spacing', 'Mullion Phase', 'Transom Phase') if gregorian else ('Angle', 'Spacing', 'Phase')
    for title, names in [('Opening', ('Arch Style', 'Width', 'Springing Height', 'Rise', 'Arch Segments')), ('Lattice', pattern + (f'{stock} Width', f'{stock} Depth', f'{stock} Sides')), ('Finish', ('Fuse Crossings', 'Material'))]:
        panel = g.interface.new_panel(name=title)
        for name in names:
            g.interface.move_to_parent(g.interface.items_tree[name], panel, 100)
    h.layout()
    return g
