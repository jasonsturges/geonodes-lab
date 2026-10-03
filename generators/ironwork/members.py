"""Members: GNL • Picket, Post, Scroll and Panel (three-low-poly fence geometry, plus the website
graveyard's square tubing, fitted ring band and derelict decay)."""
import math

from authoring.graph import Graph
from authoring.naming import named
from common import rand, unit, transform, panels, menu, sweep, square, circle, vertical_line


RING_BED = .003   # rails and pickets bed this far into a ring, so it reads riveted, not floating

# Picket
# ---------------------------------------------------------------------------

def picket_group():
    """WroughtIronPicketGeometry: a bar with a finial; flats face the run (half-segment turn)."""
    G = Graph(named('Picket'))
    G.input('Height', 'NodeSocketFloat', 2.0, .1, 6.0, 'Bar height, finial excluded. Base at Z = 0.')
    G.input('Radius', 'NodeSocketFloat', .05, .005, .3, 'Corner radius of the bar section.')
    G.input('Sides', 'NodeSocketInt', 8, 3, 32, '4 = square tubing, flats facing the run. 8 = round-ish.')
    G.input('Finial', 'NodeSocketMenu', description='Spear (SDK cone), Ball, or None.')
    G.input('Finial Height', 'NodeSocketFloat', .3, .0, 1.0)
    G.input('Finial Radius', 'NodeSocketFloat', .075, .005, .4)
    G.input('Finial Depth', 'NodeSocketFloat', 1.0, .05, 1.0, 'Squash the finial across the panel (SDK finialScaleZ).')
    G.output('Mesh')
    G.finish_io()
    i = G.i
    turn = G.div(math.pi, i['Sides'])
    bar = G.n('GeometryNodeMeshCylinder', 'Bar', fill_type='NGON')
    G.link(i['Sides'], bar.inputs['Vertices'])
    G.link(i['Radius'], bar.inputs['Radius'])
    G.link(i['Height'], bar.inputs['Depth'])
    bar = transform(G, bar.outputs['Mesh'], translation=G.xyz(0, 0, G.mul(i['Height'], .5)),
                    rotation=G.xyz(0, 0, turn), label='Base at 0, flats to the run')
    spear = G.n('GeometryNodeMeshCone', 'Spear', fill_type='NGON')
    G.link(i['Sides'], spear.inputs['Vertices'])
    G.link(i['Finial Radius'], spear.inputs['Radius Bottom'])
    G.link(i['Finial Height'], spear.inputs['Depth'])
    spear = spear.outputs['Mesh']           # Cone spans Z 0…Depth
    ball = G.n('GeometryNodeMeshUVSphere', 'Ball')
    ball.inputs['Segments'].default_value = 12
    ball.inputs['Rings'].default_value = 8
    G.link(G.mul(i['Finial Height'], .5), ball.inputs['Radius'])
    ball = transform(G, ball.outputs['Mesh'], translation=G.xyz(0, 0, G.mul(i['Finial Height'], .4)),
                     label='Ball settles onto the bar')
    menu = G.n('GeometryNodeMenuSwitch', 'Finial style', data_type='GEOMETRY')
    menu.enum_items.clear()
    for name in ('Spear', 'Ball', 'None'):
        menu.enum_items.new(name)
    G.link(i['Finial'], menu.inputs['Menu'])
    G.link(spear, menu.inputs['Spear'])
    G.link(ball, menu.inputs['Ball'])
    # Transform scales before it rotates, so turn first, then squash across the panel (world Y).
    finial = transform(G, menu.outputs[0], rotation=G.xyz(0, 0, turn), label='Flats to the run')
    finial = transform(G, finial, translation=G.xyz(0, 0, i['Height']), scale=G.xyz(1, i['Finial Depth'], 1),
                       label='Squash across the panel, on top')
    G.link(G.join(bar, finial), G.o['Mesh'])
    G.layout()
    G.g.interface.items_tree['Finial'].default_value = 'Spear'
    G.g.description = 'A wrought-iron picket: bar plus finial, base at Z = 0, panel plane XZ.'
    return G.g


# ---------------------------------------------------------------------------
# Post
# ---------------------------------------------------------------------------

