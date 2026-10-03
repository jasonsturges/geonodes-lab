"""The molding family's graph writer: the shared Graph with this family's join order, welding and
face-domain attribute default, and `F`, a tiny expression wrapper so profile formulas read like math."""
from authoring.graph import Graph

# Named sections. Corner: three-low-poly MoldingProfiles.ts styles. Surface: wall-mounted sections.
CORNER = ['Cove', 'Ovolo', 'Chamfer', 'Ogee', 'Cyma', 'Scotia', 'Fillet', 'Step']
SURFACE = ['Fillet', 'Bead', 'Astragal', 'Reed', 'Ovolo', 'Ogee', 'Lip']


class MoldingGraph(Graph):
    def store(self, geometry, name, value, kind='FLOAT', domain='FACE'):
        return super().store(geometry, name, value, kind=kind, domain=domain)

    def join(self, *geometries):
        node = self.n('GeometryNodeJoinGeometry', 'Join geometry')
        for geometry in geometries:
            self.link(geometry, node.inputs[0])
        return node.outputs[0]

    def weld(self, geometry):
        node = self.n('GeometryNodeMergeByDistance', 'Clean coincident corners')
        node.inputs['Distance'].default_value = 1e-6
        self.link(geometry, node.inputs[0])
        return node.outputs[0]


class F:
    def __init__(self, h, v): self.h = h; self.v = v
    def op(self, op, b): return F(self.h, self.h.m(op, self.v, b.v if isinstance(b, F) else b))
    def __add__(self, b): return self.op('ADD', b)
    __radd__ = __add__
    def __sub__(self, b): return self.op('SUBTRACT', b)
    def __rsub__(self, b): return F(self.h, b) - self
    def __mul__(self, b): return self.op('MULTIPLY', b)
    __rmul__ = __mul__
    def __truediv__(self, b): return self.op('DIVIDE', b)
    def sin(self): return self.op('SINE', 0)
    def cos(self): return self.op('COSINE', 0)


def value(a): return a.v if isinstance(a, F) else a
