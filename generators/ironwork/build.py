"""Ironwork: wrought-iron members, forged ornament, ivy and the overthrow arch.

Writes   assets/Ironwork.blend            objects, node groups, forged and rusted iron
         examples/ironwork/gallery.blend  a fresh scene appending them

Modules  members.py    Picket, Post, Scroll, Panel
         ornament.py   Twisted Bar, Fleur-de-lis, Double Scroll, Collar, Ornamental Rail
         ivy.py        Ivy Leaf, Tendril, Ivy Iron
         overthrow.py  Overthrow (composed from the others)
         common.py     small shared helpers

Origins: three-low-poly fence geometry; the website's graveyard (panels, gateway overthrow) and
windowsill (rope twists, fitted S-scrolls); first explored in NodesLab studies 030 and 033–035.
Run: python3 scripts/build.py ironwork [--render]
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
from authoring.presentation import label, principled, studio  # noqa: E402
from members import picket_group, post_group, scroll_group, panel_group, PANEL_SPEC  # noqa: E402
from ornament import twisted_bar, fleur_group, double_scroll, collar_group, rail_group  # noqa: E402
from ivy import leaf_group, tendril_group, ivy_group, IVY_SPEC  # noqa: E402
from overthrow import overthrow_group  # noqa: E402

DEPENDS = []
FAMILY = 'Ironwork'
FILE = 'Ironwork.blend'

MEMBER_PANELS = {
    'Picket': {'Bar': ['Height', 'Radius', 'Sides'], 'Finial': ['Finial', 'Finial Height', 'Finial Radius', 'Finial Depth']},
    'Post': {'Shaft': ['Height', 'Radius', 'Sides'], 'Top': ['Ball Radius', 'Ball Settle', 'Collar']},
    'Scroll': {'Spiral': ['Start Radius', 'Turns', 'Tightness', 'Segments', 'Flip'],
               'Bar': ['Bar Width', 'Bar Thickness', 'Taper']},
    'Twisted Bar': {'Bar': ['Height', 'Style', 'Width'], 'Twist': ['Twist Pitch', 'Plain Ends', 'Strands', 'Bulge', 'Detail']},
    'Fleur-de-lis': {'Size': ['Height', 'Width', 'Thickness']},
    'Double Scroll': {'Shape': ['Style', 'Fit Width', 'Turns', 'Tightness', 'Mirror', 'Segments'],
                      'Bar': ['Bar Width', 'Bar Thickness', 'Taper']},
    'Ornamental Rail': {'Run': ['Length', 'Height', 'Spacing', 'Bar Width'],
                        'Ornament': ['Twist Style', 'Scroll Style', 'Scrolls', 'Fleur Finials', 'Collars']},
    'Panel': PANEL_SPEC,
}
TAGS = ('wrought iron', 'Geometry Nodes')


def ivy_object(ivy, iron):
    """GNL • Ivy Iron grows its own vine, or follows any curve object chosen in Path Object."""
    G = Graph(named('Ivy Iron • Object'), modifier=True)
    G.input('Geometry', 'NodeSocketGeometry')
    G.input('Path Object', 'NodeSocketObject', description='Optional curve object for the vine. Empty = grow one.')
    items = [x for x in ivy.interface.items_tree
             if x.item_type == 'SOCKET' and x.in_out == 'INPUT' and x.socket_type != 'NodeSocketGeometry']
    for x in items:
        sub = getattr(x, 'subtype', 'NONE')
        G.input(x.name, x.socket_type, getattr(x, 'default_value', None), getattr(x, 'min_value', None),
                getattr(x, 'max_value', None), x.description, subtype=None if sub in ('NONE', '') else sub)
    G.input('Material', 'NodeSocketMaterial')
    G.output('Geometry')
    G.finish_io()
    info = G.n('GeometryNodeObjectInfo', 'Path', transform_space='RELATIVE')
    G.link(G.i['Path Object'], info.inputs['Object'])
    node = G.group(ivy, 'Ivy Iron')
    G.link(info.outputs['Geometry'], node.inputs['Path'])
    for x in items:
        G.link(G.i[x.name], node.inputs[x.name])
    G.link(G.material(node.outputs[0], G.i['Material']), G.o['Geometry'])
    G.layout()
    spec = {k: [n for n in v if n != 'Path'] for k, v in IVY_SPEC.items()}
    spec['Vine'] = ['Path Object'] + spec['Vine']
    G.panels({**spec, 'Surface': ['Material']})
    obj = assets.host('Ivy Iron', G.g, {'Material': iron}, location=(0, 0, 1.0))
    return assets.mark(obj, FAMILY, 'Forged ivy: grows its own seeded vine, or set Vine → Path Object to any curve. '
                                    'Leaves alternate, taper and can face outward to climb a post.', (*TAGS, 'ivy'))


def export_assets():
    iron = principled(named('Iron • Forged'), (.025, .025, .028), roughness=.42, metallic=.85)
    rust = principled(named('Iron • Rusted'), (.09, .035, .016), roughness=.8, metallic=.35)
    picket, post, scroll = picket_group(), post_group(), scroll_group()
    panel = panel_group(picket)
    twisted, fleur, double, collar = twisted_bar(), fleur_group(), double_scroll(), collar_group()
    rail = rail_group(twisted, double, fleur, collar)
    leaf, tendril = leaf_group(), tendril_group()
    ivy = ivy_group(leaf, tendril)
    overthrow = overthrow_group({named('Scroll'): scroll, named('Double Scroll'): double,
                                 named('Fleur-de-lis'): fleur, named('Ivy Iron'): ivy, named('Ivy Leaf'): leaf})
    members = (picket, post, scroll, panel, twisted, fleur, double, rail)
    for group in members:
        name = group.name.removeprefix(named(''))
        if name != 'Panel':   # the panel group arranges its own panels
            Graph.of(group).panels(MEMBER_PANELS[name])
    entries = [assets.mark(g, FAMILY, g.description) for g in (*members, collar, leaf, tendril, ivy, overthrow)]
    for group in members:
        name = group.name.removeprefix(named(''))
        wrapper = assets.object_group(group, panels=MEMBER_PANELS[name], closed=('Decay',))
        obj = assets.host(name, wrapper, {'Material': iron},
                          rotation=(math.pi / 2, 0, 0) if name == 'Scroll' else (0, 0, 0))
        if name == 'Fleur-de-lis':
            set_input(obj.modifiers[0], 'Height', .3)
        entries.append(assets.mark(obj, FAMILY, f'{group.description} Controls are on the modifier (wrench tab).', TAGS))
    entries.append(ivy_object(ivy, iron))
    arch = assets.host('Overthrow', overthrow, {'Material': iron}, location=(0, 0, 2.4))
    entries.append(assets.mark(arch, FAMILY, f'{overthrow.description} Origin: centre of the springing line.',
                               (*TAGS, 'arch', 'gate')))
    for material in (iron, rust):
        entries.append(assets.mark(material, FAMILY, f'{material.name}.'))
    assets.export(FILE, entries)


def gallery():
    """Members, ornament and the overthrow, appended from the saved file; a derelict panel shows decay."""
    names = ['Picket', 'Post', 'Twisted Bar', 'Fleur-de-lis', 'Double Scroll', 'Panel', 'Ornamental Rail',
             'Ivy Iron', 'Overthrow']
    loaded = assets.load_into_fresh_scene(FILE, [named(n) for n in names])
    obj = {n: loaded[named(n)] for n in names}
    with bpy.data.libraries.load(str(assets.ASSETS / FILE), link=False) as (src, dst):
        dst.materials = [named('Iron • Rusted')]
    rust = dst.materials[0]
    rust.asset_clear()
    scene = bpy.context.scene
    # Front row: members and ornament. Middle: rail and panels. Back: the overthrow, standing on its legs.
    front = [('Picket', -4.4, 0, {}), ('Post', -3.8, 0, {'Height': 1.6, 'Collar': True}),
             ('Twisted Bar', -3.1, 0, {'Style': 'Rope', 'Height': 1.4, 'Width': .06, 'Twist Pitch': .16}),
             ('Fleur-de-lis', -2.2, .2, {'Height': .6, 'Width': .5, 'Thickness': .04}),
             ('Double Scroll', -.9, .5, {'Fit Width': .8, 'Bar Width': .016, 'Bar Thickness': .007}),
             ('Ivy Iron', 1.4, 1.0, {'Length': 1.6})]
    for name, x, z, settings in front:
        obj[name].location = (x, 0, z)
        for key, value in settings.items():
            set_input(obj[name].modifiers[0], key, value)
        label(name.upper(), (x, -.7, .01), size=.12)
    obj['Ornamental Rail'].location = (-3.1, 2.4, 0)
    set_input(obj['Ornamental Rail'].modifiers[0], 'Length', 2.0)
    label('ORNAMENTAL RAIL', (-3.1, 1.7, .01), size=.13)
    obj['Panel'].location = (0, 2.4, 0)
    set_input(obj['Panel'].modifiers[0], 'Rings', True)
    label('PANEL • FITTED RINGS', (0, 1.7, .01), size=.13)
    derelict = obj['Panel'].copy()
    derelict.name = 'Panel • derelict copy'
    scene.collection.objects.link(derelict)
    derelict.location = (2.9, 2.4, 0)
    for key, value in (('Missing Pickets', .15), ('Bent Pickets', .25), ('Decay Seed', 6), ('Material', rust)):
        set_input(derelict.modifiers[0], key, value)
    label('SAME PANEL • DECAY + RUST', (2.9, 1.7, .01), size=.13)
    obj["Overthrow"].location = (-.2, 6.2, .2)   # legs reach 0.2 below the springing: they stand on the floor
    for key, value in (('Infill', 'Spokes and Volutes'), ('Centre', 'Medallion'), ('Crown', 'Fleur-de-lis'), ('Ivy', True)):
        set_input(obj['Overthrow'].modifiers[0], key, value)
    label("OVERTHROW", (-.2, 5.5, .01), size=.14)
    studio(scene, camera_location=(-.4, -9.0, 8.2), target=(-.4, 2.6, .9), lens=27, light_scale=1.3)
    obj['Panel'].select_set(True)
    bpy.context.view_layer.objects.active = obj['Panel']
    save_gallery(ROOT / 'examples/ironwork', 'READ ME • Ironwork')


def main():
    require_background()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    export_assets()
    gallery()


if __name__ == '__main__':
    main()
