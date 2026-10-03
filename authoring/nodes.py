"""Small graph-writing primitives. Geometry formulas stay with their authors."""
import bpy


def socket(group, name, kind, default=None, low=None, high=None,
           direction='INPUT', *, description=None, subtype=None):
    result = group.interface.new_socket(
        name=name, in_out=direction, socket_type=kind)
    for key, value in (('default_value', default), ('min_value', low),
                       ('max_value', high), ('description', description),
                       ('subtype', subtype)):
        if value is not None:
            setattr(result, key, value)
    return result


def node(group, kind, label, x, y, *, width=190):
    result = group.nodes.new(kind)
    result.label = label
    result.location = (x, y)
    result.width = width
    return result


def feed(group, value, target):
    """Connect a socket, or assign a literal default; preserve native node types."""
    if isinstance(value, bpy.types.NodeSocket):
        group.links.new(value, target)
    else:
        target.default_value = value


def calc(group, operation, a, b=0, x=0, y=0):
    result = node(group, 'ShaderNodeMath', operation, x, y)
    result.operation = operation
    feed(group, a, result.inputs[0])
    feed(group, b, result.inputs[1])
    return result.outputs[0]


def vec(group, operation, a, b=0, x=0, y=0):
    """Binary vector operations plus NORMALIZE, SCALE and DOT_PRODUCT.

    This intentionally is not a wrapper for every Vector Math socket layout.
    Use native nodes directly for operations with other arities/output types.
    """
    allowed = {'ADD', 'SUBTRACT', 'MULTIPLY', 'DIVIDE', 'CROSS_PRODUCT',
               'NORMALIZE', 'SCALE', 'DOT_PRODUCT'}
    if operation not in allowed:
        raise ValueError(f'Unsupported vec operation: {operation}')
    result = node(group, 'ShaderNodeVectorMath', operation, x, y)
    result.operation = operation
    feed(group, a, result.inputs[0])
    if operation != 'NORMALIZE':
        feed(group, b, result.inputs['Scale'] if operation == 'SCALE'
             else result.inputs[1])
    return result.outputs['Value'] if operation == 'DOT_PRODUCT' else result.outputs[0]


def attr(group, name, kind, x, y):
    result = node(group, 'GeometryNodeInputNamedAttribute', name, x, y)
    result.data_type = kind
    result.inputs['Name'].default_value = name
    return result.outputs['Attribute']
