"""Wood materials: procedural grain from the members' `grain` attribute, with optional per-member `tint`."""
import bpy


def wood_material(name, light, dark, *, weathered=0.0):
    """Procedural grain driven by the 'grain' attribute (local, pre-warp position: X along the grain)."""
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = .85
    attr = nt.nodes.new('ShaderNodeAttribute')
    attr.attribute_name = 'grain'
    mapping = nt.nodes.new('ShaderNodeMapping')
    mapping.inputs['Scale'].default_value = (.35, 6, 6)   # long streaks along X
    nt.links.new(attr.outputs['Vector'], mapping.inputs['Vector'])
    wave = nt.nodes.new('ShaderNodeTexWave')
    wave.wave_type = 'RINGS'
    wave.rings_direction = 'X'
    wave.inputs['Scale'].default_value = 2.0
    wave.inputs['Distortion'].default_value = 6.0
    wave.inputs['Detail'].default_value = 4.0
    nt.links.new(mapping.outputs['Vector'], wave.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].color = (*light, 1)
    nt.links.new(wave.outputs['Fac'], ramp.inputs['Fac'])
    gray = nt.nodes.new('ShaderNodeMix')
    gray.data_type = 'RGBA'
    gray.inputs['Factor'].default_value = weathered
    # Optional per-member tint (-1…1) written by assemblies (e.g. a fence): 0 or absent = unchanged.
    tint = nt.nodes.new('ShaderNodeAttribute')
    tint.attribute_name = 'tint'
    shade = nt.nodes.new('ShaderNodeMath')
    shade.operation = 'MULTIPLY_ADD'
    nt.links.new(tint.outputs['Fac'], shade.inputs[0])
    shade.inputs[1].default_value = .3
    shade.inputs[2].default_value = 1.0
    darken = nt.nodes.new('ShaderNodeMix')
    darken.data_type = 'RGBA'
    darken.blend_type = 'MULTIPLY'
    darken.inputs['Factor'].default_value = 1.0
    nt.links.new(ramp.outputs['Color'], darken.inputs['A'])
    combine = nt.nodes.new('ShaderNodeCombineColor')
    for k in range(3):
        nt.links.new(shade.outputs[0], combine.inputs[k])
    nt.links.new(combine.outputs[0], darken.inputs['B'])
    nt.links.new(darken.outputs['Result'], gray.inputs['A'])
    gray.inputs['B'].default_value = (.13, .12, .11, 1)
    nt.links.new(gray.outputs['Result'], bsdf.inputs['Base Color'])
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .35
    nt.links.new(wave.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    mat.diffuse_color = (*[(a + b) / 2 for a, b in zip(light, dark)], 1)
    return mat
