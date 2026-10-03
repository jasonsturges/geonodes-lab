# Molding

Named molding sections as reusable **profile curves**, straight pieces built from them, and **Molding Run**:
any section along any curve, every corner mitered exactly. Origin: three-low-poly `MoldingProfiles.ts`
(corner styles), `SurfaceProfiles.ts` and `MoldingGeometry`.

| Output | Contents |
| --- | --- |
| `assets/Molding.blend` | Objects **GNL • Corner Molding**, **Surface Molding** and **Molding Run**; node groups of the same names, the two **Profile** groups and **GNL • Molding Run • Object**; and **GNL • Painted Molding**. Catalog: GeoNodes Lab/Molding |
| `examples/molding/gallery.blend` | Every named section side by side, plus both straight objects. [Guide](../../examples/molding/README.md) |
| `examples/molding/room.blend` | Crown, chair rail and base around one room plan: inside corners, a chimney breast, a curved bay. [Guide](../../examples/molding/README.md#the-room) |

```sh
python3 scripts/build.py molding --render
python3 scripts/check.py molding        # 92 section cases against SDK fixtures, 43 Molding Run cases
```

Modules: `profiles.py` (the named sections), `molding.py` (the straight piece), `run.py` (Molding Run), and `graph.py` (this family's
Graph, the `F` formula wrapper and the section names). `build.py` is the source of truth.

## Two families

- **Corner Molding:** Cove, Ovolo, Chamfer, Ogee, Cyma, Scotia, Fillet, Step.
  Solid-backed section, with two backs meeting at the origin. Crown/base changes
  orientation while preserving the same section.
- **Surface Molding:** Fillet, Bead, Astragal, Reed, Ovolo, Ogee, Lip.
  Single flat supporting back, including the Lip's undercut.

`assets/Molding.blend` contains, for each family, a ready-to-append object,
a standalone modifier group, and a reusable **GNL • … Molding Profile** curve group.
No template mesh attributes are required. Each recipe uses native sampled math,
mesh-to-curve, Fill Curve and Extrude Mesh with explicit back closure.

| Control | Default corner / surface | Range / meaning |
| --- | --- | --- |
| Profile | Ogee / Astragal | Named native menu |
| Length | 1.2 | .05–10, straight X run |
| Height | .09 / .07 | .02–.3; drop or rise along wall |
| Projection | .065 / .028 | .005–.2; distance from wall |
| Segments | 6 | 1–16; curved contour subdivisions |
| Crown (corner only) | On | Downward; off is upward base |
| Reeds (surface only) | 4 | 2–8; used by Reed |
| Reed Backing | .1 | .02–.4 fraction of projection; used by Reed |
| Material | Painted molding | User-replaceable material |

Fixed Chamfer, Fillet and Step polygons ignore Segments. Ogee/Cyma use rounded
half-segment counts for their two quarters, matching the SDK. Bead/Astragal use
2×Segments across their half ellipse. Reed deliberately uses 2×Segments per bead
and an explicit backing: the SDK's unbacked beads touch at zero-thickness valleys
and its one-segment reed degenerates. The native Reed preserves total Height and
Projection while keeping a connected solid even at low resolution.

Straight pieces are centered on local X. Back at Y=0, projection toward −Y,
height toward +Z for base/surface and −Z for crown. Crown reverses the transformed
face winding. Outputs: Geometry and Profile. **Profile remains in canonical XY**:
X is wall distance (height), Y is projection. It is independent of run length and
crown orientation, suitable for explicit future path framing. The profile groups
also export only that closed curve. Moving an object places its origin; no wall
placement or facing inference is hidden in these generators.

Real FLOAT2 UVMap uses dominant-axis physical-scale projection on every face.
Coordinates overlap for tiling, not packed baking, and are not a continuous
perimeter unwrap. Meshes are flat shaded, capped, and have square ends. Surface
material editing is ordinary Blender material editing, separate from geometry.

## Verification

`check.py` loads the exported objects into a fresh scene and checks 92 combinations
of profile, resolution and crown/base mode for closed topology, winding, positive
volume, expected cross-section vertices, run endpoints and nondegenerate UVs.
`sdk-reference.json` is an independently generated fixture from the actual SDK
MoldingProfiles.ts and SurfaceProfiles.ts at unit dimensions (segments 1,2,6,16).
Reed's intentional change uses an independent backed-bead formula in the check.
Additional checks vary reed count, backing, dimensions and independent host inputs.
These are sampled contract checks, not proof of arbitrary dimensions or export
triangulation. Collinear loop triangles in valid n-gons are allowed as in windows.

**Molding Run** is checked in its own fresh session on five poly plans (closed rectangle and triangle;
an open L, a chimney breast, and 30° and 120° turns) × Crown / Base / Chair Rail × inward / outward,
cycling through the sections. An independent oracle recomputes each point's miter in plain Python: every
predicted vertex must exist in the mesh, the vertex count must be path points × section points, and the
volume must equal section area × the length of its centroid line (exact for a chain of mitered prisms).
A Bézier path, a two-spline path and the no-path sample room are checked for watertight, outward shells.


## Molding Run

**GNL • Molding Run** is three-low-poly's `MoldingGeometry`: a section swept along a wall line, the
**corner a property of the path, not of the section**. Each corner is cut on the vertical plane that
bisects it, and both lengths share that one ring of vertices, so the joint closes exactly at any angle
for any section. As in the SDK, an inside corner is mitered, not coped (these walls are square).

| Control (object) | Meaning |
| --- | --- |
| Path | Any curve object: poly, Bézier or NURBS; several splines make several runs. Empty: a sample 4 × 3 room |
| Run | **Crown** hangs down from the path; **Base** and **Chair Rail** rise from it |
| Corner Profile / Surface Profile | The section for Crown and Base / for Chair Rail |
| Height, Projection, Segments | Section size and smoothness, as for the straight pieces |
| Outward | Off: the molding projects to the **left** of the path's direction, the room side of a plan drawn anticlockwise from above. On: to the right, e.g. wrapping the outside of a box |
| Material | Any material |

**How it works** (open the **GNL • Molding Run** group to follow along):

1. **Resample Curve** (Evaluated) turns any path into its evaluated points: corners stay sharp, and a
   Bézier gives as many points as its resolution.
2. At each point, **Field at Index** fetches the previous and next point *within the same spline*
   (Curve of Point / Points of Curve), wrapping on closed splines. The perpendiculars of the incoming and
   outgoing directions are averaged into the **miter direction n**, and the section is widened by
   **k = 1 / cos(turn / 2)**, so it still reaches its full projection from both walls.
3. **Curve to Mesh** sweeps the section along the path, which gives the mesh its topology (and caps the
   ends of open runs). Then **Set Position** places every vertex exactly:
   path point + n · k · projection + height down (crown) or up. Curve to Mesh's own twisting frames are
   never used, which is why the joints are exact.
4. **Flip Faces** keeps normals outward for every Crown and Outward combination, and **UVMap** runs along
   the molding (distance along the path, distance around the section).

**Limits, as in the SDK:** a short run between two inside corners has a floor: narrower than
2 · projection · tan(turn / 2), the two miters overlap. Likewise a curve bent tighter than the
projection makes the section cross itself. Neither is repaired; the request simply does not fit.
Returns (a run dying back into the wall) and sprung crown sections are not modeled.

## Next applications

three-low-poly's molding studies that remain open here: **returns** (a run ending back into the wall),
**sprung** crown sections (hollow-backed, set at an angle), the **dentil cornice** and the **corbel run**.
Each would start as a study.
