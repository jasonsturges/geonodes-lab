# Fences

Promoted from the NodesLab prototype's study 029 (rustic fence),
the NodesLab prototype's study 031 (iron fence) and
the NodesLab prototype's study 036 (gateway). Each study keeps its own copy.

| Output | Contents |
| --- | --- |
| `assets/Fences.blend` | Objects and node groups **GNL • Rustic Fence**, **GNL • Iron Fence**, **GNL • Gateway**, plus the shared **GNL • Path Stations** group. Dependencies travel inside: GNL • Hewn Timber, GNL • Panel / Post / Overthrow, GNL • Brick Pier and their materials. Catalog: GeoNodes Lab/Fences |
| `examples/fences/gallery.blend` | A fresh scene appending all three, with the fences on your own curves over rolling ground. [Guide](../../examples/fences/README.md) |

Build with `python3 scripts/build.py fences [--render]`.
Check with `python3 scripts/check.py fences` (32 cases). `build.py` is the source of truth. It appends
the timber, ironwork and masonry assets, so rebuild those first after changing them.

## Contract

- **GNL • Path Stations** (node group): Path (curve geometry; empty = a straight run along X), Spacing,
  Ground (mesh geometry), Jitter, Seed → **Stations** (points with `tangent` and `side`), **Closed** and
  **Count**. Stations divide the path evenly, and a closed path shares its seam station. It's the shared
  core of both fences, and it's ready for anything set out along a path: lamp posts, bollards, trees.
- **GNL • Rustic Fence:** panels Path, Posts, Rails, Decay and Surface. Every post and rail is its own
  seeded GNL • Hewn Timber. Decay has its own seed, and never moves intact members.
- **GNL • Iron Fence:** panels Path, Panels, Posts, Decay and Surface. Panels rake to the slope or step
  level. Seeded derelict panels rust, sag and lose pickets.
- **GNL • Gateway:** origin at the opening centre, on the ground. Two GNL • Brick Piers, GNL • Overthrow on
  their **Top**, and two hinged GNL • Panel leaves. One **Ruin** control ages everything from one seed.
- Path and Ground are **object** inputs on the fences: pick any curve and any mesh in your scene.

## How it works

The studies' READMEs explain each piece:
- 029: For Each zones for unique logs,
  rails between sampled stations.
- 031: instanced posts, per-bay panels, rake.
- 036: seating on outputs, hinges,
  menu pass-through, Ruin.

What promotion added is **GNL • Path Stations**. Both fences previously carried their own copy of the
station logic, and now they call one group.

**Note on appending:** if you append GNL • Panel from `Ironwork.blend` *and* a fence from `Fences.blend`
into the same project, Blender keeps both copies (the second named `GNL • Panel.001`). That's harmless.
They're the same group from two files.
