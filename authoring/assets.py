"""Asset packaging: catalogs, marking, appending dependencies, ready-made objects and export.

Every family file is a standalone product (docs/authoring.md, rule 1): parts borrowed from other
families are appended in at build time and travel inside the file.
"""
from pathlib import Path
import uuid
import bpy

from .graph import Graph
from .modifiers import set_input
from .naming import CATALOG_ROOT, named

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
CATALOG_FILE = ASSETS / 'blender_assets.cats.txt'
# Stable catalog IDs: derived from the family name, so rebuilding never reshuffles catalogs.
NAMESPACE = uuid.UUID('6a1f3e0c-58b4-4a8f-9d1e-2c7b5a904e31')


def catalog_id(family):
    """The family's catalog (created in blender_assets.cats.txt if missing). Returns its UUID string."""
    cid = str(uuid.uuid5(NAMESPACE, family))
    text = CATALOG_FILE.read_text() if CATALOG_FILE.exists() else '# Blender Asset Catalog Definition File\nVERSION 1\n\n'
    if cid not in text:
        CATALOG_FILE.write_text(text.rstrip('\n') + f'\n{cid}:{CATALOG_ROOT}/{family}:{family}\n')
    return cid


def mark(item, family, description, tags=()):
    """Mark a node group, object or material as an asset of `family`."""
    item.asset_mark()
    item.asset_data.catalog_id = catalog_id(family)
    item.asset_data.description = description
    for tag in tags:
        item.asset_data.tags.new(tag)
    return item


def append(filename, *, node_groups=(), materials=(), objects=()):
    """Append data blocks from another family's asset file; returns {name: data block}.

    The appended copies are dependencies of the file being built, not assets of it, so their asset
    marks are cleared. (libraries.load replaces the items of the lists it is given, so copies are passed.)
    """
    with bpy.data.libraries.load(str(ASSETS / filename), link=False) as (src, dst):
        missing = [n for n in (*node_groups, *materials, *objects)
                   if n not in (*src.node_groups, *src.materials, *src.objects)]
        if missing:
            raise KeyError(f'{filename} has no {missing}; rebuild it first (scripts/build.py)')
        dst.node_groups = list(node_groups)
        dst.materials = list(materials)
        dst.objects = list(objects)
    loaded = [*dst.node_groups, *dst.materials, *dst.objects]
    for item in loaded:
        item.asset_clear()
    return {item.name: item for item in loaded}


def object_group(member, *, material_inputs=('Material',), panels=None, closed=(), smooth=False):
    """A modifier group for a ready-made object: the member's inputs, a material, flat shading.

    `member` is a node group outputting one mesh. Menu defaults are copied after wiring.
    """
    name = member.name
    G = Graph(f'{name} • Object', modifier=True)
    G.input('Geometry', 'NodeSocketGeometry')
    items = [x for x in member.interface.items_tree if x.item_type == 'SOCKET' and x.in_out == 'INPUT']
    for x in items:
        is_menu = x.socket_type == 'NodeSocketMenu'
        sub = getattr(x, 'subtype', 'NONE')
        G.input(x.name, x.socket_type, None if is_menu else getattr(x, 'default_value', None),
                getattr(x, 'min_value', None), getattr(x, 'max_value', None), x.description,
                subtype=None if sub in ('NONE', '') else sub)
    for m in material_inputs:
        G.input(m, 'NodeSocketMaterial')
    G.output('Geometry')
    G.finish_io()
    node = G.group(member)
    for x in items:
        G.link(G.i[x.name], node.inputs[x.name])
    geometry = node.outputs[0]
    if material_inputs:
        geometry = G.material(geometry, G.i[material_inputs[0]])
    G.link(G.shade(geometry, smooth), G.o['Geometry'])
    G.layout()
    G.defaults({x.name: x.default_value for x in items if x.socket_type == 'NodeSocketMenu'})
    if panels:
        G.panels({**panels, 'Surface': list(material_inputs)}, closed=closed)
    return G.g


def host(name, group, settings=None, *, location=(0, 0, 0), rotation=(0, 0, 0)):
    """A ready-made object: an empty mesh whose whole geometry is `group` (a modifier group)."""
    obj = bpy.data.objects.new(named(name), bpy.data.meshes.new(f'{name} • generated host'))
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    mod = obj.modifiers.new(name, 'NODES')
    mod.node_group = group
    for key, value in (settings or {}).items():
        set_input(mod, key, value)
    return obj


def export(filename, entries):
    """Write the family's asset file with exactly these data blocks (and what they depend on)."""
    path = ASSETS / filename
    bpy.data.libraries.write(str(path), set(entries), fake_user=True)
    return path


def load_into_fresh_scene(filename, objects):
    """Gallery helper: a fresh project appending objects from the SAVED file, as a user would."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(ASSETS / filename), link=False) as (src, dst):
        dst.objects = list(objects)
    loaded = {}
    for obj in dst.objects:
        bpy.context.scene.collection.objects.link(obj)
        obj.asset_clear()   # in a project, appended copies are ordinary objects
        loaded[obj.name] = obj
    return loaded
