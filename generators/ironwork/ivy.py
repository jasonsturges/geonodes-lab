"""Ivy ironwork: GNL • Ivy Leaf, Tendril and Ivy Iron (a forged vine on any curve)."""
import math

from authoring.graph import Graph
from authoring.naming import named
from common import rand, unit, transform, panels, menu, sweep, square, circle, vertical_line


# Ivy leaf outline, normalized (length 1, stalk at the origin): a long central lobe, two shallow
# side lobes each side and a heart-shaped notch where the stalk joins. The website's leaf
# (Ivy.ts) is the same five-lobe idea with deep notches; at forged-ornament size those read as
# stars, so the sinuses here are shallow. Right half, tip to notch; mirrored for the left.
LEAF_RIGHT = [(0, 1.0), (.1, .83), (.16, .69), (.23, .63), (.37, .63), (.47, .53), (.43, .42), (.37, .36),
              (.45, .26), (.42, .13), (.28, .04), (.12, .03)]
LEAF_NOTCH = (0, .1)
LEAF = LEAF_RIGHT + [LEAF_NOTCH] + [(-x, y) for x, y in reversed(LEAF_RIGHT[1:])]


def leaf_group():
    """A cast ivy leaf: five-lobe outline, filled, thickened and gently cupped. Stalk at the
    origin, length along +Z, face toward −Y (the leaf lies in the XZ plane)."""
    G = Graph(named('Ivy Leaf'))
    G.input('Size', 'NodeSocketFloat', .1, .005, 2.0, 'Stalk to tip.')
    G.input('Thickness', 'NodeSocketFloat', .006, .0005, .1, '')
    G.input('Cup', 'NodeSocketFloat', .15, 0.0, 1.0, 'Lobes lift toward the face, × Size.')
    G.input('Angular', 'NodeSocketBool', False, description='Straight-edged low-poly outline (website style).')
    G.output('Mesh')
    G.finish_io()
    i = G.i
    s = i['Size']
    pts = [G.xyz(G.mul(s, x), G.mul(s, y), 0) for x, y in LEAF]
    line = G.n('GeometryNodeMeshLine', 'Outline stations')
    line.inputs['Count'].default_value = len(pts)
    placed = G.set_position(line.outputs['Mesh'], G.pick(G.index, pts))
    curve = G.n('GeometryNodeMeshToCurve', 'Outline')
    G.link(placed, curve.inputs['Mesh'])
    closed = G.n('GeometryNodeSetSplineCyclic', 'Close it')
    G.link(curve.outputs[0], closed.inputs['Geometry'])
    closed.inputs['Cyclic'].default_value = True
    # Soft (default): Catmull-Rom through the same points rounds the lobes like forged sheet.
    soft = G.n('GeometryNodeCurveSplineType', 'Soften', spline_type='CATMULL_ROM')
    G.link(closed.outputs[0], soft.inputs['Curve'])
    res = G.n('GeometryNodeSetSplineResolution', 'Smoothness')
    G.link(soft.outputs[0], res.inputs['Curve'])
    res.inputs['Resolution'].default_value = 4
    outline = G.switch('GEOMETRY', i['Angular'], res.outputs[0], closed.outputs[0])
    fill = G.n('GeometryNodeFillCurve', 'Leaf face')
    G.link(outline, fill.inputs['Curve'])
    fill.inputs['Mode'].default_value = 'N-gons'
    extrude = G.n('GeometryNodeExtrudeMesh', 'Thickness', mode='FACES')
    G.link(fill.outputs[0], extrude.inputs['Mesh'])
    G.link(i['Thickness'], extrude.inputs['Offset Scale'])
    extrude.inputs['Individual'].default_value = False
    bottom = G.n('GeometryNodeFlipFaces', 'Back face')
    G.link(fill.outputs[0], bottom.inputs['Mesh'])
    weld = G.n('GeometryNodeMergeByDistance', 'Weld')
    G.link(G.join(extrude.outputs['Mesh'], bottom.outputs[0]), weld.inputs['Geometry'])
    weld.inputs['Distance'].default_value = 1e-7
    # Cup: lift each point by its distance from the midrib (x), so the lobes rise like a real leaf.
    x, y, z = G.sep(G.position())
    cupped = G.set_position(weld.outputs[0], G.xyz(x, y, G.add(z, G.mul(G.mul(i['Cup'], s),
                                                                         G.div(G.mul(x, x), G.mul(s, s))))))
    stood = transform(G, cupped, rotation=(math.pi / 2, 0, 0), label='Into XZ: length up +Z, face −Y')
    G.link(stood, G.o['Mesh'])
    G.layout()
    G.g.description = "A cast ivy leaf after the website's angular five-lobe outline, stalk at the origin."
    return G.g


