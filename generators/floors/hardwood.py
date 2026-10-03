"""GNL • Hardwood Floor: seeded boards laid at any angle and clipped to a rectangular room.

Origin: three-low-poly `HardwoodFloor` (factory/floors), first built in the NodesLab prototype. Layout,
shape and color variation draw from independent seeds.
"""
import math

import bpy

from authoring.naming import named
from authoring.nodes import socket, feed
from graph import FloorGraph as Graph


def layout_group():
    h = Graph(named('Floor Laying'))
    g = h.g
    m = h.math
    for name in ('Run', 'Across', 'Board Width', 'Row Gap', 'Shortest Board', 'Longest Board', 'Stagger Target'):
        socket(g, name, 'NodeSocketFloat')
    socket(g, 'Layout Seed', 'NodeSocketInt')
    for name, kind in [('Placements', 'NodeSocketGeometry'), ('Rows', 'NodeSocketInt'), ('Actual Board Width', 'NodeSocketFloat'), ('Closest Joint', 'NodeSocketFloat')]:
        socket(g, name, kind, direction='OUTPUT')
    inp = h.n('NodeGroupInput', 'Application dimensions')
    o = inp.outputs
    run = o['Run']
    across = o['Across']
    longest = m('MINIMUM', m('MAXIMUM', o['Shortest Board'], o['Longest Board']), run)
    shortest = m('MINIMUM', m('MAXIMUM', m('MINIMUM', o['Shortest Board'], o['Longest Board']), .05), longest)
    target = m('MINIMUM', o['Stagger Target'], m('MULTIPLY', m('SUBTRACT', longest, shortest), .5))
    rows = m('MAXIMUM', 1, m('ROUND', m('DIVIDE', across, m('ADD', o['Board Width'], o['Row Gap']))))
    pitch = m('DIVIDE', across, rows)
    width = m('SUBTRACT', pitch, o['Row Gap'])
    bound = m('MULTIPLY', rows, m('ADD', m('CEIL', m('DIVIDE', run, m('MULTIPLY', shortest, .45))), 1))
    end = h.n('GeometryNodeRepeatOutput', 'Lay one board per iteration')
    end.repeat_items.clear()
    for kind, name in [('GEOMETRY', 'Placements'), ('GEOMETRY', 'Previous Joints'), ('GEOMETRY', 'Current Joints'), ('FLOAT', 'Cursor'), ('INT', 'Row'), ('FLOAT', 'Closest')]:
        end.repeat_items.new(kind, name)
    start = h.n('GeometryNodeRepeatInput', 'Laying state')
    start.pair_with_output(end)
    h.link(bound, start.inputs['Iterations'])
    start.inputs['Closest'].default_value = 1000000
    state = start.outputs
    cursor = state['Cursor']
    row = state['Row']
    active = m('LESS_THAN', row, rows)
    remaining = m('SUBTRACT', run, cursor)
    candidates = h.n('GeometryNodeMeshLine', '24 length candidates')
    candidates.inputs['Count'].default_value = 24
    index = h.n('GeometryNodeInputIndex', 'Candidate index').outputs[0]
    identity = m('ADD', m('MULTIPLY', state['Iteration'], 53), index)
    draw = h.draw(o['Layout Seed'], identity)
    candidate = m('ADD', shortest, m('MULTIPLY', draw, m('SUBTRACT', longest, shortest)))
    starter = m('ADD', .3, m('MULTIPLY', .7, h.draw(m('ADD', o['Layout Seed'], 701), identity)))
    candidate = m('MULTIPLY', candidate, h.switch('FLOAT', m('LESS_THAN', cursor, .00001), 1, starter))
    candidate = m('MAXIMUM', candidate, m('MULTIPLY', shortest, .45))
    candidate = h.switch('FLOAT', m('LESS_THAN', m('SUBTRACT', remaining, candidate), shortest), candidate, remaining)
    candidate = m('MINIMUM', candidate, remaining)
    ends = m('ADD', cursor, candidate)
    near = h.n('GeometryNodeProximity', 'Clearance from previous row joints')
    near.target_element = 'POINTS'
    h.link(state['Previous Joints'], near.inputs['Geometry'])
    h.link(h.xyz(ends, 0, 0), near.inputs['Source Position'])
    # Empty previous row has no joint to avoid.
    count = h.n('GeometryNodeAttributeDomainSize', 'Previous joint count')
    count.component = 'MESH'
    h.link(state['Previous Joints'], count.inputs['Geometry'])
    clearance = h.switch('FLOAT', m('GREATER_THAN', count.outputs['Point Count'], 0), 1000000, near.outputs['Distance'])
    score = m('MINIMUM', clearance, target)
    best = h.stats(candidates.outputs['Mesh'], score, 'Max')
    eligible = m('GREATER_THAN', score, m('SUBTRACT', best, .000001))
    choice = h.stats(candidates.outputs['Mesh'], index, 'Min', selection=eligible)
    chosen = h.sample(candidates.outputs['Mesh'], candidate, choice)
    distance = h.sample(candidates.outputs['Mesh'], clearance, choice)
    next_cursor = m('ADD', cursor, chosen)
    finish = m('GREATER_THAN', next_cursor, m('SUBTRACT', run, .0001))
    center = h.xyz(m('SUBTRACT', m('ADD', cursor, m('MULTIPLY', chosen, .5)), m('MULTIPLY', run, .5)),
                 m('SUBTRACT', m('MULTIPLY', m('ADD', row, .5), pitch), m('MULTIPLY', across, .5)), 0)
    point = h.n('GeometryNodeMeshLine', 'One board identity')
    point.inputs['Count'].default_value = 1
    h.link(center, point.inputs['Start Location'])
    placed = h.store(point.outputs['Mesh'], 'board_length', chosen)
    placed = h.store(placed, 'board_id', state['Iteration'], 'INT')
    placed = h.store(placed, 'row_id', row, 'INT')
    placed = h.store(placed, 'joint_clearance', distance)
    joint = h.n('GeometryNodeMeshLine', 'Internal end joint')
    joint.inputs['Count'].default_value = 1
    h.link(h.xyz(next_cursor, 0, 0), joint.inputs['Start Location'])
    joints = h.join(state['Current Joints'], h.switch('GEOMETRY', finish, joint.outputs['Mesh'], None))
    h.link(h.join(state['Placements'], h.switch('GEOMETRY', active, None, placed)), end.inputs['Placements'])
    h.link(h.switch('GEOMETRY', finish, state['Previous Joints'], joints), end.inputs['Previous Joints'])
    h.link(h.switch('GEOMETRY', finish, joints, None), end.inputs['Current Joints'])
    h.link(h.switch('FLOAT', finish, next_cursor, 0), end.inputs['Cursor'])
    h.link(m('ADD', row, finish), end.inputs['Row'])
    measured = h.switch('FLOAT', m('MULTIPLY', active, m('SUBTRACT', 1, finish)), 1000000, distance)
    h.link(m('MINIMUM', state['Closest'], measured), end.inputs['Closest'])
    out = h.n('NodeGroupOutput', 'Laying result')
    h.link(end.outputs['Placements'], out.inputs['Placements'])
    h.link(rows, out.inputs['Rows'])
    h.link(width, out.inputs['Actual Board Width'])
    h.link(h.switch('FLOAT', m('LESS_THAN', end.outputs['Closest'], 999999), 0, end.outputs['Closest']), out.inputs['Closest Joint'])
    h.layout()
    return g


