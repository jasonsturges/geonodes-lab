"""GNL • Brick Pier: stretcher bond, alternating stone quoins, mortar core, plinth and cap.

Origin: the website graveyard's BrickPierGeometry.ts (which places three-low-poly's QuoinStackGeometry
at the corners), first explored in the NodesLab prototype's study 032. Its laying loop becomes
"overprovision and filter": one point per possible brick slot, closed-form stretcher-bond arithmetic,
and Delete Geometry for the slots the loop would never lay.
"""
import math

from authoring.graph import Graph
from authoring.naming import named


def rand(G, index, k, seed):
    node = G.n('ShaderNodeTexWhiteNoise', f'Random channel {k}', noise_dimensions='4D')
    G.link(G.xyz(index, k, 0), node.inputs['Vector'])
    G.link(seed, node.inputs['W'])
    return G.sub(G.mul(node.outputs['Value'], 2), 1)


def unit(G, index, k, seed):
    return G.mul(G.add(rand(G, index, k, seed), 1), .5)


def box(G, size, centre, label):
    cube = G.n('GeometryNodeMeshCube', label)
    G.link(size, cube.inputs['Size'])
    node = G.n('GeometryNodeTransform', f'{label} position')
    G.link(cube.outputs['Mesh'], node.inputs['Geometry'])
    G.link(centre, node.inputs['Translation'])
    return node.outputs[0]


def set_material(G, geometry, material):
    node = G.n('GeometryNodeSetMaterial', 'Material')
    G.link(geometry, node.inputs['Geometry'])
    G.link(material, node.inputs['Material'])
    return node.outputs[0]


def cubes_on_points(G, points, label):
    """A unit cube on every point, scaled by its 'size' and turned by its 'yaw' attributes."""
    cube = G.n('GeometryNodeMeshCube', 'Unit cube')
    inst = G.n('GeometryNodeInstanceOnPoints', label)
    G.link(points, inst.inputs['Points'])
    G.link(cube.outputs['Mesh'], inst.inputs['Instance'])
    G.link(G.xyz(0, 0, G.named('yaw')), inst.inputs['Rotation'])
    G.link(G.named('size', 'FLOAT_VECTOR'), inst.inputs['Scale'])
    real = G.n('GeometryNodeRealizeInstances', 'Real geometry')
    G.link(inst.outputs[0], real.inputs['Geometry'])
    return real.outputs[0]


SPEC = {
    'Shaft': ['Width', 'Height'],
    'Bricks': ['Brick Length', 'Brick Height', 'Brick Depth', 'Mortar', 'Min Bat', 'Brick Wander'],
    'Quoins': ['Long Leg', 'Short Leg', 'Proud'],
    'Plinth and Cap': ['Plinth Width', 'Plinth Height', 'Cap Width', 'Cap Height'],
    'Decay': ['Decay Seed', 'Missing Bricks', 'Missing Quoins', 'Missing Cap'],
    'Surface': ['Seed', 'Brick', 'Mortar Material', 'Quoin', 'Stone'],
}


