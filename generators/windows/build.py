"""Windows: named openings (three-low-poly ArchProfile styles), lattices, glass and assembled windows.

Writes   assets/Windows.blend            objects, node groups, materials
         examples/windows/gallery.blend  a fresh scene appending them

Modules  graph.py    the shared Graph plus the Arch Style menu, and the common opening inputs
         opening.py  Opening Profile: outline, region and cutter from one named opening
         lattice.py  Diamond Lattice, Gregorian Lattice
         pane.py     Window Pane
         frame.py    Opening Boundary Offset, Window Frame
         window.py   Diamond Window, Gregorian Window

Every group that takes an opening takes the SAME five inputs (Arch Style, Width, Springing Height,
Rise, Arch Segments) and evaluates the same GNL • Opening Profile, so a lattice, its glass and its
frame always agree.
Run: python3 scripts/build.py windows [--render]
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
from opening import opening_group  # noqa: E402
from lattice import lattice_group  # noqa: E402
from pane import pane_group  # noqa: E402
from frame import offset_group, frame_group  # noqa: E402
from window import assembly_group  # noqa: E402

DEPENDS = []
FAMILY = 'Windows'
FILE = 'Windows.blend'
OBJECTS = ['Diamond Lattice', 'Gregorian Lattice', 'Window Pane', 'Diamond Window', 'Gregorian Window']


def materials():
    return {
        'came': principled(named('Came • Dark Bronze'), (.18, .10, .035), roughness=.32, metallic=.65),
        'bars': principled(named('Bars • Painted Walnut'), (.107, .051, .033), roughness=.6, metallic=.05),
        'glass': principled(named('Glass • Clear Blue'), (.72, .9, .96), roughness=.07, glass=True),
        'iron': principled(named('Frame • Ironwork'), (.025, .033, .045), roughness=.4, metallic=.35),
    }


def export_assets():
    mats = materials()
    opening = opening_group()
    diamond = lattice_group(opening, mats['came'])
    gregorian = lattice_group(opening, mats['bars'], gregorian=True)
    pane = pane_group(opening, mats['glass'])
    frame = frame_group(opening, offset_group(), mats['iron'])
    diamond_window = assembly_group(opening, diamond, pane, frame, mats['iron'], mats['glass'])
    gregorian_window = assembly_group(opening, gregorian, pane, frame, mats['bars'], mats['glass'], gregorian=True)
    descriptions = {
        opening: 'Named opening (Square, Semicircle, Segmental, Horseshoe, Elliptical, Pointed, Ogee): outline, '
                 'filled region and closed cutter from one definition. Upright XZ, sill centre at the origin.',
        diamond: 'Two diagonal came families fitted to a named opening: angle, spacing and phase.',
        gregorian: 'Upright mullions and level transoms fitted to a named opening, independent spacing and phase.',
        pane: 'Glass that fits the named opening exactly: a surface or a thin closed slab, with a real UVMap.',
        frame: 'A frame offset from a named opening boundary, inside and out.',
        diamond_window: 'Diamond window: cell-count alignment, shared opening, offset frame and optional glass.',
        gregorian_window: 'Gregorian window: light-count alignment, shared opening, offset frame and optional glass.',
    }
    entries = [assets.mark(g, FAMILY, text) for g, text in descriptions.items()]
    for name, group in zip(OBJECTS, (diamond, gregorian, pane, diamond_window, gregorian_window)):
        obj = assets.host(name, group)
        bpy.context.view_layer.update()
        set_input(obj.modifiers[0], 'Arch Style', 'Semicircle')
        entries.append(assets.mark(obj, FAMILY, f'{descriptions[group]} Controls are on the modifier (wrench tab).',
                                   ('window', 'arch', 'Geometry Nodes')))
    entries += [assets.mark(m, FAMILY, f'{m.name}.') for m in mats.values()]
    assets.export(FILE, entries)


def gallery():
    loaded = assets.load_into_fresh_scene(FILE, [named(n) for n in OBJECTS])
    styles = ['Semicircle', 'Pointed', 'Square', 'Ogee', 'Segmental']
    for k, (name, style) in enumerate(zip(OBJECTS, styles)):
        obj = loaded[named(name)]
        obj.location = (-4.4 + k * 2.2, 0, 0)
        set_input(obj.modifiers[0], 'Arch Style', style)
        label(name.upper(), (obj.location.x, -.6, .01), size=.13)
        label(style.upper(), (obj.location.x, -.85, .01), size=.1)
    studio(bpy.context.scene, camera_location=(0, -11.5, 3.8), target=(0, 0, 1.15), lens=32)
    first = loaded[named('Diamond Window')]
    first.select_set(True)
    bpy.context.view_layer.objects.active = first
    save_gallery(ROOT / 'examples/windows', 'READ ME • Windows')


def main():
    require_background()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    export_assets()
    gallery()


if __name__ == '__main__':
    main()
