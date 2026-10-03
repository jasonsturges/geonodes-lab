"""GNL • Corner / Surface Molding Profile: named cross-sections as closed curves in XY (height X,
projection Y), scaled to Height and Projection. Reusable on their own (e.g. as a sweep profile)."""
import math

from authoring.naming import named
from authoring.nodes import socket
from graph import MoldingGraph as Graph, F, value, CORNER, SURFACE


def profile_group(surface=False):
    styles = SURFACE if surface else CORNER
    title = 'Surface' if surface else 'Corner'
    h = Graph(named(title + ' Molding Profile'))
    g = h.g
    m = h.m
    socket(g, 'Profile', 'NodeSocketMenu')
    socket(g, 'Height', 'NodeSocketFloat', .07 if surface else .09, .02, .3)
    socket(g, 'Projection', 'NodeSocketFloat', .028 if surface else .065, .005, .2)
    socket(g, 'Segments', 'NodeSocketInt', 6, 1, 16)
    if surface:
        socket(g, 'Reeds', 'NodeSocketInt', 4, 2, 8)
        socket(g, 'Reed Backing', 'NodeSocketFloat', .1, .02, .4, description='Fraction of projection retained behind the reeds.')
    socket(g, 'Profile', 'NodeSocketGeometry', direction='OUTPUT')
    o = h.n('NodeGroupInput', 'Named profile parameters').outputs
    n = F(h, o['Segments'])
    half = (n / 2).op('ROUND', 0).op('MAXIMUM', 1)
    index = F(h, h.n('GeometryNodeInputIndex', 'Local profile sample').outputs[0])
    choose = h.n('GeometryNodeMenuSwitch', 'Named section')
    choose.data_type = 'GEOMETRY'
    choose.enum_items.clear()
    for style in styles:
        choose.enum_items.new(style)
    h.link(o['Profile'], choose.inputs['Menu'])
    for style in styles:
        pieces = []

        def curve(steps, fn, enabled=None):
            count = steps + 1
            t = index / steps
            x, y = fn(t)
            line = h.n('GeometryNodeMeshLine', style + ' samples')
            h.link(value(count), line.inputs['Count'])
            place = h.n('GeometryNodeSetPosition', style + ' section')
            h.link(line.outputs[0], place.inputs[0])
            h.link(h.xyz(value(x), value(y), 0), place.inputs['Position'])
            geo = place.outputs[0]
            if enabled is not None:
                geo = h.switch('GEOMETRY', enabled, None, geo)
            pieces.append(geo)

        def line(a, b): curve(1, lambda t: (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        def q(t): return t * (math.pi / 2)
        if not surface:
            line((0, 0), (1, 0))
            if style == 'Chamfer':
                line((1, 0), (0, 1))
            elif style == 'Fillet':
                line((1, 0), (1, 1))
                line((1, 1), (0, 1))
            elif style == 'Step':
                for a, b in [((1, 0), (1, .45)), ((1, .45), (.45, .45)), ((.45, .45), (.45, 1)), ((.45, 1), (0, 1))]:
                    line(a, b)
            elif style == 'Cove':
                curve(n, lambda t: (1 - q(t).sin(), 1 - q(t).cos()))
            elif style == 'Ovolo':
                curve(n, lambda t: (q(t).cos(), q(t).sin()))
            elif style == 'Ogee':
                curve(half, lambda t: (.5 + .5 * q(t).cos(), .5 * q(t).sin()))
                curve(half, lambda t: (.5 - .5 * q(t).sin(), 1 - .5 * q(t).cos()))
            elif style == 'Cyma':
                curve(half, lambda t: (1 - .5 * q(t).sin(), .5 * (1 - q(t).cos())))
                curve(half, lambda t: (.5 * q(t).cos(), .5 + .5 * q(t).sin()))
            elif style == 'Scotia':
                curve(n, lambda t: ((1 - t) * (1 - t) * (1 - t) + .45 * (1 - t) * (1 - t) * t, 1.95 * (1 - t) * t * t + t * t * t))
            line((0, 1), (0, 0))
        else:
            line((0, 0), (1, 0))
            if style == 'Fillet':
                line((1, 0), (1, 1))
                line((1, 1), (0, 1))
                line((0, 1), (0, 0))
            elif style == 'Bead':
                curve(n * 2, lambda t: (.5 + .5 * (t * math.pi).cos(), (t * math.pi).sin()))
            elif style == 'Astragal':
                line((1, 0), (1, .3))
                line((1, .3), (.82, .3))
                curve(n * 2, lambda t: (.5 + .32 * (t * math.pi).cos(), .3 + .7 * (t * math.pi).sin()))
                line((.18, .3), (0, .3))
                line((0, .3), (0, 0))
            elif style == 'Reed':
                reeds = F(h, o['Reeds'])
                back = F(h, o['Reed Backing'])
                line((1, 0), (1, back))
                for j in range(8):
                    curve(n * 2, lambda t, j=j: (1 - (F(h, j) + .5) / reeds + (F(h, .5) / reeds) * (t * math.pi).cos(), back + (1 - back) * (t * math.pi).sin()), m('LESS_THAN', j, o['Reeds']))
                line((0, back), (0, 0))
            elif style == 'Ovolo':
                line((1, 0), (1, 1))
                curve(n, lambda t: (1 - q(t).sin(), q(t).cos()))
            elif style == 'Ogee':
                line((1, 0), (1, 1))
                curve(half, lambda t: (.5 + .5 * q(t).cos(), 1 - .5 * q(t).sin()))
                curve(half, lambda t: (.5 - .5 * q(t).sin(), .5 * q(t).cos()))
            elif style == 'Lip':
                line((1, 0), (1, .45))
                curve(n, lambda t: (.72 + .28 * q(t).cos(), .45 + .55 * q(t).sin()))
                line((.72, 1), (.5, .28))
                curve(n, lambda t: (.5 * (1 - q(t).sin()), .28 * q(t).cos()))
        joined = h.join(*pieces)
        merge = h.n('GeometryNodeMergeByDistance', 'Join profile endpoints')
        merge.inputs['Distance'].default_value = 1e-6
        h.link(joined, merge.inputs[0])
        tocurve = h.n('GeometryNodeMeshToCurve', style + ' closed outline')
        h.link(merge.outputs[0], tocurve.inputs[0])
        h.link(tocurve.outputs[0], choose.inputs[style])
    result = h.transform(choose.outputs[0], scale=h.xyz(o['Height'], o['Projection'], 1))
    out = h.n('NodeGroupOutput', 'Reusable cross-section XY')
    h.link(result, out.inputs[0])
    next(s for s in g.interface.items_tree if s.name == 'Profile' and s.in_out == 'INPUT').default_value = 'Astragal' if surface else 'Ogee'
    h.layout()
    return g
