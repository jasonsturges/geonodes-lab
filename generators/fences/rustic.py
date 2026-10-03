"""GNL • Rustic Fence: a split-rail fence along any curve; every post and rail is its own seeded
GNL • Hewn Timber (NodesLab study 029)."""
import math

import bpy

from authoring.graph import Graph
from authoring.naming import named
from common import rand, unit, foreach, generation, transform, rand1
from stations import stations


def rustic_fence_group(timber, stations_group):
    G = Graph(named('Rustic Fence'), modifier=True)
    G.stations_group = stations_group
    G.input('Geometry', 'NodeSocketGeometry')
    spec = [
        ('Path', [('Path', 'NodeSocketObject', None, None, None, 'A curve object (open or closed). Empty = a straight run.'),
                  ('Run Length', 'NodeSocketFloat', 9.6, .5, 100.0, 'Straight run length when no Path is set.'),
                  ('Bay Length', 'NodeSocketFloat', 2.4, .5, 10.0, 'Target post spacing; posts divide the path evenly.'),
                  ('Ground', 'NodeSocketObject', None, None, None, 'Optional mesh: posts drop onto it.')]),
        ('Posts', [('Post Height', 'NodeSocketFloat', 1.65, .3, 5.0, 'Above ground.'),
                   ('Post Diameter', 'NodeSocketFloat', .22, .03, 1.0, ''),
                   ('Height Variation', 'NodeSocketFloat', .07, 0.0, .5, 'Fraction of Post Height.'),
                   ('Lean', 'NodeSocketFloat', .045, 0.0, .5, 'Maximum tilt (radians).'),
                   ('Jitter', 'NodeSocketFloat', .055, 0.0, .5, 'How far posts stray from even spacing (metres).'),
                   ('Bury', 'NodeSocketFloat', .1, 0.0, 1.0, 'Depth below ground.'),
                   ('Facets', 'NodeSocketInt', 7, 3, 16, 'Axe faces on every log.')]),
        ('Rails', [('Rail Count', 'NodeSocketInt', 3, 1, 6, ''),
                   ('Bottom Rail', 'NodeSocketFloat', .3, 0.0, 1.0, 'Lowest rail, fraction of each post height.'),
                   ('Top Rail', 'NodeSocketFloat', .8, 0.0, 1.0, 'Highest rail, fraction of each post height.'),
                   ('Rail Diameter', 'NodeSocketFloat', .16, .02, 1.0, ''),
                   ('Overlap', 'NodeSocketFloat', .7, 0.0, 3.0, 'Rail overrun past each post, × rail diameter.'),
                   ('Alternate Sides', 'NodeSocketBool', True, None, None, 'Rails cross from the front of one post to the back of the next.'),
                   ('Rail Jitter', 'NodeSocketFloat', .035, 0.0, .3, 'Vertical wander at each rail end (metres).')]),
        ('Decay', [('Decay Seed', 'NodeSocketInt', 1, 0, 65535, 'Independent of Seed: change the ruin, keep the fence.'),
                   ('Missing Rails', 'NodeSocketFloat', 0.0, 0.0, 1.0, 'Chance each rail is gone.'),
                   ('Dropped Rails', 'NodeSocketFloat', 0.0, 0.0, 1.0, 'Chance a rail has fallen at one end.'),
                   ('Extra Lean', 'NodeSocketFloat', 0.0, 0.0, .6, 'Additional tilt for decaying posts (radians).')]),
        ('Surface', [('Seed', 'NodeSocketInt', 0xF3CE, 0, 65535, 'Layout and every log.'),
                     ('Post Material', 'NodeSocketMaterial', None, None, None, ''),
                     ('Rail Material', 'NodeSocketMaterial', None, None, None, '')]),
    ]
    for _, items in spec:
        for name, kind, default, lo, hi, text in items:
            G.input(name, kind, default, lo, hi, text)
    G.output('Geometry')
    G.finish_io()
    i = G.i
    seed, dseed = i['Seed'], i['Decay Seed']

    # --- Stations: GNL • Path Stations spaces, jitters and grounds them; each post then gets its numbers.
    posts, closed = stations(G, i, spacing=i['Bay Length'], jitter=i['Jitter'], seed=seed)
    idx = G.index
    height = G.mul(i['Post Height'], G.add(1, G.mul(i['Height Variation'], rand(G, idx, 3, seed))))
    posts = G.store(posts, 'height', height)
    decaying = G.mul(i['Extra Lean'], unit(G, idx, 4, dseed))
    lean = G.xyz(G.add(G.mul(i['Lean'], rand(G, idx, 5, seed)), G.mul(decaying, rand(G, idx, 6, dseed))),
                 G.add(G.mul(i['Lean'], rand(G, idx, 7, seed)), G.mul(decaying, rand(G, idx, 8, dseed))),
                 G.mul(math.pi, rand(G, idx, 9, seed)))
    posts = G.store(posts, 'lean', lean, kind='FLOAT_VECTOR')
    posts = G.store(posts, 'diameter', G.mul(i['Post Diameter'], G.add(1, G.mul(.1, rand(G, idx, 10, seed)))))

    # --- One log per post. -------------------------------------------------------------------------
    zin, zout = foreach(G, posts, 'post')
    k = zin.outputs['Index']
    log = G.group(timber, 'Post log')
    G.link(G.add(G.sample(posts, G.named('height'), k, kind='FLOAT'), i['Bury']), log.inputs['Length'])
    G.link(G.sample(posts, G.named('diameter'), k, kind='FLOAT'), log.inputs['Diameter'])
    G.link(G.add(G.mul(seed, 7), k), log.inputs['Seed'])
    G.link(i['Facets'], log.inputs['Facets'])
    sink = G.n('GeometryNodeTransform', 'Bury')
    G.link(log.outputs[0], sink.inputs['Geometry'])
    G.link(G.xyz(0, 0, G.mul(i['Bury'], -1)), sink.inputs['Translation'])
    stand = G.n('GeometryNodeTransform', 'Lean, then stand at the station')
    G.link(sink.outputs[0], stand.inputs['Geometry'])
    G.link(G.sample(posts, G.named('lean', 'FLOAT_VECTOR'), k), stand.inputs['Rotation'])
    G.link(G.sample(posts, G.position(), k), stand.inputs['Translation'])
    member = G.store(stand.outputs[0], 'tint', rand(G, k, 11, seed))
    G.link(member, generation(zout))
    post_logs = zout.outputs[2]

    # --- Rails: n per bay, each spanning post a → post b. ------------------------------------------
    n = i['Rail Count']
    size = G.n('GeometryNodeAttributeDomainSize', 'Post count', component='POINTCLOUD')
    G.link(posts, size.inputs[0])
    p_count = size.outputs['Point Count']
    spans = G.sub(p_count, G.sub(1, closed))
    rails = G.points(G.mul(spans, n), (0, 0, 0))
    r_idx = G.index
    missing = G.m('LESS_THAN', unit(G, r_idx, 21, dseed), i['Missing Rails'])
    zin, zout = foreach(G, rails, 'rail')
    G.link(G.m('SUBTRACT', 1, missing), zin.inputs['Selection'])
    k = zin.outputs['Index']
    bay = G.m('FLOOR', G.div(k, n))
    level = G.m('FLOORED_MODULO', k, n)
    a, b = bay, G.m('FLOORED_MODULO', G.add(bay, 1), p_count)
    pa, pb = G.sample(posts, G.position(), a), G.sample(posts, G.position(), b)
    ha = G.sample(posts, G.named('height'), a, kind='FLOAT')
    hb = G.sample(posts, G.named('height'), b, kind='FLOAT')
    sa = G.sample(posts, G.named('side', 'FLOAT_VECTOR'), a)
    sb = G.sample(posts, G.named('side', 'FLOAT_VECTOR'), b)
    step = G.div(G.sub(i['Top Rail'], i['Bottom Rail']), G.hi(G.sub(n, 1), 1))
    frac = G.switch('FLOAT', G.m('GREATER_THAN', n, 1), G.mul(G.add(i['Top Rail'], i['Bottom Rail']), .5),
                    G.add(i['Bottom Rail'], G.mul(level, step)))
    flip = G.sub(G.mul(G.m('FLOORED_MODULO', G.add(bay, level), 2), 2), 1)   # -1, +1 alternating
    offset = G.mul(G.mul(G.switch('FLOAT', i['Alternate Sides'], 0.0, flip), i['Post Diameter']), .34)
    start = G.v('ADD', G.v('ADD', pa, G.xyz(0, 0, G.add(G.mul(ha, frac), G.mul(i['Rail Jitter'], rand(G, k, 22, seed))))),
                G.v('SCALE', sa, scale=offset))
    end = G.v('ADD', G.v('ADD', pb, G.xyz(0, 0, G.add(G.mul(hb, frac), G.mul(i['Rail Jitter'], rand(G, k, 23, seed))))),
              G.v('SCALE', sb, scale=G.mul(offset, -1)))
    # Decay: a dropped rail rests one end on the ground beside its post.
    dropped = G.m('LESS_THAN', unit(G, k, 24, dseed), i['Dropped Rails'])
    which = G.m('GREATER_THAN', unit(G, k, 25, dseed), .5)
    sxa, sya, _ = G.sep(start)
    exa, eya, _ = G.sep(end)
    _, _, za = G.sep(pa)
    _, _, zb = G.sep(pb)
    rest = G.mul(i['Rail Diameter'], .5)
    start = G.switch('VECTOR', G.m('MULTIPLY', dropped, G.sub(1, which)), start, G.xyz(sxa, sya, G.add(za, rest)))
    end = G.switch('VECTOR', G.m('MULTIPLY', dropped, which), end, G.xyz(exa, eya, G.add(zb, rest)))
    direction = G.v('NORMALIZE', G.v('SUBTRACT', end, start))
    over = G.mul(i['Overlap'], i['Rail Diameter'])
    span = G.add(G.v('DISTANCE', start, end), G.mul(over, 2))
    log = G.group(timber, 'Rail log')
    G.link(span, log.inputs['Length'])
    G.link(G.mul(i['Rail Diameter'], G.add(1, G.mul(.12, rand(G, k, 26, seed)))), log.inputs['Diameter'])
    G.link(G.add(G.add(G.mul(seed, 13), k), 1000), log.inputs['Seed'])
    G.link(i['Facets'], log.inputs['Facets'])
    log.inputs['Taper'].default_value = .05
    align = G.n('FunctionNodeAlignRotationToVector', 'Point the log along the rail', axis='Z')
    G.link(direction, align.inputs['Vector'])
    lay = G.n('GeometryNodeTransform', 'Lay the rail')
    G.link(log.outputs[0], lay.inputs['Geometry'])
    G.link(align.outputs['Rotation'], lay.inputs['Rotation'])
    G.link(G.v('SUBTRACT', start, G.v('SCALE', direction, scale=over)), lay.inputs['Translation'])
    member = G.store(lay.outputs[0], 'tint', rand(G, k, 27, seed))
    G.link(member, generation(zout))
    rail_logs = zout.outputs[2]

    # --- Materials, flat low-poly shading, done. -----------------------------------------------------
    def finish(geometry, material):
        node = G.n('GeometryNodeSetMaterial', 'Material')
        G.link(geometry, node.inputs['Geometry'])
        G.link(material, node.inputs['Material'])
        return node.outputs[0]
    fence = G.join(finish(post_logs, i['Post Material']), finish(rail_logs, i['Rail Material']))
    flat = G.n('GeometryNodeSetShadeSmooth', 'Flat facets')
    G.link(fence, flat.inputs['Mesh'])
    flat.inputs['Shade Smooth'].default_value = False
    G.link(flat.outputs[0], G.o['Geometry'])
    G.layout()
    for title, items in spec:
        panel = G.g.interface.new_panel(name=title, default_closed=title == 'Decay')
        for name, *_ in items:
            G.g.interface.move_to_parent(G.g.interface.items_tree[name], panel, 100)
    G.g.description = 'Split-rail fence along any curve: seeded hewn posts and rails, ground drop, seeded decay.'
    return G.g
