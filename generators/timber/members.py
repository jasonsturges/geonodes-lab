"""Timber members: GNL • Weathered Plank (a sawn board) and GNL • Hewn Timber (a split log).

Origin: three-low-poly WeatheredPlankGeometry and createHewnTimberGeometry, reworked in Blender with
smooth seeded noise, the four lumber warps (bow, crook, cup, twist), per-facet hewing, and a `grain`
attribute for materials. First explored in the NodesLab prototype's study 028.
"""
import math

from authoring.graph import Graph
from authoring.naming import named


# ---------------------------------------------------------------------------
# Noise helpers
# ---------------------------------------------------------------------------

def hash_noise(G, vector, w):
    """Signed per-position hash in [-1, 1]: Blender's White Noise is the SDK's sin-hash analogue.

    Same position + same W gives the same value, which keeps coincident corners welded.
    Exact SDK numbers are not reproduced (float32 sin-hash is not portable); the role is.
    """
    node = G.n('ShaderNodeTexWhiteNoise', 'Hash (white noise)', noise_dimensions='4D')
    G.link(vector, node.inputs['Vector'])
    G.link(w, node.inputs['W'])
    return G.sub(G.mul(node.outputs['Value'], 2), 1)


def smooth_noise(G, vector, w, scale=1.0, detail=2.0):
    """Signed coherent noise, roughly [-1, 1]: neighbouring points move together."""
    node = G.n('ShaderNodeTexNoise', 'Smooth noise', noise_dimensions='4D')
    G.link(vector, node.inputs['Vector'])
    G.link(w, node.inputs['W'])
    node.inputs['Scale'].default_value = scale
    node.inputs['Detail'].default_value = detail
    return G.mul(G.sub(node.outputs['Fac'], .5), 2.5)


def sign(G, value):
    return G.m('SIGN', value)


def store_uv_and_grain(G, mesh, uv, grain):
    mesh = G.store(mesh, 'UVMap', uv, kind='FLOAT2', domain='CORNER')
    return G.store(mesh, 'grain', grain, kind='FLOAT_VECTOR')


# ---------------------------------------------------------------------------
# Weathered Plank
# ---------------------------------------------------------------------------

def plank():
    """Blender-native plank: smooth seeded wander and the four classic lumber warps."""
    G = Graph(named('Weathered Plank'))
    for name, default, lo, hi, text in [
            ('Length', 3.0, .3, 8.0, 'Long axis, along local X. Centered at the origin.'),
            ('Width', .45, .05, 1.0, ''), ('Thickness', .14, .01, .4, '')]:
        G.input(name, 'NodeSocketFloat', default, lo, hi, text)
    G.input('Length Segments', 'NodeSocketInt', 24, 1, 200, 'More segments let edges and warp curve smoothly.')
    G.input('Width Segments', 'NodeSocketInt', 4, 1, 32)
    G.input('Seed', 'NodeSocketInt', 137, 0, 65535, 'Change for a different board.')
    for name, default, lo, hi, text in [
            ('Edge Roughness', .04, 0.0, .3, 'Wavy, uneven long edges, fraction of width.'),
            ('End Skew', .06, 0.0, .3, 'Ends cut slightly off square, fraction of width.'),
            ('Bow', .03, 0.0, .5, 'Bend along the length, out of the face (metres at mid-length).'),
            ('Crook', .015, 0.0, .5, 'Bend along the length, in the plane of the face (metres).'),
            ('Cup', .01, 0.0, .1, 'Edges curl up across the width (metres).'),
            ('Twist', math.radians(4), 0.0, math.radians(45), 'End-to-end rotation about the long axis.'),
            ('Surface', .03, 0.0, .2, 'Fine surface unevenness, fraction of thickness.')]:
        G.input(name, 'NodeSocketFloat', default, lo, hi, text, subtype='ANGLE' if name == 'Twist' else None)
    G.input('Randomize Warp', 'NodeSocketBool', True,
            description='Each warp becomes a seeded amount between -max and +max. Off: exactly the values above.')
    G.output('Mesh')
    G.finish_io()
    i = G.i
    L, W, T, seed = i['Length'], i['Width'], i['Thickness'], i['Seed']
    cube = G.n('GeometryNodeMeshCube', 'Board')
    G.link(G.xyz(L, W, T), cube.inputs['Size'])
    G.link(G.add(i['Length Segments'], 1), cube.inputs['Vertices X'])
    G.link(G.add(i['Width Segments'], 1), cube.inputs['Vertices Y'])
    cube.inputs['Vertices Z'].default_value = 2
    pos = G.position()
    x, y, z = G.sep(pos)
    nx = G.div(x, G.mul(L, .5))           # -1 … 1 along the length
    ey = G.div(y, G.mul(W, .5))           # -1 … 1 across the width
    along = G.sub(1, G.mul(nx, nx))       # 0 at the ends, 1 at mid-length

    def warp(k):
        """+1 when not randomizing, else a seeded amount in [-1, 1] for warp k."""
        return G.switch('FLOAT', i['Randomize Warp'], 1.0, hash_noise(G, G.xyz(k, 0, 0), seed))

    # Edges wander smoothly along the length; each long edge has its own noise.
    edge = smooth_noise(G, G.xyz(G.div(x, W), G.mul(sign(G, y), 7), 0), seed, scale=.6)
    dy = G.mul(G.mul(G.mul(edge, i['Edge Roughness']), W), G.m('ABSOLUTE', ey))
    # Ends: a seeded skew angle plus slight raggedness.
    end = G.m('GREATER_THAN', G.m('ABSOLUTE', nx), .999)
    skew = G.mul(hash_noise(G, G.xyz(sign(G, x), 3, 0), seed), ey)
    ragged = G.mul(hash_noise(G, G.xyz(sign(G, x), G.mul(y, 13), G.mul(z, 13)), G.add(seed, 5)), .25)
    dx = G.mul(G.mul(end, G.mul(G.add(skew, ragged), G.mul(W, i['End Skew']))), sign(G, x))
    # Warps.
    dz = G.add(G.mul(G.mul(i['Bow'], warp(1)), along), G.mul(G.mul(i['Cup'], warp(3)), G.mul(ey, ey)))
    dy = G.add(dy, G.mul(G.mul(i['Crook'], warp(2)), along))
    surface = smooth_noise(G, G.v('SCALE', pos, scale=G.div(6, W)), G.add(seed, 11), detail=4)
    dz = G.add(dz, G.mul(G.mul(surface, i['Surface']), T))
    px, py, pz = G.add(x, dx), G.add(y, dy), G.add(z, dz)
    # Twist: rotate each cross-section about X, linearly from end to end.
    a = G.mul(G.mul(i['Twist'], warp(4)), G.mul(nx, .5))
    ca, sa = G.m('COSINE', a), G.m('SINE', a)
    moved = G.xyz(px, G.sub(G.mul(py, ca), G.mul(pz, sa)), G.add(G.mul(py, sa), G.mul(pz, ca)))
    mesh = G.set_position(cube.outputs['Mesh'], moved)
    mesh = store_uv_and_grain(G, mesh, cube.outputs['UV Map'], pos)
    G.link(mesh, G.o['Mesh'])
    G.layout()
    G.g.description = 'Rough-sawn board, long axis X, centered. Seeded edges/ends and bow, crook, cup, twist.'
    return G.g


