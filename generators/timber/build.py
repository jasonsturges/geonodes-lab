"""Timber: GNL • Weathered Plank and GNL • Hewn Timber, seeded wood members with exact warps and grain.

Writes   assets/Timber.blend            groups, ready-made objects, three wood materials
         examples/timber/gallery.blend  a fresh scene appending them (a small lumber yard)

Run: python3 scripts/build.py timber [--render]
"""
from pathlib import Path
import math
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT), str(HERE)]

import bpy  # noqa: E402
from authoring import assets  # noqa: E402
from authoring.graph import Graph  # noqa: E402
from authoring.lifecycle import require_background, save_gallery  # noqa: E402
from authoring.modifiers import set_input  # noqa: E402
from authoring.naming import named  # noqa: E402
from authoring.presentation import label, studio  # noqa: E402
from members import plank, timber  # noqa: E402
from materials import wood_material  # noqa: E402

DEPENDS = []
FAMILY = 'Timber'
FILE = 'Timber.blend'

PANELS = {
    'Weathered Plank': {
        'Size': ['Length', 'Width', 'Thickness'],
        'Resolution': ['Length Segments', 'Width Segments'],
        'Variation': ['Seed', 'Edge Roughness', 'End Skew', 'Surface'],
        'Warp': ['Bow', 'Crook', 'Cup', 'Twist', 'Randomize Warp'],
    },
    'Hewn Timber': {
        'Size': ['Length', 'Diameter', 'Taper'],
        'Resolution': ['Facets', 'Rings'],
        'Variation': ['Seed', 'Facet Variation', 'Irregularity'],
        'Warp': ['Bow', 'Twist', 'Randomize Warp'],
    },
}


def materials():
    # Shader colors are linear; three-low-poly's sRGB hex colors are converted (docs/blender-gotchas.md).
    return {
        'rough': wood_material(named('Wood • Rough-Sawn'), (.17, .085, .04), (.065, .03, .014)),
        'weathered': wood_material(named('Wood • Weathered'), (.2, .17, .13), (.08, .06, .045), weathered=.5),
        'hewn': wood_material(named('Wood • Hewn'), (.17, .11, .06), (.07, .045, .025), weathered=.2),
    }


def worn_edges(obj):
    """Worn arrises belong to the modifier stack, not the member graph: a Bevel after the nodes."""
    bevel = obj.modifiers.new('Worn edges (Bevel)', 'BEVEL')
    bevel.width, bevel.segments, bevel.limit_method = .006, 2, 'ANGLE'
    bevel.angle_limit = math.radians(50)


def export_assets():
    mats = materials()
    groups = {'Weathered Plank': plank(), 'Hewn Timber': timber()}
    entries = []
    for name, group in groups.items():
        Graph.of(group).panels(PANELS[name], closed=('Resolution',))
        entries.append(assets.mark(group, FAMILY, group.description))
        wrapper = assets.object_group(group, panels=PANELS[name], closed=('Resolution',))
        material = mats['rough'] if name == 'Weathered Plank' else mats['hewn']
        obj = assets.host(name, wrapper, {'Material': material})
        if name == 'Weathered Plank':
            worn_edges(obj)
        entries.append(assets.mark(obj, FAMILY, f'{group.description} Controls are on the modifier (wrench tab).',
                                   ('timber', 'wood', 'Geometry Nodes')))
    for material in mats.values():
        entries.append(assets.mark(material, FAMILY, 'Procedural grain from the "grain" attribute; '
                                                     'optional per-member "tint" (-1…1).'))
    assets.export(FILE, entries)


def gallery():
    """A small lumber yard: the two objects, then seeded copies sharing their node groups."""
    loaded = assets.load_into_fresh_scene(FILE, [named('Weathered Plank'), named('Hewn Timber')])
    board, log = loaded[named('Weathered Plank')], loaded[named('Hewn Timber')]
    weathered = bpy.data.materials.get(named('Wood • Weathered'))
    if weathered is None:   # materials not referenced by the objects aren't appended with them
        with bpy.data.libraries.load(str(assets.ASSETS / FILE), link=False) as (src, dst):
            dst.materials = [named('Wood • Weathered')]
        weathered = dst.materials[0]
    scene = bpy.context.scene
    board.location = (-2.2, 0, .07)
    log.location = (1.0, 0, 0)
    label(named('WEATHERED PLANK').upper(), (-2.2, -.8, .01), size=.15)
    label(named('HEWN TIMBER').upper(), (1.0, -.8, .01), size=.15)
    for k in range(6):
        copy = board.copy()
        copy.name = f'Plank • seed {k + 1}'
        scene.collection.objects.link(copy)
        copy.location = (-2.2 + (k % 2) * .02, 2.2 + (k % 2) * .03, .035 + k * .072)
        copy.rotation_euler.z = (k - 2.5) * .03
        for key, value in (('Seed', 500 + k * 13), ('Thickness', .07), ('Width', .3), ('Material', weathered)):
            set_input(copy.modifiers[0], key, value)
    label('SIX SEEDS • WEATHERED MATERIAL', (-2.2, 1.45, .01), size=.15)
    for k in range(5):
        copy = log.copy()
        copy.name = f'Log • seed {k + 1}'
        scene.collection.objects.link(copy)
        copy.location = (2.6 + k * .55, 2.2, 0)
        set_input(copy.modifiers[0], 'Seed', 40 + k * 7)
        set_input(copy.modifiers[0], 'Length', 1.6 + .2 * (k % 3))
    label('FIVE SEEDS', (3.7, 1.45, .01), size=.15)
    studio(scene, camera_location=(.6, -7.5, 4.8), target=(.6, 1.1, .5), lens=35)
    board.select_set(True)
    bpy.context.view_layer.objects.active = board
    save_gallery(ROOT / 'examples/timber', 'READ ME • Timber')


def main():
    require_background()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    export_assets()
    gallery()


if __name__ == '__main__':
    main()
