"""Ornament: GNL • Twisted Bar, Fleur-de-lis, Double Scroll (S/C), Collar and the Ornamental Rail
(the website windowsill rail)."""
import math

from authoring.graph import Graph
from authoring.naming import named
from common import rand, unit, transform, panels, menu, sweep, square, circle, vertical_line


# Twisted bar
# ---------------------------------------------------------------------------

def twisted_bar():
    G = Graph(named('Twisted Bar'))
    G.input('Height', 'NodeSocketFloat', 1.0, .05, 6.0, 'Base at Z = 0.')
    G.input('Style', 'NodeSocketMenu', description='Square Twist (forge), Rope (strands on a helix), Basket (bulging cage).')
    G.input('Width', 'NodeSocketFloat', .03, .003, .3, 'Square bar width / overall rope or basket width.')
    G.input('Twist Pitch', 'NodeSocketFloat', .08, .005, 2.0, 'Rise per full turn (website rope: 0.08).')
    G.input('Plain Ends', 'NodeSocketFloat', .06, 0.0, 2.0, 'Untwisted square bar left at each end, as forged.')
    G.input('Strands', 'NodeSocketInt', 2, 2, 8, 'Rope and basket strands.')
    G.input('Bulge', 'NodeSocketFloat', 2.0, 1.0, 6.0, 'Basket: widest cage as a multiple of Width.')
    G.input('Detail', 'NodeSocketInt', 120, 8, 2000, 'Stations along the twisted length.')
    G.output('Mesh')
    G.finish_io()
    i = G.i
    h, w = i['Height'], i['Width']
    plain = G.lo(i['Plain Ends'], G.mul(h, .45))
    z0, z1 = plain, G.sub(h, plain)
    span = G.sub(z1, z0)
    ends = G.join(sweep(G, vertical_line(G, 0.0, z0, 2), square(G, w), label='Plain foot'),
                  sweep(G, vertical_line(G, z1, h, 2), square(G, w), label='Plain head'))
    ends = G.switch('GEOMETRY', G.m('GREATER_THAN', plain, 1e-5), None, ends)
    axis = vertical_line(G, z0, z1, i['Detail'])
    turns = G.div(G.sub(G.sep(G.position())[2], z0), i['Twist Pitch'])
    # Square twist: a square section whose tilt advances one turn per pitch.
    tilt = G.n('GeometryNodeSetCurveTilt', 'Twist')
    G.link(axis, tilt.inputs['Curve'])
    G.link(G.mul(turns, math.tau), tilt.inputs['Tilt'])
    twist = sweep(G, tilt.outputs[0], square(G, w), label='Square twist')
    # Rope / basket: copies of the axis, each pushed round a helix with its own phase.
    dup = G.n('GeometryNodeDuplicateElements', 'One curve per strand', domain='SPLINE')
    G.link(axis, dup.inputs['Geometry'])
    G.link(i['Strands'], dup.inputs['Amount'])
    k = dup.outputs['Duplicate Index']
    strands = G.store(dup.outputs['Geometry'], 'strand', k, domain='CURVE')
    x, y, z = G.sep(G.position())
    u = G.div(G.sub(z, z0), G.hi(span, 1e-6))                  # 0 … 1 over the twisted length
    phase = G.add(G.mul(G.div(G.sub(z, z0), i['Twist Pitch']), math.tau),
                  G.div(G.mul(G.named('strand'), math.tau), i['Strands']))
    strand_r = G.div(w, G.mul(i['Strands'], 1.15))                # strands touch around the helix
    rope_r = G.sub(G.mul(w, .5), strand_r)
    basket_r = G.mul(rope_r, G.add(1, G.mul(G.sub(i['Bulge'], 1), G.m('SINE', G.mul(u, math.pi)))))
    def helix(radius):
        return G.set_position(strands, G.xyz(G.mul(radius, G.m('COSINE', phase)), G.mul(radius, G.m('SINE', phase)), z))
    rope = sweep(G, helix(rope_r), circle(G, strand_r, 6), label='Rope strands')
    basket = sweep(G, helix(basket_r), circle(G, strand_r, 6), label='Basket strands')
    pick = menu(G, i['Style'], ('Square Twist', 'Rope', 'Basket'), 'Twist style')
    G.link(twist, pick.inputs['Square Twist'])
    G.link(rope, pick.inputs['Rope'])
    G.link(basket, pick.inputs['Basket'])
    G.link(G.join(ends, pick.outputs[0]), G.o['Mesh'])
    G.layout()
    G.g.interface.items_tree['Style'].default_value = 'Square Twist'
    G.g.description = 'A twisted iron bar along Z: forge square twist, rope or basket, with plain square ends.'
    return G.g


