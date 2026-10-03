"""GNL • Overthrow: the arch over a gateway, composed from the ironwork vocabulary."""
import math

import bpy

from authoring.graph import Graph
from authoring.naming import named
from common import rand, unit, transform, panels, menu, sweep, square, circle, vertical_line


def round_bar(G, curve, radius, sides=6, label='Round bar'):
    section = G.n('GeometryNodeCurvePrimitiveCircle', f'{label} section')
    G.link(radius, section.inputs['Radius'])
    section.inputs['Resolution'].default_value = sides
    sweep = G.n('GeometryNodeCurveToMesh', label)
    G.link(curve, sweep.inputs['Curve'])
    G.link(section.outputs[0], sweep.inputs['Profile Curve'])
    sweep.inputs['Fill Caps'].default_value = True
    return sweep.outputs[0]


def realize(G, inst, label):
    node = G.n('GeometryNodeRealizeInstances', label)
    G.link(inst, node.inputs['Geometry'])
    return node.outputs[0]


OVERTHROW_SPEC = {
    'Arch': ['Span', 'Shape', 'Rise', 'Leg Height', 'Inner Ratio'],
    'Bars': ['Arch Bar', 'Tie Bar', 'Inner Bar', 'Spoke Bar'],
    'Infill': ['Infill', 'Spokes', 'Scroll Bar'],
    'Ornament': ['Centre', 'Crown', 'Ivy'],
    'Decay': ['Decay Seed', 'Missing Spokes'],
    'Surface': ['Material'],
}


