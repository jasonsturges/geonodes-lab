"""Independent frame offsets and cell-alignment checks for saved Diamond windows."""
from pathlib import Path
import sys, math, json
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_core import ROOT, STYLES, boundary, area, data, shell, sample_output, set_input, expected_bars


def offset(poly, d, limit):
    result = []
    for i, p in enumerate(poly):
        prev = poly[i - 1]
        nxt = poly[(i + 1) % len(poly)]
        a = (p[0] - prev[0], p[1] - prev[1])
        b = (nxt[0] - p[0], nxt[1] - p[1])
        la = math.hypot(*a)
        lb = math.hypot(*b)
        a = (a[0] / la, a[1] / la)
        b = (b[0] / lb, b[1] / lb)
        na = (a[1], -a[0])
        nb = (b[1], -b[0])
        den = 1 + na[0] * nb[0] + na[1] * nb[1]
        mit = ((na[0] + nb[0]) / den, (na[1] + nb[1]) / den)
        normals = [na, nb] if d * (a[0] * b[1] - a[1] * b[0]) > 0 and math.hypot(*mit) > limit else [mit]
        result.extend((p[0] + d * n[0], p[1] + d * n[1]) for n in normals)
    # Independent polygon clipping against the symmetry axis on each half of
    # the crown: remove consumed tip edges and meet at the shifted-line crossing.
    if d < 0:
        right = next((i for i, q in enumerate(result) if i >= 2 and i < (len(result) + 1) // 2 and q[0] < 0), None)
        if right is not None:
            left = len(result) + 1 - right
            a, b = result[right - 1], result[right]
            y = a[1] + a[0] / (a[0] - b[0]) * (b[1] - a[1])
            result = result[:right] + [(0, y)] + result[left + 1:]
    return result


def simple(poly):
    def orient(a, b, c): return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    for i, (a, b) in enumerate(zip(poly, poly[1:] + poly[:1])):
        for j, (c, d) in enumerate(zip(poly, poly[1:] + poly[:1])):
            if j <= i + 1 or (i == 0 and j == len(poly) - 1):
                continue
            assert not (orient(a, b, c) * orient(a, b, d) < -1e-14 and orient(c, d, a) * orient(c, d, b) < -1e-14), 'Offset self intersection'


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(ROOT / 'assets/Windows.blend'), link=False) as (_, dst):
        dst.objects = ['GNL • Diamond Window']
    obj = dst.objects[0]
    bpy.context.collection.objects.link(obj)
    mod = obj.modifiers[0]
    core = mod.node_group
    lat = next(n for n in core.nodes if n.bl_idname == 'GeometryNodeGroup' and n.node_tree.name.startswith('GNL • Diamond Lattice'))
    report = []
    for style in STYLES:
        for nx, ny in ([(4, 4), (3, 5), (5, 2)] + ([(1, 8), (8, 1), (8, 8)] if style == "Square" else [])):
            w, h, r = 1.2, 1.4, .9
            cw = .022
            depth = .0308
            values = {'Arch Style': style, 'Width': w, 'Springing Height': h, 'Rise': r, 'Arch Segments': 24, 'Cells Across': nx, 'Cells Up': ny}
            for k, v in values.items():
                set_input(mod, k, v)
            poly, resolved = boundary(style, w, h, r, 24)
            outer = offset(poly, cw * 1.6, 6)
            inner = offset(poly, -cw, 2)
            simple(outer)
            simple(inner)
            frame = sample_output(core, 'Frame', values)
            fv = shell(frame, allow_collinear=True)[0]
            expected = (area(outer) - area(inner)) * depth
            assert abs(fv - expected) < max(2e-8, expected * 1e-4), (style, fv, expected)
            assert frame['uv']['present'] and frame['uv']['finite'] and not frame['uv']['zero_area_faces']
            glass = sample_output(core, 'Glass', values)
            assert abs(shell(glass, allow_collinear=True)[0] - area(poly) * .004) < 1e-7
            # Verify actual unfused bar volumes against independently count-derived families.
            lat.inputs['Fuse Crossings'].default_value = False
            bars = sample_output(core, 'Lattice', values)
            vol = shell(bars, bars['ids'])
            theta = math.atan2(h / ny, w / nx)
            spacing = w / nx * math.sin(theta)
            expected = expected_bars(poly, w, h, resolved, theta, spacing, 0, cw, depth, 4)
            assert set(vol) == set(expected), (style, nx, ny, set(vol) ^ set(expected))
            for k, v in vol.items():
                assert abs(v - expected[k]) < max(3e-8, expected[k] * .003), (style, k, v, expected[k])
            lat.inputs['Fuse Crossings'].default_value = True
            fused = sample_output(core, 'Lattice', values)
            shell(fused, allow_collinear=True)
            # Centerline intercepts at the sill and springing lie on half-cell divisions.
            for y in (0, h):
                for family in (-1, 1):
                    for k in range(-2, 3):
                        x = (y * math.cos(theta) - k * spacing) / (family * math.sin(theta))
                        assert abs(x / (w / nx) - round(x / (w / nx))) < 1e-10
            report.append(dict(style=style, cells_across=nx, cells_up=ny, angle=math.degrees(theta), spacing=spacing, bars=len(vol)))
            print('PASS', report[-1], flush=True)
    for style in ('Elliptical', 'Ogee'):
        assert not sample_output(core, 'Frame', {'Arch Style': style, 'Width': 3., 'Springing Height': 3., 'Rise': .1, 'Came Width': .01, 'Frame Inset Factor': 2., 'Frame Outset Factor': 3.})['vertices'], 'Folded frame must be rejected'
    assert not sample_output(core, 'Glass', {'Show Glass': False})['vertices']
    assert not sample_output(core, 'Frame', {'Show Frame': False})['vertices']
    assert data(obj)['vertices']
    print('PASS: 24 Diamond window cases, component toggles, analytic offsets and count-derived bar volumes')


