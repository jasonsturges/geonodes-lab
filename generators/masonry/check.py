"""Independent checks for assets/Masonry.blend (study 032's checks, on the saved asset). Never imports build.py.

The brick layout is compared with a plain-Python transcription of the website's laying loop
(BrickPierGeometry.ts): per face and course, the exact multiset of brick lengths. Quoins,
coursing, heights and decay are measured on mesh islands.

Run: python3 scripts/check.py masonry
"""
from pathlib import Path
from collections import Counter
import math
import sys
import bpy
import bmesh

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from authoring.modifiers import set_input  # noqa: E402

GROUP = 'GNL • Brick Pier'
DEFAULTS = dict(w=.9, h=2.6, b=.3, bh=.1, d=.12, m=.014, bat=.25, long=.3, short=.18, proud=.025,
                pw=1.2, ph=.5, cw=1.35, ch=.3)


def website_bricks(w, h, b, bh, m, bat, long, short, **_):
    """The website's loop: returns (courses, gauge, Counter of rounded brick lengths over 4 faces)."""
    courses = max(1, round(h / (bh + m)))
    gauge = h / courses
    lengths = Counter()
    for _face in range(4):
        for c in range(courses):
            start_leg = long if c % 2 == 0 else short
            end_leg = short if c % 2 == 0 else long
            x, to = start_leg + m, w - end_leg - m
            first = c % 2 == 1
            while x < to - 1e-6:
                remaining = to - x
                length = b / 2 if first else b
                first = False
                if remaining < length + 1e-6:
                    length = remaining
                    if length < b * bat:
                        break
                lengths[round(length, 4)] += 1
                x += length + m
    return courses, gauge, lengths


def parts(settings):
    obj = bpy.data.objects.new('check pier', bpy.data.meshes.new('check pier'))
    bpy.context.scene.collection.objects.link(obj)
    mod = obj.modifiers.new('pier', 'NODES')
    mod.node_group = bpy.data.node_groups[GROUP]
    for key, value in settings.items():
        set_input(mod, key, value)
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    assert all(e.is_manifold for e in bm.edges), 'every stone and brick is a closed box'
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
    bm.free()
    evaluated.to_mesh_clear()
    bpy.data.objects.remove(obj)
    return list(groups.values())


def size(part):
    return tuple(max(p[k] for p in part) - min(p[k] for p in part) for k in range(3))


NAMES = {'w': 'Width', 'h': 'Height', 'b': 'Brick Length', 'bh': 'Brick Height', 'd': 'Brick Depth',
         'm': 'Mortar', 'bat': 'Min Bat', 'long': 'Long Leg', 'short': 'Short Leg', 'proud': 'Proud',
         'pw': 'Plinth Width', 'ph': 'Plinth Height', 'cw': 'Cap Width', 'ch': 'Cap Height'}


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mine = bpy.data.objects.new('My object', bpy.data.meshes.new('mine'))
    bpy.context.scene.collection.objects.link(mine)
    with bpy.data.libraries.load(str(ROOT / 'assets/Masonry.blend'), link=False, assets_only=True) as (src, dst):
        assert src.objects == ['GNL • Brick Pier'] and 'GNL • Brick Pier' in src.node_groups, (src.objects, src.node_groups)
        assert len(src.materials) == 4, src.materials
        dst.node_groups = ['GNL • Brick Pier']
    assert bpy.data.objects.get(mine.name) is mine and not bpy.data.texts
    cases = 0
    variants = [{}, {'w': .65, 'h': 3.2, 'b': .4, 'long': .26, 'short': .14},
                {'w': 1.3, 'h': 1.4, 'b': .22, 'bh': .07, 'long': .36, 'short': .2},
                {'w': 1.0, 'h': 2.0, 'b': .25, 'bat': .6}, {'w': .5, 'h': 1.0, 'b': .3, 'long': .2, 'short': .12}]
    for v in variants:
        o = {**DEFAULTS, **v}
        settings = {NAMES[k]: val for k, val in o.items()} | {'Brick Wander': 0.0}
        ps = parts(settings)
        courses, gauge, expected = website_bricks(**o)
        brick_h = gauge - o['m']
        bricks = [p for p in ps if abs(size(p)[2] - brick_h) < 1e-5]
        quoins = [p for p in ps if abs(size(p)[2] - gauge * .96) < 1e-5]
        # A brick's length runs along its face: X on the front/back faces, Y on the sides.
        def along(p):
            cx = sum(q[0] for q in p) / len(p)
            cy = sum(q[1] for q in p) / len(p)
            return size(p)[0] if abs(cy) > abs(cx) else size(p)[1]
        got = Counter(round(along(p), 4) for p in bricks)
        assert got == expected, (v, sorted(got.items()), sorted(expected.items()))
        assert len(quoins) == 4 * courses, (len(quoins), courses)
        for p in quoins:   # outer corner stands Proud beyond both faces; legs are long × short
            xs, ys = [q[0] for q in p], [q[1] for q in p]
            assert abs(max(map(abs, xs)) - (o['w'] / 2 + o['proud'])) < 1e-5
            assert abs(max(map(abs, ys)) - (o['w'] / 2 + o['proud'])) < 1e-5
            assert sorted(round(x, 4) for x in size(p)[:2]) == sorted([round(o['long'], 4), round(o['short'], 4)])
        top = max(q[2] for p in ps for q in p)
        assert abs(top - (o['ph'] + o['h'] + o['ch'])) < 1e-5, top
        cases += 1
    # Alternation round the pier: at course 0 each corner's longer leg lies along the face it starts.
    ps = parts({'Brick Wander': 0.0})
    gauge = 2.6 / round(2.6 / .114)
    first = [p for p in ps if abs(size(p)[2] - gauge * .96) < 1e-5 and min(q[2] for q in p) < .5 + gauge]
    along_x = sum(1 for p in first if size(p)[0] > size(p)[1])
    assert len(first) == 4 and along_x == 2, 'two corners long on X faces, two on Y faces'
    cases += 1
    # Decay: bricks and quoins vanish, the cap can fall, and decay never moves what remains.
    base = parts({})
    none = parts({'Missing Bricks': 1.0, 'Missing Quoins': 1.0})
    assert len(none) == 1 + 4, 'only the mortar core and the four stone pieces remain'
    some, other = parts({'Missing Bricks': .3, 'Decay Seed': 2}), parts({'Missing Bricks': .3, 'Decay Seed': 3})
    keep = lambda ps: {tuple(sorted(p)) for p in ps}
    assert keep(some) <= keep(base) and keep(other) <= keep(base) and keep(some) != keep(other)
    capless = parts({'Missing Cap': True})
    assert max(q[2] for p in capless for q in p) <= .5 + 2.6 + 1e-5
    cases += 3
    print(f'Masonry: {cases} cases passed')


main()
