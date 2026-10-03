"""Opt-in scene presentation for studies and examples (first used by study 027 / vessels).

A light floor, flat text labels, a three-light gray studio, a framed camera, Material
Preview lit by the scene (not Blender's default forest HDRI) and Cycles previews on the
Mac GPU. Modeling assets never depend on this module.
"""
from mathutils import Vector
import bpy


def principled(name, color, *, roughness=0.5, metallic=0.0, glass=False, alpha=None):
    """A Principled material whose viewport (Solid mode) color matches its base color."""
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    if glass:
        bsdf.inputs['Transmission Weight'].default_value = 1.0
        bsdf.inputs['IOR'].default_value = 1.45
        mat.use_raytrace_refraction = True
        mat.thickness_mode = 'SLAB'
    mat.diffuse_color = (*color, alpha if alpha is not None else (.25 if glass else 1))
    return mat


def label(text, location, *, size=0.18, material=None, collection=None):
    """Flat text lying on the floor, centered under an object."""
    data = bpy.data.curves.new(text, 'FONT')
    data.body = text
    data.size = size
    data.align_x = 'CENTER'
    if material is None:
        material = bpy.data.materials.get('Label ink') or principled('Label ink', (.06, .07, .09), roughness=.8)
    data.materials.append(material)
    obj = bpy.data.objects.new(f'Label • {text}', data)
    (collection or bpy.context.scene.collection).objects.link(obj)
    obj.location = location
    obj.hide_select = True
    return obj


def studio(scene, *, camera_location, target, lens=45, floor_color=(.55, .56, .58), samples=64,
           resolution=(1800, 1000), light_scale=1.0):
    """Gray world, key/fill/rim area lights, a floor, a camera and viewport defaults."""
    world = bpy.data.worlds.new('Studio')
    if world.node_tree is None:
        world.use_nodes = True
    background = world.node_tree.nodes['Background']
    background.inputs['Color'].default_value = (.32, .34, .38, 1)
    background.inputs['Strength'].default_value = .6
    world.color = (.32, .34, .38)
    scene.world = world
    for name, loc, energy, size in [('Key', (6, -9, 9), 2500, 6), ('Fill', (-9, -4, 5), 800, 8),
                                    ('Rim', (0, 9, 7), 1500, 6)]:
        light = bpy.data.objects.new(name, bpy.data.lights.new(name, 'AREA'))
        light.data.energy, light.data.size = energy * light_scale ** 2, size * light_scale
        scene.collection.objects.link(light)
        light.location = Vector(loc) * light_scale
        light.rotation_euler = (-light.location).to_track_quat('-Z', 'Y').to_euler()
    floor = bpy.data.objects.new('Floor', bpy.data.meshes.new('Floor'))
    floor.data.from_pydata([(-30, -30, 0), (30, -30, 0), (30, 30, 0), (-30, 30, 0)], [], [(0, 1, 2, 3)])
    floor.data.materials.append(principled('Floor', floor_color, roughness=.6))
    floor.hide_select = True
    scene.collection.objects.link(floor)
    cam = bpy.data.objects.new('Camera', bpy.data.cameras.new('Camera'))
    scene.collection.objects.link(cam)
    cam.location = camera_location
    cam.rotation_euler = (Vector(target) - Vector(camera_location)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    scene.camera = cam
    scene.eevee.use_raytracing = True
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = resolution
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                shading = area.spaces.active.shading
                shading.type = 'MATERIAL'
                shading.use_scene_world = True  # not Blender's default forest HDRI
                shading.use_scene_lights = True
                area.spaces.active.region_3d.view_perspective = 'CAMERA'
            elif area.type == 'PROPERTIES':
                area.spaces.active.context = 'MODIFIER'
    return cam


def use_gpu(scene):
    """Render on the Mac GPU (Metal) when available; preferences are not saved in the file."""
    prefs = bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type = 'METAL'
        prefs.get_devices()
        for device in prefs.devices:
            device.use = True
        scene.cycles.device = 'GPU'
    except TypeError:
        pass
