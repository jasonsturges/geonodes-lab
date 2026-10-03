"""GNL • Gateway: two brick piers, the overthrow seated on their tops, two hinged gate leaves, and one
Ruin control (NodesLab study 036; website graveyard Gateway.ts)."""
import math

import bpy

from authoring.graph import Graph
from authoring.naming import named
from common import rand, unit, foreach, generation, transform, rand1


GATEWAY_SPEC = {
    'Opening': ['Opening Width', 'Pier Width', 'Pier Height'],
    'Gates': ['Gate Height', 'Gap', 'Bar Radius', 'Rings', 'Swing Left', 'Swing Right', 'Clearance'],
    'Overthrow': ['Shape', 'Rise', 'Infill', 'Centre', 'Crown', 'Ivy'],
    'Ruin': ['Ruin', 'Decay Seed'],
    'Surface': ['Brick', 'Mortar', 'Quoin', 'Stone', 'Iron', 'Rust'],
}


def gateway_group(pier, arch, panel):
    G = Graph(named('Gateway'), modifier=True)
    G.input('Geometry', 'NodeSocketGeometry')
    for name, kind, default, lo, hi, text in [
            ('Opening Width', 'NodeSocketFloat', 3.0, .8, 12.0, 'Clear width between the pier faces.'),
            ('Pier Width', 'NodeSocketFloat', .9, .3, 3.0, ''),
            ('Pier Height', 'NodeSocketFloat', 2.6, .5, 8.0, 'Brick shaft height (plinth and cap add to it).'),
            ('Gate Height', 'NodeSocketFloat', 2.4, .3, 6.0, 'Picket height of the gate leaves.'),
            ('Gap', 'NodeSocketFloat', .26, .0, 1.0, 'Clear air between pickets.'),
            ('Bar Radius', 'NodeSocketFloat', .04, .005, .2, ''),
            ('Rings', 'NodeSocketBool', True, None, None, 'Fitted ring band (website gate doors).'),
            ('Swing Left', 'NodeSocketFloat', math.radians(45), -math.pi / 2, math.pi / 2, 'Open angle; + swings away from the viewer.'),
            ('Swing Right', 'NodeSocketFloat', math.radians(-24), -math.pi / 2, math.pi / 2, ''),
            ('Clearance', 'NodeSocketFloat', .05, .0, .5, 'Gap under the leaves.'),
            ('Shape', 'NodeSocketMenu', None, None, None, ''),
            ('Rise', 'NodeSocketFloat', 2.0, .2, 10.0, 'Elliptical / Pointed crown height.'),
            ('Infill', 'NodeSocketMenu', None, None, None, ''),
            ('Centre', 'NodeSocketMenu', None, None, None, ''),
            ('Crown', 'NodeSocketMenu', None, None, None, ''),
            ('Ivy', 'NodeSocketBool', False, None, None, ''),
            ('Ruin', 'NodeSocketFloat', 0.0, 0.0, 1.0, 'Ages everything: bricks, spokes, pickets, a failed hinge, rust.'),
            ('Decay Seed', 'NodeSocketInt', 1, 0, 65535, 'Which bricks, spokes and pickets; which hinge fails.'),
            ('Brick', 'NodeSocketMaterial', None, None, None, ''),
            ('Mortar', 'NodeSocketMaterial', None, None, None, ''),
            ('Quoin', 'NodeSocketMaterial', None, None, None, ''),
            ('Stone', 'NodeSocketMaterial', None, None, None, ''),
            ('Iron', 'NodeSocketMaterial', None, None, None, ''),
            ('Rust', 'NodeSocketMaterial', None, None, None, 'Iron once the gateway is mostly ruined.')]:
        sub = 'ANGLE' if name.startswith('Swing') else None
        G.input(name, kind, default, lo, hi, text, subtype=sub)
    G.output('Geometry')
    G.output('Top', 'NodeSocketFloat')
    G.finish_io()
    i = G.i
    W, pw, ruin, seed = i['Opening Width'], i['Pier Width'], i['Ruin'], i['Decay Seed']
    half = G.mul(W, .5)
    centre = G.add(half, G.mul(pw, .5))

    # --- Piers: one each side, each its own decay seed; ruin removes bricks and quoins. -----------
    def one_pier(side, label):
        node = G.group(pier, label)
        G.link(pw, node.inputs['Width'])
        G.link(i['Pier Height'], node.inputs['Height'])
        G.link(G.mul(pw, 1.33), node.inputs['Plinth Width'])
        G.link(G.mul(pw, 1.5), node.inputs['Cap Width'])
        G.link(G.mul(ruin, .3), node.inputs['Missing Bricks'])
        G.link(G.mul(ruin, .2), node.inputs['Missing Quoins'])
        G.link(G.m('GREATER_THAN', G.mul(ruin, rand1(G, 10 + side, seed)), .55), node.inputs['Missing Cap'])
        G.link(G.add(G.mul(seed, 2), side + 1), node.inputs['Decay Seed'])
        for key in ('Brick', 'Stone'):
            G.link(i[key], node.inputs[key])
        G.link(i['Mortar'], node.inputs['Mortar Material'])
        G.link(i['Quoin'], node.inputs['Quoin'])
        placed = transform(G, node.outputs['Geometry'], translation=G.xyz(G.mul(centre, side), 0, 0), label=f'{label} in place')
        return placed, node.outputs['Top']
    left, top_l = one_pier(-1, 'Left pier')
    right, top_r = one_pier(1, 'Right pier')
    top = G.hi(top_l, top_r)

    # --- Overthrow: legs land on the cap tops; its span is pier centre to pier centre. ------------
    iron = G.switch('MATERIAL', G.m('GREATER_THAN', ruin, .5), i['Iron'], i['Rust'])
    over = G.group(arch, 'Overthrow')
    G.link(G.mul(centre, 2), over.inputs['Span'])
    for key in ('Shape', 'Rise', 'Infill', 'Centre', 'Crown', 'Ivy'):
        G.link(i[key], over.inputs[key])
    G.link(G.mul(ruin, .35), over.inputs['Missing Spokes'])
    G.link(seed, over.inputs['Decay Seed'])
    G.link(iron, over.inputs['Material'])
    leg = over.inputs['Leg Height'].default_value
    arch_geo = transform(G, over.outputs['Geometry'], translation=G.xyz(0, 0, G.add(top, leg)), label='On the caps')

    # --- Gate leaves: hinged at the pier faces, swung open; ruin bends pickets and fails a hinge. --
    leaf_len = G.sub(half, .05)

    def leaf(side, swing, label):
        node = G.group(panel, label)
        G.link(leaf_len, node.inputs['Length'])
        G.link(i['Gate Height'], node.inputs['Bar Height'])
        G.link(i['Gap'], node.inputs['Gap'])
        G.link(i['Bar Radius'], node.inputs['Bar Radius'])
        G.link(i['Rings'], node.inputs['Rings'])
        node.inputs['Finial Height'].default_value = .22
        node.inputs['Finial Radius'].default_value = .07
        G.link(G.mul(ruin, .15), node.inputs['Missing Pickets'])
        G.link(G.mul(ruin, .35), node.inputs['Bent Pickets'])
        G.link(G.add(G.mul(seed, 3), side + 5), node.inputs['Decay Seed'])
        # Hinge edge at the origin: the leaf runs inward (toward the opening's centre) from its hinge.
        geo = transform(G, node.outputs['Mesh'], translation=G.xyz(G.mul(G.add(G.mul(leaf_len, .5), .02), -side), 0, 0),
                        label=f'{label} hinge at origin')
        # A failed hinge (one leaf, chosen by the seed): the free end drops and the leaf twists.
        fails = G.mul(G.m('GREATER_THAN', ruin, .3),
                      G.m('LESS_THAN' if side < 0 else 'GREATER_THAN', rand1(G, 20, seed), .5))
        droop = G.mul(G.mul(fails, G.mul(ruin, .12)), side)
        geo = transform(G, geo, rotation=G.xyz(G.mul(fails, .05), droop, 0), label=f'{label} sag')
        geo = transform(G, geo, rotation=G.xyz(0, 0, G.mul(swing, -side)), label=f'{label} swing')
        geo = transform(G, geo, translation=G.xyz(G.mul(half, side), 0, i['Clearance']), label=f'{label} at the pier')
        mat = G.n('GeometryNodeSetMaterial', f'{label} iron')
        G.link(geo, mat.inputs['Geometry'])
        G.link(iron, mat.inputs['Material'])
        return mat.outputs[0]
    gates = G.join(leaf(-1, i['Swing Left'], 'Left leaf'), leaf(1, i['Swing Right'], 'Right leaf'))

    G.link(G.join(left, right, arch_geo, gates), G.o['Geometry'])
    G.link(top, G.o['Top'])
    G.layout()
    G.g.interface_update(bpy.context)
    for name in ('Shape', 'Infill', 'Centre', 'Crown'):
        # 'Infill' names both a panel and a socket in GNL • Overthrow: look up the socket.
        source = next(x for x in arch.interface.items_tree if x.item_type == 'SOCKET' and x.name == name)
        G.g.interface.items_tree[name].default_value = source.default_value
    for title, names in GATEWAY_SPEC.items():
        p = G.g.interface.new_panel(name=title, default_closed=title == 'Surface')
        for name in names:
            G.g.interface.move_to_parent(G.g.interface.items_tree[name], p, 100)
    G.g.description = 'Two brick piers, an overthrow on their caps, two hinged gate leaves; one Ruin control.'
    return G.g
