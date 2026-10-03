"""GNL • Molding Run: a named section swept along any wall line, every corner mitered exactly.

Origin: three-low-poly `MoldingGeometry` (crown or base, inward or outward facing, open or closed) and
its `miterFrames`; the NodesLab prototype's studies 022–024 (corners, polygons, Bézier runs).

How it works
  1. The path (any curve: poly, Bézier, NURBS) is resampled to its evaluated points, keeping only the
     points where it turns (so an inside corner's miter never overshoots a nearby station and folds).
  2. At each point, the wall's inward side is perp(d) = (−dy, dx) of the direction d. At a corner, the
     section lies on the plane bisecting the turn: its offset direction n is the normalized sum of the
     two neighbouring perps, and the section is widened by k = 1 / cos(turn / 2) = 1 / (n · perp(d_in)).
     Both neighbours share that ring, so the joint closes exactly, at any angle, for any section.
     ("The miter never sees the profile, because the corner is a property of the path.")
  3. Curve to Mesh supplies the topology (path × section, caps on open runs); then every vertex is placed
     exactly: path point + n · k · projection + Z · height (down for a crown, up for base and rails).
"""
from authoring.graph import Graph
from authoring.naming import named


def run_group():
    G = Graph(named('Molding Run'))
    G.input('Path', 'NodeSocketGeometry', description='The wall line: any curve. Closed curves make a closed run with no ends.')
    G.input('Section', 'NodeSocketGeometry', description='A closed section curve in XY: X = height, Y = projection (e.g. a Molding Profile).')
    G.input('Crown', 'NodeSocketBool', True, description='Hang down from the path (crown / cornice). Off: rise from it (base, chair rail).')
    G.input('Outward', 'NodeSocketBool', False,
            description='Project to the right of the path direction (round a chimney breast). Off: to the left, '
                        'which is the room side when a room is drawn anticlockwise from above.')
    G.output('Mesh')
    G.finish_io()
    i = G.i

    # --- Path: evaluated points, with each point's mitered offset direction stored on it. ----------
    path = G.n('GeometryNodeResampleCurve', 'Evaluated points')
    path.inputs['Mode'].default_value = 'Evaluated'
    G.link(i['Path'], path.inputs['Curve'])
    path = path.outputs[0]

    def directions():
        """Fields: the flat directions in and out of each point, from its neighbours in the same spline
        (a path may hold several runs), wrapping on closed splines; and whether it is an open run's end."""
        spline = G.n('GeometryNodeCurveOfPoint', 'Which spline')
        first = G.n('GeometryNodePointsOfCurve', 'Spline start and length')
        G.link(spline.outputs['Curve Index'], first.inputs['Curve Index'])
        start, n_points = first.outputs['Point Index'], first.outputs['Total']
        local = spline.outputs['Index in Curve']
        cyclic = G.n('GeometryNodeInputSplineCyclic', 'Closed?').outputs[0]
        last = G.sub(n_points, 1)
        wrap_prev = G.m('FLOORED_MODULO', G.sub(local, 1), n_points)
        wrap_next = G.m('FLOORED_MODULO', G.add(local, 1), n_points)
        prev = G.at(G.position(), G.add(start, G.switch('FLOAT', cyclic, G.hi(G.sub(local, 1), 0), wrap_prev)))
        nxt = G.at(G.position(), G.add(start, G.switch('FLOAT', cyclic, G.lo(G.add(local, 1), last), wrap_next)))
        here = G.position()

        def flat_dir(a, b):
            x, y, _ = G.sep(G.v('SUBTRACT', b, a))
            return G.v('NORMALIZE', G.xyz(x, y, 0))
        d_in, d_out = flat_dir(prev, here), flat_dir(here, nxt)
        # An open run's ends have only one neighbour: use the direction that exists (a square cut).
        d_in = G.switch('VECTOR', G.m('LESS_THAN', G.v('LENGTH', d_in), .5), d_in, d_out)
        d_out = G.switch('VECTOR', G.m('LESS_THAN', G.v('LENGTH', d_out), .5), d_out, d_in)
        is_end = G.m('MULTIPLY', G.sub(1, cyclic), G.m('MAXIMUM', G.m('COMPARE', local, 0), G.m('COMPARE', local, last)))
        return d_in, d_out, is_end

    # Keep a station only where the path turns. A straight wall evaluates to many collinear points, and an
    # INSIDE corner's miter carries the section forward by projection · tan(turn / 2): any station closer
    # than that would be overshot and the strip would fold back on itself. Collinear points carry no
    # shape, so each straight wall becomes one span, corner to corner; curves keep all their points.
    d_in, d_out, is_end = directions()
    straight = G.m('GREATER_THAN', G.v('DOT_PRODUCT', d_in, d_out), 1 - 1e-6)
    drop = G.n('GeometryNodeDeleteGeometry', 'Drop collinear points', domain='POINT')
    G.link(path, drop.inputs['Geometry'])
    G.link(G.m('MULTIPLY', straight, G.sub(1, is_end)), drop.inputs['Selection'])
    path = drop.outputs[0]
    d_in, d_out, _ = directions()
    pos = G.position()

    def perp(d):
        x, y, _ = G.sep(d)
        return G.xyz(G.mul(y, -1), x, 0)
    n = G.v('NORMALIZE', G.v('ADD', perp(d_in), perp(d_out)))
    widen = G.div(1.0, G.hi(G.v('DOT_PRODUCT', n, perp(d_in)), .05))
    side = G.switch('FLOAT', i['Outward'], 1.0, -1.0)
    path = G.store(path, 'run_origin', pos, kind='FLOAT_VECTOR')
    path = G.store(path, 'run_miter', G.v('SCALE', n, scale=G.mul(widen, side)), kind='FLOAT_VECTOR')
    along = G.n('GeometryNodeSplineParameter', 'Distance along the run').outputs['Length']
    path = G.store(path, 'run_u', along)

    # --- Section: remember each section point's (height, projection), and its distance around. ------
    section = G.store(i['Section'], 'run_hp', G.position(), kind='FLOAT_VECTOR')
    around = G.n('GeometryNodeSplineParameter', 'Distance around the section').outputs['Length']
    section = G.store(section, 'run_v', around)

    sweep = G.n('GeometryNodeCurveToMesh', 'Topology: path × section')
    G.link(path, sweep.inputs['Curve'])
    G.link(section, sweep.inputs['Profile Curve'])
    sweep.inputs['Fill Caps'].default_value = True

    # --- Place every vertex exactly. ------------------------------------------------------------------
    h, p, _ = G.sep(G.named('run_hp', 'FLOAT_VECTOR'))
    up = G.switch('FLOAT', i['Crown'], 1.0, -1.0)
    placed = G.v('ADD', G.v('ADD', G.named('run_origin', 'FLOAT_VECTOR'),
                            G.v('SCALE', G.named('run_miter', 'FLOAT_VECTOR'), scale=p)),
                 G.xyz(0, 0, G.mul(h, up)))
    mesh = G.set_position(sweep.outputs[0], placed)
    # Crown and Outward each mirror the section, reversing the winding; the plain sweep is inside out.
    # So the faces need flipping exactly when the two agree (both on or both off).
    flip = G.n('GeometryNodeFlipFaces', 'Normals outward')
    G.link(mesh, flip.inputs['Mesh'])
    exactly_one = G.m('COMPARE', G.m('ADD', G.mul(i['Crown'], 1), G.mul(i['Outward'], 1)), 1)
    G.link(G.sub(1, exactly_one), flip.inputs['Selection'])
    mesh = flip.outputs[0]
    uv = G.xyz(G.named('run_u'), G.named('run_v'), 0)
    mesh = G.store(mesh, 'UVMap', uv, kind='FLOAT2', domain='CORNER')
    for name in ('run_origin', 'run_miter', 'run_hp', 'run_u', 'run_v'):
        remove = G.n('GeometryNodeRemoveAttribute', 'Remove helper')
        remove.inputs['Name'].default_value = name
        G.link(mesh, remove.inputs['Geometry'])
        mesh = remove.outputs[0]
    G.link(mesh, G.o['Mesh'])
    G.layout()
    G.g.description = ('A named section swept along any wall line with every corner mitered exactly: open or closed, '
                       'crown or rising, inward or outward. UVs run along the molding.')
    return G.g


