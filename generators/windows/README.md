# Windows

Named openings and everything built on them, in one file. Origin: three-low-poly `ArchProfile.ts`
(the seven named arch styles) and its lattice window factories (`DiamondLatticeWindow`,
`GregorianLatticeWindow`), first built in the NodesLab prototype.

| Output | Contents |
| --- | --- |
| `assets/Windows.blend` | Objects **GNL • Diamond Lattice**, **Gregorian Lattice**, **Window Pane**, **Diamond Window**, **Gregorian Window**; node groups for each plus **GNL • Opening Profile**, **Window Frame** and **Opening Boundary Offset**; four materials. Catalog: GeoNodes Lab/Windows |
| `examples/windows/gallery.blend` | A fresh scene appending all five objects, each showing a different arch style. [Guide](../../examples/windows/README.md) |

```sh
python3 scripts/build.py windows --render
python3 scripts/check.py windows        # five suites, 96 cases
```

Modules: `opening.py` (the arch profiles), `lattice.py`, `pane.py`, `frame.py`, `window.py`, and `graph.py`
(the shared Graph plus the Arch Style menu). The checks live in `verify_*.py`, dispatched by `check.py`.

## The one idea: a named opening

Every group here takes the **same five inputs**: **Arch Style**, **Width**, **Springing Height**, **Rise** and
**Arch Segments**. Every group evaluates the same **GNL • Opening Profile**. A lattice, its glass and its frame
therefore always agree, because they're cut from one definition. Arch styles follow three-low-poly's
`ArchProfile` exactly: Square, Semicircle, Segmental, Horseshoe, Elliptical, Pointed and Ogee.

Arch Style is a **menu** input. Because a menu can drive only one Menu Switch, each group turns it into an
index once, and per-style values are picked with Index Switches. See
[Blender gotchas](../../docs/blender-gotchas.md).

## Shared opening

`assets/Windows.blend` → NodeTree → **GNL • Opening Profile** is a
composition group. One description produces **Outline**, **Region**, **Cutter**,
and **Resolved Rise** outputs. The outline is a cyclic polyline; Region is its
filled surface; Cutter is a closed centered extrusion. Geometry is upright in XZ,
sill centered at the origin, with the region facing −Y. Cutter Depth spans Y
symmetrically. Placement belongs to the consuming object/assembly.

| Input | Default | Supported range / meaning |
| --- | --- | --- |
| Arch Style | Semicircle | Square, Semicircle, Segmental, Horseshoe, Elliptical, Pointed, Ogee |
| Width | 1.2 | 0.4–3; width between the jambs |
| Springing Height | 1.4 | 0.3–3; sill to start of arch |
| Rise | 0.6 | 0.1–2; requested rise above springing |
| Arch Segments | 24 | 4–64 intervals per half; crown retained |
| Cutter Depth | 0.3 | 0.02–2 |

Square resolves rise to zero. Semicircle resolves it to Width/2. Segmental caps
rise at Width/2. Horseshoe and Pointed enforce a minimum of Width/2. Elliptical
and Ogee use the requested rise. Horseshoe can bulge beyond the jamb width;
Width therefore does not always mean total bounding-box width.

The native menu selects the shape equations. Sampling retains the sill corners,
springings and crown. Square includes collinear samples along its lintel; these
are not additional corners. Ogee uses two tangent-continuous quadratic segments
per half. The curve resolution contract is explicit and differs from Three's
curve-type-dependent `getPoints` sampling. All consumers of this group's outputs
receive the same sampled boundary, avoiding independent approximations.

The filled region has a real planar UVMap in physical units. The cutter is a
modeling volume, not a textured production part; its side UVs are not a surface
mapping contract. It is ready as geometry for the future wall-opening study,
not a claim that a wall assembly has already been implemented.

## Diamond lattice

`assets/Windows.blend` contains **GNL • Diamond Lattice** as both Object
and NodeTree assets. It includes the opening group as a local dependency. Append
with either route; the node group replaces any host mesh and needs no template
attributes, Python callbacks, external textures or DCC runtime.

