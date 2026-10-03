"""Small helpers shared by the fence modules."""
from authoring.graph import Graph


def rand(G, index, k, seed):
    """A seeded value in [-1, 1] for element `index` and channel `k` (White Noise as a hash)."""
    node = G.n('ShaderNodeTexWhiteNoise', f'Random channel {k}', noise_dimensions='4D')
    G.link(G.xyz(index, k, 0), node.inputs['Vector'])
    G.link(seed, node.inputs['W'])
    return G.sub(G.mul(node.outputs['Value'], 2), 1)


def unit(G, index, k, seed):
    """A seeded value in [0, 1]."""
    return G.mul(G.add(rand(G, index, k, seed), 1), .5)


def foreach(G, points, label):
    """A For Each Element zone over points; returns (zone input node, zone output node)."""
    zin = G.n('GeometryNodeForeachGeometryElementInput', f'For each {label}')
    zout = G.n('GeometryNodeForeachGeometryElementOutput', f'… next {label}')
    zin.pair_with_output(zout)
    zout.domain = 'POINT'
    G.link(points, zin.inputs['Geometry'])
    return zin, zout


def generation(zout):
    """The zone's generated-geometry input: everything linked here is joined across iterations."""
    return next(s for s in zout.inputs if s.identifier == 'Generation_0')


def transform(G, geometry, translation=None, rotation=None, label='Transform'):
    node = G.n('GeometryNodeTransform', label)
    G.link(geometry, node.inputs['Geometry'])
    if translation is not None:
        G.link(translation, node.inputs['Translation'])
    if rotation is not None:
        G.link(rotation, node.inputs['Rotation'])
    return node.outputs[0]


def rand1(G, k, seed):
    node = G.n('ShaderNodeTexWhiteNoise', f'Random {k}', noise_dimensions='4D')
    G.link(G.xyz(k, 0, 0), node.inputs['Vector'])
    G.link(seed, node.inputs['W'])
    return node.outputs['Value']          # 0 … 1
