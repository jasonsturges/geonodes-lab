# Molding

Named molding sections as reusable **profile curves**, and straight molding runs built from them. Origin:
three-low-poly `MoldingProfiles.ts` (corner styles) and `SurfaceProfiles.ts`.

| Output | Contents |
| --- | --- |
| `assets/Molding.blend` | Objects and node groups **GNL • Corner Molding** and **GNL • Surface Molding**, their **Profile** groups, and **GNL • Painted Molding**. Catalog: GeoNodes Lab/Molding |
| `examples/molding/gallery.blend` | Every named section side by side, plus both objects. [Guide](../../examples/molding/README.md) |

```sh
python3 scripts/build.py molding --render
python3 scripts/check.py molding        # 92 profile/mode cases against SDK fixtures
```

Modules: `profiles.py` (the named sections), `molding.py` (the straight run), and `graph.py` (this family's
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


## Next applications

The complete SDK MoldingGeometry path API is not implemented by these straight
assets. Preserve separate investigations for: editable planar curves and profile
orientation; inside/outside corners and genuine shared miter sections; short-run
self-overlap; lofted returns to a wall; sprung profiles and their clearance limits.
Curve to Mesh is a useful Blender-native candidate for curved runs, but a sweep's
orientation and corner behavior need verification before claiming exact miters.
An inward overlap can hide a seam visually, but does not certify a clean solid.
Generic object rotation places stock at an angle; it does not hollow its back into
a sprung section. SDK studies remain the references for these distinct questions.
