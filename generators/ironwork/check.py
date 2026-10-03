"""Independent checks for assets/Ironwork.blend. Never imports build.py.

Appends from the saved asset file into a fresh session and repeats study 030's measurements:
member heights and flats, scroll section/volume/mirror, panel spacing (resolveFenceSpan),
fitted rings and decay.

Run: python3 scripts/check.py ironwork
"""
from pathlib import Path
import math
import bpy
import bmesh
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from authoring.modifiers import set_input  # noqa: E402
ASSET = ROOT / 'assets/Ironwork.blend'
P = 'GNL •'
BED = .003


def evaluate(group, settings):
    g = bpy.data.node_groups.new('check probe', 'GeometryNodeTree')
    g.is_modifier = True
    g.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    node = g.nodes.new('GeometryNodeGroup')
    node.node_tree = bpy.data.node_groups[f'{P} {group}']
    for key, value in settings.items():
        node.inputs[key].default_value = value
    g.links.new(node.outputs[0], g.nodes.new('NodeGroupOutput').inputs[0])
    obj = bpy.data.objects.new('check probe', bpy.data.meshes.new('check probe'))
    bpy.context.scene.collection.objects.link(obj)
    obj.modifiers.new('probe', 'NODES').node_group = g
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    closed = all(e.is_manifold for e in bm.edges)
    volume = bm.calc_volume(signed=True)
    parent = list(range(len(bm.verts)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for e in bm.edges:
        parent[find(e.verts[0].index)] = find(e.verts[1].index)
    parts = {}
    for v in bm.verts:
        parts.setdefault(find(v.index), []).append(tuple(v.co))
    bm.free()
    evaluated.to_mesh_clear()
    bpy.data.objects.remove(obj)
    bpy.data.node_groups.remove(g)
    return list(parts.values()), closed, volume


def span(part, axis):
    return min(p[axis] for p in part), max(p[axis] for p in part)


def resolve_fence_span(length, pitch, item_width):
    """three-low-poly resolveFenceSpan({ pitch, length, itemWidth })."""
    fits = max(1, math.floor(length / item_width)) if item_width > 0 else math.inf
    bars = min(max(1, round(length / pitch)), fits)
    return bars, length / bars


def check_members():
    cases = 0
    for sides, r, h, fh, fr, depth in [(8, .05, 2.0, .3, .075, 1.0), (4, .05, 2.0, .3, .09, .3), (6, .03, 1.2, .2, .06, 1.0)]:
        parts, closed, volume = evaluate('Picket', {'Sides': sides, 'Radius': r, 'Height': h, 'Finial Height': fh,
                                                    'Finial Radius': fr, 'Finial Depth': depth})
        bar = next(p for p in parts if abs(span(p, 2)[0]) < 1e-6 and abs(span(p, 2)[1] - h) < 1e-6)
        x0, x1 = span(bar, 0)
        assert abs(x1 - r * math.cos(math.pi / sides)) < 1e-6 and abs(x0 + x1) < 1e-6, ('flats face the run', x0, x1)
        top = max(q[2] for p in parts for q in p)
        assert closed and volume > 0 and abs(top - (h + fh)) < 1e-6, (sides, top)
        cases += 1
    full, _, _ = evaluate('Picket', {'Sides': 4, 'Finial Depth': 1.0})
    flat, _, _ = evaluate('Picket', {'Sides': 4, 'Finial Depth': .3})
    width = lambda parts: max(span(p, 1)[1] - span(p, 1)[0] for p in parts if span(p, 2)[0] > 1.9)
    assert abs(width(flat) - .3 * width(full)) < 1e-6, 'Finial Depth squashes the finial across the panel'
    for style, extra in (('Ball', .3 * .4 + .15), ('None', 0.0)):
        parts, closed, _ = evaluate('Picket', {'Finial': style})
        top = max(q[2] for p in parts for q in p)
        assert closed and abs(top - (2.0 + extra)) < 1e-6, (style, top)
    cases += 3
    for h, ball, settle in [(1.1, .1, .6), (2.3, .13, .6), (1.5, .2, -.2)]:
        parts, closed, _ = evaluate('Post', {'Height': h, 'Ball Radius': ball, 'Ball Settle': settle})
        top = max(q[2] for p in parts for q in p)
        assert closed and abs(top - (h + settle * ball + ball)) < 1e-6, (h, top)
        cases += 1
    for r0, turns, k, w, t, taper in [(1.4, 1.6, .22, .16, .05, .45), (.5, 1.5, .22, .07, .028, .45), (1, 1, 0, .1, .1, 1)]:
        s = {'Start Radius': r0, 'Turns': turns, 'Tightness': k, 'Bar Width': w, 'Bar Thickness': t, 'Taper': taper}
        parts, closed, volume = evaluate('Scroll', s)
        z0, z1 = span(parts[0], 2)
        assert closed and abs(z1 - t / 2) < 1e-6 and abs(z0 + t / 2) < 1e-6, ('section thickness', z0, z1)
        # Volume of a swept rectangle scaled by s(u) along the spiral (fine trapezoid sum).
        n, total = 4000, 0.0
        for j in range(n):
            u0, u1 = j / n, (j + 1) / n
            th0, th1 = u0 * turns * math.tau, u1 * turns * math.tau
            p0 = (r0 * math.exp(-k * th0) * math.cos(th0), r0 * math.exp(-k * th0) * math.sin(th0))
            p1 = (r0 * math.exp(-k * th1) * math.cos(th1), r0 * math.exp(-k * th1) * math.sin(th1))
            sc = 1 - (1 - taper) * (u0 + u1) / 2
            total += math.dist(p0, p1) * w * t * sc * sc
        assert abs(volume - total) < .03 * total, ('scroll volume', volume, total)
        mirrored, closed_m, volume_m = evaluate('Scroll', {**s, 'Flip': True})
        assert closed_m and abs(volume_m - volume) < 1e-6 * max(1, volume), 'mirror keeps outward normals'
        a = sorted((round(x, 5), round(-y, 5), round(z, 5)) for x, y, z in parts[0])
        b = sorted((round(x, 5), round(y, 5), round(z, 5)) for x, y, z in mirrored[0])
        assert a == b, 'Flip mirrors across X'
        cases += 1
    return cases


def check_panel():
    cases = 0
    for L, gap, r, sides, height in [(2.4, .3, .05, 4, 2.0), (3.0, .3, .05, 4, 2.0), (5.88, .3, .085, 4, 2.3),
                                     (1.0, .24, .03, 4, 1.0), (.3, .0, .2, 6, 1.0), (4.0, .5, .04, 8, 1.6)]:
        settings = {'Length': L, 'Gap': gap, 'Bar Radius': r, 'Sides': sides, 'Bar Height': height, 'Rings': True}
        parts, closed, volume = evaluate('Panel', settings)
        count, pitch = resolve_fence_span(L, 2 * r + gap, 2 * r)
        bars = [p for p in parts if abs(span(p, 2)[0]) < 1e-6 and abs(span(p, 2)[1] - height) < 1e-6]
        assert closed and len(bars) == count, (L, gap, r, len(bars), count)
        xs = sorted((span(b, 0)[0] + span(b, 0)[1]) / 2 for b in bars)
        assert all(abs(x - ((k + .5) * pitch - L / 2)) < 1e-6 for k, x in enumerate(xs)), (L, xs)
        rails = [p for p in parts if abs(span(p, 0)[1] - span(p, 0)[0] - L) < 1e-6]
        assert len(rails) == 3, ('foot, top and band rail', len(rails))
        rings = [p for p in parts if p not in bars and p not in rails and abs(span(p, 1)[1] - span(p, 1)[0]) > 0
                 and span(p, 2)[0] < height - .25 and span(p, 2)[0] > .25 and abs(span(p, 0)[1] - span(p, 0)[0]) < pitch]
        assert len(rings) == count - 1, ('one ring per opening', len(rings), count - 1)
        fitted = pitch / 2 - r * math.cos(math.pi / sides) + BED
        top_underside = height - .25 - .05
        for ring in rings:
            cx = (span(ring, 0)[0] + span(ring, 0)[1]) / 2
            cz = (span(ring, 2)[0] + span(ring, 2)[1]) / 2
            reach = max(math.hypot(p[0] - cx, p[2] - cz) for p in ring)
            assert abs(reach - fitted) < 1e-5, ('ring meets the picket flats, bedded', reach, fitted)
            assert abs(span(ring, 2)[1] - (top_underside + BED)) < 1e-5, 'ring top beds into the top rail'
        cases += 1
    # Decay: Missing 1 leaves only rails; the decay seed never moves rails; bent pickets lean their tips.
    parts, _, _ = evaluate('Panel', {'Missing Pickets': 1.0})
    assert len(parts) == 2, ('only the two rails remain', len(parts))
    a, _, _ = evaluate('Panel', {'Bent Pickets': 1.0, 'Decay Seed': 2})
    b, _, _ = evaluate('Panel', {'Bent Pickets': 1.0, 'Decay Seed': 3})
    rails_of = lambda parts: sorted(sorted(p) for p in parts if abs(span(p, 0)[1] - span(p, 0)[0] - 2.4) < 1e-6)
    assert rails_of(a) == rails_of(b) and a != b, 'decay seed changes pickets only'
    straight, _, _ = evaluate('Panel', {})
    tips = lambda parts: sorted(max(p, key=lambda q: q[2])[0] for p in parts if span(p, 2)[1] > 2.0)
    assert any(abs(x - y) > .05 for x, y in zip(tips(a), tips(straight))), 'bent tips move along the run'
    cases += 3
    return cases


# --- Ornament and ivy (measurements from studies 033 and 034) -----------------

def evaluate_flat(group, settings):
    g = bpy.data.node_groups.new('check probe', 'GeometryNodeTree')
    g.is_modifier = True
    g.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    node = g.nodes.new('GeometryNodeGroup')
    node.node_tree = bpy.data.node_groups[f'{P} {group}']
    for key, value in settings.items():
        node.inputs[key].default_value = value
    g.links.new(node.outputs[0], g.nodes.new('NodeGroupOutput').inputs[0])
    obj = bpy.data.objects.new('check probe', bpy.data.meshes.new('check probe'))
    bpy.context.scene.collection.objects.link(obj)
    obj.modifiers.new('probe', 'NODES').node_group = g
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    result = ([tuple(v.co) for v in bm.verts], all(e.is_manifold for e in bm.edges), bm.calc_volume(signed=True))
    parent = list(range(len(bm.verts)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for e in bm.edges:
        parent[find(e.verts[0].index)] = find(e.verts[1].index)
    islands = len({find(v.index) for v in bm.verts})
    bm.free()
    evaluated.to_mesh_clear()
    bpy.data.objects.remove(obj)
    bpy.data.node_groups.remove(g)
    return (*result, islands)


def symmetric(verts, mapping, tol=1e-4):
    return all(min(math.dist(mapping(p), q) for q in verts) < tol for p in verts)


def check_twists():
    cases = 0
    w, h, plain, pitch = .06, 1.2, .1, .16
    common = {'Height': h, 'Width': w, 'Plain Ends': plain, 'Twist Pitch': pitch, 'Detail': 401}
    verts, closed, volume, _ = evaluate_flat('Twisted Bar', {**common, 'Style': 'Square Twist'})
    assert closed and volume > 0 and abs(max(v[2] for v in verts) - h) < 1e-6
    # Stations every 0.0025 over the 1.0 twisted span: an eighth turn is 8 stations.
    def ring(z):
        return [v for v in verts if abs(v[2] - z) < 1e-6]
    for k, angle in ((0, 0), (1, math.pi / 4), (2, math.pi / 2), (8, 0)):
        z = plain + k * pitch / 8
        reach = max(abs(v[0]) for v in ring(z))
        corner = w / 2 * (abs(math.cos(angle)) + abs(math.sin(angle)))   # x-extent of a turned square
        assert abs(reach - corner) < 1e-5, ('square twist turns one turn per pitch', k, reach, corner)
    cases += 1
    for style, strands, bulge in (('Rope', 2, 1.0), ('Rope', 3, 1.0), ('Basket', 4, 2.0)):
        verts, closed, volume, islands = evaluate_flat('Twisted Bar', {**common, 'Style': style, 'Strands': strands,
                                                                  'Bulge': bulge})
        strand_r = w / (strands * 1.15)
        helix_r = w / 2 - strand_r
        widest = (helix_r * bulge if style == 'Basket' else helix_r) + strand_r
        twisted = [v for v in verts if plain + 1e-6 < v[2] < h - plain - 1e-6]
        reach = max(math.hypot(v[0], v[1]) for v in twisted)
        assert closed and islands == strands + 2, (style, strands, closed, islands)
        assert reach <= widest + 1e-5 and reach > widest * .97, (style, reach, widest)
        cases += 1
    return cases


def check_fleur():
    verts, closed, volume, islands = evaluate_flat('Fleur-de-lis', {'Height': .8, 'Width': .7, 'Thickness': .05})
    xs, ys, zs = zip(*verts)
    assert closed and volume > 0 and islands == 1
    assert abs(max(zs) - .8) < 1e-6 and abs(min(zs)) < 1e-6, 'stem at 0, tip at Height'
    assert abs((max(xs) - min(xs)) - .7 * .96) < 1e-6, 'widest at the side petals (0.48 × 2 of Width)'
    assert abs(max(ys) - .025) < 1e-6 and abs(min(ys) + .025) < 1e-6, 'thickness centered on Y'
    assert symmetric(verts, lambda p: (-p[0], p[1], p[2])), 'mirror symmetric'
    return 1


def check_scrolls():
    cases = 0
    for fit in (.2, .9, 1.7):
        s_verts, closed, volume, _ = evaluate_flat('Double Scroll', {'Style': 'S', 'Fit Width': fit})
        xs = [v[0] for v in s_verts]
        assert closed and volume > 0 and abs((max(xs) - min(xs)) - fit) < 1e-5, ('S width', fit)
        assert symmetric(s_verts, lambda p: (-p[0], -p[1], -p[2]), 1e-4 * max(1, fit)), 'S is point symmetric'
        c_verts, closed, volume, _ = evaluate_flat('Double Scroll', {'Style': 'C', 'Fit Width': fit})
        xs = [v[0] for v in c_verts]
        assert closed and volume > 0 and abs((max(xs) - min(xs)) - fit) < 1e-5, ('C width', fit)
        assert symmetric(c_verts, lambda p: (-p[0], p[1], p[2]), 1e-4 * max(1, fit)), 'C is mirror symmetric'
        m_verts, _, _, _ = evaluate_flat('Double Scroll', {'Style': 'C', 'Fit Width': fit, 'Mirror': True})
        assert sorted(round(v[2], 4) for v in m_verts) == sorted(round(-v[2], 4) for v in c_verts), \
            'Mirror flips the curls'
        cases += 1
    return cases


def check_rail():
    cases = 0
    for L, spacing, bw in ((2.0, .18, .016), (2.4, .22, .016), (1.0, .25, .02)):
        verts, closed, _, islands = evaluate_flat('Ornamental Rail', {'Length': L, 'Spacing': spacing, 'Bar Width': bw,
                                                                 'Collars': False, 'Scrolls': False})
        count = max(2, round(L / spacing) + 1)
        twisted = count // 2
        # Square pickets (1 island each) + rope pickets (2 strands + 2 plain ends) + 2 rails.
        assert islands == (count - twisted) + twisted * 4 + 2, (L, islands, count)
        with_scrolls = evaluate_flat('Ornamental Rail', {'Length': L, 'Spacing': spacing, 'Bar Width': bw,
                                                    'Collars': False})[3]
        # Each scroll is two forged spirals meeting at their open ends (as on the website): 2 pieces per gap.
        assert with_scrolls == islands + 2 * (count - 1), 'one S-scroll per gap'
        cases += 1
    return cases


def islands(group, settings, path=None):
    g = bpy.data.node_groups.new('check probe', 'GeometryNodeTree')
    g.is_modifier = True
    g.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    node = g.nodes.new('GeometryNodeGroup')
    node.node_tree = bpy.data.node_groups[f'{P} {group}']
    for key, value in settings.items():
        node.inputs[key].default_value = value
    if path is not None:
        info = g.nodes.new('GeometryNodeObjectInfo')
        info.inputs['Object'].default_value = path
        g.links.new(info.outputs['Geometry'], node.inputs['Path'])
    g.links.new(node.outputs[0], g.nodes.new('NodeGroupOutput').inputs[0])
    obj = bpy.data.objects.new('check probe', bpy.data.meshes.new('check probe'))
    bpy.context.scene.collection.objects.link(obj)
    obj.modifiers.new('probe', 'NODES').node_group = g
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    closed = all(e.is_manifold for e in bm.edges)
    volume = bm.calc_volume(signed=True)
    parent = list(range(len(bm.verts)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for e in bm.edges:
        parent[find(e.verts[0].index)] = find(e.verts[1].index)
    parts = {}
    for v in bm.verts:
        parts.setdefault(find(v.index), []).append(tuple(v.co))
    bm.free()
    evaluated.to_mesh_clear()
    bpy.data.objects.remove(obj)
    bpy.data.node_groups.remove(g)
    return list(parts.values()), closed, volume


def poly(points):
    data = bpy.data.curves.new('check vine', 'CURVE')
    data.dimensions = '3D'
    spline = data.splines.new('POLY')
    spline.points.add(len(points) - 1)
    for p, co in zip(spline.points, points):
        p.co = (*co, 1)
    obj = bpy.data.objects.new('check vine', data)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def check_ivy():
    cases = 0
    # The leaf: closed, mirror symmetric, Size from stalk to tip (angular outline is exact).
    for angular in (True, False):
        parts, closed, volume = islands('Ivy Leaf', {'Size': .2, 'Angular': angular, 'Cup': 0.0})
        verts = parts[0]
        assert len(parts) == 1 and closed and volume > 0
        assert abs(max(v[2] for v in verts) - .2) < 1e-5, 'tip at Size'
        assert all(min(math.dist((-x, y, z), q) for q in verts) < 1e-5 for x, y, z in verts), 'symmetric'
        if angular:
            assert abs(max(v[0] for v in verts) - .47 * .2) < 1e-6, 'widest at the side lobes'
        cases += 1
    # A straight vine along X: count, alternation, angle, taper.
    L, spacing, angle = 2.0, .2, math.radians(50)
    straight = poly([(-1, 0, 0), (1, 0, 0)])
    settings = {'Leaf Spacing': spacing, 'Leaf Angle': angle, 'Tendril Chance': 0.0, 'Size Jitter': 0.0,
                'Leaf Taper': 0.0, 'Cup': 0.0, 'Leaf Size': .1, 'Stem Radius': .02, 'Tip Scale': .4}
    parts, closed, _ = islands('Ivy Iron', settings, straight)
    stem = max(parts, key=lambda p: max(q[0] for q in p) - min(q[0] for q in p))
    leaves = [p for p in parts if p is not stem]
    expected = math.floor(L / spacing + 1e-6) + 1
    assert closed and len(leaves) == expected, (len(leaves), expected)
    leaves.sort(key=lambda p: min(q[0] for q in p))
    sides = []
    for k, p in enumerate(leaves):
        # The stalk sits on the station (−1 + k·spacing, 0, 0); the tip is the leaf's farthest point.
        stalk = (-1 + k * spacing, 0.0, 0.0)
        flat = lambda q: math.hypot(q[0] - stalk[0], q[2])           # in the ornament's XZ plane
        tip = max(p, key=flat)
        sides.append(1 if tip[2] > 0 else -1)
        measured = math.atan2(abs(tip[2]), abs(tip[0] - stalk[0]))
        assert abs(flat(tip) - .1) < 1e-4, ('tip at Leaf Size from the stalk', flat(tip))
        assert abs(measured - angle) < 1e-3, ('leaf angle', math.degrees(measured))
    assert all(a != b for a, b in zip(sides, sides[1:])), 'leaves alternate sides'
    cases += 2
    root = [math.hypot(q[1], q[2]) for q in stem if abs(q[0] + 1) < 1e-4]
    tip = [math.hypot(q[1], q[2]) for q in stem if abs(q[0] - 1) < 1e-4]
    assert abs(max(root) - .02) < 1e-5 and abs(max(tip) - .02 * .4) < 1e-5, ('taper', max(root), max(tip))
    cases += 1
    parts, _, _ = islands('Ivy Iron', {**settings, 'Tendril Chance': 1.0}, straight)
    assert len(parts) == 1 + 2 * expected, 'a curl at every station'
    cases += 1
    # Climbing a post: with Climb on, leaves lie outside the helix (facing out); off, some cut inside.
    r = .07
    helix = poly([(r * math.cos(t * 3 * math.tau), r * math.sin(t * 3 * math.tau), t * 1.5) for t in
                  [k / 150 for k in range(151)]])
    climb = {'Leaf Spacing': .1, 'Leaf Size': .07, 'Stem Radius': .008, 'Tendril Chance': 0.0, 'Cup': 0.0}
    on, _, _ = islands('Ivy Iron', {**climb, 'Climb': True}, helix)
    off, _, _ = islands('Ivy Iron', {**climb, 'Climb': False}, helix)
    def inner(parts):
        stem = max(parts, key=len)
        return min(math.hypot(q[0], q[1]) for p in parts if p is not stem for q in p)
    # Climb: every leaf lies tangent outside the helix (within its own thickness). Off: some cut inside.
    assert inner(on) > r * .95 and inner(off) < r * .9, ('climb faces out', inner(on), inner(off))
    cases += 1
    a, b, c = (islands('Ivy Iron', {'Seed': s})[0] for s in (4, 4, 5))
    assert a == b and a != c, 'seeds'
    cases += 1
    return cases


# --- Overthrow (measurements from study 035) -------------------------------------

OVERTHROW = 'GNL • Overthrow'
BARE = {'Infill': 'None', 'Centre': 'None', 'Crown': 'None', 'Ivy': False}


def evaluate_arch(settings):
    obj = bpy.data.objects.new('check arch', bpy.data.meshes.new('check arch'))
    bpy.context.scene.collection.objects.link(obj)
    mod = obj.modifiers.new('arch', 'NODES')
    mod.node_group = bpy.data.node_groups[OVERTHROW]
    for key, value in settings.items():
        set_input(mod, key, value)
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    verts = [tuple(v.co) for v in bm.verts]
    parent = list(range(len(bm.verts)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for e in bm.edges:
        parent[find(e.verts[0].index)] = find(e.verts[1].index)
    pieces = len({find(v.index) for v in bm.verts})
    bm.free()
    evaluated.to_mesh_clear()
    bpy.data.objects.remove(obj)
    return verts, pieces


def check_overthrow():
    cases = 0
    # Bare arch: three shapes, measured span, crown and legs.
    bar = .05
    for shape, span, rise, leg in [('Semicircle', 3.0, 0, .2), ('Semicircle', 5.0, 0, .3),
                                   ('Elliptical', 3.0, .9, .2), ('Pointed', 3.0, 2.0, .2), ('Pointed', 2.0, 1.0, 0.0)]:
        s = {**BARE, 'Shape': shape, 'Span': span, 'Rise': rise or 1.0, 'Leg Height': leg, 'Arch Bar': bar}
        verts, pieces = evaluate_arch(s)
        crown = span / 2 if shape == 'Semicircle' else rise
        xs, zs = [v[0] for v in verts], [v[2] for v in verts]
        assert abs((max(xs) - min(xs)) - (span + 2 * bar)) < 1e-4, (shape, span, max(xs) - min(xs))
        assert abs(max(zs) - (crown + bar)) < 2e-3, (shape, max(zs), crown + bar)   # sampled crown, 96 stations
        if leg > 0:
            assert abs(min(zs) + leg) < 1e-4, ('legs reach Leg Height below the springing', shape, min(zs))
        else:   # no legs: the lowest point is the underside of the hexagonal tie bar
            assert abs(min(zs) + .032 * math.cos(math.pi / 6)) < 1e-4, (shape, min(zs))
        assert pieces == 3, ('arch, tie and inner arc', pieces)
        cases += 1
    # Pointed: the two arcs meet in a point at the crown (an apex vertex sits on the centre line).
    verts, _ = evaluate_arch({**BARE, 'Shape': 'Pointed', 'Rise': 2.0, 'Arch Bar': .001})
    top = max(verts, key=lambda v: v[2])
    assert abs(top[0]) < 2e-3 and abs(top[2] - 2.001) < 2e-3, top
    cases += 1
    # Infill options, counted as forged pieces on top of the bare 3.
    for n in (5, 9, 12):
        spokes = evaluate_arch({**BARE, 'Infill': 'Spokes', 'Spokes': n})[1] - 3
        volutes = evaluate_arch({**BARE, 'Infill': 'Spokes and Volutes', 'Spokes': n})[1] - 3 - n
        gaps = evaluate_arch({**BARE, 'Infill': 'Gap Scrolls', 'Spokes': n})[1] - 3 - n
        centre = 1 if n % 2 else 0   # an odd count has a spoke on the centre line: no volute there
        assert spokes == n and volutes == n - centre and gaps == 2 * (n - 1), (n, spokes, volutes, gaps)
        cases += 1
    # Decay: every spoke gone takes its volute with it.
    assert evaluate_arch({**BARE, 'Infill': 'Spokes and Volutes', 'Missing Spokes': 1.0})[1] == 3
    partial = evaluate_arch({**BARE, 'Infill': 'Spokes', 'Missing Spokes': .5, 'Decay Seed': 2})[1] - 3
    assert 0 < partial < 9
    cases += 1
    # Crowns: ball and spike top = apex + bar + k(0.17 + 0.42), k = span / 5 (website sizes).
    for span in (3.0, 5.0):
        verts, _ = evaluate_arch({**BARE, 'Crown': 'Ball and Spike', 'Span': span})
        k = span / 5
        assert abs(max(v[2] for v in verts) - (span / 2 + .05 + k * .59)) < 1e-4, span
        verts, _ = evaluate_arch({**BARE, 'Crown': 'Fleur-de-lis', 'Span': span})
        assert abs(max(v[2] for v in verts) - (span / 2 + .05 - .025 + k * .7)) < 1e-4, span
        cases += 1
    # Centre and ivy add ornament without disturbing the bare arch.
    bare, _ = evaluate_arch(BARE)
    for extra in ({'Centre': 'Medallion'}, {'Ivy': True}):
        verts, pieces = evaluate_arch({**BARE, **extra})
        assert pieces > 3 and set(map(tuple, bare)) <= set(map(tuple, verts)), extra
        cases += 1
    return cases


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mine = bpy.data.objects.new('My object', bpy.data.meshes.new('mine'))
    bpy.context.scene.collection.objects.link(mine)
    names = [f'{P} {n}' for n in ('Picket', 'Post', 'Scroll', 'Panel', 'Twisted Bar', 'Fleur-de-lis',
                                  'Double Scroll', 'Ornamental Rail', 'Ivy Iron', 'Overthrow')]
    with bpy.data.libraries.load(str(ASSET), link=False, assets_only=True) as (src, dst):
        assert sorted(src.objects) == sorted(names), src.objects
        assert set(names) <= set(src.node_groups), src.node_groups
        extra = [f'{P} {n}' for n in ('Collar', 'Ivy Leaf', 'Tendril')]
        assert set(extra) <= set(src.node_groups), src.node_groups
        assert len(src.materials) == 2, src.materials
        dst.objects = list(names)
        dst.node_groups = list(names) + list(extra)
    for obj in dst.objects:
        bpy.context.scene.collection.objects.link(obj)
    assert bpy.data.objects.get(mine.name) is mine and not bpy.data.texts
    cases = 1
    for obj in dst.objects:
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        assert len(mesh.polygons) > 0 and any(mesh.materials), obj.name
        evaluated.to_mesh_clear()
        cases += 1
    panel = bpy.data.node_groups[f'{P} Panel']
    titles = [x.name for x in panel.interface.items_tree if x.item_type == 'PANEL']
    assert titles == ['Run', 'Pickets', 'Rails', 'Rings', 'Decay'], titles
    cases += check_members() + check_panel() + 1
    cases += check_twists() + check_fleur() + check_scrolls() + check_rail() + check_ivy() + check_overthrow()
    print(f'Ironwork: {cases} cases passed')


main()