def tendril_group():
    """A small forged curl: a log spiral starting at the origin heading +Z, curling toward +X."""
    G = Graph(named('Tendril'))
    G.input('Size', 'NodeSocketFloat', .05, .005, 1.0, 'Starting radius of the curl.')
    G.input('Turns', 'NodeSocketFloat', 1.4, .2, 4.0)
    G.input('Radius', 'NodeSocketFloat', .004, .0005, .05, 'Bar radius at the root.')
    G.output('Mesh')
    G.finish_io()
    i = G.i
    n = 40
    line = G.n('GeometryNodeMeshLine', 'Curl stations')
    line.inputs['Count'].default_value = n + 1
    theta = G.mul(G.div(G.index, n), G.mul(i['Turns'], math.tau))
    r = G.mul(i['Size'], G.m('EXPONENT', G.mul(theta, -.28)))
    # The website volute: (u, v) = (r·sinθ, r0 − r·cosθ) starts on its own tangent, heading +u.
    spot = G.xyz(G.sub(i['Size'], G.mul(r, G.m('COSINE', theta))), 0, G.mul(r, G.m('SINE', theta)))
    curve = G.n('GeometryNodeMeshToCurve', 'Curl')
    G.link(G.set_position(line.outputs['Mesh'], spot), curve.inputs['Mesh'])
    profile = G.n('GeometryNodeCurvePrimitiveCircle', 'Round bar')
    profile.inputs['Resolution'].default_value = 6
    G.link(i['Radius'], profile.inputs['Radius'])
    sweep = G.n('GeometryNodeCurveToMesh', 'Forge')
    G.link(curve.outputs[0], sweep.inputs['Curve'])
    G.link(profile.outputs[0], sweep.inputs['Profile Curve'])
    sweep.inputs['Fill Caps'].default_value = True
    t = G.n('GeometryNodeSplineParameter', 'Along').outputs['Factor']
    G.link(G.sub(1, G.mul(t, .6)), sweep.inputs['Scale'])
    G.link(sweep.outputs[0], G.o['Mesh'])
    G.layout()
    G.g.description = 'A tendril curl: a tapering log spiral, root at the origin heading +Z.'
    return G.g


IVY_SPEC = {
    'Vine': ['Path', 'Length', 'Waviness', 'Wavelength', 'Stem Radius', 'Tip Scale'],
    'Leaves': ['Leaf Spacing', 'Leaf Size', 'Leaf Taper', 'Leaf Angle', 'Size Jitter', 'Cup'],
    'Tendrils': ['Tendril Chance', 'Tendril Size'],
    'Facing': ['Climb'],
    'Variation': ['Seed'],
}


