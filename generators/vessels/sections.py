"""Operations on any silhouette: inward offset, shell (glass section), liquid fill, and the lathe."""
import math

from authoring.graph import Graph
from authoring.naming import named


def offset_group():
    """Move every point inward along the profile's own normal (SDK offsetInward)."""
    G = Graph(named('Offset Profile Inward'))
    G.input('Profile', 'NodeSocketGeometry')
    G.input('Distance', 'NodeSocketFloat', 0.05, 0.0, 1.0)
    G.output('Profile')
    G.finish_io()
    pos = G.position()
    last = G.sub(G.point_count(G.i['Profile']), 1)
    prev = G.at(pos, G.hi(G.sub(G.index, 1), 0))
    nxt = G.at(pos, G.lo(G.add(G.index, 1), last))
    tx, _, tz = G.sep(G.v('NORMALIZE', G.v('SUBTRACT', nxt, prev)))
    # Tangent turned +90° in the XZ plane points toward the axis for a base-to-rim profile.
    moved = G.v('ADD', pos, G.v('SCALE', G.xz(G.mul(tz, -1), tx), scale=G.i['Distance']))
    x, _, z = G.sep(moved)
    # Never cross the axis; and a point that starts on the axis stays there (closes the floor).
    ox, _, _ = G.sep(pos)
    x = G.switch('FLOAT', G.m('GREATER_THAN', ox, 1e-6), 0.0, G.hi(x, 0))
    G.link(G.set_position(G.i['Profile'], G.xz(x, z)), G.o['Profile'])
    G.layout()
    return G.g


def shell_group(offset):
    """Thicken a silhouette into the closed section that is actually lathed (SDK vesselShell)."""
    G = Graph(named('Vessel Shell'))
    G.input('Silhouette', 'NodeSocketGeometry')
    G.input('Thickness', 'NodeSocketFloat', 0.04, 0.0, 1.0,
            '0 = single surface with a rolled rim (good for transparent glass); >0 = full double wall.')
    G.input('Rim', 'NodeSocketFloat', 0.1, 0.0, 0.9, 'Rolled-rim bead, as a fraction of rim radius (Thickness 0 only).')
    G.input('Rounded Rim', 'NodeSocketBool', True, description='Round the double wall over a bead; off = flat rim.')
    G.input('Rim Segments', 'NodeSocketInt', 6, 2, 32)
    G.output('Section')
    G.finish_io()
    sil, seg = G.i['Silhouette'], G.i['Rim Segments']
    count = G.point_count(sil)
    rim = G.sample(sil, G.position(), G.sub(count, 1))
    rim_r, _, rim_z = G.sep(rim)

    # Double wall: up the outside, over a bead, down the offset inner wall.
    t = G.lo(G.i['Thickness'], G.mul(rim_r, .8))
    off = G.group(offset, 'Inner wall')
    G.link(sil, off.inputs['Profile'])
    G.link(t, off.inputs['Distance'])
    inner = off.outputs[0]
    inner_rim = G.sample(inner, G.position(), G.sub(count, 1))
    centre = G.v('SCALE', G.v('ADD', rim, inner_rim), scale=.5)
    radius = G.mul(G.v('DISTANCE', rim, inner_rim), .5)
    cx, _, cz = G.sep(centre)
    a0 = G.m('ARCTAN2', G.sub(rim_z, cz), G.sub(rim_r, cx))
    a = G.add(a0, G.mul(math.pi, G.div(G.add(G.index, 1), seg)))
    bead = G.points(G.switch('INT', G.i['Rounded Rim'], 0, G.sub(seg, 1)),
                    G.xz(G.add(cx, G.mul(radius, G.m('COSINE', a))), G.add(cz, G.mul(radius, G.m('SINE', a)))))
    reverse = G.n('GeometryNodeReverseCurve', 'Inner wall runs rim to floor')
    G.link(inner, reverse.inputs['Curve'])
    double = G.chain(G.ordered(G.curve_points(sil), 0), G.ordered(bead, 1e4),
                     G.ordered(G.curve_points(reverse.outputs[0]), 2e4))

    # Single surface: replace the rim point with a rolled lip that stops at the inner rim.
    b = G.mul(G.mul(G.lo(G.i['Rim'], .9), rim_r), .5)
    roll = G.mul(math.pi, G.div(G.index, seg))
    lip = G.points(G.switch('INT', G.m('GREATER_THAN', G.i['Rim'], 0), 1, G.add(seg, 1)),
                   G.xz(G.add(G.sub(rim_r, b), G.mul(b, G.m('COSINE', roll))), G.add(rim_z, G.mul(b, G.m('SINE', roll)))))
    body = G.delete(G.curve_points(sil), G.m('COMPARE', G.index, G.sub(count, 1)))
    single = G.chain(G.ordered(body, 0), G.ordered(lip, 1e4))

    G.link(G.switch('GEOMETRY', G.m('GREATER_THAN', G.i['Thickness'], 1e-6), single, double), G.o['Section'])
    G.layout()
    return G.g


