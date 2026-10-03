"""Fences: GNL • Path Stations, Rustic Fence, Iron Fence and Gateway.

Writes   assets/Fences.blend            groups and objects; borrowed parts travel inside
         examples/fences/gallery.blend  a fresh scene: both fences on your curves over a hill, the gateway

Borrowed (appended at build time, so Fences.blend stands alone): GNL • Hewn Timber (Timber.blend),
GNL • Panel / Post / Overthrow (Ironwork.blend), GNL • Brick Pier (Masonry.blend), with materials.

Modules  stations.py  rustic.py  iron.py  gateway.py  common.py
Run: python3 scripts/build.py fences [--render]   (after timber, ironwork and masonry)
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
from stations import path_stations_group  # noqa: E402
from rustic import rustic_fence_group  # noqa: E402
from iron import iron_fence_group  # noqa: E402
from gateway import gateway_group  # noqa: E402

DEPENDS = ['timber', 'ironwork', 'masonry']
FAMILY = 'Fences'
FILE = 'Fences.blend'


def borrowed():
    """Parts from the other families, appended so they travel inside Fences.blend."""
    n = named
    parts = {}
    parts.update(assets.append('Timber.blend', node_groups=[n('Hewn Timber')],
                               materials=[n('Wood • Hewn'), n('Wood • Weathered')]))
    parts.update(assets.append('Ironwork.blend', node_groups=[n('Panel'), n('Post'), n('Overthrow')],
                               materials=[n('Iron • Forged'), n('Iron • Rusted')]))
    parts.update(assets.append('Masonry.blend', node_groups=[n('Brick Pier')],
                               materials=[n('Brick • Clay'), n('Mortar'), n('Stone • Dressed'), n('Stone • Plinth and Cap')]))
    return parts


def export_assets():
    p, n = borrowed(), named
    stations_group = path_stations_group()
    rustic = rustic_fence_group(p[n('Hewn Timber')], stations_group)
    iron_fence = iron_fence_group(p[n('Panel')], p[n('Post')], stations_group)
    gate = gateway_group(p[n('Brick Pier')], p[n('Overthrow')], p[n('Panel')])
    iron, rust = p[n('Iron • Forged')], p[n('Iron • Rusted')]
    objects = {
        'Rustic Fence': assets.host('Rustic Fence', rustic, {'Post Material': p[n('Wood • Hewn')],
                                                             'Rail Material': p[n('Wood • Hewn')]}),
        'Iron Fence': assets.host('Iron Fence', iron_fence, {'Iron': iron, 'Rust': rust}),
        'Gateway': assets.host('Gateway', gate, {'Brick': p[n('Brick • Clay')], 'Mortar': p[n('Mortar')],
                                                 'Quoin': p[n('Stone • Dressed')], 'Stone': p[n('Stone • Plinth and Cap')],
                                                 'Iron': iron, 'Rust': rust}),
    }
    tips = {'Rustic Fence': 'Set Path → Path to any curve object, and Ground to a mesh.',
            'Iron Fence': 'Set Path → Path to any curve object, and Ground to a mesh.',
            'Gateway': 'Origin at the opening centre, on the ground.'}
    entries = [assets.mark(g, FAMILY, g.description) for g in (stations_group, rustic, iron_fence, gate)]
    for name, obj in objects.items():
        entries.append(assets.mark(obj, FAMILY, f'{obj.modifiers[0].node_group.description} {tips[name]}',
                                   ('fence', 'Geometry Nodes')))
    assets.export(FILE, entries)


def bezier(name, points, location):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    spline = data.splines.new('BEZIER')
    spline.bezier_points.add(len(points) - 1)
    for p, co in zip(spline.bezier_points, points):
        p.co = co
        p.handle_left_type = p.handle_right_type = 'AUTO'
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    return obj


def rolling_ground(location, size):
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=60, y_subdivisions=40, size=1, location=location)
    ground = bpy.context.object
    ground.name = 'Ground • rolling'
    ground.scale = (*size, 1)
    texture = bpy.data.textures.new('Rolling', 'CLOUDS')
    texture.noise_scale = 1.4
    displace = ground.modifiers.new('Rolling (Displace)', 'DISPLACE')
    displace.texture, displace.strength, displace.mid_level, displace.texture_coords = texture, .7, 0.0, 'GLOBAL'
    ground.data.materials.append(principled('Grass', (.09, .16, .05), roughness=.9))
    return ground


def gallery():
    loaded = assets.load_into_fresh_scene(FILE, [named('Rustic Fence'), named('Iron Fence'), named('Gateway')])
    rustic, iron_fence, gate = (loaded[named(k)] for k in ('Rustic Fence', 'Iron Fence', 'Gateway'))
    ground = rolling_ground((4.5, 3.5, 0), (14, 8))
    rustic.location = (4.5, 3.5, 0)
    path = bezier('Rustic path • edit me', [(-6, 1.5, 2), (-2, -1, 2), (2, 1.2, 2), (6, -.5, 2)], (4.5, 3.5, 0))
    for key, value in (('Path', path), ('Ground', ground), ('Bay Length', 2.2)):
        set_input(rustic.modifiers[0], key, value)
    iron_fence.location = (4.5, 6.5, 0)
    path = bezier('Iron path • edit me', [(-6, -.5, 2), (-1.5, .8, 2), (3, -.4, 2), (6.5, .6, 2)], (4.5, 6.5, 0))
    for key, value in (('Path', path), ('Ground', ground), ('Rings', True)):
        set_input(iron_fence.modifiers[0], key, value)
    gate.location = (-5.5, 1.5, 0)
    label(named('Gateway').upper(), (-5.5, .2, .01), size=.2)
    label('RUSTIC AND IRON FENCES • ALONG YOUR CURVES, ONTO THE GROUND', (4.5, -1.2, .01), size=.2)
    studio(bpy.context.scene, camera_location=(0, -16.5, 8.5), target=(0, 3.0, 1.2), lens=28, light_scale=1.6)
    gate.select_set(True)
    bpy.context.view_layer.objects.active = gate
    save_gallery(ROOT / 'examples/fences', 'READ ME • Fences')


def main():
    require_background()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    export_assets()
    gallery()


if __name__ == '__main__':
    main()
