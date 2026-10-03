"""Background-only authoring: builders reset their scene and overwrite their outputs."""
from pathlib import Path
import sys
import bpy

from .presentation import use_gpu


def require_background():
    if not bpy.app.background:
        raise RuntimeError('Run this builder in a background Blender process (scripts/build.py); '
                           'it resets its scene and overwrites generated output.')


def wants_render():
    return '--render' in sys.argv


def save_scene(path, *, readme=None, readme_title='READ ME', render=False, preview='preview.png'):
    """Save the current scene (embedding its README as a text block) and optionally render `preview`
    beside it (a second example in one folder uses e.g. 'room-preview.png')."""
    require_background()
    path = Path(path)
    if readme is not None and Path(readme).exists():
        bpy.data.texts.new(readme_title).write(Path(readme).read_text())
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    if render:
        scene = bpy.context.scene
        use_gpu(scene)
        scene.render.filepath = str(path.parent / preview)
        bpy.ops.render.render(write_still=True)


def save_study(directory, title):
    directory = Path(directory)
    save_scene(directory / 'study.blend', readme=directory / 'README.md', readme_title=title, render=wants_render())


def save_gallery(directory, title):
    directory = Path(directory)
    save_scene(directory / 'gallery.blend', readme=directory / 'README.md', readme_title=title, render=wants_render())