def fill_group(offset):
    """The liquid: the silhouette, offset by a gap and cut at the fill level (SDK fillProfile)."""
    G = Graph(named('Liquid Fill'))
    G.input('Silhouette', 'NodeSocketGeometry')
    G.input('Fill', 'NodeSocketFloat', 0.5, 0.0, 1.0, 'Fraction of the vessel height.', subtype='FACTOR')
    G.input('Inset', 'NodeSocketFloat', 0.03, 0.0, 0.5, 'Gap off the glass, as a fraction of the widest radius.')
    G.output('Section')
    G.finish_io()
    sil = G.i['Silhouette']
    x, _, z = G.sep(G.position())
    base, top = G.stat(sil, z, 'Min'), G.stat(sil, z, 'Max')
    level = G.add(base, G.mul(G.sub(top, base), G.clamp(G.i['Fill'], 0, 1)))
    gap = G.mul(G.clamp(G.i['Inset'], 0, .5), G.stat(sil, x, 'Max'))
    off = G.group(offset, 'Clear the glass')
    G.link(sil, off.inputs['Profile'])
    G.link(gap, off.inputs['Distance'])
    inner = off.outputs[0]

    # Keep points up to the first one above the level; slide that one down onto the level.
    pos = G.position()
    _, _, pz = G.sep(pos)
    above = G.m('GREATER_THAN', pz, level)
    acc = G.n('GeometryNodeAccumulateField', 'Points above so far', data_type='FLOAT', domain='POINT')
    G.link(above, acc.inputs['Value'])
    prev = G.at(pos, G.hi(G.sub(G.index, 1), 0))
    _, _, prev_z = G.sep(prev)
    t = G.div(G.sub(level, prev_z), G.hi(G.sub(pz, prev_z), 1e-9))
    # Delete first: fields re-evaluate on each node's input, so moved points would no longer read as "above".
    cut = G.delete(inner, G.m('GREATER_THAN', G.sub(acc.outputs['Leading'], above), .5))
    onto = G.v('ADD', prev, G.v('SCALE', G.v('SUBTRACT', pos, prev), scale=t))
    cut = G.set_position(cut, onto, above)

    first = G.sample(inner, G.position(), 0)
    fx, _, fz = G.sep(first)
    surface = G.sample(cut, G.position(), G.sub(G.point_count(cut), 1))
    sx, _, sz = G.sep(surface)
    floor = G.points(G.m('GREATER_THAN', fx, 1e-6), G.xz(0, fz))
    meniscus = G.points(G.m('GREATER_THAN', sx, 1e-6), G.xz(0, sz))
    liquid = G.chain(G.ordered(floor, -1), G.ordered(G.curve_points(cut), 0), G.ordered(meniscus, 1e5))
    deep_enough = G.m('GREATER_THAN', level, G.add(fz, 1e-6))
    G.link(G.switch('GEOMETRY', deep_enough, None, liquid), G.o['Section'])
    G.layout()
    return G.g


