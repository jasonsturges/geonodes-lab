# Blender gotchas

Each lesson here cost real debugging time and was confirmed by a check. Blender 5.2.

## Geometry Nodes

| Gotcha | Symptom | Fix |
| --- | --- | --- |
| **A Menu input can drive only one Menu Switch.** Each switch defines its own item list. | The menu socket has no items, and setting its default fails with `enum not found in ()` | One Menu Switch turns the menu into an **index**, and **Index Switches** pick per option everywhere after |
| **Transform scales before it rotates.** | A squash meant for one axis lands on a diagonal | Two Transform nodes: rotate in the first, scale in the second |
| **Fields re-evaluate on the geometry each node receives.** | After moving points, a later "is this above the level?" test sees the *moved* positions | Order operations deliberately (delete first, then move), or capture/store the value first |
| **Cone and Cylinder primitives:** the Cone spans Z 0…Depth (it's not centred). | Things sit half a unit off | Translate explicitly, and say which convention you rely on |
| **An open 360° arc as a lathe path tilts its end copies.** An open curve's end tangent follows its last segment. | A pinhole or hairline gap at the axis | Use a closed **Curve Circle**, and compute a UV seam separately |
| **Curve to Mesh** puts the profile's X along the path normal and its Y along −Z for a circle in XY. Faces come out wound inward for a lathe. | Negative volume, inside-out shading | Feed `(radius − 1, −height)` on a unit circle, then **Flip Faces** |
| **Extrude Mesh (faces) moves the face** rather than copying it. | An open plate | Join the original face back (flipped) and **Merge by Distance** |
| **Spline Parameter → Factor is by length.** | A taper reaches its thinnest too early on spirals | Use **Index ÷ count** when the design tapers by station |
| **Fitting a scroll scales its bar too.** | Heavy black "blobs" | Measure the natural size (**Bounding Box**) and pre-shrink the bar |
| **Mirroring a curve keeps a Z-Up frame right-handed**, so no face flip is needed. Mirroring a *mesh* by −1 turns it inside out. | Inside-out mirrored copies | Mirror the path, not the mesh |
| **Fill Curve / Extrude** options are input sockets now (e.g. `inputs['Mode']`), not properties. | `AttributeError: 'mode'` | Set the socket's default value |

## Python authoring

| Gotcha | Fix |
| --- | --- |
| `bpy.data.libraries.load(...)` **replaces the items of the list you pass** with the loaded data blocks | Pass a copy: `dst.objects = list(names)` |
| A **panel and a socket can share a name** (e.g. "Infill"); `interface.items_tree[name]` may return the panel | Look sockets up by `item_type == 'SOCKET'` |
| A Menu socket's default can't be set until it's wired to its switch | Set menu defaults after linking (and after `interface_update`) |
| `bl_socket_idname` includes the subtype (e.g. `NodeSocketFloatAngle`), which `new_socket` rejects | Use `socket_type`, and pass `subtype` separately |
| Shader colors are **linear**; web and SDK hex colors are **sRGB** | Convert (e.g. `#654029` ≈ linear 0.127, 0.051, 0.022), or the material looks washed out |
| Background builds use `--factory-startup`, which ignores user preferences (GPU devices too) | Enable Metal devices in the builder before rendering (`authoring.presentation.use_gpu`) |

## Viewport

| Gotcha | Fix |
| --- | --- |
| Material Preview lights scenes with a built-in forest HDRI, which glass and metal reflect | Shading popover → **Scene World** and **Scene Lights** (our scenes set this) |
| EEVEE's screen-space refraction dims what's seen through two layers of glass | Use Cycles (**Rendered**) to judge glass |