The modifier adds these independent pattern controls:

| Input | Default | Supported range / meaning |
| --- | --- | --- |
| Angle | 45° | 15°–75°; bar families at +angle and −angle from horizontal |
| Spacing | 0.19 | 0.08–0.6; perpendicular distance between bars in each family |
| Phase | 0 | −1–1; signed perpendicular offset applied to both families |
| Came Width | 0.022 | 0.01–0.08; nominal section diameter across the opening |
| Came Depth | 0.022 | 0.01–0.12; nominal section diameter through the opening |
| Came Sides | 4 | 3–16; actual polygon cross-section resolution |
| Fuse Crossings | On | Native Boolean union for clean rendered crossings |
| Material | Dark bronze | User-supplied material socket |

As in the SDK, section sizes scale a regular polygon with circumradius 0.5 and
half-segment rotation. A four-sided section has flat-to-flat width equal to the
nominal width divided by √2. Higher side counts approach an elliptical section.
Came Sides does not change Arch Segments: one describes stock, the other its
boundary cuts. The later window assembly will derive angle and spacing from cell
counts; this standalone component intentionally exposes geometric controls.

A For Each zone builds each long polygonal bar, then intersects it with the shared
opening cutter. Both ends acquire the boundary's facets. Native Boolean operations
also handle concave heads and disconnected portions without a convex-hull shortcut.
Candidates whose total retained axial span is at most three nominal came widths
are omitted as tiny corner offcuts. For a candidate split into disconnected portions,
this threshold applies to the complete candidate span, not each portion separately.
This differs from the SDK's centerline-chord filtering and may retain different
small fragments. Came Count reports retained candidate bars before optional fusion.

With Fuse Crossings off, bars are separate closed solids that interpenetrate,
matching the SDK construction intent. Exact coplanar front faces can cause shading
artifacts at their intersections. With it on, native union removes overlap and
internal faces. `came_id` and `came_family` face attributes indicate original bar
provenance; after fusion they are not a partition into independent closed solids.
The Boolean can leave collinear vertices inside valid n-gons. Export triangulation
needs separate review; the native polygonal surface is what is validated here.

Lattice faces carry a real FLOAT2 UVMap using dominant-axis physical-scale planar
projections. These are overlapping tiling coordinates, not packed bake islands
or a continuous cylindrical unwrap. The shared material controls appearance; this
asset has no randomized color recipe. Geometry Nodes re-evaluates all controls live.

## Gregorian lattice

**GNL • Gregorian Lattice**) and `examples/windows/gallery.blend`.
It uses the same Opening Profile and `lattice_group(..., gregorian=True)` in `lattice.py`. The bar
construction, clipping, material, UV mapping and fusion code are shared; each public group has its
own interface.

It retains all opening inputs and replaces Diamond's pattern inputs with:

| Input | Default | Supported range / meaning |
| --- | --- | --- |
| Mullion Spacing | 0.24 | 0.08–0.6; upright bar spacing |
| Transom Spacing | 0.3 | 0.08–0.6; horizontal bar spacing |
| Mullion Phase | 0 | −1–1; positive moves uprights toward −X |
| Transom Phase | 0 | −1–1; positive moves horizontal bars upward |
| Bar Width | 0.03 | 0.01–0.08; nominal section diameter across opening |
| Bar Depth | 0.03 | 0.01–0.12; nominal section diameter through opening |
| Bar Sides | 4 | 3–16 |
| Material | Painted walnut bars | Replaceable material socket |
| Fuse Crossings | On | Same union behavior as Diamond |

Output **Bar Count** counts candidates before fusion. `came_id` and `came_family`
remain common attributes for both lattices; Gregorian family 0 is upright, family 1
is horizontal. Width/depth are independently editable, with equal defaults; changing
width does not automatically change depth. The polygon sizing convention described
above applies here too.

