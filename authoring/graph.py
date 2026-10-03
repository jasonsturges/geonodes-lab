"""A small, readable Geometry Nodes graph writer shared by builders.

`Graph` wraps one node group: declare sockets, call `finish_io()`, build with short helpers (math,
vectors, fields, geometry, seeded randomness), then `layout()` for a left-to-right arrangement and
`panels()` to group inputs. Builders keep their own geometry formulas; this removes wiring noise.
Tested in Blender 5.2.1.
"""
import bpy
from .nodes import socket, feed


class Graph:
    def __init__(self, name, *, modifier=False):
        self.g = bpy.data.node_groups.new(name, 'GeometryNodeTree')
        self.g.is_modifier = modifier
        self._index = None

    @classmethod
    def of(cls, group):
        """Wrap an existing node group (e.g. to add panels or defaults after it is built)."""
        graph = cls.__new__(cls)
        graph.g = group
        graph._index = None
        return graph

    def input(self, name, kind, default=None, low=None, high=None, description=None, subtype=None):
        return socket(self.g, name, kind, default, low, high, description=description, subtype=subtype)

    def output(self, name, kind='NodeSocketGeometry'):
        return socket(self.g, name, kind, direction='OUTPUT')

    def finish_io(self):
        self.i = self.n('NodeGroupInput', 'Inputs').outputs
        self.o = self.n('NodeGroupOutput', 'Output').inputs

    def n(self, kind, label='', **props):
        node = self.g.nodes.new(kind)
        node.label = label
        for key, value in props.items():
            setattr(node, key, value)
        return node

    def link(self, a, b):
        if a is not None:
            feed(self.g, a, b)

    # Scalar math -----------------------------------------------------------
    def m(self, op, a, b=0.0):
        node = self.n('ShaderNodeMath', op.title().replace('_', ' '), operation=op)
        self.link(a, node.inputs[0])
        self.link(b, node.inputs[1])
        return node.outputs[0]

    def add(self, a, b): return self.m('ADD', a, b)
    def sub(self, a, b): return self.m('SUBTRACT', a, b)
    def mul(self, a, b): return self.m('MULTIPLY', a, b)
    def div(self, a, b): return self.m('DIVIDE', a, b)
    def lo(self, a, b): return self.m('MINIMUM', a, b)
    def hi(self, a, b): return self.m('MAXIMUM', a, b)
    def clamp(self, a, low, high): return self.lo(self.hi(a, low), high)

    # Vectors ---------------------------------------------------------------
    def xz(self, x=0.0, z=0.0):
        """Profile coordinates: X is radius, Z is height (Blender is Z-up)."""
        node = self.n('ShaderNodeCombineXYZ', 'Radius, height')
        self.link(x, node.inputs['X'])
        self.link(z, node.inputs['Z'])
        return node.outputs[0]

    def xyz(self, x=0.0, y=0.0, z=0.0):
        node = self.n('ShaderNodeCombineXYZ', 'Combine')
        for value, target in zip((x, y, z), node.inputs):
            self.link(value, target)
        return node.outputs[0]

    def sep(self, vector):
        node = self.n('ShaderNodeSeparateXYZ', 'Separate')
        self.link(vector, node.inputs[0])
        return node.outputs['X'], node.outputs['Y'], node.outputs['Z']

    def v(self, op, a, b=None, scale=None):
        node = self.n('ShaderNodeVectorMath', op.title().replace('_', ' '), operation=op)
        self.link(a, node.inputs[0])
        if b is not None:
            self.link(b, node.inputs[1])
        if scale is not None:
            self.link(scale, node.inputs['Scale'])
        return node.outputs['Value'] if op in ('LENGTH', 'DOT_PRODUCT', 'DISTANCE') else node.outputs['Vector']

    # Fields and selection --------------------------------------------------
    @property
    def index(self):
        if self._index is None:
            self._index = self.n('GeometryNodeInputIndex', 'Index').outputs[0]
        return self._index

    def position(self):
        return self.n('GeometryNodeInputPosition', 'Position').outputs[0]

    def switch(self, kind, test, false, true):
        node = self.n('GeometryNodeSwitch', 'Switch', input_type=kind)
        self.link(test, node.inputs['Switch'])
        self.link(false, node.inputs['False'])
        self.link(true, node.inputs['True'])
        return node.outputs[0]

    def pick(self, index, values, kind='VECTOR'):
        node = self.n('GeometryNodeIndexSwitch', 'Point by index', data_type=kind)
        node.index_switch_items.clear()
        for _ in values:
            node.index_switch_items.new()
        self.link(index, node.inputs['Index'])
        for k, value in enumerate(values):
            self.link(value, node.inputs[k + 1])
        return node.outputs[0]

    def at(self, value, index, kind='FLOAT_VECTOR'):
        """Evaluate a field at another index (neighbor access)."""
        node = self.n('GeometryNodeFieldAtIndex', 'Evaluate at index', data_type=kind, domain='POINT')
        self.link(value, node.inputs['Value'])
        self.link(index, node.inputs['Index'])
        return node.outputs[0]

    def sample(self, geometry, value, index, kind='FLOAT_VECTOR'):
        node = self.n('GeometryNodeSampleIndex', 'Sample point', data_type=kind, domain='POINT')
        self.link(geometry, node.inputs['Geometry'])
        self.link(value, node.inputs['Value'])
        self.link(index, node.inputs['Index'])
        return node.outputs[0]

    def point_count(self, geometry):
        node = self.n('GeometryNodeAttributeDomainSize', 'Point count', component='CURVE')
        self.link(geometry, node.inputs[0])
        return node.outputs['Point Count']

    def stat(self, geometry, value, which):
        node = self.n('GeometryNodeAttributeStatistic', which, data_type='FLOAT', domain='POINT')
        self.link(geometry, node.inputs['Geometry'])
        self.link(value, node.inputs['Attribute'])
        return node.outputs[which]

    # Geometry --------------------------------------------------------------
    def set_position(self, geometry, position, selection=None):
        node = self.n('GeometryNodeSetPosition', 'Set position')
        self.link(geometry, node.inputs['Geometry'])
        self.link(selection, node.inputs['Selection'])
        self.link(position, node.inputs['Position'])
        return node.outputs[0]

    def store(self, geometry, name, value, kind='FLOAT', domain='POINT'):
        node = self.n('GeometryNodeStoreNamedAttribute', name, data_type=kind, domain=domain)
        node.inputs['Name'].default_value = name
        self.link(geometry, node.inputs['Geometry'])
        self.link(value, node.inputs['Value'])
        return node.outputs[0]

    def named(self, name, kind='FLOAT'):
        node = self.n('GeometryNodeInputNamedAttribute', name, data_type=kind)
        node.inputs['Name'].default_value = name
        return node.outputs['Attribute']

    def delete(self, geometry, selection, domain='POINT'):
        node = self.n('GeometryNodeDeleteGeometry', 'Delete', domain=domain)
        self.link(geometry, node.inputs['Geometry'])
        self.link(selection, node.inputs['Selection'])
        return node.outputs[0]

    def join(self, *geometries):
        node = self.n('GeometryNodeJoinGeometry', 'Join')
        for geometry in reversed(geometries):  # multi-input sockets stack newest first
            self.link(geometry, node.inputs[0])
        return node.outputs[0]

    def points(self, count, position):
        node = self.n('GeometryNodePoints', 'Points')
        self.link(count, node.inputs['Count'])
        self.link(position, node.inputs['Position'])
        return node.outputs[0]

    def curve_points(self, curve):
        node = self.n('GeometryNodeCurveToPoints', 'Curve to points', mode='EVALUATED')
        self.link(curve, node.inputs['Curve'])
        return node.outputs['Points']

    def chain(self, *parts):
        """Join point sets into ONE poly spline, ordered by their 'order' attribute."""
        node = self.n('GeometryNodePointsToCurves', 'One spline, in order')
        self.link(self.join(*parts), node.inputs['Points'])
        self.link(self.named('order'), node.inputs['Weight'])
        remove = self.n('GeometryNodeRemoveAttribute', 'Remove helper attribute')
        remove.inputs['Name'].default_value = 'order'
        self.link(node.outputs[0], remove.inputs['Geometry'])
        return remove.outputs[0]

    def ordered(self, geometry, base):
        return self.store(geometry, 'order', self.add(self.index, base))

    def group(self, tree, label=''):
        node = self.n('GeometryNodeGroup', label or tree.name)
        node.node_tree = tree
        return node

    # Seeded randomness (see docs/concepts/seeds-and-variation.md) -------------------
    def random(self, index, channel, seed):
        """A seeded value in [-1, 1] for thing `index` on independent stream `channel` (White Noise hash)."""
        node = self.n('ShaderNodeTexWhiteNoise', f'Random · channel {channel}', noise_dimensions='4D')
        self.link(self.xyz(index, channel, 0), node.inputs['Vector'])
        self.link(seed, node.inputs['W'])
        return self.sub(self.mul(node.outputs['Value'], 2), 1)

    def unit(self, index, channel, seed):
        """A seeded value in [0, 1]."""
        return self.mul(self.add(self.random(index, channel, seed), 1), .5)

    def chance(self, index, channel, seed, probability):
        """True (1) with the given probability, per thing, reproducibly."""
        return self.m('LESS_THAN', self.unit(index, channel, seed), probability)

    # Common geometry steps -------------------------------------------------------------
    def transform(self, geometry, translation=None, rotation=None, scale=None, label='Transform'):
        """Note: Transform scales BEFORE it rotates. To squash along a world axis after turning,
        use two transforms (see docs/blender-gotchas.md)."""
        node = self.n('GeometryNodeTransform', label)
        self.link(geometry, node.inputs['Geometry'])
        for value, name in ((translation, 'Translation'), (rotation, 'Rotation'), (scale, 'Scale')):
            if value is not None:
                self.link(value, node.inputs[name])
        return node.outputs[0]

    def instance(self, points, instance, *, rotation=None, scale=None, selection=None, label='Instance', realize=True):
        node = self.n('GeometryNodeInstanceOnPoints', label)
        self.link(points, node.inputs['Points'])
        self.link(instance, node.inputs['Instance'])
        for value, name in ((rotation, 'Rotation'), (scale, 'Scale'), (selection, 'Selection')):
            if value is not None:
                self.link(value, node.inputs[name])
        if not realize:
            return node.outputs[0]
        real = self.n('GeometryNodeRealizeInstances', f'{label} (real)')
        self.link(node.outputs[0], real.inputs['Geometry'])
        return real.outputs[0]

    def material(self, geometry, material, label='Material'):
        node = self.n('GeometryNodeSetMaterial', label)
        self.link(geometry, node.inputs['Geometry'])
        self.link(material, node.inputs['Material'])
        return node.outputs[0]

    def shade(self, mesh, smooth=False, label='Shading'):
        node = self.n('GeometryNodeSetShadeSmooth', label)
        self.link(mesh, node.inputs['Mesh'])
        self.link(smooth, node.inputs['Shade Smooth'])
        return node.outputs[0]

    # Menus -----------------------------------------------------------------------------
    def menu_index(self, menu_socket, options, label='Menu → index'):
        """A Menu input can drive only ONE Menu Switch. Turn it into an index here, then pick per
        option anywhere with `pick(index, values)` (an Index Switch)."""
        node = self.n('GeometryNodeMenuSwitch', label, data_type='INT')
        node.enum_items.clear()
        for k, name in enumerate(options):
            node.enum_items.new(name)
            node.inputs[name].default_value = k
        self.link(menu_socket, node.inputs['Menu'])
        return node.outputs[0]

    def menu(self, menu_socket, choices, kind='GEOMETRY', label='Menu'):
        """One Menu Switch choosing between `choices` = {option name: value}."""
        node = self.n('GeometryNodeMenuSwitch', label, data_type=kind)
        node.enum_items.clear()
        for name in choices:
            node.enum_items.new(name)
        self.link(menu_socket, node.inputs['Menu'])
        for name, value in choices.items():
            self.link(value, node.inputs[name])
        return node.outputs[0]

    # Interface finishing ---------------------------------------------------------------
    def socket_item(self, name):
        """The input socket called `name` (a panel can share a socket's name, so look up by type)."""
        return next(x for x in self.g.interface.items_tree
                    if x.item_type == 'SOCKET' and x.in_out == 'INPUT' and x.name == name)

    def defaults(self, values):
        """Set Menu input defaults: only possible after the menus are wired."""
        self.g.interface_update(bpy.context)
        for name, value in values.items():
            self.socket_item(name).default_value = value

    def panels(self, spec, closed=()):
        """Group inputs into collapsible panels: {'Panel': ['Input', ...]}."""
        for title, names in spec.items():
            panel = self.g.interface.new_panel(name=title, default_closed=title in closed)
            for name in names:
                self.g.interface.move_to_parent(self.socket_item(name), panel, 100)

    def layout(self):
        """Place nodes in columns by their distance from the group input."""
        nodes = list(self.g.nodes)
        incoming = {n: [l.from_node for l in self.g.links if l.to_node == n] for n in nodes}
        depth = {}

        def d(node, seen=()):
            if node in depth:
                return depth[node]
            if node in seen:
                return 0
            value = 1 + max((d(p, seen + (node,)) for p in incoming[node]), default=-1)
            depth[node] = value
            return value
        for node in nodes:
            d(node)
        out = [n for n in nodes if n.bl_idname == 'NodeGroupOutput']
        last = max(depth.values()) + 1
        for node in out:
            depth[node] = last
        rows = {}
        for node in nodes:
            col = depth[node]
            row = rows.get(col, 0)
            rows[col] = row + 1
            node.location = (col * 240, -row * 190)
            node.width = 180


def polyline(G, count, position):
    """A single POLY spline whose point positions are computed from their Index."""
    line = G.n('GeometryNodeMeshLine', 'Profile stations')
    G.link(count, line.inputs['Count'])
    placed = G.set_position(line.outputs[0], position)
    curve = G.n('GeometryNodeMeshToCurve', 'Stations to curve')
    G.link(placed, curve.inputs['Mesh'])
    return curve.outputs[0]
