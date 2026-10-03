# Masonry

**GNL • Brick Pier**, promoted from the NodesLab prototype's study 032, which
keeps its own copy. Source: the website graveyard's `BrickPierGeometry.ts`.

| Output | Contents |
| --- | --- |
| `assets/Masonry.blend` | Node group and object **GNL • Brick Pier**; materials **GNL • Brick • Clay**, **GNL • Mortar**, **GNL • Stone • Dressed**, **GNL • Stone • Plinth and Cap**. Catalog: GeoNodes Lab/Masonry |
| `examples/masonry/gallery.blend` | A fresh scene appending the pier, plus a decayed copy. [Guide](../../examples/masonry/README.md) |

Build with `python3 scripts/build.py masonry [--render]`.
Check with `python3 scripts/check.py masonry` (9 cases: brick for brick against the website's laying loop).

## Contract

- **Base at Z = 0**, centred, square shaft. The panels:
  - **Shaft**: Width, Height. Courses are fitted to the height.
  - **Bricks**: size, mortar (which adds to the pitch), Min Bat for closers, Brick Wander.
  - **Quoins**: long and short legs, Proud.
  - **Plinth and Cap.**
  - **Decay**: missing bricks, missing quoins, fallen cap, Decay Seed.
  - **Surface**: Seed and four materials.
- **Outputs:** *Geometry*, **Top** (the cap top, or the shaft top if the cap has fallen) and **Courses**.
  Assemblies use *Top* to seat things on the pier. The gateway stands its overthrow there.
- Bricks and quoins store a seeded **`tone`** (−1…1). The supplied brick and quoin materials read it.

## How it works

See the NodesLab prototype's study 032: one point per
possible brick slot, closed-form stretcher-bond arithmetic, **Delete Geometry** for slots the website's
loop would never lay, and a unit cube instanced and scaled into every brick.

A **Quoin Pattern** option (Alternating / Balanced / Straight) is planned with the walls-and-quoins work.