Gregorian additionally drops a candidate when its clipped geometry cannot span the
original section's full lateral extent (2e-6 tolerance). This removes bars lying
along sill, jambs or a square lintel, and near-edge strips narrower than their stock.
An arched head may retain a bar above a jamb when its full width fits there. This
is a Boolean clipping policy, not an exact reproduction of the SDK's ring-ray
rejection. The total axial-span offcut policy and concave-region caveat are the same
as Diamond's. Neither asset models carpentry joints or fabrication joinery.

Build the opening with `build.py` first if absent or changed. Gregorian's builder
only rewrites its own asset and consumer. Its 14 profile/section/phase cases use
independent section integration, fused topology and UV checks, plus an explicit
six-bar rectangle proving perimeter omission, and an independent host. Re-run
both lattice checks whenever shared bar construction changes.

### Native operations versus shared authoring

The opening uses Blender's **Fill Curve** and **Extrude Mesh**, plus a reversed
back cap, to produce its closed cutter. Extrusion itself is native. The reusable
**GNL • Opening Profile** node group packages that composition with the named
profile equations. Consumers reuse its geometry outputs without copying formulas.
Python's shared helpers write nodes and sockets; they do not replace Blender's
geometry engine. A standalone generic extrusion wrapper is not needed yet.

## Exact-opening Window Pane

`assets/Windows.blend`, plus `examples/windows/gallery.blend`.
It consumes the existing Opening Profile asset directly: Region for a surface,
Cutter for a solid. No duplicate profile or extrusion implementation is introduced.

All opening controls and rise rules above apply. Additional controls:

| Input | Default | Meaning |
| --- | --- | --- |
| Solid Glass | On | Closed slab; off returns a single front-facing surface |
| Thickness | 0.004 | 0.001–0.03 total depth centered on Y=0; ignored for surface |
| Material | Clear blue glass | Replaceable material socket |

Outputs are Geometry, Outline and Resolved Rise. The boundary exactly matches the
opening, without expansion or contraction. This is deliberately the zero-rebate
subset of the SDK PaneGeometry interface. Signed Rebate and Miter Limit remain
pending with the frame/jamb work; it is not yet full PaneGeometry option coverage.
A true offset must be shared with the frame; changing width/height or scaling the
pane would not preserve a constant rebate. Study 018 is convex-only and cannot
simply be applied to every named arch.

Solid mode is the default for Blender refraction: the default Principled material
has Transmission Weight 1, IOR 1.45, Roughness 0.07 and a pale blue Base Color.
Surface mode is geometric compatibility for a user-supplied surface material;
the default refractive shader is intended for the closed solid. Alpha stays 1:
transmission and alpha transparency are different controls. Material parameters
are edited in Material Properties; the geometry modifier selects the material.

Faces carry real FLOAT2 UVMap coordinates. Front/back use physical XZ coordinates;
edge faces use dominant-axis projections. Coordinates overlap for tiling and are
not a packed bake atlas. The pane has hard geometric edges without bevels. The
consumer's colored cards are staging only and are absent from the asset.

Checks cover all seven styles at two resolutions/thicknesses, in both solid and
surface modes: analytic sampled boundary agreement, closed slab volume, winding,
UV coverage, surface area, independent modifier values and material replacement.
The supported shape contract remains the shared named opening's sampled polygon.

## Count-driven Diamond Window

NodeTree **GNL • Diamond Window**, plus an independent consumer. It appends the
existing Diamond lattice and Window Pane groups, and points both at one shared
Opening Profile dependency. `frame.py` supplies window-local native offset/frame
groups, included in this asset; they are not promoted as arbitrary-curve assets.

Cells Across and Cells Up are integers 1–8, default 4. For opening width W,
springing height H and counts X,Y:

- cell width = W/X; cell height = H/Y
- angle = atan2(cell height, cell width)
- spacing = cell width × sin(angle); phase = 0

These are derived inputs connected to the standalone lattice. Links may carry
angles/spacing outside that component's standalone UI sliders. Counts align
centerline divisions in the rectangular part, not every visible glass polygon.
Arches trim cells above springing; frame inset covers member ends. In particular,
odd counts can put half-cell intersections along a jamb, and finite stock width
and the component's short-offcut filtering remain relevant.

