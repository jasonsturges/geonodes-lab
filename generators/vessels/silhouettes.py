"""Vessel silhouettes: the outer wall, base to rim, as one curve in the XZ plane (X = radius).

One node group per three-low-poly `vesselProfiles.ts` function. Parameter names and defaults follow
the SDK; SDK defaults derived from other values (baseRadius = 0.7 × radius) become factor inputs.
"""
import math

from authoring.graph import Graph, polyline
from authoring.naming import named


SILHOUETTES = {}


def silhouette(name, sockets):
    def register(fn):
        SILHOUETTES[name] = (sockets, fn)
        return fn
    return register


@silhouette('Florence Flask', [
    ('Body Radius', 1.0, 0.2, 5.0, 'Bulb (sphere) radius.'),
    ('Neck Radius', 0.2, 0.01, 2.0, 'Straight neck radius. Meets the bulb tangentially.'),
    ('Neck Height', 1.5, 0.01, 5.0, 'Neck length above the bulb shoulder.'),
    ('Profile Segments', 32, 3, 128, 'Arc stations over the bulb.')])
def florence(G, i):
    R, nr, nh, seg = i['Body Radius'], i['Neck Radius'], i['Neck Height'], i['Profile Segments']
    top = G.m('ARCSINE', G.clamp(G.div(nr, R), 0, 1))
    k = G.div(G.lo(G.index, seg), seg)
    theta = G.sub(math.pi, G.mul(G.sub(math.pi, top), k))
    arc = G.xz(G.mul(R, G.m('SINE', theta)), G.add(G.mul(R, G.m('COSINE', theta)), R))
    shoulder = G.add(G.mul(R, G.m('COSINE', top)), R)
    neck = G.xz(nr, G.add(shoulder, nh))
    return G.add(seg, 2), G.switch('VECTOR', G.m('GREATER_THAN', G.index, seg), arc, neck)


@silhouette('Erlenmeyer Flask', [
    ('Body Radius', 1.0, 0.2, 5.0, 'Base radius, the widest point.'),
    ('Neck Radius', 0.3, 0.01, 2.0, 'Neck radius.'),
    ('Body Height', 2.5, 0.2, 8.0, 'Conical body height, before the neck.'),
    ('Neck Height', 1.0, 0.01, 5.0, 'Straight neck height.')])
def erlenmeyer(G, i):
    R, nr, bh, nh = i['Body Radius'], i['Neck Radius'], i['Body Height'], i['Neck Height']
    pts = [G.xz(0, 0), G.xz(G.mul(R, .875), 0), G.xz(R, G.mul(bh, .04)), G.xz(nr, bh), G.xz(nr, G.add(bh, nh))]
    return len(pts), G.pick(G.index, pts)


@silhouette('Test Tube', [
    ('Radius', 0.2, 0.01, 2.0, 'Tube radius.'),
    ('Height', 3.0, 0.1, 10.0, 'Overall height, rounded bottom to rim. Keep above Radius.'),
    ('Profile Segments', 16, 3, 64, 'Arc stations over the hemispherical bottom.')])
def test_tube(G, i):
    r, h, seg = i['Radius'], i['Height'], i['Profile Segments']
    k = G.div(G.lo(G.index, seg), seg)
    theta = G.sub(math.pi, G.mul(math.pi / 2, k))
    arc = G.xz(G.mul(r, G.m('SINE', theta)), G.add(G.mul(r, G.m('COSINE', theta)), r))
    return G.add(seg, 2), G.switch('VECTOR', G.m('GREATER_THAN', G.index, seg), arc, G.xz(r, h))


@silhouette('Graduated Cylinder', [
    ('Radius', 0.35, 0.02, 2.0, 'Bore radius.'),
    ('Height', 3.0, 0.2, 10.0, 'Overall height.'),
    ('Foot Radius Factor', 1.5, 1.0, 4.0, 'Base-foot radius as a multiple of Radius (SDK default 1.5).'),
    ('Foot Height Factor', 0.08, 0.01, 0.4, 'Foot height as a fraction of Height (SDK default 0.08).')])
def graduated(G, i):
    r, h = i['Radius'], i['Height']
    fr, fh = G.mul(r, i['Foot Radius Factor']), G.mul(h, i['Foot Height Factor'])
    pts = [G.xz(0, 0), G.xz(fr, 0), G.xz(fr, G.mul(fh, .5)), G.xz(r, fh), G.xz(r, h)]
    return len(pts), G.pick(G.index, pts)


