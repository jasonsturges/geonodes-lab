"""Floors: GNL • Hardwood Floor (more three-low-poly floors, such as plank, flagstone and hexagonal
tile, belong here).

Writes   assets/Floors.blend            the floor object and its node groups, a board-tint material
         examples/floors/gallery.blend  a fresh scene appending it: one room, three laying angles

Modules  graph.py     the shared Graph plus the names this family's formulas use
         hardwood.py  Floor Laying, Resolve Floor Offcuts, Hardwood Floor
Run: python3 scripts/build.py floors [--render]
"""
from pathlib import Path
import math
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
from hardwood import layout_group, floor_group, public_group, timber_material  # noqa: E402

DEPENDS = []
FAMILY = 'Floors'
FILE = 'Floors.blend'


def export_assets():
    tint = timber_material()
    group = public_group(floor_group(layout_group(), tint))
    obj = assets.host('Hardwood Floor', group)
    assets.export(FILE, [
        assets.mark(group, FAMILY, 'Complete hardwood floor generator; replaces host geometry. '
                                   'Seeded laying, per-board clipping to the room, UVs and color.'),
        assets.mark(obj, FAMILY, 'Seeded boards laid at any angle and clipped to a rectangular room. '
                                 'Controls are on the modifier (wrench tab).', ('floor', 'wood', 'Geometry Nodes')),
        assets.mark(tint, FAMILY, 'Reads each board\'s "hardwood_tint" color.')])


def gallery():
    loaded = assets.load_into_fresh_scene(FILE, [named('Hardwood Floor')])
    floor = loaded[named('Hardwood Floor')]
    scene = bpy.context.scene
    copies = [floor]
    for k in (1, 2):
        copy = floor.copy()
        copy.name = f'Hardwood Floor • copy {k}'
        scene.collection.objects.link(copy)
        copies.append(copy)
    for obj, x, angle, seed, title in zip(copies, (-5.4, 0, 5.4), (0, 45, 90), (1, 7, 23),
                                          ('STRAIGHT', 'DIAGONAL 45°', 'ACROSS THE ROOM')):
        obj.location = (x, 0, .056)   # boards hang below their top surface (Z = 0): lift clear of the studio floor
        set_input(obj.modifiers[0], 'Rotation', math.radians(angle))
        set_input(obj.modifiers[0], 'Layout Seed', seed)
        label(title, (x, -2.9, .01), size=.22)
    studio(scene, camera_location=(0, -13.5, 9.5), target=(0, -.4, 0), lens=30, light_scale=1.4)
    floor.select_set(True)
    bpy.context.view_layer.objects.active = floor
    save_gallery(ROOT / 'examples/floors', 'READ ME • Floors')


def main():
    require_background()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    export_assets()
    gallery()


if __name__ == '__main__':
    main()
