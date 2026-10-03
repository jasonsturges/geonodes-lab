"""Masonry materials. Bricks and quoins store a seeded `tone` (-1…1) that these materials read."""
from authoring.naming import named
from authoring.presentation import principled


def toned(name, color, *, hue=.012, sat=.12, val=.18, roughness=.85):
    """A material whose color wanders with the per-part 'tone' attribute (-1…1)."""
    mat = principled(name, color, roughness=roughness)
    nt = mat.node_tree
    bsdf = nt.nodes['Principled BSDF']
    attr = nt.nodes.new('ShaderNodeAttribute')
    attr.attribute_name = 'tone'
    hsv = nt.nodes.new('ShaderNodeHueSaturation')
    hsv.inputs['Color'].default_value = (*color, 1)
    for socket, amount in (('Hue', hue), ('Saturation', sat), ('Value', val)):
        node = nt.nodes.new('ShaderNodeMath')
        node.operation = 'MULTIPLY_ADD'
        nt.links.new(attr.outputs['Fac'], node.inputs[0])
        node.inputs[1].default_value = amount
        node.inputs[2].default_value = .5 if socket == 'Hue' else 1.0
        nt.links.new(node.outputs[0], hsv.inputs[socket])
    nt.links.new(hsv.outputs['Color'], bsdf.inputs['Base Color'])
    return mat




def materials():
    """Website colors (sRGB) converted to linear; the limestone toned down for studio light."""
    brick = toned(named('Brick • Clay'), (.112, .042, .025))
    mortar = principled(named('Mortar'), (.023, .019, .018), roughness=.95)
    quoin = toned(named('Stone • Dressed'), (.46, .41, .32), hue=.004, sat=.05, val=.08, roughness=.7)
    stone = principled(named('Stone • Plinth and Cap'), (.34, .31, .26), roughness=.75)
    return brick, mortar, quoin, stone
