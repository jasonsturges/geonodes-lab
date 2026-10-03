"""Independent axis-aligned section integration and boundary checks for Gregorian."""
from pathlib import Path
import sys, math, json
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_core import ROOT, STYLES, boundary, data, shell, expected_bars, set_input, get_input


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(ROOT / 'assets/Windows.blend'), link=False) as (_, dst):
        dst.objects = ['GNL • Gregorian Lattice']
    obj = dst.objects[0]
    bpy.context.collection.objects.link(obj)
    mod = obj.modifiers[0]
    report = []
    for style in STYLES:
        for sides, ms, ts, mp, tp, r, n in [(4, .24, .3, 0., 0., .6, 24), (7, .21, .34, .105, -.11, 1., 32)]:
            values = {'Arch Style': style, 'Width': 1.2, 'Springing Height': 1.5, 'Rise': r, 'Arch Segments': n, 'Mullion Spacing': ms, 'Transom Spacing': ts, 'Mullion Phase': mp, 'Transom Phase': tp, 'Bar Width': .03, 'Bar Depth': .045, 'Bar Sides': sides, 'Fuse Crossings': False}
            for k, v in values.items():
                set_input(mod, k, v)
            poly, rise = boundary(style, 1.2, 1.5, r, n)
            d = data(obj)
            volumes = shell(d, d['ids'])
            expected = expected_bars(poly, 1.2, 1.5, rise, 0, ms, 0, .03, .045, sides, families=[(math.pi / 2, ms, mp), (0, ts, tp)], full_section=True)
            assert set(volumes) == set(expected), (style, sides, set(volumes) ^ set(expected))
            for key, v in volumes.items():
                assert abs(v - expected[key]) < max(2e-8, expected[key] * .002), (style, key, v, expected[key])
            assert d['uv']['present'] and d['uv']['finite'] and not d['uv']['zero_area_faces']
            set_input(mod, 'Fuse Crossings', True)
            fused = data(obj)
            fv = shell(fused, allow_collinear=True)[0]
            assert 0 < fv <= sum(volumes.values()) + 1e-7
            assert fused['uv']['present'] and fused['uv']['finite'] and not fused['uv']['zero_area_faces']
            report.append(dict(style=style, sides=sides, mullion_spacing=ms, transom_spacing=ts, mullion_phase=mp, transom_phase=tp, bars=len(volumes)))
            print('PASS', report[-1], flush=True)
    # Square boundary-coincident bars at jambs, sill and head must be omitted.
    for k, v in {'Arch Style': 'Square', 'Width': 1.2, 'Springing Height': 1.2, 'Mullion Spacing': .3, 'Transom Spacing': .3, 'Mullion Phase': 0., 'Transom Phase': 0., 'Bar Sides': 4, 'Fuse Crossings': False}.items():
        set_input(mod, k, v)
    d = data(obj)
    assert len(shell(d, d['ids'])) == 6, 'Expected 3 mullions and 3 transoms, with perimeter omitted'
    sibling = bpy.data.objects.new('Independent host', bpy.data.meshes.new('Empty'))
    bpy.context.collection.objects.link(sibling)
    other = sibling.modifiers.new('Native Gregorian', 'NODES')
    other.node_group = mod.node_group
    set_input(other, 'Width', 2.)
    assert abs(get_input(mod, 'Width') - 1.2) < 1e-6 and len(data(sibling)['vertices']) > 0
    print('PASS: 14 Gregorian cases, boundary coincidence, fused topology/UVs and independent host')