def resolve_offcuts_group():
    """Measure offcuts, then assign small pieces to retained boards in their row."""
    h = Graph(named('Resolve Floor Offcuts'))
    g = h.g
    m = h.math
    socket(g, 'Placements', 'NodeSocketGeometry')
    for name in ('Room Width', 'Room Depth', 'Actual Board Width', 'Thickness', 'Rotation', 'Min Sliver Area'):
        socket(g, name, 'NodeSocketFloat')
    socket(g, 'Placements', 'NodeSocketGeometry', direction='OUTPUT')
    inp = h.n('NodeGroupInput', 'Laid boards and room')
    o = inp.outputs
    end = h.n('GeometryNodeForeachGeometryElementOutput', 'Measure original clipped footprint')
    end.domain = 'POINT'
    end.input_items.new('VECTOR', 'Center')
    end.input_items.new('FLOAT', 'Length')
    end.main_items.new('FLOAT', 'Area')
    start = h.n('GeometryNodeForeachGeometryElementInput', 'Inspect each original board')
    start.pair_with_output(end)
    pos = h.n('GeometryNodeInputPosition', 'Laying center').outputs[0]
    h.link(o['Placements'], start.inputs['Geometry'])
    h.link(pos, start.inputs['Center'])
    h.link(h.attr('board_length'), start.inputs['Length'])
    sep = h.n('ShaderNodeSeparateXYZ', 'Laying coordinates')
    h.link(start.outputs['Center'], sep.inputs[0])
    x = sep.outputs['X']
    y = sep.outputs['Y']
    c = m('COSINE', o['Rotation'])
    s = m('SINE', o['Rotation'])
    center = h.xyz(m('SUBTRACT', m('MULTIPLY', x, c), m('MULTIPLY', y, s)), m('ADD', m('MULTIPLY', x, s), m('MULTIPLY', y, c)), m('MULTIPLY', o['Thickness'], -.5))
    board = h.transform(h.cube(h.xyz(start.outputs['Length'], o['Actual Board Width'], o['Thickness'])), center, h.xyz(0, 0, o['Rotation']))
    room = h.cube(h.xyz(o['Room Width'], o['Room Depth'], m('MULTIPLY', o['Thickness'], 3)))
    cut = h.n('GeometryNodeMeshBoolean', 'Original board intersection')
    cut.operation = 'INTERSECT'
    cut.solver = 'EXACT'
    h.link(board, cut.inputs[1])
    h.link(room, cut.inputs[1])
    area = h.n('GeometryNodeInputMeshFaceArea', 'Footprint area').outputs[0]
    normal = h.n('GeometryNodeInputNormal', 'Top face').outputs[0]
    ns = h.n('ShaderNodeSeparateXYZ', 'Normal')
    h.link(normal, ns.inputs[0])
    h.link(h.stats(cut.outputs[0], area, 'Sum', domain='FACE', selection=m('GREATER_THAN', ns.outputs['Z'], .5)), end.inputs['Area'])
    geo = h.store(end.outputs[0], 'original_area', end.outputs['Area'])
    original = h.attr('original_area')
    keep = m('MULTIPLY', m('GREATER_THAN', original, 1e-8), m('GREATER_THAN', original, m('SUBTRACT', o['Min Sliver Area'], 1e-9)))
    geo = h.store(geo, 'keep_board', keep, 'BOOLEAN')
    # Separate rows widely for a nearest-point query: X remains the run coordinate.
    # 1000 exceeds the entire supported run. Verify the sampled row before assigning.
    ps = h.n('ShaderNodeSeparateXYZ', 'Original center')
    h.link(pos, ps.inputs[0])
    encoded = h.xyz(ps.outputs['X'], m('MULTIPLY', h.attr('row_id', 'INT'), 1000), 0)
    move = h.n('GeometryNodeSetPosition', 'Row-separated search points')
    h.link(geo, move.inputs['Geometry'])
    h.link(encoded, move.inputs['Position'])
    remove = h.n('GeometryNodeDeleteGeometry', 'Search retained boards only')
    remove.domain = 'POINT'
    h.link(move.outputs[0], remove.inputs['Geometry'])
    h.link(m('SUBTRACT', 1, h.attr('keep_board', 'BOOLEAN')), remove.inputs['Selection'])
    nearest = h.n('GeometryNodeSampleNearest', 'Nearest retained board in row')
    nearest.domain = 'POINT'
    h.link(remove.outputs[0], nearest.inputs['Geometry'])
    h.link(encoded, nearest.inputs['Sample Position'])
    index = nearest.outputs[0]
    owner = h.sample(remove.outputs[0], h.attr('board_id', 'INT'), index, 'INT')
    owner_row = h.sample(remove.outputs[0], h.attr('row_id', 'INT'), index, 'INT')
    count = h.n('GeometryNodeAttributeDomainSize', 'Any retained boards')
    count.component = 'MESH'
    h.link(remove.outputs[0], count.inputs['Geometry'])
    same_row = m('LESS_THAN', m('ABSOLUTE', m('SUBTRACT', owner_row, h.attr('row_id', 'INT'))), .5)
    assign = m('MULTIPLY', same_row, m('MULTIPLY', m('GREATER_THAN', count.outputs['Point Count'], 0), m('GREATER_THAN', original, 1e-8)))
    geo = h.store(geo, 'offcut_owner', h.switch('INT', assign, -1, owner), 'INT')
    out = h.n('NodeGroupOutput', 'Original placements plus ownership')
    h.link(geo, out.inputs[0])
    h.layout()
    return g


