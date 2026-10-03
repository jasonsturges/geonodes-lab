"""Check exported pane against independent opening equations and slab volume."""
from pathlib import Path
import sys, json
import bpy
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_core import ROOT, STYLES, boundary, area, data, shell, set_input, get_input


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(ROOT / 'assets/Windows.blend'), link=False) as (_, dst):
        dst.objects = ['GNL • Window Pane']
    obj = dst.objects[0]
    bpy.context.collection.objects.link(obj)
    mod = obj.modifiers[0]
    report = []
    for style in STYLES:
        for width, height, rise, n, thickness in [(1.2, 1.4, .4, 4, .001), (.8, .7, 1.2, 64, .03)]:
            for k, v in {'Arch Style': style, 'Width': width, 'Springing Height': height, 'Rise': rise, 'Arch Segments': n, 'Thickness': thickness, 'Solid Glass': True}.items():
                set_input(mod, k, v)
            poly, resolved = boundary(style, width, height, rise, n)
            expected = area(poly) * thickness
            d = data(obj)
            volume = shell(d, allow_collinear=True)[0]
            assert abs(volume - expected) < max(1e-8, expected * 1e-5), (style, volume, expected)
            assert abs(min(v[1] for v in d['vertices']) + thickness / 2) < 1e-6
            assert abs(max(v[1] for v in d['vertices']) - thickness / 2) < 1e-6
            for x, y, z in d['vertices']:
                assert min((x - px)**2 + (z - pz)**2 for px, pz in poly) < 1e-10, 'Boundary mismatch'
            assert len(d['vertices']) == 2 * len(poly)
            assert d['uv']['present'] and d['uv']['finite'] and not d['uv']['zero_area_faces']
            set_input(mod, 'Solid Glass', False)
            surface = data(obj)
            surface_area = 0
            assert len(surface['vertices']) == len(poly)
            assert all(abs(v[1]) < 1e-6 for v in surface['vertices'])
            for tri, _ in surface['tris']:
                a, b, c = [Vector(surface['vertices'][i]) for i in tri]
                normal = (b - a).cross(c - a)
                assert normal.y < 1e-10, 'Front winding must face -Y'
                surface_area += normal.length / 2
            assert abs(surface_area - area(poly)) < 1e-5
            assert surface['uv']['present'] and surface['uv']['finite'] and not surface['uv']['zero_area_faces']
            report.append(dict(style=style, width=width, rise=rise, segments=n, thickness=thickness, volume=volume))
            print('PASS', report[-1], flush=True)
    other = bpy.data.objects.new('Independent pane', bpy.data.meshes.new('Host'))
    bpy.context.collection.objects.link(other)
    om = other.modifiers.new('Pane', 'NODES')
    om.node_group = mod.node_group
    set_input(om, 'Width', 2.)
    assert abs(get_input(mod, 'Width') - .8) < 1e-6 and data(other)['vertices']
    # Material replacement travels through the public socket.
    material = bpy.data.materials.new('Replacement')
    set_input(om, 'Material', material)
    bpy.context.view_layer.update()
    evaluated = other.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        assert material in list(mesh.materials) and all(mesh.materials[p.material_index] == material for p in mesh.polygons)
    finally:
        evaluated.to_mesh_clear()
    print('PASS: 14 profiles in solid and surface modes, independent host and material replacement')


