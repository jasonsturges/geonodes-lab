# Floors

Floor generators from three-low-poly's `factory/floors`. First: **GNL • Hardwood Floor**, with seeded
boards laid at any angle and clipped to a rectangular room. Plank, flagstone and hexagonal tile floors
belong here next.

| Output | Contents |
| --- | --- |
| `assets/Floors.blend` | Object and node group **GNL • Hardwood Floor** (plus its internal laying and offcut groups), and **GNL • Hardwood • Board tint**. Catalog: GeoNodes Lab/Floors |
| `examples/floors/gallery.blend` | One room laid straight, diagonally and across. [Guide](../../examples/floors/README.md) |

```sh
python3 scripts/build.py floors --render
python3 scripts/check.py floors
```

Modules: `hardwood.py` (Floor Laying, Resolve Floor Offcuts, Hardwood Floor) and `graph.py`.

**Origin and level:** the room is centred on the origin, and the boards' **top surface is Z = 0** (finished
floor level). Boards hang below it by their thickness.

## Construction

The public group presents application controls and calls its construction group.
Inside, **GNL • Floor Laying** computes placements on a sheet large enough to cover
the rotated room. A Repeat Zone tracks the current row, cursor and neighboring
row's joints. Each step considers 24 seeded lengths and chooses the first candidate
that reaches the capped stagger target, or the best available candidate. Native
Geometry Proximity measures the distance to neighboring joints.

A For Each Geometry Element zone constructs each board separately, rotates it,
and intersects it with the rectangular room using native Exact Mesh Boolean.
This introduces corner topology as required, including multi-facet ends. A
1e-6-unit Merge by Distance inside each board cleans coincident intersections.
It never welds adjacent boards together. A preliminary clipping pass measures
each original footprint. Pieces below Min Sliver Area are assigned to the nearest
retained board in the same row; that board extends over their run before final
clipping. Thus a tiny wall-end triangle does not leave a missing wedge. Only
small pieces with no retained board in their row are discarded. Numerical
zero-area pieces (≤1e-8 square units) are always omitted. The retained closed
board solids are joined into one object. Absorbed pieces inherit their owner's
color and ID. This intentionally improves on the SDK's discard-only policy.

Board widths adjust to fit an integer number of rows. Row gaps include a half-gap
at the two covering-sheet margins. A shortened first board starts each row; a
remainder below the minimum is absorbed into its predecessor. Consequently a
starter may be below Shortest Board, and the final board may exceed Longest Board.
Lengths are absolute; increasing room size adds boards.

Stagger is a target, capped at half the difference between longest and shortest
lengths. The graph reports the actual closest distance between neighboring-row
internal joints **on the covering sheet**, before wall cuts and sliver removal.
A zero target removes the clearance preference; it does not force a grid.

## Public inputs

All dimensions are Blender units. The floor is centered in XY; its top is Z=0
and underside is Z=−Thickness. Rotation is around Z, with zero running along X.

| Controls | Default | Supported UI range / meaning |
| --- | --- | --- |
| Room Width / Depth | 5 / 4 | 1.5–10 each; rectangular room |
| Rotation | 45° | Any orientation in ±360° |
| Board Width | 0.2 | 0.08–0.5; nominal width, fitted width is reported |
| Thickness | 0.055 | 0.02–0.2 |
| Row Gap | 0.012 | 0–0.03; no extra butt-joint gap |
| Shortest / Longest Board | 0.5 / 1.4 | 0.2–3 / 0.3–4; accepts either order and clamps to run |
| Stagger Target | 0.35 | 0–1.5; bounded-search target |
| Min Sliver Area | 0.004 | 0–0.05; absorb small pieces into a retained board in the same row, otherwise discard |
| Layout Seed | 20907 | 0–65535; repeatable layout |
| Color Seed | 17 | 0–65535; independent per-board color |
| Color A / B | Warm Brown endpoints | Linear-RGB interpolation between editable colors |
| Use Base Color Variation | Off | Switch from endpoints to HSL offsets |
| Base Color / Color Variance | #6b4b2c / 0.06 | HSL spread; hue varies by one-third the S/L spread |
| Material | Included board-tint material | Replace with a material using the documented attributes |

Outputs: Geometry, Board Count, Row Count, Actual Board Width, Closest Joint,
Sliver Count, Clipped Count and Absorbed Count. Sliver Count counts actual discarded
pieces; Absorbed Count counts pieces incorporated into neighboring boards.
Counts and diagnostics are available to wrapper
graphs through sockets. They are not automatic text fields in the modifier panel.
Clipped Count measures retained boards whose footprint area was reduced by a wall,
including cuts that still leave four sides. It does not infer cuts from vertex count.
Boundary absorption can extend a board beyond the ordinary length range. Closest
Joint still describes the original covering-sheet layout, not the finished
boundary-adjusted joints. Color identity is retained, while an extended board's
UV origin can shift to its new end.

UI ranges define this release's operating envelope. Programmatically injected
values outside it are unsupported. Dimensions interact: extreme combinations
create thousands of boards and take longer to evaluate. There is no arbitrary
room outline, concave boundary, hole, floor trim, bevel or timber deformation in
this release. Separate touching solids intentionally retain internal mating faces.

## Randomness and application interfaces

Explicit native Random Value seeds and stable laying-sequence IDs make fixed
inputs repeatable in the tested Blender version. Changing color inputs never
changes the layout, topology or UVs. Layout edits can change sequence assignments;
board identity is not persistent through every room/rotation edit. Random draws
are Blender-native, not Mulberry32. Exact SDK seed-to-board sequences are not promised.

The SDK's `HardwoodFloorOptions` and `PlankFloorLayoutOptions` guide functionality.
The application derives sheet extents and boundary cuts internally, just as a
picket exposes drop/inset and a window can expose cell counts instead of low-level
angles and spacing. Low-level operations retain their own meanings.

JavaScript ColorSampler callbacks become native material/node composition here.
The supplied material reads `hardwood_tint`. A custom shader can use `board_id`
with a color ramp or other mapping. The default matches the host's Warm Brown
endpoint recipe; Use Base Color Variation provides the SDK-style legacy HSL option.
Three.js ownership/dispose and draw-call contracts do not transfer to Blender.
The graph produces one mesh object with one selected material; it does not promise
one draw call across Blender render engines.

## UV and material contract

Every evaluated face corner has a real two-component **UVMap** layer. Top and
bottom use board-aligned coordinates in physical units, so U follows the grain
and one UV unit corresponds to one Blender unit. Side/end faces use an appropriate
planar projection with height as V. Cut faces receive their own mapping after the
Boolean; mapping does not rely on cutter UV interpolation.

These are overlapping per-board projections intended for tiling textures, not
packed unique bake islands. Side projections can have seams and directional
changes at angled cuts. Export and texture baking require their own review.
The included material is uniform within each board, with no external wood texture.

Face attributes: `board_id`, `row_id`, `retained_area`, `hardwood_tint`.
These make whole-board selection and custom material composition possible.

## Build and verify

From the repository root:

```sh
python3 scripts/build.py floors --render
python3 scripts/check.py floors
```

Build runs separately from interactive Blender and replaces only this asset and
consumer. Check appends the exported object into a scene with an existing object,
checks layout invariants, compares each retained board against an independent
2D clipping/volume oracle, and audits closure, winding, finite/nondegenerate UVs,
constant per-board colors, repeatability and independent consumer inputs.
