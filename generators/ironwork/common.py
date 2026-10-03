"""Small helpers shared by the ironwork modules (thin names over authoring.graph.Graph methods)."""
from authoring.graph import Graph


def rand(G, index, k, seed):
    return G.random(index, k, seed)


def unit(G, index, k, seed):
    return G.unit(index, k, seed)


def transform(G, geometry, translation=None, rotation=None, scale=None, label='Transform'):
    return G.transform(geometry, translation, rotation, scale, label)


def panels(G, spec, closed=()):
    G.panels(spec, closed=closed)


def menu(G, socket, options, label):
    node = G.n('GeometryNodeMenuSwitch', label, data_type='GEOMETRY')
    node.enum_items.clear()
    for name in options:
        node.enum_items.new(name)
    G.link(socket, node.inputs['Menu'])
    return node


def sweep(G, curve, profile, *, caps=True, scale=None, label='Sweep'):
    node = G.n('GeometryNodeCurveToMesh', label)
    G.link(curve, node.inputs['Curve'])
    G.link(profile, node.inputs['Profile Curve'])
    node.inputs['Fill Caps'].default_value = caps
    if scale is not None:
        G.link(scale, node.inputs['Scale'])
    return node.outputs[0]


def square(G, width, height=None):
    node = G.n('GeometryNodeCurvePrimitiveQuadrilateral', 'Bar section')
    G.link(width, node.inputs['Width'])
    G.link(height if height is not None else width, node.inputs['Height'])
    return node.outputs[0]


def circle(G, radius, resolution=8):
    node = G.n('GeometryNodeCurvePrimitiveCircle', 'Round section')
    G.link(radius, node.inputs['Radius'])
    node.inputs['Resolution'].default_value = resolution
    return node.outputs[0]


def vertical_line(G, z0, z1, count):
    line = G.n('GeometryNodeCurvePrimitiveLine', 'Bar axis')
    G.link(G.xyz(0, 0, z0), line.inputs['Start'])
    G.link(G.xyz(0, 0, z1), line.inputs['End'])
    res = G.n('GeometryNodeResampleCurve', 'Stations')
    G.link(line.outputs[0], res.inputs['Curve'])
    G.link(count, res.inputs['Count'])
    return res.outputs[0]


# ---------------------------------------------------------------------------
