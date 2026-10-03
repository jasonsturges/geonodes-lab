# Vessels

Native Geometry Nodes vessels ported from three-low-poly `src/geometry/vessels/vesselProfiles.ts`,
first explored in the NodesLab prototype's study 027 (vessel profiles).

| Output | Contents |
| --- | --- |
| `assets/Vessels.blend` | 8 vessel objects, **GNL • Vessel From Curve**, the **GNL • Vase Profile** curve, and the public node groups. Catalog: GeoNodes Lab/Vessels |
| `examples/vessels/gallery.blend` | The showroom: a fresh scene appending from the asset file. [Guide](../../examples/vessels/README.md) |

```sh
python3 scripts/build.py vessels --render
python3 scripts/check.py vessels
```

`build.py` is the source of truth (with its modules `silhouettes.py`, `sections.py`, `vessel.py`). It overwrites
both outputs, so explore in a copy. `--render` also renders the gallery preview.

## Contract

- **Silhouette**: one curve in the XZ plane: X = radius ≥ 0, Z = height, ordered base → rim,
  starting on the axis. Any curve type works, because the Vessel group bakes it to evaluated points first.
  The liquid assumes the silhouette rises from base to rim (no undercut lip).
- **Vessel**: Silhouette → *Geometry* (glass + liquid), *Glass*, *Liquid*, *Glass Section*, *Liquid Section*.
  Inputs are grouped into the panels Silhouette, Glass, Liquid and Detail.
- **Thickness**: 0 gives a single surface with a rolled rim; above 0 gives a closed double wall offset along
  the silhouette normal. Thickness is capped at 0.8 × rim radius. Very thick walls on tight curves
  can fold, as in the SDK. Nothing repairs that.
- **Lathe**: Curve to Mesh on a closed circle. Output is closed with outward normals when given a
  closed section. `UVMap`: U around the axis (seam at +X), V along the profile.
- **Objects**: each named object's **Shape** panel mirrors the SDK function's options. SDK defaults
  derived from other values (e.g. `baseRadius = 0.7 × radius`) are factor inputs.
  The shipped wall is 0.03; the SDK default is 0.

## How it works

Background on curve types, evaluated points and Curve to Mesh is in
[Curves](../../docs/concepts/curves.md).

```
Silhouette ─► Smooth? ─► Resample (evaluated) ─┬─► Vessel Shell ─► Lathe ─► Set Material ─► Glass
                                               └─► Liquid Fill  ─► Lathe ─► Set Material ─► Liquid
```

1. **Silhouette.** Each named group is a **Mesh Line** of N stations. **Set Position** computes
   each station from its **Index**: **Index Switch** picks the SDK's fixed points, and sine/cosine
   math gives arcs such as the Florence bulb or the wine shoulder. **Mesh to Curve** turns the
   stations into one poly curve.
2. **Smooth Silhouette** (optional). **Set Spline Type → Catmull-Rom** plus **Set Spline
   Resolution** rounds the polygon through its own points. **Resample Curve (Evaluated)** then
   bakes any curve type, including a Bézier or NURBS you drew, into plain points.
3. **Offset Profile Inward.** Each point moves by *Distance* along the profile's inward normal.
   The tangent comes from the neighbours (**Evaluate at Index**, index ± 1), turned 90° in the XZ
   plane. Points never cross the axis, and points that start on the axis stay there.
4. **Vessel Shell.** For a double wall, the outer silhouette, a semicircular bead over the rim,
   and the reversed inner wall are tagged with an `order` value. **Points to Curves** joins them
   into one closed section in that order. For a single surface, the rim point is replaced by a
   rolled lip.
5. **Liquid Fill.** The silhouette is offset by the gap. **Accumulate Field** counts points above
   the level, and everything after the first crossing is deleted. That crossing point slides
   down onto the level. Points on the axis close the floor and the flat meniscus.
6. **Lathe.** **Curve to Mesh** spins the section around a unit **Curve Circle**. **Merge by
   Distance** welds the axis poles and **Flip Faces** turns normals outward. The `UVMap` comes
   from the angle around Z and the position along the profile. Faces shade smooth except edges
   sharper than *Smooth Angle*.

Every socket has a tooltip: hover over a control in the wrench tab or on a node to read it.

## Checks (`check.py`, 139 cases)

The checks append from the saved asset file into a fresh session that already has an object
in it. They verify the public panels and outputs. Silhouettes, shells and fills match the SDK
oracle point for point. Each object at its defaults is closed and outward, with UVs and the
exact lathe volume. Vessel From Curve works with the shipped Bézier. The bare **GNL • Vessel**
group works inside a user's own graph fed by a NURBS curve.

## Not yet

Cork stopper, flask stand, test-tube rack, labels and a production-grade glass shader. Beaker,
vase and graduated-cylinder markings from the SDK's other vessel files are also not ported yet.