def post_group():
    """WroughtIronPostGeometry: a slim shaft under a ball that settles onto it."""
    G = Graph(named('Post'))
    G.input('Height', 'NodeSocketFloat', 1.1, .2, 6.0, 'Shaft height, ball excluded.')
    G.input('Radius', 'NodeSocketFloat', .06, .01, .4)
    G.input('Sides', 'NodeSocketInt', 6, 3, 32)
    G.input('Ball Radius', 'NodeSocketFloat', .1, .0, .6)
    G.input('Ball Settle', 'NodeSocketFloat', .6, -1.0, 1.0, 'Ball centre above the shaft top, × ball radius (SDK 0.6).')
    G.input('Collar', 'NodeSocketBool', False, description='A forged collar under the ball (Blender extra).')
    G.output('Mesh')
    G.finish_io()
    i = G.i
    shaft = G.n('GeometryNodeMeshCylinder', 'Shaft', fill_type='NGON')
    G.link(i['Sides'], shaft.inputs['Vertices'])
    G.link(i['Radius'], shaft.inputs['Radius'])
    G.link(i['Height'], shaft.inputs['Depth'])
    shaft = transform(G, shaft.outputs['Mesh'], translation=G.xyz(0, 0, G.mul(i['Height'], .5)), label='Base at 0')
    ball = G.n('GeometryNodeMeshUVSphere', 'Ball')
    ball.inputs['Segments'].default_value = 8
    ball.inputs['Rings'].default_value = 6
    G.link(i['Ball Radius'], ball.inputs['Radius'])
    centre = G.add(i['Height'], G.mul(i['Ball Settle'], i['Ball Radius']))
    ball = transform(G, ball.outputs['Mesh'], translation=G.xyz(0, 0, centre), label='Ball')
    collar = G.n('GeometryNodeMeshCylinder', 'Collar', fill_type='NGON')
    G.link(i['Sides'], collar.inputs['Vertices'])
    G.link(G.mul(i['Radius'], 1.6), collar.inputs['Radius'])
    G.link(G.mul(i['Radius'], .8), collar.inputs['Depth'])
    collar = transform(G, collar.outputs['Mesh'], translation=G.xyz(0, 0, G.sub(i['Height'], G.mul(i['Radius'], .6))),
                       label='Collar under the ball')
    collar = G.switch('GEOMETRY', i['Collar'], None, collar)
    G.link(G.join(shaft, ball, collar), G.o['Mesh'])
    G.layout()
    G.g.description = 'A wrought-iron post: shaft and ball finial, base at Z = 0.'
    return G.g


# ---------------------------------------------------------------------------
# Scroll
# ---------------------------------------------------------------------------

def scroll_group():
    """WroughtIronScrollGeometry: a flat bar along a logarithmic spiral, drawn down as it curls."""
    G = Graph(named('Scroll'))
    G.input('Start Radius', 'NodeSocketFloat', 1.4, .05, 5.0, 'Radius at the open end.')
    G.input('Turns', 'NodeSocketFloat', 1.6, .1, 5.0)
    G.input('Tightness', 'NodeSocketFloat', .22, 0.0, 1.0, 'Logarithmic decay k in r = r0·e^(-kθ). 0 = a circle.')
    G.input('Bar Width', 'NodeSocketFloat', .16, .005, 1.0, 'The wide face, lying in the plane of the scroll.')
    G.input('Bar Thickness', 'NodeSocketFloat', .05, .002, .5, 'Out of the plane.')
    G.input('Taper', 'NodeSocketFloat', .45, .05, 1.0, 'Section scale at the curl (1 = no taper).')
    G.input('Segments', 'NodeSocketInt', 96, 8, 512)
    G.input('Flip', 'NodeSocketBool', False, description='Mirror: curl the other way (website gate ornament).')
    G.output('Mesh')
    G.output('Path', 'NodeSocketGeometry')
    G.finish_io()
    i = G.i
    line = G.n('GeometryNodeMeshLine', 'Spiral stations')
    G.link(G.add(i['Segments'], 1), line.inputs['Count'])
    theta = G.mul(G.div(G.index, i['Segments']), G.mul(i['Turns'], math.tau))
    r = G.mul(i['Start Radius'], G.m('EXPONENT', G.mul(G.mul(i['Tightness'], -1), theta)))
    mirror = G.switch('FLOAT', i['Flip'], 1.0, -1.0)
    spot = G.xyz(G.mul(r, G.m('COSINE', theta)), G.mul(G.mul(r, G.m('SINE', theta)), mirror), 0)
    path = G.n('GeometryNodeMeshToCurve', 'Spiral')
    G.link(G.set_position(line.outputs['Mesh'], spot), path.inputs['Mesh'])
    normal = G.n('GeometryNodeSetCurveNormal', 'Keep the wide face in the plane')
    G.link(path.outputs[0], normal.inputs['Curve'])
    normal.inputs['Mode'].default_value = 'Z Up'
    section = G.n('GeometryNodeCurvePrimitiveQuadrilateral', 'Flat bar section')
    G.link(i['Bar Width'], section.inputs['Width'])
    G.link(i['Bar Thickness'], section.inputs['Height'])
    sweep = G.n('GeometryNodeCurveToMesh', 'Forge')
    G.link(normal.outputs[0], sweep.inputs['Curve'])
    G.link(section.outputs[0], sweep.inputs['Profile Curve'])
    sweep.inputs['Fill Caps'].default_value = True
    # The SDK tapers by station (even in angle), not by arc length: most of a log spiral's length
    # is in its outer sweep, so a length factor would thin the bar too early.
    t = G.div(G.n('GeometryNodeSplineParameter', 'Open end → curl').outputs['Index'], i['Segments'])
    G.link(G.sub(1, G.mul(G.sub(1, i['Taper']), t)), sweep.inputs['Scale'])
    # No face flip needed when mirrored: Z-Up normals keep the sweep frame right-handed.
    G.link(sweep.outputs[0], G.o['Mesh'])
    G.link(normal.outputs[0], G.o['Path'])
    G.layout()
    G.g.description = 'A forged scroll: flat bar on a logarithmic spiral in the XY plane, tapering into the curl.'
    return G.g


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------

