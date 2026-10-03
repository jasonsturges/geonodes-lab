# Curves

Many GeoNodes Lab tools (vessels, ivy, scrolls, fences) start from a **curve**: a profile,
a path or a silhouette. This page explains what a curve is in Blender, how the curve types
differ, and how Geometry Nodes turns curves into meshes. Examples come from the
[Vessels](../../generators/vessels/README.md) asset.

## Control points and evaluated points

A curve has **control points**: the dots you edit in Edit Mode. Blender draws the curve, and
Geometry Nodes uses it, through its **evaluated points**, computed from the control points:

- *Poly* curves: evaluated points **are** the control points; segments are straight.
- *Smooth* types (Bézier, NURBS, Catmull-Rom): evaluated points are sampled along the smooth
  curve. **Resolution** sets how many per segment.

Most curve nodes (Curve to Mesh, Curve to Points in *Evaluated* mode, Resample Curve in
*Evaluated* mode) work on evaluated points. That's why the Vessel group starts with
**Resample Curve → Evaluated**: whatever type of curve arrives, it becomes a poly curve with
exactly the points you see. The offsets and cuts that follow then work on a known list of points.

## The four spline types

| Type | Passes through its points? | Controls | Typical use |
| --- | --- | --- | --- |
| **Poly** | Yes; straight segments | Points only | Generated profiles (every SDK silhouette), exact facets |
| **Bézier** | Yes; smooth between | Each point has two **handles** (Auto, Vector, Aligned, Free) | Hand-drawn profiles; precise tangents (the Vase Profile) |
| **NURBS** | No; points *pull* the curve | Point weights, Order, Endpoint option | Very smooth design curves; CAD-style shapes |
| **Catmull-Rom** | Yes; smooth between | Points only; tangents are automatic | Rounding an existing point list (Smooth Silhouette) |

Converting between them is a single node: **Set Spline Type**. Smoothness is the
**Set Spline Resolution** node, or *Resolution* in the curve's Object Data properties.

### Why Smooth Silhouette uses Catmull-Rom

The SDK draws silhouettes as point lists, where "roundness is point count": to round a
shoulder you add points. In Blender, **Set Spline Type → Catmull-Rom** turns the same points
into a smooth curve that still passes through every point, with no extra parameters.
Catmull-Rom works out each point's tangent from its neighbours, so the curve stays faithful to
the original shape. The trade-off is that it rounds *every* corner, including ones you want
sharp, such as a bottle's foot. NURBS would smooth more, but its curve doesn't pass through the
points, so the bottle's dimensions would drift. That's why NURBS isn't the default.

### Bézier handles in brief

When editing a Bézier (`Tab` in the 3D view), press `V` to set a handle type:

- **Auto**: smooth, computed for you (most of the Vase Profile)
- **Vector**: points straight at the neighbour, which makes a corner (the Vase's flat base and foot)
- **Aligned**: smooth, but you control the length and direction
- **Free**: the two handles move independently

## From curve to mesh

| Goal | Node pattern | Example |
| --- | --- | --- |
| Tube or molding along a path | **Curve to Mesh** (path + profile curve) | Sweeps, molding |
| Lathe (spin a profile) | **Curve to Mesh** with a **Curve Circle** as the path and the profile as the profile | GNL • Lathe |
| Flat filled shape | **Fill Curve** | Opening regions |
| Points along a curve | **Curve to Points**, **Resample Curve** | Profile stations |

**Curve to Mesh** places the profile curve's local X along the path's normal and its local Y
along the path's binormal. For a circle path in the XY plane, that means X points outward and Y
points down (−Z). The Lathe group therefore feeds the profile as *(radius − 1, −height)* around a
unit circle, so each point lands exactly at *(radius, height)*. Using a **closed** circle matters.
An open 360° arc tilts its end copies, because an open curve's end tangent follows its last
segment. That leaves a pinhole at the axis.

## Fields and neighbours

Curve points have an **Index**. Several vessel nodes use it:

- **Index Switch**: point *i* takes the *i*-th value, which is how a fixed list of SDK points becomes a curve.
- **Evaluate at Index**: read a neighbour's position (index ± 1) to get the tangent, as in the inward offset.
- **Accumulate Field**: a running count along the curve, e.g. how many points so far sit above the fill level.

A field is evaluated **on the geometry the node receives**. If one node moves points and a later
node asks "is this point above the level?", it sees the *moved* positions. Order operations
deliberately. The Liquid Fill group deletes first, then moves.

## Using your own curve

1. Add a curve: `Shift A` → Curve → Bézier (or Path, which is NURBS).
2. Rotate it into the X–Z plane, or draw in front view (numpad `1`).
3. In a Geometry Nodes graph, **Object Info** (Relative) → **Geometry** gives you the curve. Use
   *Relative* so moving the host object doesn't double-transform it.
4. Feed it to any node that expects a curve: GNL • Vessel *Silhouette*, GNL • Lathe *Profile*, or a sweep's *Profile*.