# ---------------------------------------------------------------------------
# Fleur-de-lis
# ---------------------------------------------------------------------------

# Right half of the outline, normalized: x is half-width (0…0.5), y is height (0…1).
# Centre petal tip → neck → side petal (up, out, curling down to its tip) → back under the petal
# → band → flared tail → the stem at the bottom centre. Mirrored for the left half.
FLEUR = [(0, 1.0), (.045, .93), (.085, .83), (.105, .72), (.1, .62), (.075, .53),
         (.13, .58), (.21, .63), (.3, .655), (.38, .63), (.44, .575), (.475, .5), (.48, .42), (.46, .35),
         (.43, .31), (.41, .345), (.415, .41), (.39, .47), (.33, .515), (.25, .52), (.17, .49), (.12, .43),
         (.17, .43), (.17, .34), (.09, .34), (.11, .25), (.15, .16), (.155, .1), (.11, .11), (.06, .06),
         (.035, 0.0)]


def fleur_group():
    G = Graph(named('Fleur-de-lis'))
    G.input('Height', 'NodeSocketFloat', .3, .02, 2.0, 'Stem at Z = 0; in the XZ plane, facing −Y.')
    G.input('Width', 'NodeSocketFloat', .26, .02, 2.0, '')
    G.input('Thickness', 'NodeSocketFloat', .025, .002, .3, 'Plate thickness, centered on Y = 0.')
    G.output('Mesh')
    G.finish_io()
    i = G.i
    outline = FLEUR + [(-x, y) for x, y in reversed(FLEUR[1:])]   # the tip (0, 1) is its own mirror
    pts = [G.xyz(G.mul(i['Width'], x), G.mul(i['Height'], y), 0) for x, y in outline]
    line = G.n('GeometryNodeMeshLine', 'Outline stations')
    line.inputs['Count'].default_value = len(pts)
    placed = G.set_position(line.outputs['Mesh'], G.pick(G.index, pts))
    curve = G.n('GeometryNodeMeshToCurve', 'Outline')
    G.link(placed, curve.inputs['Mesh'])
    closed = G.n('GeometryNodeSetSplineCyclic', 'Close it')
    G.link(curve.outputs[0], closed.inputs['Geometry'])
    closed.inputs['Cyclic'].default_value = True
    fill = G.n('GeometryNodeFillCurve', 'Fill the plate')
    G.link(closed.outputs[0], fill.inputs['Curve'])
    fill.inputs['Mode'].default_value = 'N-gons'
    extrude = G.n('GeometryNodeExtrudeMesh', 'Give it thickness', mode='FACES')
    G.link(fill.outputs[0], extrude.inputs['Mesh'])
    G.link(i['Thickness'], extrude.inputs['Offset Scale'])
    extrude.inputs['Individual'].default_value = False
    # Extrude moves the face, so the original outline face is added back (flipped) as the bottom,
    # and the shared rim welded: a closed plate.
    bottom = G.n('GeometryNodeFlipFaces', 'Bottom face')
    G.link(fill.outputs[0], bottom.inputs['Mesh'])
    weld = G.n('GeometryNodeMergeByDistance', 'Weld the rim')
    G.link(G.join(extrude.outputs['Mesh'], bottom.outputs[0]), weld.inputs['Geometry'])
    weld.inputs['Distance'].default_value = 1e-6
    plate = transform(G, weld.outputs[0], translation=G.xyz(0, 0, G.mul(i['Thickness'], -.5)),
                      label='Center the thickness')
    # Stand the plate up: XY drawing → XZ plane (height up), thickness along Y.
    stood = transform(G, plate, rotation=(math.pi / 2, 0, 0), label='Stand up')
    G.link(stood, G.o['Mesh'])
    G.layout()
    G.g.description = 'A cast fleur-de-lis plate: centre petal, curled side petals, band and flared tail.'
    return G.g


