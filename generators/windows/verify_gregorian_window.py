"""Verify count-driven Gregorian composition, including one-light empty leading."""
from pathlib import Path
import sys, math, json
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_core import ROOT, STYLES, boundary, area, data, shell, sample_output, set_input, expected_bars, get_input
from verify_diamond_window import offset, simple


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(ROOT / 'assets/Windows.blend'), link=False) as (_, dst):
        dst.objects = ['GNL • Gregorian Window']
    obj = dst.objects[0]
    bpy.context.collection.objects.link(obj)
    mod = obj.modifiers[0]
    core = mod.node_group
    lat = next(n for n in core.nodes if n.bl_idname == 'GeometryNodeGroup' and n.node_tree.name.startswith('GNL • Gregorian Lattice'))
    report = []
    for style in STYLES:
        for nx, ny in [(3, 4), (4, 3), (1, 1), (8, 8)]:
            w, h, r = 1.2, 1.4, .9
            bw = .03
            depth = .03
            values = {'Arch Style': style, 'Width': w, 'Springing Height': h, 'Rise': r, 'Arch Segments': 24, 'Lights Across': nx, 'Lights Up': ny}
            for k, v in values.items():
                set_input(mod, k, v)
            poly, resolved = boundary(style, w, h, r, 24)
            outer = offset(poly, bw * 1.6, 6)
            inner = offset(poly, -bw, 2)
            simple(outer)
            simple(inner)
            frame = sample_output(core, 'Frame', values)
            fv = shell(frame, allow_collinear=True)[0]
            assert abs(fv - (area(outer) - area(inner)) * depth) < 2e-7
            assert frame['uv']['finite'] and not frame['uv']['zero_area_faces']
            glass = sample_output(core, 'Glass', values)
            assert abs(shell(glass, allow_collinear=True)[0] - area(poly) * .004) < 1e-7
            ms = w / nx
            ts = h / ny
            phase = ms / 2 if nx % 2 else 0
            lat.inputs['Fuse Crossings'].default_value = False
            bars = sample_output(core, 'Lattice', values)
            expected = expected_bars(poly, w, h, resolved, 0, ms, phase, bw, depth, 4, families=[(math.pi / 2, ms, phase), (0, ts, 0)], full_section=True)
            volumes = shell(bars, bars['ids']) if bars['vertices'] else {}
            assert set(volumes) == set(expected), (style, nx, ny, set(volumes) ^ set(expected))
            for key, v in volumes.items():
                assert abs(v - expected[key]) < max(3e-8, expected[key] * .003), (style, key, v, expected[key])
            if style == 'Square':
                assert len(volumes) == nx + ny - 2, 'One fewer internal bar per light count'
            lat.inputs['Fuse Crossings'].default_value = True
            fused = sample_output(core, 'Lattice', values)
            if volumes:
                shell(fused, allow_collinear=True)
                assert fused['uv']['finite'] and not fused['uv']['zero_area_faces']
            else:
                assert not fused['vertices']
            report.append(dict(style=style, lights_across=nx, lights_up=ny, mullion_spacing=ms, transom_spacing=ts, mullion_phase=phase, bars=len(volumes)))
            print('PASS', report[-1], flush=True)
    assert not sample_output(core, 'Glass', {'Show Glass': False})['vertices']
    assert not sample_output(core, 'Frame', {'Show Frame': False})['vertices']
    other = bpy.data.objects.new('Independent consumer', bpy.data.meshes.new('Host'))
    bpy.context.collection.objects.link(other)
    om = other.modifiers.new('Window', 'NODES')
    om.node_group = core
    set_input(om, 'Lights Across', 2)
    assert get_input(mod, 'Lights Across') == 8 and data(other)['vertices']
    print('PASS: 28 Gregorian window cases, toggles and independent consumer')


