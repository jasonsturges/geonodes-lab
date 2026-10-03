"""Vessels: lathed glass vessels with liquid, from any silhouette curve.

Writes   assets/Vessels.blend           objects, node groups and two materials
         examples/vessels/gallery.blend  a fresh scene appending them (the family's showroom)

Origin: three-low-poly `src/geometry/vessels/vesselProfiles.ts`, first explored in NodesLab study 027.
Run: python3 scripts/build.py vessels [--render]
"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT), str(HERE)]

import bpy  # noqa: E402
from authoring import assets  # noqa: E402
from authoring.lifecycle import require_background, save_gallery  # noqa: E402
from authoring.modifiers import set_input  # noqa: E402
from authoring.naming import named  # noqa: E402
from authoring.presentation import label, principled, studio  # noqa: E402
from silhouettes import SILHOUETTES, silhouette_group  # noqa: E402
from sections import offset_group, shell_group, fill_group, lathe_group  # noqa: E402
from vessel import vessel_group, vessel_object_group  # noqa: E402

DEPENDS = []
FAMILY = 'Vessels'
FILE = 'Vessels.blend'
NAMES = ['Florence Flask', 'Erlenmeyer Flask', 'Test Tube', 'Graduated Cylinder', 'Pipette',
         'Apothecary Jar', 'Potion Bottle', 'Wine Bottle']


def materials():
    glass = principled(named('Glass'), (.86, .94, 1.0), glass=True, roughness=.04)
    liquid = principled(named('Liquid'), (.42, .1, .75), roughness=.25)
    return glass, liquid


def vase_profile():
    """An editable Bézier silhouette (X = radius, Z = height) for GNL • Vessel From Curve."""
    data = bpy.data.curves.new(named('Vase Profile'), 'CURVE')
    data.dimensions = '3D'
    spline = data.splines.new('BEZIER')
    points = [(0, 0), (.55, 0), (.85, .9), (.45, 2.0), (.38, 2.5), (.6, 2.9)]
    spline.bezier_points.add(len(points) - 1)
    for p, (r, z) in zip(spline.bezier_points, points):
        p.co = (r, 0, z)
        p.handle_left_type = p.handle_right_type = 'AUTO'
    for p in spline.bezier_points[:2]:   # a flat base: straight from the axis to the foot
        p.handle_left_type = p.handle_right_type = 'VECTOR'
    spline.resolution_u = 10
    obj = bpy.data.objects.new(named('Vase Profile'), data)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def export_assets():
    glass, liquid = materials()
    offset = offset_group()
    shell, fill, lathe = shell_group(offset), fill_group(offset), lathe_group()
    vessel = vessel_group(shell, fill, lathe)
    groups = [vessel, lathe, shell, fill]
    objects = []
    for name in NAMES + ['Vessel From Curve']:
        if name == 'Vessel From Curve':
            group = vessel_object_group(name, None, vessel, from_object=True)
        else:
            silhouette = silhouette_group(name)
            groups.append(silhouette)
            group = vessel_object_group(name, silhouette, vessel)
        obj = assets.host(name, group, {'Glass Material': glass, 'Liquid Material': liquid})
        tip = ('Pick any curve in Shape → Profile Curve (try GNL • Vase Profile).' if name == 'Vessel From Curve'
               else 'Controls are on the modifier (wrench tab).')
        assets.mark(obj, FAMILY, f'{name}: glass and liquid from native Geometry Nodes. {tip}',
                    ('vessel', 'glass', 'Geometry Nodes'))
        objects.append(obj)
    profile = assets.mark(vase_profile(), FAMILY, 'An editable Bézier silhouette for GNL • Vessel From Curve.')
    for group in groups:
        assets.mark(group, FAMILY, group.description)
    for material in (glass, liquid):
        assets.mark(material, FAMILY, f'{material.name} for vessels.')
    assets.export(FILE, [*groups, *objects, profile, glass, liquid])


def gallery():
    """The showroom: every vessel and a vase drawn from a curve, appended from the saved file."""
    loaded = assets.load_into_fresh_scene(FILE, [named(n) for n in NAMES] + [named('Vessel From Curve'),
                                                                             named('Vase Profile')])
    glass = bpy.data.materials[named('Glass')]
    liquids = {name: principled(f'Liquid • {name}', color) for name, color in [
        ('violet', (.42, .1, .75)), ('emerald', (.05, .6, .3)), ('amber', (.95, .5, .05)),
        ('wine', (.35, .02, .05)), ('blue', (.08, .3, .9)), ('pink', (.9, .2, .5))]}
    row = [('Florence Flask', 1.0, 'blue', .4, {}), ('Erlenmeyer Flask', 1.0, 'emerald', .3, {}),
           ('Test Tube', .6, 'pink', .55, {}), ('Graduated Cylinder', .75, 'blue', .6, {}),
           ('Pipette', .6, 'amber', .4, {}), ('Apothecary Jar', 1.5, 'amber', .45, {'Smooth Silhouette': True}),
           ('Potion Bottle', 1.0, 'violet', .5, {}), ('Wine Bottle', .7, 'wine', .6, {'Shoulder Segments': 10})]
    x, placed = 0.0, []
    for name, half, liquid, level, extra in row:
        x += half + .3
        placed.append((name, x, liquid, level, extra))
        x += half + .3
    for name, px, liquid, level, extra in placed:
        obj = loaded[named(name)]
        obj.location = (px - x / 2, 0, 0)
        mod = obj.modifiers[0]
        for key, value in {'Glass Material': glass, 'Liquid Material': liquids[liquid], 'Fill': level, **extra}.items():
            set_input(mod, key, value)
        label(name.upper(), (px - x / 2, -1.75, .01), size=.15)
    vessel, curve = loaded[named('Vessel From Curve')], loaded[named('Vase Profile')]
    vessel.location = (0, 4.5, 0)
    set_input(vessel.modifiers[0], 'Profile Curve', curve)
    set_input(vessel.modifiers[0], 'Liquid Material', liquids['emerald'])
    set_input(vessel.modifiers[0], 'Fill', .45)
    curve.parent = vessel       # the curve rides with its vessel (Object Info is relative)
    curve.location = (0, 0, 0)
    label('VESSEL FROM YOUR CURVE', (2.4, 4.5, .01), size=.15)
    studio(bpy.context.scene, camera_location=(0, -19, 13), target=(0, 1.6, .8), lens=40)
    bpy.context.view_layer.objects.active = loaded[named('Potion Bottle')]
    loaded[named('Potion Bottle')].select_set(True)
    save_gallery(ROOT / 'examples/vessels', 'READ ME • Vessels')


def main():
    require_background()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    export_assets()
    gallery()


if __name__ == '__main__':
    main()
