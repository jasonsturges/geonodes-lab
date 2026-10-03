"""Molding: named corner and surface sections, as reusable profile curves and straight molding runs.

Writes   assets/Molding.blend            GNL • Corner Molding / Surface Molding (objects and groups),
                                         their Profile groups, and a painted material
         examples/molding/gallery.blend  every named section, plus crown and base examples
         examples/molding/room.blend     Molding Run: crown, chair rail and base around one room plan

Modules  graph.py     the shared Graph for this family, F (formula wrapper), section names
         profiles.py  Corner / Surface Molding Profile: closed section curves
         molding.py   Corner / Surface Molding: a section extruded along a straight run, with UVs
         run.py       Molding Run: a section swept along any curve, every corner mitered exactly

Origin: three-low-poly `MoldingProfiles.ts` (corner styles), `SurfaceProfiles.ts` and `MoldingGeometry`
(the run), first built in the NodesLab prototype (its studies 022–024 explored miters, polygons and Béziers).
Run: python3 scripts/build.py molding [--render]
"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT), str(HERE)]

import bpy  # noqa: E402
from authoring import assets  # noqa: E402
from authoring.graph import Graph  # noqa: E402
from authoring.lifecycle import require_background, save_gallery, save_scene, wants_render  # noqa: E402
from authoring.modifiers import set_input  # noqa: E402
from authoring.naming import named  # noqa: E402
from authoring.presentation import label, principled, studio  # noqa: E402
from graph import CORNER, SURFACE  # noqa: E402
from profiles import profile_group  # noqa: E402
from molding import molding_group  # noqa: E402
from run import run_group, run_object_group  # noqa: E402

DEPENDS = []
FAMILY = 'Molding'
FILE = 'Molding.blend'


def export_assets():
    paint = principled(named('Painted Molding'), (.72, .65, .5), roughness=.5)
    entries = [assets.mark(paint, FAMILY, 'Painted trim.')]
    profiles = {}
    for surface, title in ((False, 'Corner'), (True, 'Surface')):
        profile = profiles[title] = profile_group(surface)
        group = molding_group(profile, paint, surface)
        kind = 'corner (crown or base)' if not surface else 'wall-mounted surface'
        entries.append(assets.mark(profile, FAMILY, f'Named {kind} molding sections as closed XY curves.'))
        entries.append(assets.mark(group, FAMILY, f'A straight {kind} molding run from a named section, with UVs.'))
        obj = assets.host(f'{title} Molding', group)
        entries.append(assets.mark(obj, FAMILY, f'{group.asset_data.description} Controls are on the modifier.',
                                   ('molding', 'trim', 'Geometry Nodes')))
    run = run_group()
    wrapper = run_object_group(run, profiles['Corner'], profiles['Surface'])
    entries.append(assets.mark(run, FAMILY, run.description))
    obj = assets.host('Molding Run', wrapper, {'Material': paint})
    entries.append(assets.mark(obj, FAMILY, 'Crown, base or chair rail along any curve object, every corner mitered '
                                            'exactly. Set Path → Path on the modifier.', ('molding', 'trim', 'Geometry Nodes')))
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


# Room plan, drawn so the room lies on the path's LEFT (Inward). Corners are sharp (vector handles);
# the bay is a true circular arc through (2, -.7), (2.45, 0), (2, .7) as three Bézier points.
BAY_CENTRE, BAY_RADIUS = (1.68056, 0.0), .76969


def room_plan():
    import math
    cx, r = BAY_CENTRE[0], BAY_RADIUS
    half = math.atan2(.7, 2 - cx)                       # half the bay's arc angle
    handle = 4 / 3 * math.tan(half / 2 / 2) * r         # Bézier handle for each half of the arc
    tangent = lambda x, y: (-y / r, (x - cx) / r)  # noqa: E731  arc tangent, travelling +y (anticlockwise)
    corners = [(2, -1.5), (2, -.7), (2.45, 0), (2, .7), (2, 1.5), (.5, 1.5), (.5, 1.0), (-.5, 1.0), (-.5, 1.5),
               (-2, 1.5), (-2, -1.5)]
    data = bpy.data.curves.new('Room plan', 'CURVE')
    data.dimensions = '3D'
    spline = data.splines.new('BEZIER')
    spline.bezier_points.add(len(corners) - 1)
    spline.resolution_u = 16
    for k, (p, co) in enumerate(zip(spline.bezier_points, corners)):
        p.co = (*co, 0)
        p.handle_left_type = p.handle_right_type = 'FREE'
        prev = corners[max(k - 1, 0)]
        nxt = corners[min(k + 1, len(corners) - 1)]
        p.handle_left = (co[0] + (prev[0] - co[0]) / 3, co[1] + (prev[1] - co[1]) / 3, 0)
        p.handle_right = (co[0] + (nxt[0] - co[0]) / 3, co[1] + (nxt[1] - co[1]) / 3, 0)
        if co in ((2, -.7), (2.45, 0), (2, .7)):
            tx, ty = tangent(*co)
            if co != (2, -.7):
                p.handle_left = (co[0] - tx * handle, co[1] - ty * handle, 0)
            if co != (2, .7):
                p.handle_right = (co[0] + tx * handle, co[1] + ty * handle, 0)
    return data


def walls_group(height, thickness, plaster):
    """Scene dressing for the room example (not an asset): the walls are Molding Run too, with a plain
    rectangle as the section, projected OUTWARD (behind the room). So they have real thickness, every
    corner mitered, and they follow the same plan as the moldings."""
    G = Graph('Room walls • example only', modifier=True)
    G.input('Geometry', 'NodeSocketGeometry')
    G.input('Plan', 'NodeSocketObject')
    G.output('Geometry')
    G.finish_io()
    info = G.n('GeometryNodeObjectInfo', 'Plan', transform_space='RELATIVE')
    G.link(G.i['Plan'], info.inputs['Object'])
    section = G.n('GeometryNodeCurvePrimitiveQuadrilateral', 'Wall section: height × thickness')
    section.inputs['Width'].default_value, section.inputs['Height'].default_value = height, thickness
    section = G.transform(section.outputs[0], (height / 2, thickness / 2, 0), label='Back on the plan line')
    run = G.group(bpy.data.node_groups[named('Molding Run')], 'Molding Run')
    G.link(info.outputs['Geometry'], run.inputs['Path'])
    G.link(section, run.inputs['Section'])
    run.inputs['Crown'].default_value = False
    run.inputs['Outward'].default_value = True
    G.link(G.shade(G.material(run.outputs[0], plaster)), G.o['Geometry'])   # flat: walls are planes
    G.layout()
    return G.g


def room():
    """Crown, chair rail and base: three Molding Run copies on linked duplicates of one room plan."""
    loaded = assets.load_into_fresh_scene(FILE, [named('Molding Run')])
    crown = loaded[named('Molding Run')]
    scene = bpy.context.scene
    plan = room_plan()
    height = 2.4
    runs = {}
    for name, z, settings in (
            ('Crown', height, {'Run': 'Crown', 'Corner Profile': 'Cyma', 'Height': .16, 'Projection': .12}),
            ('Chair Rail', .9, {'Run': 'Chair Rail', 'Surface Profile': 'Astragal', 'Height': .07, 'Projection': .03}),
            ('Base', 0, {'Run': 'Base', 'Corner Profile': 'Ogee', 'Height': .16, 'Projection': .035})):
        path = bpy.data.objects.new(f'{name} path • edit the room plan', plan)   # linked duplicates: one plan
        scene.collection.objects.link(path)
        path.location.z = z
        obj = crown if name == 'Crown' else crown.copy()
        if obj is not crown:
            scene.collection.objects.link(obj)
        obj.name = f'Molding Run • {name}'
        set_input(obj.modifiers[0], 'Path', path)
        for key, value in settings.items():
            set_input(obj.modifiers[0], key, value)
        path.hide_render = True
        runs[name] = obj
    walls = bpy.data.objects.new('Walls • example only', bpy.data.meshes.new('Walls'))
    scene.collection.objects.link(walls)
    mod = walls.modifiers.new('Walls', 'NODES')
    mod.node_group = walls_group(height, .12, principled('Wall • Sage Plaster', (.16, .22, .18), roughness=.85))
    set_input(mod, 'Plan', scene.objects['Base path • edit the room plan'])
    for text, location in (('INSIDE CORNER', (-1.35, 1.15)), ('CHIMNEY BREAST', (0, .7)), ('CURVED BAY', (1.55, 0)),
                           ('OPEN END • SQUARE CUT', (-1.3, -1.25))):
        label(text, (*location, .002), size=.1)
    studio(scene, camera_location=(-.3, -5.2, 2.1), target=(.1, .5, 1.05), lens=22, light_scale=.9)
    runs['Crown'].select_set(True)
    bpy.context.view_layer.objects.active = runs['Crown']
    directory = ROOT / 'examples/molding'
    save_scene(directory / 'room.blend', readme=directory / 'README.md', readme_title='READ ME • Molding',
               render=wants_render(), preview='room-preview.png')


def main():
    require_background()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    export_assets()
    gallery()
    room()


if __name__ == '__main__':
    main()