def overthrow_group(orn):
    G = Graph(named('Overthrow'), modifier=True)
    G.input('Geometry', 'NodeSocketGeometry')
    for name, kind, default, lo, hi, text in [
            ('Span', 'NodeSocketFloat', 3.0, .5, 20.0, 'Springing to springing, centre of the arch bar.'),
            ('Shape', 'NodeSocketMenu', None, None, None, 'Semicircle, Elliptical (any rise) or Pointed (gothic).'),
            ('Rise', 'NodeSocketFloat', 1.1, .1, 10.0, 'Elliptical and Pointed: crown height above the springing.'),
            ('Leg Height', 'NodeSocketFloat', .2, 0.0, 2.0, 'The arch bar continues straight down by this at each end.'),
            ('Inner Ratio', 'NodeSocketFloat', .64, .2, .95, 'Inner arc as a fraction of the outer (website 0.64).'),
            ('Arch Bar', 'NodeSocketFloat', .05, .005, .3, 'Radius.'),
            ('Tie Bar', 'NodeSocketFloat', .032, .005, .3, ''),
            ('Inner Bar', 'NodeSocketFloat', .032, .005, .3, ''),
            ('Spoke Bar', 'NodeSocketFloat', .018, .003, .2, ''),
            ('Infill', 'NodeSocketMenu', None, None, None, 'Spokes, Spokes and Volutes, Gap Scrolls or None.'),
            ('Spokes', 'NodeSocketInt', 9, 2, 64, ''),
            ('Scroll Bar', 'NodeSocketFloat', .024, .003, .2, 'Width of volute and scroll bar.'),
            ('Centre', 'NodeSocketMenu', None, None, None, 'Medallion (stem, paired C scrolls, leaf clasp) or None.'),
            ('Crown', 'NodeSocketMenu', None, None, None, 'Ball and Spike, Fleur-de-lis or None.'),
            ('Ivy', 'NodeSocketBool', False, None, None, 'A forged ivy vine winding along the arch.'),
            ('Decay Seed', 'NodeSocketInt', 1, 0, 65535, ''),
            ('Missing Spokes', 'NodeSocketFloat', 0.0, 0.0, 1.0, 'Chance each spoke (and its ornament) is gone.'),
            ('Material', 'NodeSocketMaterial', None, None, None, '')]:
        G.input(name, kind, default, lo, hi, text)
    G.output('Geometry')
    G.output('Apex', 'NodeSocketFloat')
    G.finish_io()
    i = G.i
    H = G.mul(i['Span'], .5)

    # A menu input can drive only ONE Menu Switch (each switch defines its own item list), so the
    # shape menu becomes an index once, and Index Switches pick per shape everywhere after.
    shape_menu = G.n('GeometryNodeMenuSwitch', 'Shape → index', data_type='INT')
    shape_menu.enum_items.clear()
    for k, name in enumerate(('Semicircle', 'Elliptical', 'Pointed')):
        shape_menu.enum_items.new(name)
        shape_menu.inputs[name].default_value = k
    G.link(i['Shape'], shape_menu.inputs['Menu'])
    shape = shape_menu.outputs[0]

    # --- The arch as a function of t (0 at the right springing, 1 at the left). ------------------
    def arch(t, scale=1.0):
        a = G.mul(t, math.pi)
        semi = G.xyz(G.mul(H, G.m('COSINE', a)), 0, G.mul(H, G.m('SINE', a)))
        ell = G.xyz(G.mul(H, G.m('COSINE', a)), 0, G.mul(i['Rise'], G.m('SINE', a)))
        # Pointed: two arcs through the springings and the apex (0, Rise), centres on the springing line.
        rho = G.div(G.add(G.mul(H, H), G.mul(i['Rise'], i['Rise'])), G.mul(H, 2))
        c = G.sub(H, rho)
        amax = G.m('ARCTAN2', i['Rise'], G.mul(c, -1))
        right = G.m('LESS_THAN', t, .5)
        u = G.switch('FLOAT', right, G.mul(G.sub(1, t), 2), G.mul(t, 2))
        ang = G.mul(u, amax)
        px = G.add(c, G.mul(rho, G.m('COSINE', ang)))
        pointed = G.xyz(G.switch('FLOAT', right, G.mul(px, -1), px), 0, G.mul(rho, G.m('SINE', ang)))
        return G.v('SCALE', G.pick(shape, [semi, ell, pointed]), scale=scale)

    apex = G.pick(shape, [H, i['Rise'], i['Rise']], kind='FLOAT')

    N = 96

    def arch_curve(scale, legs, label):
        count = N + 1 + (2 if legs else 0)
        line = G.n('GeometryNodeMeshLine', f'{label} stations')
        line.inputs['Count'].default_value = count
        k = G.index
        if legs:
            t = G.div(G.lo(G.hi(G.sub(k, 1), 0), N), N)
            base = arch(t, scale)
            leg_r = G.xyz(H, 0, G.mul(i['Leg Height'], -1))
            leg_l = G.xyz(G.mul(H, -1), 0, G.mul(i['Leg Height'], -1))
            pos = G.switch('VECTOR', G.m('COMPARE', k, 0), G.switch('VECTOR', G.m('COMPARE', k, N + 2), base, leg_l), leg_r)
        else:
            pos = arch(G.div(k, N), scale)
        curve = G.n('GeometryNodeMeshToCurve', label)
        G.link(G.set_position(line.outputs['Mesh'], pos), curve.inputs['Mesh'])
        return curve.outputs[0]

    outer = round_bar(G, arch_curve(1.0, True, 'Arch'), i['Arch Bar'], 8, 'Arch bar')
    inner = round_bar(G, arch_curve(i['Inner Ratio'], False, 'Inner arc'), i['Inner Bar'], 6, 'Inner arc bar')
    tie_line = G.n('GeometryNodeCurvePrimitiveLine', 'Tie')
    G.link(G.xyz(G.mul(H, -1), 0, 0), tie_line.inputs['Start'])
    G.link(G.xyz(H, 0, 0), tie_line.inputs['End'])
    tie = round_bar(G, tie_line.outputs[0], i['Tie Bar'], 6, 'Tie bar')

    # --- Spokes: from the inner arc to the outer at the same t (website: 8%…92% of the arch). -----
    n = i['Spokes']
    spokes_pts = G.points(n, (0, 0, 0))
    tk = G.add(.08, G.div(G.mul(.84, G.index), G.hi(G.sub(n, 1), 1)))
    gone = G.m('LESS_THAN', G.mul(G.add(rand(G, G.index, 1, i['Decay Seed']), 1), .5), i['Missing Spokes'])
    start = arch(tk, i['Inner Ratio'])
    end = arch(tk)
    spokes_pts = G.store(spokes_pts, 'start', start, kind='FLOAT_VECTOR')
    spokes_pts = G.store(spokes_pts, 'dir', G.v('SUBTRACT', end, start), kind='FLOAT_VECTOR')
    spokes_pts = G.store(spokes_pts, 't', tk)
    spokes_pts = G.delete(spokes_pts, gone)
    spokes_pts = G.set_position(spokes_pts, G.named('start', 'FLOAT_VECTOR'))
    rod = G.n('GeometryNodeMeshCylinder', 'Unit rod', fill_type='NGON')
    rod.inputs['Vertices'].default_value = 6
    rod.inputs['Depth'].default_value = 1.0
    G.link(i['Spoke Bar'], rod.inputs['Radius'])
    rod = transform(G, rod.outputs['Mesh'], translation=(0, 0, .5), label='Rod from its foot')
    align = G.n('FunctionNodeAlignRotationToVector', 'Along the spoke', axis='Z')
    G.link(G.named('dir', 'FLOAT_VECTOR'), align.inputs['Vector'])
    inst = G.n('GeometryNodeInstanceOnPoints', 'A rod per spoke')
    G.link(spokes_pts, inst.inputs['Points'])
    G.link(rod, inst.inputs['Instance'])
    G.link(align.outputs['Rotation'], inst.inputs['Rotation'])
    G.link(G.xyz(1, 1, G.v('LENGTH', G.named('dir', 'FLOAT_VECTOR'))), inst.inputs['Scale'])
    spokes = realize(G, inst.outputs[0], 'Real spokes')

    # --- Volutes laid against the spokes (gate-ornament "touch"): open end on the spoke at mid
    # radius, curling toward the centre line. GNL • Scroll lies in XY: open end (r0, 0) heading +Y.
    mid_r = G.mul(G.add(1, i['Inner Ratio']), .5)
    r0 = G.mul(i['Span'], .055)
    vol = G.group(orn[named('Scroll')], 'Volute')
    G.link(r0, vol.inputs['Start Radius'])
    vol.inputs['Turns'].default_value = 1.2
    vol.inputs['Tightness'].default_value = .26
    G.link(i['Scroll Bar'], vol.inputs['Bar Width'])
    G.link(G.mul(i['Scroll Bar'], .45), vol.inputs['Bar Thickness'])
    vol.inputs['Segments'].default_value = 48
    vol_xz = transform(G, vol.outputs['Mesh'], rotation=(math.pi / 2, 0, 0), label='Volute into XZ')
    vol_f = G.group(orn[named('Scroll')], 'Volute, mirrored')
    for name in ('Start Radius', 'Bar Width', 'Bar Thickness'):
        G.link(vol.inputs[name].links[0].from_socket, vol_f.inputs[name])
    for name, value in (('Turns', 1.2), ('Tightness', .26), ('Segments', 48)):
        vol_f.inputs[name].default_value = value
    vol_f.inputs['Flip'].default_value = True
    vol_f_xz = transform(G, vol_f.outputs['Mesh'], rotation=(math.pi / 2, 0, 0), label='Mirrored volute into XZ')
    centre_t = G.mul(G.sub(G.named('t'), .5), 1)
    mid = arch(G.named('t'), mid_r)
    mx, _, mz = G.sep(mid)
    d = G.v('NORMALIZE', G.named('dir', 'FLOAT_VECTOR'))
    dx, _, dz = G.sep(d)
    # In-plane perpendicular to the spoke, (−dz, dx), flipped if needed so it points toward x = 0.
    toward = G.mul(G.m('SIGN', G.mul(G.mul(dz, -1), mx)), -1)
    nx, nz = G.mul(G.mul(dz, -1), toward), G.mul(dx, toward)
    phi = G.m('ARCTAN2', nz, G.mul(nx, -1))
    not_centre = G.m('GREATER_THAN', G.m('ABSOLUTE', centre_t), .02)
    vpts = G.set_position(spokes_pts, G.v('ADD', mid, G.xyz(G.mul(nx, r0), 0, G.mul(nz, r0))))

    def volutes(geometry, right_side, label):
        inst = G.n('GeometryNodeInstanceOnPoints', label)
        G.link(vpts, inst.inputs['Points'])
        G.link(geometry, inst.inputs['Instance'])
        side = G.m('GREATER_THAN', mx, 0) if right_side else G.m('LESS_THAN', mx, 0)
        G.link(G.m('MULTIPLY', side, not_centre), inst.inputs['Selection'])
        G.link(G.xyz(0, phi, 0), inst.inputs['Rotation'])
        return realize(G, inst.outputs[0], f'{label} (real)')
    volute_geo = G.join(volutes(vol_xz, True, 'Right volutes'), volutes(vol_f_xz, False, 'Left volutes'))

    # --- Gap scrolls: an S scroll across each gap between spokes, tangential at mid radius. -------
    gaps = G.points(G.sub(n, 1), (0, 0, 0))
    tg = G.add(.08, G.div(G.mul(.84, G.add(G.index, .5)), G.hi(G.sub(n, 1), 1)))
    t_step = G.div(.84, G.hi(G.sub(n, 1), 1))
    ga = arch(G.sub(tg, G.mul(t_step, .5)), mid_r)
    gb = arch(G.add(tg, G.mul(t_step, .5)), mid_r)
    gap_w = G.sub(G.v('DISTANCE', ga, gb), G.mul(i['Spoke Bar'], 3))
    gx, _, gz = G.sep(G.v('SUBTRACT', gb, ga))
    gaps = G.set_position(gaps, arch(tg, mid_r))
    ds = G.group(orn[named('Double Scroll')], 'Gap scroll')
    ds.inputs['Fit Width'].default_value = 1.0
    # Built at width 1 and scaled to each gap, so the bar is given as a fraction of a typical gap.
    # The gap at the crown of *this* arch shape (a single value: the field at a constant t).
    typical = G.v('DISTANCE', arch(G.sub(.5, G.mul(t_step, .5)), mid_r), arch(G.add(.5, G.mul(t_step, .5)), mid_r))
    # Fitting to width 1 scales the bar by 1 / natural width; each instance then scales by its gap.
    s_probe = G.group(orn[named('Double Scroll')], 'S natural size probe')
    s_probe.inputs['Fit Width'].default_value = 0.0
    s_bounds = G.n('GeometryNodeBoundBox', 'S natural width')
    G.link(s_probe.outputs[0], s_bounds.inputs['Geometry'])
    sx0, _, _ = G.sep(s_bounds.outputs['Min'])
    sx1, _, _ = G.sep(s_bounds.outputs['Max'])
    pre = G.div(G.sub(sx1, sx0), typical)
    G.link(G.mul(G.mul(i['Scroll Bar'], .7), pre), ds.inputs['Bar Width'])
    G.link(G.mul(G.mul(i['Scroll Bar'], .35), pre), ds.inputs['Bar Thickness'])
    ginst = G.n('GeometryNodeInstanceOnPoints', 'A scroll per gap')
    G.link(gaps, ginst.inputs['Points'])
    G.link(ds.outputs[0], ginst.inputs['Instance'])
    G.link(G.xyz(0, G.m('ARCTAN2', G.mul(gz, -1), gx), 0), ginst.inputs['Rotation'])
    G.link(gap_w, ginst.inputs['Scale'])
    gap_geo = realize(G, ginst.outputs[0], 'Real gap scrolls')

    fill = G.n('GeometryNodeMenuSwitch', 'Infill', data_type='GEOMETRY')
    fill.enum_items.clear()
    for name in ('Spokes', 'Spokes and Volutes', 'Gap Scrolls', 'None'):
        fill.enum_items.new(name)
    G.link(i['Infill'], fill.inputs['Menu'])
    G.link(spokes, fill.inputs['Spokes'])
    G.link(G.join(spokes, volute_geo), fill.inputs['Spokes and Volutes'])
    G.link(G.join(spokes, gap_geo), fill.inputs['Gap Scrolls'])

    # --- Centre medallion: a stem from the tie to the inner arc, paired C scrolls, a leaf clasp. --
    inner_top = G.mul(apex, i['Inner Ratio'])
    stem_line = G.n('GeometryNodeCurvePrimitiveLine', 'Stem')
    G.link(G.xyz(0, 0, inner_top), stem_line.inputs['End'])
    stem = round_bar(G, stem_line.outputs[0], G.mul(i['Inner Bar'], .9), 6, 'Stem')
    # Double Scroll scales its bar along with its size when fitting. Measure its natural width,
    # then hand it a bar pre-shrunk by exactly the fitting factor, so the bar ends up Scroll Bar wide.
    probe = G.group(orn[named('Double Scroll')], 'Natural size probe')
    probe.inputs['Style'].default_value = 'C'
    probe.inputs['Fit Width'].default_value = 0.0
    bounds = G.n('GeometryNodeBoundBox', 'Natural width')
    G.link(probe.outputs[0], bounds.inputs['Geometry'])
    nx0, _, _ = G.sep(bounds.outputs['Min'])
    nx1, _, _ = G.sep(bounds.outputs['Max'])
    fit = G.mul(G.mul(apex, i['Inner Ratio']), .72)   # the C's span, stood upright: most of the stem
    shrink = G.div(G.sub(nx1, nx0), fit)
    pair = G.group(orn[named('Double Scroll')], 'Medallion scrolls')
    pair.inputs['Style'].default_value = 'C'
    G.link(fit, pair.inputs['Fit Width'])
    G.link(G.mul(G.mul(i['Scroll Bar'], .8), shrink), pair.inputs['Bar Width'])
    G.link(G.mul(G.mul(i['Scroll Bar'], .4), shrink), pair.inputs['Bar Thickness'])
    # A C lies with its back up and its curls down. Stood upright (a quarter turn about Y) it reads
    # "(" or ")": the left one turns its back outward, the right one too, curls in toward the stem.
    stem_r = G.mul(i['Inner Bar'], .9)
    mid_z = G.mul(inner_top, .5)

    def upright(turn, side, label):
        stood = transform(G, pair.outputs[0], rotation=(0, turn, 0), label=label)
        box = G.n('GeometryNodeBoundBox', f'{label} bounds')
        G.link(stood, box.inputs['Geometry'])
        lo_x, _, _ = G.sep(box.outputs['Min'])
        hi_x, _, _ = G.sep(box.outputs['Max'])
        # Slide it sideways until its curl edge just touches the stem.
        dx = G.sub(stem_r, lo_x) if side > 0 else G.sub(G.mul(stem_r, -1), hi_x)
        return transform(G, stood, translation=G.xyz(dx, 0, mid_z), label=f'{label} against the stem')
    pair_up = upright(math.pi / 2, 1, 'Right C')
    pair_dn = upright(-math.pi / 2, -1, 'Left C')
    clasp = G.group(orn[named('Ivy Leaf')], 'Leaf clasp')
    G.link(G.mul(H, .16), clasp.inputs['Size'])
    G.link(G.mul(H, .016), clasp.inputs['Thickness'])
    leaves = G.join(*[transform(G, clasp.outputs[0], translation=G.xyz(0, -.012, G.mul(inner_top, z)),
                                rotation=(0, ang, 0), label='Clasp leaf')
                      for z, ang in ((.5, .8), (.5, -.8), (.08, 1.1), (.08, -1.1))])
    medallion = G.join(stem, pair_up, pair_dn, leaves)
    centre = G.n('GeometryNodeMenuSwitch', 'Centre', data_type='GEOMETRY')
    centre.enum_items.clear()
    for name in ('Medallion', 'None'):
        centre.enum_items.new(name)
    G.link(i['Centre'], centre.inputs['Menu'])
    G.link(medallion, centre.inputs['Medallion'])

    # --- Crown. -------------------------------------------------------------------------------------
    k = G.div(i['Span'], 5.0)                                     # website sizes are for a 5 m span
    ball = G.n('GeometryNodeMeshUVSphere', 'Ball')
    ball.inputs['Segments'].default_value = 12
    ball.inputs['Rings'].default_value = 8
    G.link(G.mul(k, .11), ball.inputs['Radius'])
    spike = G.n('GeometryNodeMeshCone', 'Spike', fill_type='NGON')
    spike.inputs['Vertices'].default_value = 6
    G.link(G.mul(k, .085), spike.inputs['Radius Bottom'])
    G.link(G.mul(k, .42), spike.inputs['Depth'])
    top = G.add(apex, i['Arch Bar'])
    ball_spike = G.join(transform(G, ball.outputs['Mesh'], translation=G.xyz(0, 0, G.add(top, G.mul(k, .08))), label='Ball'),
                        transform(G, spike.outputs['Mesh'], translation=G.xyz(0, 0, G.add(top, G.mul(k, .17))), label='Spike'))
    fleur = G.group(orn[named('Fleur-de-lis')], 'Crown fleur')
    G.link(G.mul(k, .7), fleur.inputs['Height'])
    G.link(G.mul(k, .6), fleur.inputs['Width'])
    G.link(G.mul(k, .05), fleur.inputs['Thickness'])
    fleur_top = transform(G, fleur.outputs[0], translation=G.xyz(0, 0, G.sub(top, G.mul(i['Arch Bar'], .5))), label='Fleur on the crown')
    crown = G.n('GeometryNodeMenuSwitch', 'Crown', data_type='GEOMETRY')
    crown.enum_items.clear()
    for name in ('Ball and Spike', 'Fleur-de-lis', 'None'):
        crown.enum_items.new(name)
    G.link(i['Crown'], crown.inputs['Menu'])
    G.link(ball_spike, crown.inputs['Ball and Spike'])
    G.link(fleur_top, crown.inputs['Fleur-de-lis'])

    # --- Ivy winding along the arch, just in front of it. -------------------------------------------
    ivy_line = G.n('GeometryNodeMeshLine', 'Ivy path stations')
    ivy_line.inputs['Count'].default_value = 129
    t = G.div(G.index, 128)
    wind = G.v('ADD', arch(G.add(.03, G.mul(t, .94)), G.add(.92, G.mul(.05, G.m('SINE', G.mul(t, 9 * math.pi))))),
               G.xyz(0, G.add(-.06, G.mul(.03, G.m('COSINE', G.mul(t, 9 * math.pi)))), 0))
    ivy_curve = G.n('GeometryNodeMeshToCurve', 'Ivy path')
    G.link(G.set_position(ivy_line.outputs['Mesh'], wind), ivy_curve.inputs['Mesh'])
    vine = G.group(orn[named('Ivy Iron')], 'Ivy')
    G.link(ivy_curve.outputs[0], vine.inputs['Path'])
    G.link(G.mul(i['Arch Bar'], .3), vine.inputs['Stem Radius'])
    G.link(G.mul(i['Span'], .05), vine.inputs['Leaf Spacing'])
    G.link(G.mul(i['Span'], .04), vine.inputs['Leaf Size'])
    ivy = G.switch('GEOMETRY', i['Ivy'], None, vine.outputs[0])

    whole = G.join(outer, inner, tie, fill.outputs[0], centre.outputs[0], crown.outputs[0], ivy)
    flat = G.n('GeometryNodeSetShadeSmooth', 'Flat iron')
    G.link(whole, flat.inputs['Mesh'])
    flat.inputs['Shade Smooth'].default_value = False
    mat = G.n('GeometryNodeSetMaterial', 'Iron')
    G.link(flat.outputs[0], mat.inputs['Geometry'])
    G.link(i['Material'], mat.inputs['Material'])
    G.link(mat.outputs[0], G.o['Geometry'])
    G.link(apex, G.o['Apex'])
    G.layout()
    defaults = {'Shape': 'Semicircle', 'Infill': 'Spokes', 'Centre': 'None', 'Crown': 'Ball and Spike'}
    G.g.interface_update(bpy.context)   # resolve which menu items each Menu input exposes
    for name, value in defaults.items():
        try:
            G.g.interface.items_tree[name].default_value = value
        except TypeError as error:
            raise TypeError(f'{name}: {error}')
    for title, names in OVERTHROW_SPEC.items():
        panel = G.g.interface.new_panel(name=title, default_closed=title in ('Bars', 'Decay'))
        for name in names:
            G.g.interface.move_to_parent(G.g.interface.items_tree[name], panel, 100)
    G.g.description = 'A wrought-iron overthrow: arch on legs, tie, crescent infill, centre, crown, ivy, decay.'
    return G.g


# ---------------------------------------------------------------------------
