"""Masonry: GNL • Brick Pier with alternating stone quoins, plinth, cap and seeded decay.

Writes   assets/Masonry.blend            the pier group and object, four materials
         examples/masonry/gallery.blend  a fresh scene appending it, plus a decayed copy

Run: python3 scripts/build.py masonry [--render]
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
from authoring.presentation import label, studio  # noqa: E402
from pier import pier_group  # noqa: E402
from materials import materials  # noqa: E402

DEPENDS = []
FAMILY = 'Masonry'
FILE = 'Masonry.blend'
SLOTS = ('Brick', 'Mortar Material', 'Quoin', 'Stone')


def export_assets():
    mats = materials()
    group = pier_group()
    obj = assets.host('Brick Pier', group, dict(zip(SLOTS, mats)))
    entries = [assets.mark(group, FAMILY, group.description),
               assets.mark(obj, FAMILY, f'{group.description} Controls are on the modifier (wrench tab).',
                           ('masonry', 'brick', 'pier', 'Geometry Nodes'))]
    entries += [assets.mark(m, FAMILY, f'{m.name}: reads the per-brick "tone" attribute where relevant.') for m in mats]
    assets.export(FILE, entries)


def gallery():
    loaded = assets.load_into_fresh_scene(FILE, [named('Brick Pier')])
    pier = loaded[named('Brick Pier')]
    pier.location = (-1.3, 0, 0)
    label(named('Brick Pier').upper(), (-1.3, -1.1, .01), size=.15)
    ruin = pier.copy()
    ruin.name = 'Pier • decayed copy'
    bpy.context.scene.collection.objects.link(ruin)
    ruin.location = (1.3, 0, 0)
    for key, value in (('Missing Bricks', .22), ('Missing Quoins', .15), ('Missing Cap', True), ('Decay Seed', 5)):
        set_input(ruin.modifiers[0], key, value)
    label('SAME PIER • DECAY', (1.3, -1.1, .01), size=.15)
    studio(bpy.context.scene, camera_location=(0, -7.5, 3.6), target=(0, 0, 1.5), lens=34)
    pier.select_set(True)
    bpy.context.view_layer.objects.active = pier
    save_gallery(ROOT / 'examples/masonry', 'READ ME • Masonry')


def main():
    require_background()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    export_assets()
    gallery()


if __name__ == '__main__':
    main()