Came Width defaults to .022 (UI .01–.05), Came Depth .0308 (.015–.1). The frame's
inset is Came Width × Frame Inset Factor (default 1, range .5–2); outset is Came
Width × Frame Outset Factor (1.6, range 0–3). Frame depth follows Came Depth. Glass
Thickness defaults to .004 (.001–.01). Show Frame and Show Glass default on. Lead,
Frame and Glass Material sockets are independent; the first two initially share
one ironwork material. Emissive glass is configured through its material rather
than an additional geometry input. Signed glass rebate remains deferred.

Frame offsets intersect shifted edge lines. Expanding joins beyond a miter limit
bevel (outer limit 6; inward concave joins 2); contracting convex joins keep their
intersection. This differs from the SDK's unconditional miter-limit bevel. For
symmetric heads, consumed crown edges are replaced by their intersection at the
symmetry axis. It resolves the Ogee tip's local fold without rewriting the profile.
The native graph checks nonadjacent nonparallel edge intersections and suppresses
the frame on failure, exposing Frame Valid. This is a bounded named-opening
implementation: no general arrangement repair, hole nesting solver or complete
collinear-overlap detection. Slider ranges are not a guarantee that every
combination yields a valid frame. Reduce offsets when rejected.

Native Fill Curve fills the nested frame boundaries, then Extrude Mesh plus back
closure makes a centered solid. Real FLOAT2 UVMap uses dominant-axis physical
projections. Joined assembly geometry preserves three components and materials;
it does not Boolean-union the frame, leading and glass. Separate Lattice, Frame,
Glass, Cutter, Angle and Spacing outputs allow further composition. Cutter depth
is currently .5. Full wall fitting, rebate grooves and fabrication joints are not
implemented by this asset.

The checks independently solve offset coordinates/area and lattice family volumes,
verify closed components and UVs, exercise seven profiles and odd/even counts,
check extreme square count ratios, component toggles and rejected shallow arches.

## Count-driven Gregorian Window

in `assets/Windows.blend`, with its own consumer. It uses the same assembly
builder and frame implementation as Diamond, selecting the Gregorian lattice and
its distinct public interface. Opening, glass, toggles, frame factors, UV and offset
limitations described above also apply.

**Lights Across** defaults to 3, **Lights Up** to 4; both range 1–8. Mullion spacing
is Width / Lights Across, transom spacing is Springing Height / Lights Up. Odd
across counts use half-spacing phase; even counts use zero phase. Transom phase is
zero. This gives N−1 internal divisions across a rectangular opening; the arch may
add clipped pieces above springing. Square 1 × 1 has no internal bars. These are
opening divisions, not equal clear-glass widths after frame inset and stock width.

Bar Width and Bar Depth both default to .03, with independent controls. Width's
range is .01–.05; depth .015–.1. Bar and Frame Material initially share a painted
walnut material. Separate component outputs remain named Lattice, Frame and Glass
for consistency. Derived outputs are Mullion Spacing, Transom Spacing and Mullion
Phase; there is no editable spacing/phase input at assembly level.

Frame authoring now removes redundant collinear boundary samples before offsetting.
This avoids false folds when a square lintel's inset corner passes nearby samples;
curved geometry and the common opening itself are unchanged. Both assemblies use
this correction. The offset groups remain window-local and bounded, not a general
polygon repair library. Glass rebate is still deferred.

Checks cover 28 combinations of seven profiles and odd/even, single-light and dense
counts, independent frame and bar volumes, fused topology/UVs, empty leading,
component toggles and independent modifier reuse. Recheck Diamond when the common
assembly builder or frame code changes.

The Gregorian Lattice unions its two bar families (uprights and levels) as **separate operands**. That
avoids a zero-area face that the all-at-once self-intersection union produced in a dense Horseshoe case.
In the prototype this was patched only into the window's copy. Here it's part of the lattice itself, and
both the standalone lattice suite (14 cases) and the window suite (28 cases) pass with it.