# ---------------------------------------------------------------------------
# S / C scroll fitted to a gap
# ---------------------------------------------------------------------------

def double_scroll():
    G = Graph(named('Double Scroll'))
    G.input('Style', 'NodeSocketMenu', description='S: curls turn opposite ways. C: both curl the same way.')
    G.input('Fit Width', 'NodeSocketFloat', .2, 0.0, 5.0, 'Scale so the scroll spans exactly this (0 = natural size).')
    G.input('Turns', 'NodeSocketFloat', 1.35, .25, 4.0, 'Website rail: 1.35.')
    G.input('Tightness', 'NodeSocketFloat', .26, 0.0, 1.0, '')
    G.input('Bar Width', 'NodeSocketFloat', .014, .001, .3, 'Wide face, in the plane (before fitting).')
    G.input('Bar Thickness', 'NodeSocketFloat', .005, .001, .3, '')
    G.input('Taper', 'NodeSocketFloat', .5, .05, 1.0, 'Section scale at the curls.')
    G.input('Mirror', 'NodeSocketBool', False, description='Flip the path (not the mesh), as the website does.')
    G.input('Segments', 'NodeSocketInt', 36, 6, 256, 'Per spiral.')
    G.output('Mesh')
    G.finish_io()
    i = G.i
    r0 = .07
    line = G.n('GeometryNodeMeshLine', 'Spiral stations')
    G.link(G.add(i['Segments'], 1), line.inputs['Count'])
    theta = G.mul(G.div(G.index, i['Segments']), G.mul(i['Turns'], math.tau))
    r = G.mul(r0, G.m('EXPONENT', G.mul(G.mul(i['Tightness'], -1), theta)))
    mirror = G.switch('FLOAT', i['Mirror'], 1.0, -1.0)
    a = G.set_position(line.outputs['Mesh'], G.xyz(G.mul(r, G.m('COSINE', theta)),
                                                   G.mul(G.mul(r, G.m('SINE', theta)), mirror), 0))
    to_curve = G.n('GeometryNodeMeshToCurve', 'Spiral A')
    G.link(a, to_curve.inputs['Mesh'])
    spiral = to_curve.outputs[0]
    # S: the second spiral is the first turned half a turn about (r0, 0), meeting it at its open end.
    # C: the second is the first reflected across x = r0, so both curls fall on the same side.
    x, y, _ = G.sep(G.position())
    s_pos = G.xyz(G.sub(G.mul(r0, 2), x), G.mul(y, -1), 0)
    c_pos = G.xyz(G.sub(G.mul(r0, 2), x), y, 0)
    pick = G.n('GeometryNodeMenuSwitch', 'S or C', data_type='VECTOR')
    pick.enum_items.clear()
    for name in ('S', 'C'):
        pick.enum_items.new(name)
    G.link(i['Style'], pick.inputs['Menu'])
    G.link(s_pos, pick.inputs['S'])
    G.link(c_pos, pick.inputs['C'])
    b = G.set_position(spiral, pick.outputs[0])
    both = G.join(spiral, b)
    normal = G.n('GeometryNodeSetCurveNormal', 'Wide face in the plane')
    G.link(both, normal.inputs['Curve'])
    normal.inputs['Mode'].default_value = 'Z Up'
    t = G.div(G.n('GeometryNodeSplineParameter', 'Join → curl').outputs['Index'], i['Segments'])
    mesh = sweep(G, normal.outputs[0], square(G, i['Bar Width'], i['Bar Thickness']),
                 scale=G.sub(1, G.mul(G.sub(1, i['Taper']), t)), label='Forge both halves')
    # Fit: center on its bounds, scale uniformly in the plane so its width is Fit Width.
    bounds = G.n('GeometryNodeBoundBox', 'Bounds')
    G.link(mesh, bounds.inputs['Geometry'])
    lo_, hi_ = bounds.outputs['Min'], bounds.outputs['Max']
    lx, ly, _ = G.sep(lo_)
    hx, hy, _ = G.sep(hi_)
    centred = transform(G, mesh, translation=G.xyz(G.mul(G.add(lx, hx), -.5), G.mul(G.add(ly, hy), -.5), 0),
                        label='Center')
    k = G.switch('FLOAT', G.m('GREATER_THAN', i['Fit Width'], 0), 1.0, G.div(i['Fit Width'], G.sub(hx, lx)))
    fitted = transform(G, centred, scale=G.xyz(k, k, 1), label='Fit the gap')
    stood = transform(G, fitted, rotation=(math.pi / 2, 0, 0), label='Stand in the XZ plane')
    G.link(stood, G.o['Mesh'])
    G.layout()
    G.g.interface.items_tree['Style'].default_value = 'S'
    G.g.description = 'Two tapering log spirals joined at their open ends (S or C), fitted to a gap, in XZ.'
    return G.g