def timber_material():
    mat = bpy.data.materials.new(named('Hardwood • Board tint'))
    mat.use_nodes = True
    g = mat.node_tree
    bsdf = g.nodes.get('Principled BSDF')
    bsdf.inputs['Roughness'].default_value = .65
    a = g.nodes.new('ShaderNodeAttribute')
    a.attribute_name = 'hardwood_tint'
    a.location = (-300, 200)
    g.links.new(a.outputs['Color'], bsdf.inputs['Base Color'])
    return mat


def linear(hex_value):
    rgb = [int(hex_value[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055)**2.4 for v in rgb) + (1,)


def floor_group(layout, mat):
    h = Graph(named('Hardwood Floor'))
    g = h.g
    g.is_modifier = True
    m = h.math
    socket(g, 'Geometry', 'NodeSocketGeometry', direction='OUTPUT')
    for name, default, low, high in [('Room Width', 5., 1.5, 10.), ('Room Depth', 4., 1.5, 10.),
        ('Board Width', .2, .08, .5), ('Thickness', .055, .02, .2), ('Row Gap', .012, 0., .03),
        ('Shortest Board', .5, .2, 3.), ('Longest Board', 1.4, .3, 4.), ('Stagger Target', .35, 0., 1.5),
        ('Min Sliver Area', .004, 0., .05)]:
            socket(g, name, 'NodeSocketFloat', default, low, high)
    socket(g, 'Rotation', 'NodeSocketFloat', math.pi / 4, -math.tau, math.tau, subtype='ANGLE')
    socket(g, 'Layout Seed', 'NodeSocketInt', 20907, 0, 65535)
    socket(g, 'Color Seed', 'NodeSocketInt', 17, 0, 65535)
    socket(g, 'Color A', 'NodeSocketColor', linear('#493729'))
    socket(g, 'Color B', 'NodeSocketColor', linear('#93714f'))
    socket(g, 'Use Base Color Variation', 'NodeSocketBool', False)
    socket(g, 'Base Color', 'NodeSocketColor', linear('#6b4b2c'))
    socket(g, 'Color Variance', 'NodeSocketFloat', .06, 0., .3)
    socket(g, 'Material', 'NodeSocketMaterial', mat)
    for name, kind in [('Board Count', 'NodeSocketInt'), ('Row Count', 'NodeSocketInt'), ('Actual Board Width', 'NodeSocketFloat'), ('Closest Joint', 'NodeSocketFloat'), ('Sliver Count', 'NodeSocketInt'), ('Clipped Count', 'NodeSocketInt'), ('Absorbed Count', 'NodeSocketInt')]:
        socket(g, name, kind, direction='OUTPUT')
    inp = h.n('NodeGroupInput', 'Room and laying controls')
    o = inp.outputs
    c = m('COSINE', o['Rotation'])
    s = m('SINE', o['Rotation'])
    ac = m('ABSOLUTE', c)
    ass = m('ABSOLUTE', s)
    run = m('ADD', m('MULTIPLY', o['Room Width'], ac), m('MULTIPLY', o['Room Depth'], ass))
    across = m('ADD', m('MULTIPLY', o['Room Width'], ass), m('MULTIPLY', o['Room Depth'], ac))
    laying = h.n('GeometryNodeGroup', 'Fit rows to the covering sheet')
    laying.node_tree = layout
    h.link(run, laying.inputs['Run'])
    h.link(across, laying.inputs['Across'])
    for name in ('Board Width', 'Row Gap', 'Shortest Board', 'Longest Board', 'Stagger Target', 'Layout Seed'):
        h.link(o[name], laying.inputs[name])
    resolve = h.n('GeometryNodeGroup', 'Absorb tiny wall ends into adjacent boards')
    resolve.node_tree = resolve_offcuts_group()
    h.link(laying.outputs['Placements'], resolve.inputs['Placements'])
    h.link(laying.outputs['Actual Board Width'], resolve.inputs['Actual Board Width'])
    for name in ('Room Width', 'Room Depth', 'Thickness', 'Rotation', 'Min Sliver Area'):
        h.link(o[name], resolve.inputs[name])
    prepared = resolve.outputs[0]
    end = h.n('GeometryNodeForeachGeometryElementOutput', 'Keep each board a separate solid')
    end.domain = 'POINT'
    for kind, name in [('VECTOR', 'Center'), ('FLOAT', 'Length'), ('INT', 'Board ID'), ('INT', 'Row ID'), ('BOOLEAN', 'Keep')]:
        end.input_items.new(kind, name)
    for kind, name in [('FLOAT', 'Area'), ('INT', 'Retained'), ('INT', 'Sliver'), ('INT', 'Clipped')]:
        end.main_items.new(kind, name)
    start = h.n('GeometryNodeForeachGeometryElementInput', 'Build and cut each placement')
    start.pair_with_output(end)
    h.link(prepared, start.inputs['Geometry'])
    pos = h.n('GeometryNodeInputPosition', 'Board center / surface position').outputs[0]
    h.link(pos, start.inputs['Center'])
    h.link(h.attr('board_length'), start.inputs['Length'])
    h.link(h.attr('board_id', 'INT'), start.inputs['Board ID'])
    h.link(h.attr('row_id', 'INT'), start.inputs['Row ID'])
    h.link(h.attr('keep_board', 'BOOLEAN'), start.inputs['Keep'])
    p = start.outputs
    original_pos = h.n('ShaderNodeSeparateXYZ', 'Candidate center')
    h.link(pos, original_pos.inputs[0])
    own = m('LESS_THAN', m('ABSOLUTE', m('SUBTRACT', h.attr('offcut_owner', 'INT'), p['Board ID'])), .5)
    lower = m('SUBTRACT', original_pos.outputs['X'], m('MULTIPLY', h.attr('board_length'), .5))
    upper = m('ADD', original_pos.outputs['X'], m('MULTIPLY', h.attr('board_length'), .5))
    low = h.stats(prepared, lower, 'Min', selection=own)
    high = h.stats(prepared, upper, 'Max', selection=own)
    extended = m('SUBTRACT', high, low)
    center_sep = h.n('ShaderNodeSeparateXYZ', 'Laying coordinates')
    h.link(p['Center'], center_sep.inputs[0])
    x = h.switch('FLOAT', p['Keep'], center_sep.outputs['X'], m('MULTIPLY', m('ADD', low, high), .5))
    y = center_sep.outputs['Y']
    board_length = h.switch('FLOAT', p['Keep'], p['Length'], extended)
    center = h.xyz(m('SUBTRACT', m('MULTIPLY', x, c), m('MULTIPLY', y, s)), m('ADD', m('MULTIPLY', x, s), m('MULTIPLY', y, c)), m('MULTIPLY', o['Thickness'], -.5))
    board = h.cube(h.xyz(board_length, laying.outputs['Actual Board Width'], o['Thickness']))
    board = h.transform(board, center, h.xyz(0, 0, o['Rotation']))
    room = h.cube(h.xyz(o['Room Width'], o['Room Depth'], m('MULTIPLY', o['Thickness'], 3)))
    cut = h.n('GeometryNodeMeshBoolean', 'Clip complete outline to room')
    cut.operation = 'INTERSECT'
    cut.solver = 'EXACT'
    h.link(board, cut.inputs[1])
    h.link(room, cut.inputs[1])
    weld = h.n('GeometryNodeMergeByDistance', 'Clean coincident boundary intersections')
    weld.inputs['Distance'].default_value = .000001
    h.link(cut.outputs['Mesh'], weld.inputs['Geometry'])
    cut_mesh = weld.outputs['Geometry']
    normal = h.n('GeometryNodeInputNormal', 'Face normal').outputs[0]
    ns = h.n('ShaderNodeSeparateXYZ', 'Top face selection')
    h.link(normal, ns.inputs[0])
    area = h.n('GeometryNodeInputMeshFaceArea', 'Retained footprint').outputs[0]
    footprint = h.stats(cut_mesh, area, 'Sum', domain='FACE', selection=m('GREATER_THAN', ns.outputs['Z'], .5))
    nonempty = m('GREATER_THAN', footprint, .00000001)
    retain = m('MULTIPLY', nonempty, p['Keep'])
    sliver = 0  # Discarded/absorbed counts are measured on the original placements below.
    clipped = m('MULTIPLY', retain, m('LESS_THAN', footprint, m('SUBTRACT', m('MULTIPLY', board_length, laying.outputs['Actual Board Width']), .000001)))
    # Physical-scale board-aligned mapping. Separate planar projections on walls.
    ps = h.n('ShaderNodeSeparateXYZ', 'World surface')
    h.link(pos, ps.inputs[0])
    u = m('ADD', m('MULTIPLY', ps.outputs['X'], c), m('MULTIPLY', ps.outputs['Y'], s))
    v = m('SUBTRACT', m('MULTIPLY', ps.outputs['Y'], c), m('MULTIPLY', ps.outputs['X'], s))
    nx = m('ADD', m('MULTIPLY', ns.outputs['X'], c), m('MULTIPLY', ns.outputs['Y'], s))
    ny = m('SUBTRACT', m('MULTIPLY', ns.outputs['Y'], c), m('MULTIPLY', ns.outputs['X'], s))
    local_u = m('ADD', m('SUBTRACT', u, x), m('MULTIPLY', board_length, .5))
    local_v = m('ADD', m('SUBTRACT', v, y), m('MULTIPLY', laying.outputs['Actual Board Width'], .5))
    top_uv = h.xyz(local_u, local_v, 0)
    side_u = h.switch('FLOAT', m('GREATER_THAN', m('ABSOLUTE', nx), m('ABSOLUTE', ny)), local_u, local_v)
    side_uv = h.xyz(side_u, m('ADD', ps.outputs['Z'], o['Thickness']), 0)
    uv = h.switch('VECTOR', m('GREATER_THAN', m('ABSOLUTE', ns.outputs['Z']), .5), side_uv, top_uv)
    result = h.store(cut_mesh, 'UVMap', uv, 'FLOAT2', 'CORNER')
    # Color is constant per board. A separate seed cannot change any layout input.
    mix = h.n('ShaderNodeMixRGB', 'Board color between endpoints')
    mix.blend_type = 'MIX'
    h.link(h.draw(o['Color Seed'], p['Board ID']), mix.inputs[0])
    h.link(o['Color A'], mix.inputs[1])
    h.link(o['Color B'], mix.inputs[2])
    sep = h.n('FunctionNodeSeparateColor', 'Base color in HSL')
    sep.mode = 'HSL'
    h.link(o['Base Color'], sep.inputs[0])
    combine = h.n('FunctionNodeCombineColor', 'Independent HSL offsets')
    combine.mode = 'HSL'
    for i, salt in enumerate((101, 211, 307)):
        spread = m('DIVIDE', o['Color Variance'], 3) if i == 0 else o['Color Variance']
        jitter = m('MULTIPLY', m('SUBTRACT', m('MULTIPLY', h.draw(m('ADD', o['Color Seed'], salt), p['Board ID']), 2), 1), spread)
        value = m('ADD', sep.outputs[i], jitter)
        if i > 0:
            value = m('MINIMUM', 1, m('MAXIMUM', 0, value))
        h.link(value, combine.inputs[i])
    tint = h.switch('RGBA', o['Use Base Color Variation'], mix.outputs[0], combine.outputs[0])
    result = h.store(result, 'hardwood_tint', tint, 'FLOAT_COLOR', 'FACE')
    result = h.store(result, 'board_id', p['Board ID'], 'INT', 'FACE')
    result = h.store(result, 'row_id', p['Row ID'], 'INT', 'FACE')
    result = h.store(result, 'retained_area', footprint, 'FLOAT', 'FACE')
    finish = h.n('GeometryNodeSetMaterial', 'User material')
    h.link(result, finish.inputs['Geometry'])
    h.link(o['Material'], finish.inputs['Material'])
    h.link(h.switch('GEOMETRY', retain, None, finish.outputs[0]), end.inputs['Geometry'])
    for name, value in [('Area', footprint), ('Retained', retain), ('Sliver', sliver), ('Clipped', clipped)]:
        h.link(value, end.inputs[name])
    out = h.n('NodeGroupOutput', 'Production floor and diagnostics')
    h.link(next(s for s in end.outputs if s.identifier == 'Generation_0'), out.inputs['Geometry'])
    # Main geometry preserves placement points; generation geometry is separate.
    for name, field in [('Board Count', 'Retained'), ('Clipped Count', 'Clipped')]:
        h.link(h.stats(end.outputs[0], end.outputs[field], 'Sum'), out.inputs[name])
    small = m('MULTIPLY', m('GREATER_THAN', h.attr('original_area'), 1e-8), m('SUBTRACT', 1, h.attr('keep_board', 'BOOLEAN')))
    assigned = m('GREATER_THAN', h.attr('offcut_owner', 'INT'), -.5)
    h.link(h.stats(prepared, m('MULTIPLY', small, assigned), 'Sum'), out.inputs['Absorbed Count'])
    h.link(h.stats(prepared, m('MULTIPLY', small, m('SUBTRACT', 1, assigned)), 'Sum'), out.inputs['Sliver Count'])
    h.link(laying.outputs['Rows'], out.inputs['Row Count'])
    h.link(laying.outputs['Actual Board Width'], out.inputs['Actual Board Width'])
    h.link(laying.outputs['Closest Joint'], out.inputs['Closest Joint'])
    h.layout()
    return g


def public_group(core):
    """A small public entry point; construction details stay in a named group."""
    core.name = named('Hardwood Floor Construction')
    g = bpy.data.node_groups.new(named('Hardwood Floor'), 'GeometryNodeTree')
    g.is_modifier = True
    panels = {}
    sections = {'Room': ['Room Width', 'Room Depth', 'Rotation'],
              'Boards': ['Board Width', 'Thickness', 'Row Gap', 'Shortest Board', 'Longest Board'],
              'Laying': ['Stagger Target', 'Min Sliver Area', 'Layout Seed'],
              'Appearance': ['Color Seed', 'Color A', 'Color B', 'Use Base Color Variation', 'Base Color', 'Color Variance', 'Material']}
    for name in sections:
        panels[name] = g.interface.new_panel(name=name)
    for item in core.interface.items_tree:
        if item.item_type != 'SOCKET':
            continue
        new = g.interface.new_socket(name=item.name, in_out=item.in_out, socket_type=item.socket_type)
        for prop in ('default_value', 'min_value', 'max_value', 'subtype', 'description'):
            if hasattr(item, prop) and hasattr(new, prop):
                setattr(new, prop, getattr(item, prop))
        if item.in_out == 'INPUT':
            for section, names in sections.items():
                if item.name in names:
                    g.interface.move_to_parent(new, panels[section], 100)
    inp = g.nodes.new('NodeGroupInput')
    inp.location = (-350, 150)
    inp.width = 240
    construct = g.nodes.new('GeometryNodeGroup')
    construct.node_tree = core
    construct.location = (0, 150)
    construct.width = 260
    construct.label = 'Lay → clip each board → map and color'
    out = g.nodes.new('NodeGroupOutput')
    out.location = (400, 150)
    out.width = 220
    for s in construct.inputs:
        if s.name in inp.outputs:
            g.links.new(inp.outputs[s.name], s)
    for s in construct.outputs:
        if s.name in out.inputs:
            g.links.new(s, out.inputs[s.name])
    return g