def lathe_group():
    """Spin a profile (XZ plane, X = radius) around Z: Curve to Mesh with a circle as the path."""
    G = Graph(named('Lathe'))
    G.input('Profile', 'NodeSocketGeometry')
    G.input('Radial Segments', 'NodeSocketInt', 48, 3, 256)
    G.input('Smooth Angle', 'NodeSocketFloat', math.radians(40), 0.0, math.pi,
            'Edges sharper than this stay creased; the rest shade smooth.', subtype='ANGLE')
    G.output('Mesh')
    G.finish_io()
    # Curve to Mesh puts the profile's X along the path's outward normal and its Y along -Z.
    # On a unit-radius path, (radius - 1, -height) therefore lands exactly at (radius, height).
    factor = G.n('GeometryNodeSplineParameter', 'Along profile').outputs['Factor']
    profile = G.store(G.i['Profile'], 'lathe_v', factor)
    x, _, z = G.sep(G.position())
    frame = G.n('ShaderNodeCombineXYZ', 'Profile frame')
    G.link(G.sub(x, 1), frame.inputs['X'])
    G.link(G.mul(z, -1), frame.inputs['Y'])
    profile = G.set_position(profile, frame.outputs[0])
    # A closed circle keeps every profile copy exactly radial (an open arc tilts its two ends).
    circle = G.n('GeometryNodeCurvePrimitiveCircle', 'One full turn')
    G.link(G.i['Radial Segments'], circle.inputs['Resolution'])
    circle.inputs['Radius'].default_value = 1
    sweep = G.n('GeometryNodeCurveToMesh', 'Revolve')
    G.link(circle.outputs['Curve'], sweep.inputs['Curve'])
    G.link(profile, sweep.inputs['Profile Curve'])
    weld = G.n('GeometryNodeMergeByDistance', 'Weld axis poles')
    weld.inputs['Distance'].default_value = 1e-5
    G.link(sweep.outputs[0], weld.inputs['Geometry'])
    # With this profile frame Curve to Mesh winds faces inward; flip so normals face out.
    flip = G.n('GeometryNodeFlipFaces', 'Normals outward')
    G.link(weld.outputs[0], flip.inputs['Mesh'])
    mesh = flip.outputs[0]

    # UV: U is the angle around the axis, V the distance along the profile.
    # Faces that straddle the seam see their angle-0 corners as U = 1 instead of 0.
    def turns(vector):
        px, py, _ = G.sep(vector)
        return G.m('FRACT', G.add(G.div(G.m('ARCTAN2', py, px), math.tau), 1))
    centre = G.n('GeometryNodeFieldOnDomain', 'Face centre', domain='FACE', data_type='FLOAT_VECTOR')
    G.link(G.position(), centre.inputs[0])
    u = turns(G.position())
    u = G.add(u, G.m('LESS_THAN', G.sub(u, turns(centre.outputs[0])), -.5))
    uv = G.n('ShaderNodeCombineXYZ', 'U around, V along')
    G.link(u, uv.inputs['X'])
    G.link(G.named('lathe_v'), uv.inputs['Y'])
    mesh = G.store(mesh, 'UVMap', uv.outputs[0], kind='FLOAT2', domain='CORNER')
    remove = G.n('GeometryNodeRemoveAttribute', 'Remove helper')
    remove.inputs['Name'].default_value = 'lathe_v'
    G.link(mesh, remove.inputs['Geometry'])
    mesh = remove.outputs[0]
    smooth = G.n('GeometryNodeSetShadeSmooth', 'Smooth faces', domain='FACE')
    G.link(mesh, smooth.inputs['Mesh'])
    angle = G.n('GeometryNodeInputMeshEdgeAngle', 'Edge angle').outputs['Unsigned Angle']
    sharp = G.n('GeometryNodeSetShadeSmooth', 'Crease sharp edges', domain='EDGE')
    G.link(smooth.outputs[0], sharp.inputs['Mesh'])
    G.link(G.m('LESS_THAN', angle, G.i['Smooth Angle']), sharp.inputs['Shade Smooth'])
    G.link(sharp.outputs[0], G.o['Mesh'])
    G.layout()
    return G.g