# ---------------------------------------------------------------------------
# Collar and the rail composition
# ---------------------------------------------------------------------------

def collar_group():
    G = Graph(named('Collar'))
    G.input('Bar Width', 'NodeSocketFloat', .03, .003, .3, 'The bar it wraps.')
    G.input('Wrap', 'NodeSocketFloat', .006, .0005, .1, 'Band thickness around the bar.')
    G.input('Height', 'NodeSocketFloat', .025, .002, .3, '')
    G.output('Mesh')
    G.finish_io()
    i = G.i
    side = G.add(i['Bar Width'], G.mul(i['Wrap'], 2))
    cube = G.n('GeometryNodeMeshCube', 'Band')
    G.link(G.xyz(side, side, i['Height']), cube.inputs['Size'])
    G.link(cube.outputs['Mesh'], G.o['Mesh'])
    G.layout()
    G.g.description = 'A forged collar: a band wrapped round a square bar, centered at the origin.'
    return G.g


def rail_group(twisted, scroll, fleur, collar):
    """Windowsill-style rail: alternating square / twisted pickets, S-scrolls in the gaps."""
    G = Graph(named('Ornamental Rail'))
    G.input('Length', 'NodeSocketFloat', 2.0, .3, 20.0, 'Along X, centered.')
    G.input('Height', 'NodeSocketFloat', 1.0, .2, 4.0, 'Picket height between the rails.')
    G.input('Spacing', 'NodeSocketFloat', .18, .05, 2.0, 'Target picket spacing (website rail: 0.18).')
    G.input('Bar Width', 'NodeSocketFloat', .016, .003, .2, '')
    G.input('Twist Style', 'NodeSocketMenu', description='Style of every other picket.')
    G.input('Scroll Style', 'NodeSocketMenu', description='S or C scrolls in the gaps.')
    G.input('Scrolls', 'NodeSocketBool', True)
    G.input('Fleur Finials', 'NodeSocketBool', False, description='A fleur-de-lis on every twisted picket.')
    G.input('Collars', 'NodeSocketBool', True, description='Collars where scrolls meet pickets.')
    G.output('Mesh')
    G.finish_io()
    i = G.i
    L, h, bw = i['Length'], i['Height'], i['Bar Width']
    count = G.hi(2, G.add(G.m('ROUND', G.div(L, i['Spacing'])), 1))
    pitch = G.div(L, G.sub(count, 1))
    stations = G.points(count, G.xyz(G.sub(G.mul(G.index, pitch), G.mul(L, .5)), 0, 0))
    odd = G.m('FLOORED_MODULO', G.index, 2)
    plain_pts = G.delete(stations, odd)
    twist_pts = G.delete(stations, G.sub(1, odd))

    def on(points, geometry, label):
        inst = G.n('GeometryNodeInstanceOnPoints', label)
        G.link(points, inst.inputs['Points'])
        G.link(geometry, inst.inputs['Instance'])
        real = G.n('GeometryNodeRealizeInstances', f'{label} (real)')
        G.link(inst.outputs[0], real.inputs['Geometry'])
        return real.outputs[0]

    plain = G.n('GeometryNodeMeshCube', 'Square picket')
    G.link(G.xyz(bw, bw, h), plain.inputs['Size'])
    plain = transform(G, plain.outputs['Mesh'], translation=G.xyz(0, 0, G.mul(h, .5)), label='Base at 0')
    tb = G.group(twisted, 'Twisted picket')
    G.link(h, tb.inputs['Height'])
    G.link(G.mul(bw, 1.25), tb.inputs['Width'])
    G.link(i['Twist Style'], tb.inputs['Style'])
    tb.inputs['Plain Ends'].default_value = .04
    fl = G.group(fleur, 'Fleur')
    G.link(G.mul(bw, 9), fl.inputs['Height'])
    G.link(G.mul(bw, 8), fl.inputs['Width'])
    G.link(G.mul(bw, .8), fl.inputs['Thickness'])
    fl_top = transform(G, fl.outputs[0], translation=G.xyz(0, 0, h), label='On the picket top')
    twisted_geo = G.join(tb.outputs[0], G.switch('GEOMETRY', i['Fleur Finials'], None, fl_top))
    pickets = G.join(on(plain_pts, plain, 'Square pickets'), on(twist_pts, twisted_geo, 'Twisted pickets'))
    rail = G.n('GeometryNodeMeshCube', 'Rail')
    G.link(G.xyz(G.add(L, G.mul(bw, 4)), G.mul(bw, 2.2), G.mul(bw, 2.2)), rail.inputs['Size'])
    rails = G.join(transform(G, rail.outputs['Mesh'], translation=G.xyz(0, 0, h), label='Top rail'),
                   transform(G, rail.outputs['Mesh'], translation=(0, 0, 0), label='Bottom rail'))
    # Scrolls: one per gap, fitted so the curls kiss the pickets; alternate ones mirrored.
    gaps = G.points(G.sub(count, 1), G.xyz(G.sub(G.mul(G.add(G.index, .5), pitch), G.mul(L, .5)), 0, G.mul(h, .5)))
    gap_odd = G.m('FLOORED_MODULO', G.index, 2)
    sc = G.group(scroll, 'S scroll')
    G.link(G.sub(pitch, G.mul(bw, 1.1)), sc.inputs['Fit Width'])
    G.link(i['Scroll Style'], sc.inputs['Style'])
    sc_m = G.group(scroll, 'S scroll, mirrored')
    G.link(G.sub(pitch, G.mul(bw, 1.1)), sc_m.inputs['Fit Width'])
    G.link(i['Scroll Style'], sc_m.inputs['Style'])
    sc_m.inputs['Mirror'].default_value = True
    scrolls = G.join(on(G.delete(gaps, gap_odd), sc.outputs[0], 'Scrolls'),
                     on(G.delete(gaps, G.sub(1, gap_odd)), sc_m.outputs[0], 'Mirrored scrolls'))
    scrolls = G.switch('GEOMETRY', i['Scrolls'], None, scrolls)
    co = G.group(collar, 'Collar')
    G.link(G.mul(bw, 1.25), co.inputs['Bar Width'])
    collar_pts = G.points(G.mul(count, 2), G.xyz(G.sub(G.mul(G.m('FLOOR', G.div(G.index, 2)), pitch), G.mul(L, .5)), 0,
                                               G.add(G.mul(h, .5), G.mul(G.sub(G.mul(G.m('FLOORED_MODULO', G.index, 2), 2), 1), G.mul(bw, 2.2)))))
    collars = G.switch('GEOMETRY', G.m('MULTIPLY', i['Collars'], i['Scrolls']), None, on(collar_pts, co.outputs[0], 'Collars'))
    G.link(G.join(pickets, rails, scrolls, collars), G.o['Mesh'])
    G.layout()
    G.g.interface.items_tree['Twist Style'].default_value = 'Rope'
    G.g.interface.items_tree['Scroll Style'].default_value = 'S'
    G.g.description = 'Windowsill-style rail: square and twisted pickets alternate, fitted S/C scrolls between.'
    return G.g



# ---------------------------------------------------------------------------
