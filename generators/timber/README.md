# Timber

Two seeded wood members, promoted from the NodesLab prototype's study 028,
which also keeps the exact SDK ports. Sources: three-low-poly `WeatheredPlankGeometry` and
`createHewnTimberGeometry`.

| Output | Contents |
| --- | --- |
| `assets/Timber.blend` | Node groups **GNL • Weathered Plank** and **GNL • Hewn Timber**; ready-made objects of the same names; materials **GNL • Wood • Rough-Sawn / Weathered / Hewn**. Catalog: GeoNodes Lab/Timber |
| `examples/timber/gallery.blend` | A fresh scene appending them: seeded copies sharing one node group. [Guide](../../examples/timber/README.md) |

Build with `python3 scripts/build.py timber [--render]`.
Check with `python3 scripts/check.py timber` (14 cases). `build.py` (with `members.py`, `materials.py`) is the source of truth.

## Contract

- **GNL • Weathered Plank**: a rough-sawn board, long axis **X**, centered at the origin. The panels:
  - **Size**: Length, Width, Thickness
  - **Resolution**: segments
  - **Variation**: Seed, Edge Roughness, End Skew, Surface
  - **Warp**: Bow, Crook, Cup, Twist, and Randomize Warp
- **GNL • Hewn Timber**: an axe-hewn log, **Z up**, butt at Z = 0. The panels:
  - **Size**: Length, Diameter, Taper
  - **Resolution**: Facets, Rings
  - **Variation**: Seed, Facet Variation, Irregularity
  - **Warp**: Bow, Twist, and Randomize Warp
- Both output a closed mesh with a `UVMap` and a **`grain`** vector: the pre-warp local position, with X along
  the grain. The wood materials read `grain`, so the texture follows a member through warping, instancing
  and joining. They also read an optional float **`tint`** (−1…1) that an assembly can write per member.
- With **Randomize Warp** off, each warp is exact. Bow, Crook and Cup are metres at mid-length (Cup is at the
  edges). Twist is the end-to-end angle, applied linearly.

## How it works

Each member is one primitive (**Cube** or **Cone**) moved by a single **Set Position**. The position is
built from fields:

- **Where am I?** `x / (Length/2)` runs −1…1 along the board, and `(1 − x²)` is 0 at the ends and 1 at
  mid-length. That is the shape of a bow or a crook.
- **What's my noise?** A **Noise Texture** in 4D, with W = Seed, gives smooth seeded wander: each long edge
  samples its own strip of noise. **White Noise** gives per-thing random values, e.g. one random amount
  per warp, or one per log facet (the facet index comes from the vertex's angle).
- **Twist** rotates each cross-section about the long axis by an angle that grows along the length.

The objects add a material and shading. The plank object also has a **Bevel** modifier for worn edges,
stacked after the node modifier. It's ordinary Blender, and you can turn it off or tune it.