def pier_group():
    G = Graph(named('Brick Pier'), modifier=True)
    G.input('Geometry', 'NodeSocketGeometry')
    for name, kind, default, lo, hi, text in [
            ('Width', 'NodeSocketFloat', .9, .3, 4.0, 'Square shaft width.'),
            ('Height', 'NodeSocketFloat', 2.6, .3, 10.0, 'Shaft height, plinth to cap. Courses are fitted to it.'),
            ('Brick Length', 'NodeSocketFloat', .3, .05, 1.0, ''),
            ('Brick Height', 'NodeSocketFloat', .1, .02, .5, 'Nominal; the fitted course adjusts it slightly.'),
            ('Brick Depth', 'NodeSocketFloat', .12, .02, .5, 'How far a brick reaches in from the face.'),
            ('Mortar', 'NodeSocketFloat', .014, .0, .05, 'The joint, which ADDS to the pitch.'),
            ('Min Bat', 'NodeSocketFloat', .25, .0, 1.0, 'A closer shorter than this × a brick is not laid.'),
            ('Brick Wander', 'NodeSocketFloat', .004, .0, .03, 'Each brick stands in or out of the face by up to this.'),
            ('Long Leg', 'NodeSocketFloat', .3, .05, 1.0, 'Quoin long return.'),
            ('Short Leg', 'NodeSocketFloat', .18, .05, 1.0, 'Quoin short return.'),
            ('Proud', 'NodeSocketFloat', .025, .0, .1, 'Quoins stand out of both faces by this.'),
            ('Plinth Width', 'NodeSocketFloat', 1.2, .3, 5.0, ''),
            ('Plinth Height', 'NodeSocketFloat', .5, .0, 3.0, ''),
            ('Cap Width', 'NodeSocketFloat', 1.35, .3, 5.0, ''),
            ('Cap Height', 'NodeSocketFloat', .3, .0, 2.0, ''),
            ('Decay Seed', 'NodeSocketInt', 1, 0, 65535, 'Which bricks and quoins are gone.'),
            ('Missing Bricks', 'NodeSocketFloat', 0.0, 0.0, 1.0, 'Chance each brick is gone.'),
            ('Missing Quoins', 'NodeSocketFloat', 0.0, 0.0, 1.0, 'Chance each quoin is gone.'),
            ('Missing Cap', 'NodeSocketBool', False, None, None, 'The cap and its course have fallen.'),
            ('Seed', 'NodeSocketInt', 0x6272, 0, 65535, 'Brick wander and tone.'),
            ('Brick', 'NodeSocketMaterial', None, None, None, 'Reads the per-brick "tone" attribute (-1…1).'),
            ('Mortar Material', 'NodeSocketMaterial', None, None, None, ''),
            ('Quoin', 'NodeSocketMaterial', None, None, None, 'Reads "tone" too.'),
            ('Stone', 'NodeSocketMaterial', None, None, None, 'Plinth, cap and their courses.')]:
        G.input(name, kind, default, lo, hi, text)
    G.output('Geometry')
    G.output('Top', 'NodeSocketFloat')
    G.output('Courses', 'NodeSocketInt')
    G.finish_io()
    i = G.i
    w, h, m = i['Width'], i['Height'], i['Mortar']
    half = G.mul(w, .5)
    b, depth = i['Brick Length'], i['Brick Depth']
    # Coursing: the quoin stack fits its course to the height; the bricks follow that gauge.
    courses = G.hi(1, G.m('ROUND', G.div(h, G.add(i['Brick Height'], m))))
    gauge = G.div(h, courses)
    brick_h = G.sub(gauge, m)
    base = i['Plinth Height']

    # --- Bricks: points for every (face, course, slot); keep the slots a course really lays. -------
    slots = G.add(G.m('CEIL', G.div(w, G.add(b, m))), 2)      # generous upper bound per course
    per_face = G.mul(courses, slots)
    grid = G.points(G.mul(per_face, 4), (0, 0, 0))
    idx = G.index
    face = G.m('FLOOR', G.div(idx, per_face))
    course = G.m('FLOOR', G.div(G.m('FLOORED_MODULO', idx, per_face), slots))
    slot = G.m('FLOORED_MODULO', idx, slots)
    odd = G.m('FLOORED_MODULO', course, 2)
    start_leg = G.switch('FLOAT', odd, i['Long Leg'], i['Short Leg'])
    end_leg = G.switch('FLOAT', odd, i['Short Leg'], i['Long Leg'])
    lo = G.add(start_leg, m)
    hi = G.sub(G.sub(w, end_leg), m)
    # Stretcher bond: on odd courses slot 0 is a half brick and the rest shift by it.
    start = G.add(lo, G.switch('FLOAT', odd, G.mul(slot, G.add(b, m)),
                               G.switch('FLOAT', G.m('COMPARE', slot, 0), G.add(G.mul(b, .5), G.add(m, G.mul(G.sub(slot, 1), G.add(b, m)))), 0.0)))
    nominal = G.switch('FLOAT', G.m('MULTIPLY', odd, G.m('COMPARE', slot, 0)), b, G.mul(b, .5))
    length = G.lo(nominal, G.sub(hi, start))
    closer = G.m('LESS_THAN', length, G.sub(nominal, 1e-6))
    laid = G.m('MULTIPLY', G.m('LESS_THAN', start, G.sub(hi, 1e-6)),
               G.sub(1, G.m('MULTIPLY', closer, G.m('LESS_THAN', length, G.mul(b, i['Min Bat'])))))
    gone = G.m('LESS_THAN', unit(G, idx, 1, i['Decay Seed']), i['Missing Bricks'])
    bricks = G.store(grid, 'length', length)
    bricks = G.store(bricks, 'face', face)
    bricks = G.store(bricks, 'course', course)
    bricks = G.store(bricks, 'start', start)
    bricks = G.store(bricks, 'tone', rand(G, idx, 2, i['Seed']))
    bricks = G.store(bricks, 'wander', G.mul(i['Brick Wander'], rand(G, idx, 3, i['Seed'])))
    bricks = G.delete(bricks, G.m('MAXIMUM', G.sub(1, laid), gone))
    # Faces run anticlockwise from the front (−Y): outward normal n and run direction a = (−n.y, n.x)·…
    yaw = G.mul(G.named('face'), math.pi / 2)             # face f is the front turned f quarter-turns
    along = G.sub(G.add(G.named('start'), G.mul(G.named('length'), .5)), half)
    out = G.add(G.sub(half, G.mul(depth, .5)), G.named('wander'))
    z = G.add(G.add(base, G.mul(G.named('course'), gauge)), G.add(G.mul(m, .5), G.mul(brick_h, .5)))
    # Front face: along +X, outward −Y. Rotate that frame by yaw.
    cy, sy = G.m('COSINE', yaw), G.m('SINE', yaw)
    px = G.add(G.mul(along, cy), G.mul(out, sy))              # (along, −out) rotated by yaw
    py = G.sub(G.mul(along, sy), G.mul(out, cy))
    bricks = G.set_position(bricks, G.xyz(px, py, z))
    bricks = G.store(bricks, 'yaw', yaw)
    bricks = G.store(bricks, 'size', G.xyz(G.named('length'), depth, brick_h), kind='FLOAT_VECTOR')
    bricks = cubes_on_points(G, bricks, 'A brick on every laid slot')

    # --- Quoins: 4 corners × courses. Corner f sits at the START of face f. ------------------------
    qpoints = G.points(G.mul(courses, 4), (0, 0, 0))
    q = G.index
    corner = G.m('FLOOR', G.div(q, courses))
    qc = G.m('FLOORED_MODULO', q, courses)
    qodd = G.m('FLOORED_MODULO', qc, 2)
    on_face = G.switch('FLOAT', qodd, i['Long Leg'], i['Short Leg'])     # along face f (it starts here)
    on_prev = G.switch('FLOAT', qodd, i['Short Leg'], i['Long Leg'])     # back along face f−1
    proud = i['Proud']
    # In the front frame (corner 0 at (−half, −half)): the stone runs +X by on_face and +Y by on_prev,
    # from the outer corner (−half−proud, −half−proud).
    lx = G.add(G.sub(G.mul(half, -1), proud), G.mul(on_face, .5))
    ly = G.add(G.sub(G.mul(half, -1), proud), G.mul(on_prev, .5))
    qyaw = G.mul(corner, math.pi / 2)
    cq, sq = G.m('COSINE', qyaw), G.m('SINE', qyaw)
    qx = G.sub(G.mul(lx, cq), G.mul(ly, sq))
    qy = G.add(G.mul(lx, sq), G.mul(ly, cq))
    qz = G.add(base, G.mul(G.add(qc, .5), gauge))
    qgone = G.m('LESS_THAN', unit(G, q, 4, i['Decay Seed']), i['Missing Quoins'])
    quoins = G.store(qpoints, 'tone', rand(G, q, 5, i['Seed']))
    quoins = G.set_position(quoins, G.xyz(qx, qy, qz))
    quoins = G.store(quoins, 'yaw', qyaw)
    quoins = G.store(quoins, 'size', G.xyz(on_face, on_prev, G.mul(gauge, .96)), kind='FLOAT_VECTOR')
    quoins = G.delete(quoins, qgone)
    quoins = cubes_on_points(G, quoins, 'A quoin on every corner course')

    # --- Mortar core, plinth, cap and their courses. --------------------------------------------------
    shaft_top = G.add(base, h)
    core_w = G.sub(w, .02)
    core = box(G, G.xyz(core_w, core_w, h), G.xyz(0, 0, G.add(base, G.mul(h, .5))), 'Mortar core')
    plinth = box(G, G.xyz(i['Plinth Width'], i['Plinth Width'], base), G.xyz(0, 0, G.mul(base, .5)), 'Plinth')
    foot = box(G, G.xyz(G.add(w, .12), G.add(w, .12), .08), G.xyz(0, 0, G.add(base, .04)), 'Plinth course')
    cap = box(G, G.xyz(i['Cap Width'], i['Cap Width'], i['Cap Height']),
              G.xyz(0, 0, G.add(shaft_top, G.mul(i['Cap Height'], .5))), 'Cap')
    neck = box(G, G.xyz(G.add(w, .16), G.add(w, .16), .08), G.xyz(0, 0, G.sub(shaft_top, .04)), 'Cap course')
    stone = G.join(plinth, foot, G.switch('GEOMETRY', i['Missing Cap'], G.join(cap, neck), None))

    result = G.join(set_material(G, bricks, i['Brick']), set_material(G, core, i['Mortar Material']),
                    set_material(G, quoins, i['Quoin']), set_material(G, stone, i['Stone']))
    flat = G.n('GeometryNodeSetShadeSmooth', 'Flat')
    G.link(result, flat.inputs['Mesh'])
    flat.inputs['Shade Smooth'].default_value = False
    G.link(flat.outputs[0], G.o['Geometry'])
    G.link(G.switch('FLOAT', i['Missing Cap'], G.add(shaft_top, i['Cap Height']), shaft_top), G.o['Top'])
    G.link(courses, G.o['Courses'])
    G.layout()
    for title, names in SPEC.items():
        panel = G.g.interface.new_panel(name=title, default_closed=title in ('Decay', 'Plinth and Cap'))
        for name in names:
            G.g.interface.move_to_parent(G.g.interface.items_tree[name], panel, 100)
    G.g.description = 'A square brick pier: stretcher bond, alternating stone quoins, mortar core, plinth and cap.'
    return G.g


# ---------------------------------------------------------------------------
# Materials and scene
# ---------------------------------------------------------------------------