# ---------------------------------------------------------------------------
# Hewn Timber
# ---------------------------------------------------------------------------

def timber():
    """Blender-native hewn timber: seeded per-facet hewing, taper, bow and twist, in real units."""
    G = Graph(named('Hewn Timber'))
    G.input('Length', 'NodeSocketFloat', 2.0, .1, 12.0, 'Along local Z; the butt sits at Z = 0.')
    G.input('Diameter', 'NodeSocketFloat', .25, .02, 2.0, 'Across the top end.')
    G.input('Taper', 'NodeSocketFloat', .1, 0.0, .5, 'How much wider the butt is than the top.')
    G.input('Facets', 'NodeSocketInt', 7, 3, 32, 'Axe faces around the log.')
    G.input('Rings', 'NodeSocketInt', 8, 1, 64, 'Rows along the length; more lets the hewing vary.')
    G.input('Seed', 'NodeSocketInt', 7, 0, 65535, 'Change for a different log.')
    for name, default, lo, hi, text in [
            ('Facet Variation', .08, 0.0, .3, 'Each axe face cut to its own depth, fraction of radius.'),
            ('Irregularity', .05, 0.0, .3, 'Smooth lumps along the log, fraction of radius.'),
            ('Bow', .03, 0.0, .5, 'Sideways bend at mid-length (metres).'),
            ('Twist', math.radians(12), 0.0, math.pi, 'Facets spiral by this much end to end.')]:
        G.input(name, 'NodeSocketFloat', default, lo, hi, text, subtype='ANGLE' if name == 'Twist' else None)
    G.input('Randomize Warp', 'NodeSocketBool', True,
            description='Bow and twist become seeded amounts between -max and +max.')
    G.output('Mesh')
    G.finish_io()
    i = G.i
    L, seed = i['Length'], i['Seed']
    r_top = G.mul(i['Diameter'], .5)
    cone = G.n('GeometryNodeMeshCone', 'Log', fill_type='NGON')
    G.link(i['Facets'], cone.inputs['Vertices'])
    G.link(i['Rings'], cone.inputs['Side Segments'])
    G.link(r_top, cone.inputs['Radius Top'])
    G.link(G.mul(r_top, G.add(1, i['Taper'])), cone.inputs['Radius Bottom'])
    G.link(L, cone.inputs['Depth'])
    pos = G.position()
    x, y, z = G.sep(pos)
    t = G.div(z, L)                                   # 0 at the butt, 1 at the top
    angle = G.m('ARCTAN2', y, x)
    facet = G.m('FLOORED_MODULO', G.m('ROUND', G.div(G.mul(angle, i['Facets']), math.tau)), i['Facets'])
    cut = G.mul(hash_noise(G, G.xyz(facet, 0, 0), seed), i['Facet Variation'])
    lumps = G.mul(smooth_noise(G, G.v('SCALE', pos, scale=G.div(3, i['Diameter'])), G.add(seed, 23)),
                  i['Irregularity'])
    k = G.add(1, G.add(cut, lumps))

    def warp(n):
        return G.switch('FLOAT', i['Randomize Warp'], 1.0, hash_noise(G, G.xyz(n, 9, 0), seed))

    a = G.mul(G.mul(i['Twist'], warp(1)), t)
    ca, sa = G.m('COSINE', a), G.m('SINE', a)
    rx, ry = G.mul(x, k), G.mul(y, k)
    bow = G.mul(G.mul(i['Bow'], warp(2)), G.mul(G.mul(t, G.sub(1, t)), 4))
    moved = G.xyz(G.add(G.sub(G.mul(rx, ca), G.mul(ry, sa)), bow), G.add(G.mul(rx, sa), G.mul(ry, ca)), z)
    mesh = G.set_position(cone.outputs['Mesh'], moved)  # Cone already spans Z 0…Length
    mesh = store_uv_and_grain(G, mesh, cone.outputs['UV Map'], G.xyz(z, x, y))
    G.link(mesh, G.o['Mesh'])
    G.layout()
    G.g.description = 'Axe-hewn log in real units, Z up from the butt. Seeded facets, lumps, bow and twist.'
    return G.g
