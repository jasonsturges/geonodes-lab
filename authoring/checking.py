"""Check utilities: evaluate groups and objects, measure islands, append saved assets.

Checks import this, never the builders (docs/authoring.md). Nothing here writes to the repository.
"""
from pathlib import Path
import sys
import bpy
import bmesh

from .modifiers import set_input

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'


class Mesh:
    """An evaluated result: vertices, closure, signed volume, islands (each a list of vertices), materials."""

    def __init__(self, mesh):
        bm = bmesh.new()
        bm.from_mesh(mesh)
        self.verts = [tuple(v.co) for v in bm.verts]
        self.closed = all(e.is_manifold for e in bm.edges)
        self.volume = bm.calc_volume(signed=True) if bm.faces else 0.0
        parent = list(range(len(bm.verts)))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        for e in bm.edges:
            parent[find(e.verts[0].index)] = find(e.verts[1].index)
        groups = {}
        for v in bm.verts:
            groups.setdefault(find(v.index), []).append(tuple(v.co))
        self.islands = list(groups.values())
        self.faces = len(bm.faces)
        self.attributes = {a.name for a in mesh.attributes}
        self.uv_layers = [u.name for u in mesh.uv_layers]
        self.materials = {mesh.materials[p.material_index].name for p in mesh.polygons
                          if p.material_index < len(mesh.materials) and mesh.materials[p.material_index]}
        bm.free()

    def extent(self, axis):
        values = [v[axis] for v in self.verts]
        return (min(values), max(values)) if values else (0.0, 0.0)


def _evaluate(obj):
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        return Mesh(mesh)
    finally:
        evaluated.to_mesh_clear()


def evaluate_group(group_name, settings=None, *, links=None, output=0, as_points=False):
    """Run node group `group_name` with input `settings`; `links` = {input: object} feeds Object Info
    geometry. `as_points` converts a curve/points output to vertices (to read profiles and stations)."""
    g = bpy.data.node_groups.new('check probe', 'GeometryNodeTree')
    g.is_modifier = True
    g.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    node = g.nodes.new('GeometryNodeGroup')
    node.node_tree = bpy.data.node_groups[group_name]
    for key, value in (settings or {}).items():
        node.inputs[key].default_value = value
    for key, obj in (links or {}).items():
        info = g.nodes.new('GeometryNodeObjectInfo')
        info.inputs['Object'].default_value = obj
        g.links.new(info.outputs['Geometry'], node.inputs[key])
    out = node.outputs[output]
    if as_points:
        pts = g.nodes.new('GeometryNodeCurveToPoints')
        pts.mode = 'EVALUATED'
        g.links.new(out, pts.inputs[0])
        merge = g.nodes.new('GeometryNodeJoinGeometry')   # curves → points; points pass through
        g.links.new(pts.outputs[0], merge.inputs[0])
        g.links.new(out, merge.inputs[0])
        verts = g.nodes.new('GeometryNodePointsToVertices')
        g.links.new(merge.outputs[0], verts.inputs[0])
        out = verts.outputs[0]
    g.links.new(out, g.nodes.new('NodeGroupOutput').inputs[0])
    obj = bpy.data.objects.new('check probe', bpy.data.meshes.new('check probe'))
    bpy.context.scene.collection.objects.link(obj)
    obj.modifiers.new('probe', 'NODES').node_group = g
    try:
        return _evaluate(obj)
    finally:
        bpy.data.objects.remove(obj)
        bpy.data.node_groups.remove(g)


def evaluate_object(obj, settings=None):
    """Evaluate a ready-made object with temporary modifier settings (restored afterwards)."""
    mod = obj.modifiers[0]
    saved = {}
    from .modifiers import get_input
    for key, value in (settings or {}).items():
        saved[key] = get_input(mod, key)
        set_input(mod, key, value)
    try:
        return _evaluate(obj)
    finally:
        for key, value in saved.items():
            set_input(mod, key, value)


def evaluate_modifier(group_name, settings=None):
    """A temporary object running modifier group `group_name` with `settings` (objects allowed)."""
    obj = bpy.data.objects.new('check host', bpy.data.meshes.new('check host'))
    bpy.context.scene.collection.objects.link(obj)
    mod = obj.modifiers.new('check', 'NODES')
    mod.node_group = bpy.data.node_groups[group_name]
    for key, value in (settings or {}).items():
        set_input(mod, key, value)
    try:
        return _evaluate(obj)
    finally:
        bpy.data.objects.remove(obj)


def fresh_session_with(filename, *, objects=(), node_groups=()):
    """Append from the SAVED asset file into a fresh session that already holds an unrelated object,
    and confirm appending leaves the user's project intact. Returns {name: data block}."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mine = bpy.data.objects.new('My existing object', bpy.data.meshes.new('mine'))
    bpy.context.scene.collection.objects.link(mine)
    with bpy.data.libraries.load(str(ASSETS / filename), link=False, assets_only=True) as (src, dst):
        missing = [n for n in objects if n not in src.objects] + [n for n in node_groups if n not in src.node_groups]
        assert not missing, f'{filename} lacks {missing}'
        dst.objects = list(objects)
        dst.node_groups = list(node_groups)
    loaded = {}
    for obj in dst.objects:
        bpy.context.scene.collection.objects.link(obj)
        loaded[obj.name] = obj
    for group in dst.node_groups:
        loaded[group.name] = group
    assert bpy.data.objects.get(mine.name) is mine, 'appending must not disturb the project'
    assert not bpy.data.texts, 'asset files carry no text blocks'
    return loaded


def asset_listing(filename):
    """What a saved asset file offers as assets: {'objects': [...], 'node_groups': [...], 'materials': [...]}."""
    with bpy.data.libraries.load(str(ASSETS / filename), assets_only=True) as (src, _):
        return {'objects': list(src.objects), 'node_groups': list(src.node_groups), 'materials': list(src.materials)}


def report(family, cases):
    print(f'{family}: {cases} cases passed')


def panels_of(group):
    return [x.name for x in group.interface.items_tree if x.item_type == 'PANEL']
