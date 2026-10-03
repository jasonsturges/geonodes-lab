"""GNL • Diamond Window and GNL • Gregorian Window: lattice, pane and frame composed on one opening."""
import math

import bpy

from authoring.naming import named
from authoring.nodes import socket
from graph import WindowGraph as Graph, opening_inputs, STYLES


def assembly_group(opening, lattice, pane, frame, lead, glass, *, gregorian=False):
    h = Graph(named('Gregorian Window') if gregorian else named('Diamond Window'))
    g = h.g
    g.is_modifier = True
    m = h.m
    opening_inputs(g)
    across = 'Lights Across' if gregorian else 'Cells Across'
    up = 'Lights Up' if gregorian else 'Cells Up'
    stock = 'Bar' if gregorian else 'Came'
    material_name = 'Bar Material' if gregorian else 'Lead Material'
    socket(g, across, 'NodeSocketInt', 3 if gregorian else 4, 1, 8)
    socket(g, up, 'NodeSocketInt', 4, 1, 8)
    socket(g, f'{stock} Width', 'NodeSocketFloat', .03 if gregorian else .022, .01, .05)
    socket(g, f'{stock} Depth', 'NodeSocketFloat', .03 if gregorian else .0308, .015, .1)
    socket(g, 'Show Frame', 'NodeSocketBool', True)
    socket(g, 'Show Glass', 'NodeSocketBool', True)
    socket(g, 'Frame Inset Factor', 'NodeSocketFloat', 1., .5, 2.)
    socket(g, 'Frame Outset Factor', 'NodeSocketFloat', 1.6, 0., 3.)
    socket(g, 'Glass Thickness', 'NodeSocketFloat', .004, .001, .01)
    for name, mat in [(material_name, lead), ('Frame Material', lead), ('Glass Material', glass)]:
        socket(g, name, 'NodeSocketMaterial', mat)
    diagnostics = [('Mullion Spacing', 'NodeSocketFloat'), ('Transom Spacing', 'NodeSocketFloat'), ('Mullion Phase', 'NodeSocketFloat')] if gregorian else [('Angle', 'NodeSocketFloat'), ('Spacing', 'NodeSocketFloat')]
    for name, kind in [('Geometry', 'NodeSocketGeometry'), ('Lattice', 'NodeSocketGeometry'), ('Frame', 'NodeSocketGeometry'), ('Glass', 'NodeSocketGeometry'), ('Cutter', 'NodeSocketGeometry'), ('Frame Valid', 'NodeSocketBool')] + diagnostics:
        socket(g, name, kind, direction='OUTPUT')
    o = h.n('NodeGroupInput', 'One opening and meaningful cell counts').outputs
    cw = m('DIVIDE', o['Width'], o[across])
    ch = m('DIVIDE', o['Springing Height'], o[up])
    angle = m('ARCTAN2', ch, cw)
    spacing = m('MULTIPLY', cw, m('SINE', angle))
    parts = []
    for label, core in [('Lattice', lattice), ('Glass', pane), ('Frame', frame)]:
        n = h.n('GeometryNodeGroup', label + ' shares the opening')
        n.node_tree = core
        for name in ('Arch Style', 'Width', 'Springing Height', 'Rise', 'Arch Segments'):
            h.link(o[name], n.inputs[name])
        parts.append(n)
    lat, gl, fr = parts
    if gregorian:
        phase = m('MULTIPLY', m('MODULO', o[across], 2), m('MULTIPLY', cw, .5))
        h.link(cw, lat.inputs['Mullion Spacing'])
        h.link(ch, lat.inputs['Transom Spacing'])
        h.link(phase, lat.inputs['Mullion Phase'])
        lat.inputs['Transom Phase'].default_value = 0
    else:
        h.link(angle, lat.inputs['Angle'])
        h.link(spacing, lat.inputs['Spacing'])
        lat.inputs['Phase'].default_value = 0
    for name in (f'{stock} Width', f'{stock} Depth'):
        h.link(o[name], lat.inputs[name])
    h.link(o[material_name], lat.inputs['Material'])
    h.link(o['Glass Thickness'], gl.inputs['Thickness'])
    h.link(o['Glass Material'], gl.inputs['Material'])
    h.link(m('MULTIPLY', o[f'{stock} Width'], o['Frame Inset Factor']), fr.inputs['Inset'])
    h.link(m('MULTIPLY', o[f'{stock} Width'], o['Frame Outset Factor']), fr.inputs['Outset'])
    h.link(o[f'{stock} Depth'], fr.inputs['Depth'])
    h.link(o['Frame Material'], fr.inputs['Material'])
    frame_geo = h.switch('GEOMETRY', o['Show Frame'], None, fr.outputs['Geometry'])
    glass_geo = h.switch('GEOMETRY', o['Show Glass'], None, gl.outputs['Geometry'])
    out = h.n('NodeGroupOutput', 'Whole window and replaceable parts')
    h.link(h.join(lat.outputs['Geometry'], frame_geo, glass_geo), out.inputs['Geometry'])
    for name, geo in [('Lattice', lat.outputs['Geometry']), ('Frame', frame_geo), ('Glass', glass_geo), ('Cutter', lat.outputs['Cutter'])]:
        h.link(geo, out.inputs[name])
    if gregorian:
        h.link(cw, out.inputs['Mullion Spacing'])
        h.link(ch, out.inputs['Transom Spacing'])
        h.link(phase, out.inputs['Mullion Phase'])
    else:
        h.link(angle, out.inputs['Angle'])
        h.link(spacing, out.inputs['Spacing'])
    h.link(fr.outputs['Valid'], out.inputs['Frame Valid'])
    g.interface.items_tree['Arch Style'].default_value = 'Semicircle'
    for title, names in [('Opening', ('Arch Style', 'Width', 'Springing Height', 'Rise', 'Arch Segments')), ('Pattern', (across, up, f'{stock} Width', f'{stock} Depth')), ('Components', ('Show Frame', 'Show Glass', 'Frame Inset Factor', 'Frame Outset Factor', 'Glass Thickness')), ('Materials', (material_name, 'Frame Material', 'Glass Material'))]:
        panel = g.interface.new_panel(name=title)
        for name in names:
            g.interface.move_to_parent(g.interface.items_tree[name], panel, 100)
    h.layout()
    return g