PANEL_SPEC = {
    'Run': ['Length', 'Gap'],
    'Pickets': ['Bar Height', 'Bar Radius', 'Sides', 'Finial', 'Finial Height', 'Finial Radius', 'Finial Depth'],
    'Rails': ['Rail Height', 'Rail Depth', 'Bottom Rail', 'Top Rail Drop'],
    'Rings': ['Rings', 'Ring Sides'],
    'Decay': ['Decay Seed', 'Missing Pickets', 'Bent Pickets', 'Max Bend'],
}


def panel_group(picket):
    G = Graph(named('Panel'))
    for name, kind, default, lo, hi, text in [
            ('Length', 'NodeSocketFloat', 2.4, .2, 20.0, 'Run along X, centered. Pickets inset half a pitch from each end.'),
            ('Gap', 'NodeSocketFloat', .3, .0, 2.0, 'Clear air between pickets: the design value; the pitch falls out.'),
            ('Bar Height', 'NodeSocketFloat', 2.0, .2, 6.0, ''),
            ('Bar Radius', 'NodeSocketFloat', .05, .005, .3, ''),
            ('Sides', 'NodeSocketInt', 4, 3, 16, '4 = square tubing (website default).'),
            ('Finial', 'NodeSocketMenu', None, None, None, ''),
            ('Finial Height', 'NodeSocketFloat', .3, 0.0, 1.0, ''),
            ('Finial Radius', 'NodeSocketFloat', .09, .005, .4, ''),
            ('Finial Depth', 'NodeSocketFloat', 1.0, .05, 1.0, ''),
            ('Rail Height', 'NodeSocketFloat', .1, .01, .5, ''),
            ('Rail Depth', 'NodeSocketFloat', .06, .01, .5, ''),
            ('Bottom Rail', 'NodeSocketFloat', .18, 0.0, 2.0, 'Centre height of the foot rail.'),
            ('Top Rail Drop', 'NodeSocketFloat', .25, 0.0, 2.0, 'Top rail centre, below the bar top.'),
            ('Rings', 'NodeSocketBool', False, None, None, 'A forged ring fitted into every opening, under the top rail.'),
            ('Ring Sides', 'NodeSocketInt', 12, 6, 64, ''),
            ('Decay Seed', 'NodeSocketInt', 1, 0, 65535, 'Which pickets are gone or bent.'),
            ('Missing Pickets', 'NodeSocketFloat', 0.0, 0.0, 1.0, 'Chance each picket is gone.'),
            ('Bent Pickets', 'NodeSocketFloat', 0.0, 0.0, 1.0, 'Chance each picket is bent over at its foot.'),
            ('Max Bend', 'NodeSocketFloat', .35, 0.0, 1.5, 'Largest bend, radians, in the panel plane.')]:
        G.input(name, kind, default, lo, hi, text)
    G.output('Mesh')
    G.output('Picket Count', 'NodeSocketInt')
    G.finish_io()
    i = G.i
    L, r = i['Length'], i['Bar Radius']
    # resolveFenceSpan: pickets divide the run equally, never overlapping (count yields).
    asked = G.hi(1, G.m('ROUND', G.div(L, G.add(G.mul(r, 2), i['Gap']))))
    fits = G.hi(1, G.m('FLOOR', G.div(L, G.mul(r, 2))))
    count = G.lo(asked, fits)
    pitch = G.div(L, count)
    stations = G.points(count, G.xyz(G.sub(G.mul(G.add(G.index, .5), pitch), G.mul(L, .5)), 0, 0))
    gone = G.m('LESS_THAN', unit(G, G.index, 1, i['Decay Seed']), i['Missing Pickets'])
    stations = G.delete(stations, gone)
    bent = G.m('LESS_THAN', unit(G, G.index, 2, i['Decay Seed']), i['Bent Pickets'])
    bend = G.mul(G.mul(bent, i['Max Bend']), rand(G, G.index, 3, i['Decay Seed']))
    one = G.group(picket, 'One picket')
    for a, b in (('Bar Height', 'Height'), ('Bar Radius', 'Radius'), ('Sides', 'Sides'), ('Finial', 'Finial'),
                 ('Finial Height', 'Finial Height'), ('Finial Radius', 'Finial Radius'), ('Finial Depth', 'Finial Depth')):
        G.link(i[a], one.inputs[b])
    inst = G.n('GeometryNodeInstanceOnPoints', 'A picket on every station')
    G.link(stations, inst.inputs['Points'])
    G.link(one.outputs[0], inst.inputs['Instance'])
    G.link(G.xyz(0, bend, 0), inst.inputs['Rotation'])      # bent over about its foot, in the panel plane
    real = G.n('GeometryNodeRealizeInstances', 'Real geometry')
    G.link(inst.outputs[0], real.inputs['Geometry'])
    pickets = real.outputs[0]

    def rail(z, label):
        box = G.n('GeometryNodeMeshCube', label)
        G.link(G.xyz(L, i['Rail Depth'], i['Rail Height']), box.inputs['Size'])
        return transform(G, box.outputs['Mesh'], translation=G.xyz(0, 0, z), label=f'{label} height')
    top = G.sub(i['Bar Height'], i['Top Rail Drop'])
    rails = G.join(rail(i['Bottom Rail'], 'Foot rail'), rail(top, 'Top rail'))

    # Fitted ring band (website panelRingFit), touching the picket FLATS: the apothem is r·cos(π/sides).
    apothem = G.mul(r, G.m('COSINE', G.div(math.pi, i['Sides'])))
    fitted = G.add(G.sub(G.mul(pitch, .5), apothem), RING_BED)
    tube = G.hi(.018, G.mul(fitted, .13))
    centre_r = G.sub(fitted, tube)
    underside = G.sub(top, G.mul(i['Rail Height'], .5))
    ring_z = G.add(G.sub(underside, fitted), RING_BED)
    band_z = G.sub(G.add(G.sub(ring_z, fitted), RING_BED), G.mul(i['Rail Height'], .5))
    circle = G.n('GeometryNodeCurvePrimitiveCircle', 'Ring centre line')
    G.link(i['Ring Sides'], circle.inputs['Resolution'])
    G.link(centre_r, circle.inputs['Radius'])
    square = G.n('GeometryNodeCurvePrimitiveQuadrilateral', 'Square ring bar')
    G.link(G.mul(tube, 2), square.inputs['Width'])
    G.link(G.mul(tube, 2), square.inputs['Height'])
    ring = G.n('GeometryNodeCurveToMesh', 'Ring')
    G.link(circle.outputs[0], ring.inputs['Curve'])
    G.link(square.outputs[0], ring.inputs['Profile Curve'])
    ring = transform(G, ring.outputs[0], rotation=(math.pi / 2, 0, 0), label='Stand in the panel')
    openings = G.points(G.sub(count, 1), G.xyz(G.add(G.mul(L, -.5), G.mul(G.add(G.index, 1), pitch)), 0, ring_z))
    rings = G.n('GeometryNodeInstanceOnPoints', 'A ring in every opening')
    G.link(openings, rings.inputs['Points'])
    G.link(ring, rings.inputs['Instance'])
    real_rings = G.n('GeometryNodeRealizeInstances', 'Real rings')
    G.link(rings.outputs[0], real_rings.inputs['Geometry'])
    band = G.join(real_rings.outputs[0], rail(band_z, 'Band rail'))
    band = G.switch('GEOMETRY', i['Rings'], None, band)

    G.link(G.join(pickets, rails, band), G.o['Mesh'])
    G.link(count, G.o['Picket Count'])
    G.layout()
    G.g.interface.items_tree['Finial'].default_value = 'Spear'
    panels(G, PANEL_SPEC, closed=('Decay',))
    G.g.description = 'A wrought-iron fence panel along X: pickets, two rails, optional fitted rings, seeded decay.'
    return G.g



# ---------------------------------------------------------------------------