def run_object_group(run, corner_profile, surface_profile):
    """The ready-made object: pick a curve, a run type (Crown, Base, Chair Rail) and a named section."""
    G = Graph(named('Molding Run • Object'), modifier=True)
    G.input('Geometry', 'NodeSocketGeometry')
    G.input('Path', 'NodeSocketObject', description='Any curve object: the wall line (ceiling line for a crown). Empty: a sample 4 × 3 room.')
    G.input('Run', 'NodeSocketMenu', description='Crown hangs from the path; Base and Chair Rail rise from it.')
    G.input('Corner Profile', 'NodeSocketMenu', description='Section for Crown and Base.')
    G.input('Surface Profile', 'NodeSocketMenu', description='Section for Chair Rail.')
    G.input('Height', 'NodeSocketFloat', .12, .01, .6, '')
    G.input('Projection', 'NodeSocketFloat', .08, .005, .4, '')
    G.input('Segments', 'NodeSocketInt', 6, 1, 16, 'Curve stations per rounded part of the section.')
    G.input('Outward', 'NodeSocketBool', False, description='Project to the right of the path (outside corners of a chimney breast).')
    G.input('Material', 'NodeSocketMaterial')
    G.output('Geometry')
    G.finish_io()
    i = G.i
    info = G.n('GeometryNodeObjectInfo', 'Your path', transform_space='RELATIVE')
    G.link(i['Path'], info.inputs['Object'])
    # No path chosen yet: a small sample room (4 × 3, drawn anticlockwise so Inward faces the room).
    sample = G.n('GeometryNodeCurvePrimitiveQuadrilateral', 'Sample room until Path is set')
    sample.inputs['Width'].default_value, sample.inputs['Height'].default_value = 4.0, 3.0
    count = G.n('GeometryNodeAttributeDomainSize', 'Path points?', component='CURVE')
    G.link(info.outputs['Geometry'], count.inputs[0])
    path = G.switch('GEOMETRY', G.m('GREATER_THAN', count.outputs['Point Count'], 0), sample.outputs[0],
                    info.outputs['Geometry'])
    corner = G.group(corner_profile, 'Corner section')
    surface = G.group(surface_profile, 'Surface section')
    G.link(i['Corner Profile'], corner.inputs['Profile'])
    G.link(i['Surface Profile'], surface.inputs['Profile'])
    for node in (corner, surface):
        for name in ('Height', 'Projection', 'Segments'):
            G.link(i[name], node.inputs[name])
    kind = G.menu_index(i['Run'], ['Crown', 'Base', 'Chair Rail'], label='Run → index')
    section = G.switch('GEOMETRY', G.m('COMPARE', kind, 2), corner.outputs[0], surface.outputs[0])
    node = G.group(run, 'Molding Run')
    G.link(path, node.inputs['Path'])
    G.link(section, node.inputs['Section'])
    G.link(G.m('COMPARE', kind, 0), node.inputs['Crown'])
    G.link(i['Outward'], node.inputs['Outward'])
    G.link(G.shade(G.material(node.outputs[0], i['Material'])), G.o['Geometry'])
    G.layout()
    G.defaults({'Run': 'Crown', 'Corner Profile': 'Ogee', 'Surface Profile': 'Astragal'})
    G.panels({'Path': ['Path', 'Run', 'Outward'], 'Section': ['Corner Profile', 'Surface Profile', 'Height', 'Projection', 'Segments'],
              'Surface': ['Material']})
    return G.g
