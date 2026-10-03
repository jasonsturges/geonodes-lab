"""The floors family's graph writer: the shared Graph plus the names this family's formulas use."""
from authoring.graph import Graph


class FloorGraph(Graph):
    def math(self, op, a, b=0):
        return self.m(op, a, b)

    def join(self, *geometries):
        node = self.n('GeometryNodeJoinGeometry', 'Join retained elements')
        for geometry in geometries:
            self.link(geometry, node.inputs[0])
        return node.outputs[0]

    def attr(self, name, kind='FLOAT'):
        return self.named(name, kind)

    def stats(self, geometry, value, output, domain='POINT', selection=True):
        node = self.n('GeometryNodeAttributeStatistic', 'Measure ' + output, domain=domain)
        self.link(geometry, node.inputs['Geometry'])
        self.link(value, node.inputs['Attribute'])
        self.link(selection, node.inputs['Selection'])
        return node.outputs[output]

    def sample(self, geometry, value, index, kind='FLOAT'):
        return super().sample(geometry, value, index, kind=kind)

    def draw(self, seed, identity):
        """A seeded draw in [0, 1] for element `identity` (Random Value with Seed and ID)."""
        node = self.n('FunctionNodeRandomValue', 'Seeded independent draw', data_type='FLOAT')
        node.inputs['Min'].default_value = 0.
        node.inputs['Max'].default_value = 1.
        self.link(seed, node.inputs['Seed'])
        self.link(identity, node.inputs['ID'])
        return node.outputs['Value']

    def cube(self, size):
        node = self.n('GeometryNodeMeshCube', 'Board / room volume')
        self.link(size, node.inputs['Size'])
        return node.outputs['Mesh']
