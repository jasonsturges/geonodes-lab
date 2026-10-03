"""Molding: named corner and surface sections, as reusable profile curves and straight molding runs.

Writes   assets/Molding.blend            GNL • Corner Molding / Surface Molding (objects and groups),
                                         their Profile groups, and a painted material
         examples/molding/gallery.blend  every named section, plus crown and base examples

Modules  graph.py     the shared Graph for this family, F (formula wrapper), section names
         profiles.py  Corner / Surface Molding Profile: closed section curves
         molding.py   Corner / Surface Molding: a section extruded along a straight run, with UVs

Origin: three-low-poly `MoldingProfiles.ts` (corner styles) and `SurfaceProfiles.ts`, first built in
the NodesLab prototype (paths, miters, polygons and Béziers were studied there separately).
Run: python3 scripts/build.py molding [--render]
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
from graph import CORNER, SURFACE  # noqa: E402
from profiles import profile_group  # noqa: E402
from molding import molding_group  # noqa: E402

DEPENDS = []
FAMILY = 'Molding'
FILE = 'Molding.blend'


def export_assets():
    paint = principled(named('Painted Molding'), (.72, .65, .5), roughness=.5)
    entries = [assets.mark(paint, FAMILY, 'Painted trim.')]
    for surface, title in ((False, 'Corner'), (True, 'Surface')):
        profile = profile_group(surface)
        group = molding_group(profile, paint, surface)
        kind = 'corner (crown or base)' if not surface else 'wall-mounted surface'
        entries.append(assets.mark(profile, FAMILY, f'Named {kind} molding sections as closed XY curves.'))
        entries.append(assets.mark(group, FAMILY, f'A straight {kind} molding run from a named section, with UVs.'))
        obj = assets.host(f'{title} Molding', group)
        entries.append(assets.mark(obj, FAMILY, f'{group.asset_data.description} Controls are on the modifier.',
                                   ('molding', 'trim', 'Geometry Nodes')))
    assets.export(FILE, entries)


def gallery():
    """Every named section side by side, each a copy of the appended object with its Profile set."""
    loaded = assets.load_into_fresh_scene(FILE, [named('Corner Molding'), named('Surface Molding')])
    scene = bpy.context.scene
    # Short pieces running away from the camera, so each named section faces you end-on.
    for title, y, styles in (('Corner', 0.0, CORNER), ('Surface', .55, SURFACE)):
        template = loaded[named(f'{title} Molding')]
        for k, style in enumerate(styles):
            obj = template.copy()
            obj.name = f'{title} • {style}'
            scene.collection.objects.link(obj)
            obj.location = (-1.2 + k * .3, y + .12, 0)
            obj.rotation_euler.z = 1.5708
            set_input(obj.modifiers[0], 'Profile', style)
            set_input(obj.modifiers[0], 'Length', .24)
            if title == 'Corner':
                set_input(obj.modifiers[0], 'Crown', False)   # base molding: rises from the floor
            label(style.upper(), (obj.location.x, y - .06, .001), size=.028)
        label(f'{title.upper()} SECTIONS', (-1.2 + (len(styles) - 1) * .15, y - .12, .001), size=.035)
        template.location = (1.45, y + .12, 0)
        template.rotation_euler.z = 1.5708
        set_input(template.modifiers[0], 'Length', .5)
        if title == 'Corner':
            set_input(template.modifiers[0], 'Crown', False)
        label(named(f'{title} Molding').upper(), (1.45, y - .17, .001), size=.03)
    studio(scene, camera_location=(.15, -1.75, 1.05), target=(.15, .3, .02), lens=22, light_scale=.45)
    first = loaded[named('Corner Molding')]
    first.select_set(True)
    bpy.context.view_layer.objects.active = first
    save_gallery(ROOT / 'examples/molding', 'READ ME • Molding')


def main():
    require_background()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    export_assets()
    gallery()


if __name__ == '__main__':
    main()
