"""The windows family's graph writer: the shared Graph plus the named arch-style menu.

Every opening input set shares one menu (Arch Style). A Menu input can drive only ONE Menu Switch,
so `menu()` turns it into an index once and answers each style-specific value with an Index Switch.
"""
import bpy

from authoring.graph import Graph
from authoring.nodes import socket

# three-low-poly ArchProfile.ts styles, in its order.
STYLES = ['Square', 'Semicircle', 'Segmental', 'Horseshoe', 'Elliptical', 'Pointed', 'Ogee']


class WindowGraph(Graph):
    def menu(self, kind, style, values):
        """One value per arch style (in STYLES order), chosen by the Arch Style menu."""
        if not hasattr(self, 'style_index'):
            self.style_index = self.menu_index(style, STYLES, label='Named arch style')
        return self.pick(self.style_index, values, kind=kind)

    def store(self, geometry, name, value, kind='FLOAT', domain='FACE'):
        return super().store(geometry, name, value, kind=kind, domain=domain)

    def stats(self, geometry, value, output):
        node = self.n('GeometryNodeAttributeStatistic', output)
        self.link(geometry, node.inputs['Geometry'])
        self.link(value, node.inputs['Attribute'])
        return node.outputs[output]

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


def opening_inputs(g):
    """The five inputs every opening-based group shares: one named opening definition."""
    socket(g, 'Arch Style', 'NodeSocketMenu', description='three-low-poly ArchProfile style.')
    for name, default, lo, hi, text in [
            ('Width', 1.2, .4, 3., 'Clear width between the jambs.'),
            ('Springing Height', 1.4, .3, 3., 'Sill to where the arch begins.'),
            ('Rise', .6, .1, 2., 'Crown height above the springing (styles that use it).')]:
        socket(g, name, 'NodeSocketFloat', default, lo, hi, description=text)
    socket(g, 'Arch Segments', 'NodeSocketInt', 24, 4, 64, description='Intervals per half arch. The crown is always kept.')
