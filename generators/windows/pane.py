"""GNL • Window Pane: glass that fits the named opening exactly (surface or thin slab)."""
import math

import bpy

from authoring.naming import named
from authoring.nodes import socket
from graph import WindowGraph as Graph, opening_inputs, STYLES


def pane_group(opening, material):
    h = Graph(named('Window Pane'))
    g = h.g
    g.is_modifier = True
    m = h.m
    opening_inputs(g)
    socket(g, 'Solid Glass', 'NodeSocketBool', True, description='Closed glass slab. Disable for a single surface with a suitable material.')
    socket(g, 'Thickness', 'NodeSocketFloat', .004, .001, .03, description='Total thickness centered on the opening plane; used only for solid glass.')
    socket(g, 'Material', 'NodeSocketMaterial', material)
    for name in ('Geometry', 'Outline'):
        socket(g, name, 'NodeSocketGeometry', direction='OUTPUT')
    socket(g, 'Resolved Rise', 'NodeSocketFloat', direction='OUTPUT')
    inp = h.n('NodeGroupInput', 'Opening and glass')
    o = inp.outputs
    profile = h.n('GeometryNodeGroup', 'Reuse the exact opening boundary')
    profile.node_tree = opening
    for name in ('Arch Style', 'Width', 'Springing Height', 'Rise', 'Arch Segments'):
        h.link(o[name], profile.inputs[name])
    h.link(o['Thickness'], profile.inputs['Cutter Depth'])
    geo = h.switch('GEOMETRY', o['Solid Glass'], profile.outputs['Region'], profile.outputs['Cutter'])
    pos = h.n('GeometryNodeInputPosition', 'Physical UV coordinates').outputs[0]
    sep = h.n('ShaderNodeSeparateXYZ', 'Coordinates')
    h.link(pos, sep.inputs[0])
    normal = h.n('GeometryNodeInputNormal', 'Choose projection').outputs[0]
    ns = h.n('ShaderNodeSeparateXYZ', 'Normal')
    h.link(normal, ns.inputs[0])
    ax = m('ABSOLUTE', ns.outputs['X'])
    ay = m('ABSOLUTE', ns.outputs['Y'])
    az = m('ABSOLUTE', ns.outputs['Z'])
    side = h.switch('VECTOR', m('GREATER_THAN', ax, az), h.xyz(sep.outputs['X'], sep.outputs['Y']), h.xyz(sep.outputs['Y'], sep.outputs['Z']))
    uv = h.switch('VECTOR', m('GREATER_THAN', ay, m('MAXIMUM', ax, az)), side, h.xyz(sep.outputs['X'], sep.outputs['Z']))
    geo = h.store(geo, 'UVMap', uv, 'FLOAT2', 'CORNER')
    finish = h.n('GeometryNodeSetMaterial', 'Replaceable glass material')
    h.link(geo, finish.inputs['Geometry'])
    h.link(o['Material'], finish.inputs['Material'])
    out = h.n('NodeGroupOutput', 'Pane and shared outline')
    h.link(finish.outputs[0], out.inputs['Geometry'])
    h.link(profile.outputs['Outline'], out.inputs['Outline'])
    h.link(profile.outputs['Resolved Rise'], out.inputs['Resolved Rise'])
    g.interface.items_tree['Arch Style'].default_value = 'Semicircle'
    for title, names in [('Opening', ('Arch Style', 'Width', 'Springing Height', 'Rise', 'Arch Segments')), ('Glass', ('Solid Glass', 'Thickness', 'Material'))]:
        panel = g.interface.new_panel(name=title)
        for name in names:
            g.interface.move_to_parent(g.interface.items_tree[name], panel, 100)
    h.layout()
    return g