def ivy_group(leaf, tendril):
    G = Graph(named('Ivy Iron'))
    for name, kind, default, lo, hi, text in [
            ('Path', 'NodeSocketGeometry', None, None, None, 'Optional vine curve. Empty = grow a wandering vine along X.'),
            ('Length', 'NodeSocketFloat', 2.0, .1, 20.0, 'Grown vine length.'),
            ('Waviness', 'NodeSocketFloat', .12, 0.0, 2.0, 'Grown vine sway (metres).'),
            ('Wavelength', 'NodeSocketFloat', .7, .05, 10.0, ''),
            ('Stem Radius', 'NodeSocketFloat', .014, .001, .2, 'At the root.'),
            ('Tip Scale', 'NodeSocketFloat', .35, .05, 1.0, 'Stem radius at the tip, × root.'),
            ('Leaf Spacing', 'NodeSocketFloat', .17, .01, 2.0, 'Along the vine.'),
            ('Leaf Size', 'NodeSocketFloat', .1, .005, 1.0, ''),
            ('Leaf Taper', 'NodeSocketFloat', .5, 0.0, 1.0, 'Leaves shrink toward the tip by this fraction.'),
            ('Leaf Angle', 'NodeSocketFloat', math.radians(50), 0.0, math.pi / 2, 'Off the vine, alternating sides.'),
            ('Size Jitter', 'NodeSocketFloat', .2, 0.0, .9, ''),
            ('Cup', 'NodeSocketFloat', .15, 0.0, 1.0, ''),
            ('Tendril Chance', 'NodeSocketFloat', .25, 0.0, 1.0, 'Chance a leaf station also sprouts a curl opposite.'),
            ('Tendril Size', 'NodeSocketFloat', .04, .005, .5, ''),
            ('Climb', 'NodeSocketBool', False, None, None, 'Leaves face outward from the Z axis (a vine round a post). Off: they face −Y (flat ironwork).'),
            ('Seed', 'NodeSocketInt', 3, 0, 65535, '')]:
        G.input(name, kind, default, lo, hi, text, subtype='ANGLE' if name == 'Leaf Angle' else None)
    G.output('Mesh')
    G.finish_io()
    i = G.i
    seed = i['Seed']
    # --- The vine: the given path, or a grown wandering wave in the XZ plane. -------------------
    line = G.n('GeometryNodeCurvePrimitiveLine', 'Grown vine')
    half = G.mul(i['Length'], .5)
    G.link(G.xyz(G.mul(half, -1), 0, 0), line.inputs['Start'])
    G.link(G.xyz(half, 0, 0), line.inputs['End'])
    dense = G.n('GeometryNodeResampleCurve', 'Dense')
    G.link(line.outputs[0], dense.inputs['Curve'])
    G.link(G.hi(8, G.mul(i['Length'], 60)), dense.inputs['Count'])
    x, _, _ = G.sep(G.position())
    phase = G.mul(rand(G, 0, 1, seed), math.pi)
    sway = G.add(G.mul(i['Waviness'], G.m('SINE', G.add(G.div(G.mul(x, math.tau), i['Wavelength']), phase))),
                 G.mul(G.mul(i['Waviness'], .35), G.m('SINE', G.add(G.div(G.mul(x, 2.7 * math.pi), i['Wavelength']), G.mul(phase, 2)))))
    grown = G.set_position(dense.outputs[0], G.xyz(x, 0, sway))
    given = G.n('GeometryNodeResampleCurve', 'Your path, evenly')
    G.link(i['Path'], given.inputs['Curve'])
    given.inputs['Mode'].default_value = 'Length'
    given.inputs['Length'].default_value = .01
    has_path = G.m('GREATER_THAN', G.point_count(i['Path']), 0)
    vine = G.switch('GEOMETRY', has_path, grown, given.outputs[0])
    # --- Stem: round bar tapering from root to tip. -------------------------------------------------
    profile = G.n('GeometryNodeCurvePrimitiveCircle', 'Round stem')
    profile.inputs['Resolution'].default_value = 8
    G.link(i['Stem Radius'], profile.inputs['Radius'])
    stem = G.n('GeometryNodeCurveToMesh', 'Forge the stem')
    G.link(vine, stem.inputs['Curve'])
    G.link(profile.outputs[0], stem.inputs['Profile Curve'])
    stem.inputs['Fill Caps'].default_value = True
    u = G.n('GeometryNodeSplineParameter', 'Root → tip').outputs['Factor']
    G.link(G.sub(1, G.mul(u, G.sub(1, i['Tip Scale']))), stem.inputs['Scale'])
    # --- Leaf stations along the vine. ---------------------------------------------------------------
    stations = G.n('GeometryNodeCurveToPoints', 'Leaf stations', mode='LENGTH')
    G.link(vine, stations.inputs['Curve'])
    G.link(i['Leaf Spacing'], stations.inputs['Length'])
    pts = stations.outputs['Points']
    tangent = G.v('NORMALIZE', stations.outputs['Tangent'])
    idx = G.index
    count = G.n('GeometryNodeAttributeDomainSize', 'Stations', component='POINTCLOUD')
    G.link(pts, count.inputs[0])
    along = G.div(idx, G.hi(G.sub(count.outputs['Point Count'], 1), 1))     # 0 at the root, 1 at the tip
    px, py, _ = G.sep(G.position())
    face = G.switch('VECTOR', i['Climb'], (0, -1, 0), G.v('NORMALIZE', G.xyz(px, py, 0)))
    side = G.sub(G.mul(G.m('FLOORED_MODULO', idx, 2), 2), 1)                # -1, +1 alternating
    # Turn the tangent by ±Leaf Angle about the face direction (Rodrigues for a perpendicular axis).
    def turned(sign_angle):
        c, s = G.m('COSINE', sign_angle), G.m('SINE', sign_angle)
        return G.v('NORMALIZE', G.v('ADD', G.v('SCALE', tangent, scale=c),
                                    G.v('SCALE', G.v('CROSS_PRODUCT', face, tangent), scale=s)))
    leaf_dir = turned(G.mul(i['Leaf Angle'], side))
    curl_dir = turned(G.mul(G.mul(i['Leaf Angle'], side), -1.2))

    def frame(direction):
        a = G.n('FunctionNodeAlignRotationToVector', 'Length along the direction', axis='Z')
        G.link(direction, a.inputs['Vector'])
        b = G.n('FunctionNodeAlignRotationToVector', 'Face toward Face', axis='Y', pivot_axis='Z')
        G.link(a.outputs['Rotation'], b.inputs['Rotation'])
        G.link(G.v('SCALE', face, scale=-1), b.inputs['Vector'])           # leaf's −Y is its face
        return b.outputs['Rotation']
    size = G.mul(G.sub(1, G.mul(i['Leaf Taper'], along)), G.add(1, G.mul(i['Size Jitter'], rand(G, idx, 2, seed))))
    one_leaf = G.group(leaf, 'Leaf')
    G.link(i['Leaf Size'], one_leaf.inputs['Size'])
    G.link(i['Cup'], one_leaf.inputs['Cup'])
    G.link(G.mul(i['Leaf Size'], .08), one_leaf.inputs['Thickness'])
    inst = G.n('GeometryNodeInstanceOnPoints', 'A leaf at every station')
    G.link(pts, inst.inputs['Points'])
    G.link(one_leaf.outputs[0], inst.inputs['Instance'])
    G.link(frame(leaf_dir), inst.inputs['Rotation'])
    G.link(size, inst.inputs['Scale'])
    leaves = G.n('GeometryNodeRealizeInstances', 'Real leaves')
    G.link(inst.outputs[0], leaves.inputs['Geometry'])
    # Tendrils: some stations also sprout a curl on the other side.
    curl = G.group(tendril, 'Tendril')
    G.link(i['Tendril Size'], curl.inputs['Size'])
    G.link(G.mul(i['Stem Radius'], .45), curl.inputs['Radius'])
    sprout = G.m('LESS_THAN', G.mul(G.add(rand(G, idx, 3, seed), 1), .5), i['Tendril Chance'])
    cinst = G.n('GeometryNodeInstanceOnPoints', 'A curl at some stations')
    G.link(pts, cinst.inputs['Points'])
    G.link(sprout, cinst.inputs['Selection'])
    G.link(curl.outputs[0], cinst.inputs['Instance'])
    G.link(frame(curl_dir), cinst.inputs['Rotation'])
    G.link(size, cinst.inputs['Scale'])
    curls = G.n('GeometryNodeRealizeInstances', 'Real curls')
    G.link(cinst.outputs[0], curls.inputs['Geometry'])
    G.link(G.join(stem.outputs[0], leaves.outputs[0], curls.outputs[0]), G.o['Mesh'])
    G.layout()
    for title, names in IVY_SPEC.items():
        panel = G.g.interface.new_panel(name=title)
        for name in names:
            G.g.interface.move_to_parent(G.g.interface.items_tree[name], panel, 100)
    G.g.description = 'A forged ivy vine on any curve: tapering stem, cast leaves alternating sides, tendril curls.'
    return G.g



# ---------------------------------------------------------------------------