@silhouette('Pipette', [
    ('Radius', 0.1, 0.01, 1.0, 'Tube radius.'),
    ('Height', 3.0, 0.2, 10.0, 'Overall height.'),
    ('Tip Length Factor', 0.22, 0.02, 0.8, 'Cone tip length as a fraction of Height (SDK default 0.22).')])
def pipette(G, i):
    r, h = i['Radius'], i['Height']
    pts = [G.xz(0, 0), G.xz(r, G.mul(h, i['Tip Length Factor'])), G.xz(r, h)]
    return len(pts), G.pick(G.index, pts)


@silhouette('Apothecary Jar', [
    ('Radius', 1.5, 0.2, 5.0, 'Widest body radius.'),
    ('Base Radius Factor', 0.8, 0.1, 1.2, 'Foot radius as a multiple of Radius (SDK default 0.8).'),
    ('Neck Radius Factor', 0.4, 0.05, 1.0, 'Mouth radius as a multiple of Radius (SDK default 0.4).'),
    ('Height', 3.5, 0.3, 10.0, 'Overall height.')])
def apothecary(G, i):
    R, h = i['Radius'], i['Height']
    br, nr = G.mul(R, i['Base Radius Factor']), G.mul(R, i['Neck Radius Factor'])
    pts = [G.xz(0, 0), G.xz(br, 0), G.xz(G.mul(R, .98), G.mul(h, .25)), G.xz(R, G.mul(h, .5)),
           G.xz(G.mul(R, .74), G.mul(h, .78)), G.xz(nr, h)]
    return len(pts), G.pick(G.index, pts)


@silhouette('Potion Bottle', [
    ('Radius', 1.0, 0.2, 5.0, 'Widest (belly) radius.'),
    ('Base Radius Factor', 0.7, 0.1, 1.2, 'Foot radius as a multiple of Radius (SDK default 0.7).'),
    ('Neck Radius Factor', 0.4, 0.05, 1.0, 'Neck radius as a multiple of Radius (SDK default 0.4).'),
    ('Height', 2.6, 0.3, 10.0, 'Overall height.')])
def potion(G, i):
    R, h = i['Radius'], i['Height']
    br, nr = G.mul(R, i['Base Radius Factor']), G.mul(R, i['Neck Radius Factor'])
    pts = [G.xz(0, 0), G.xz(br, 0), G.xz(R, G.mul(h, .45)), G.xz(G.mul(R, .7), G.mul(h, .64)),
           G.xz(nr, G.mul(h, .8)), G.xz(nr, h)]
    return len(pts), G.pick(G.index, pts)


@silhouette('Wine Bottle', [
    ('Radius', 0.5, 0.1, 3.0, 'Body radius.'),
    ('Neck Radius', 0.18, 0.02, 1.0, 'Neck (mouth) radius.'),
    ('Height', 3.0, 0.5, 10.0, 'Overall height.'),
    ('Neck Height', 0.9, 0.05, 5.0, 'Straight neck height.'),
    ('Shoulder Height', 0.5, 0.01, 3.0, 'Height of the body-to-neck shoulder curve.'),
    ('Shoulder Segments', 6, 1, 32, '1 is a hard straight shoulder; more rounds it.')])
def wine(G, i):
    R, nr, h = i['Radius'], i['Neck Radius'], i['Height']
    nh, sh, seg = i['Neck Height'], i['Shoulder Height'], i['Shoulder Segments']
    body_top = G.hi(0, G.sub(G.sub(h, nh), sh))
    a = G.mul(G.div(G.sub(G.index, 2), seg), math.pi / 2)
    arc = G.xz(G.add(nr, G.mul(G.sub(R, nr), G.m('COSINE', a))), G.add(body_top, G.mul(sh, G.m('SINE', a))))
    head = G.pick(G.lo(G.index, 1), [G.xz(0, 0), G.xz(R, 0)])
    tail = G.xz(nr, h)
    body = G.switch('VECTOR', G.m('GREATER_THAN', G.index, G.add(seg, 2)), arc, tail)
    return G.add(seg, 4), G.switch('VECTOR', G.m('LESS_THAN', G.index, 2), body, head)


def silhouette_group(name):
    sockets, fn = SILHOUETTES[name]
    G = Graph(named(f'Silhouette • {name}'))
    for label, default, low, high, text in sockets:
        kind = 'NodeSocketInt' if isinstance(default, int) else 'NodeSocketFloat'
        G.input(label, kind, default, low, high, text)
    G.output('Silhouette')
    G.finish_io()
    count, position = fn(G, G.i)
    G.link(polyline(G, count, position), G.o['Silhouette'])
    G.layout()
    G.g.description = f'Outer wall of a {name.lower()}, base to rim, as a curve in the XZ plane (X = radius).'
    return G.g
