# Ironwork

Wrought-iron members promoted from the NodesLab prototype's study 030,
ornament from the NodesLab prototype's study 033 and ivy from
the NodesLab prototype's study 034 and the overthrow arch from
the NodesLab prototype's study 035. Each study keeps its own copy. Sources: three-low-poly `WroughtIron{Picket,Post,Scroll}Geometry` and
`resolveFenceSpan`, plus the website graveyard's panel improvements.

| Output | Contents |
| --- | --- |
| `assets/Ironwork.blend` | Objects and node groups **GNL • Picket**, **Post**, **Scroll**, **Panel**, **Twisted Bar**, **Fleur-de-lis**, **Double Scroll**, **Ornamental Rail**, **Ivy Iron**, **Overthrow**; building-block groups **GNL • Collar**, **Ivy Leaf**, **Tendril**; materials **GNL • Iron • Forged / Rusted**. Catalog: GeoNodes Lab/Ironwork |
| `examples/ironwork/gallery.blend` | A fresh scene appending them; a copy of the panel shows rings, decay and rust. [Guide](../../examples/ironwork/README.md) |

Build with `python3 scripts/build.py ironwork [--render]`.
Check with `python3 scripts/check.py ironwork` (66 cases). `build.py` is the source of truth.

## Contract

- **Picket**: base at Z = 0. A flat faces the run (±X). **Finial** is Spear, Ball or None.
  **Finial Depth** squashes the finial across the panel (Y).
- **Post**: base at Z = 0. The ball centre sits *Ball Settle* × radius above the shaft. Optional collar.
- **Scroll**: a flat bar on r = r₀·e^(−kθ) in the **XY** plane, tapering by station toward the curl.
  The object asset is stood in XZ. **Path** output: the spiral curve, for your own sweeps.
- **Panel**: a run along X, centered, in the XZ plane. The panels:
  - **Run**: Length and Gap. Picket count follows `resolveFenceSpan`.
  - **Pickets**: the picket inputs.
  - **Rails**: foot and top rail.
  - **Rings**: one per opening, fitted to the picket flats and bedded 3 mm into the top rail.
  - **Decay** (collapsed): Decay Seed, Missing Pickets, Bent Pickets, Max Bend.

  Decay never moves rails or spacing. The **Picket Count** output reports the resolved count.

- **Twisted Bar**: along Z from 0. Square Twist (tilted square sweep), Rope or Basket (strands on a helix),
  with plain square ends.
- **Fleur-de-lis**: a cast plate in XZ, stem at the origin.
- **Double Scroll**: S or C, two tapering log spirals joined at their open ends, fitted to *Fit Width*, in XZ.
- **Ornamental Rail**: the website windowsill rail, with square and twisted pickets alternating and fitted
  scrolls in the gaps.
- **Overthrow**: an arch (Semicircle / Elliptical / Pointed) on legs with tie and inner arc, infill
  (Spokes / Volutes / Gap Scrolls), Medallion centre, crown, ivy and decay. Origin: centre of the
  springing line. **Apex** output: the crown height.
- **Ivy Iron**: a forged vine (grown, or the *Path* geometry) with cast leaves and tendrils. The object
  version takes a **Path Object** curve.

## How it works

See the studies' How it works sections (030,
033,
034). In brief:
**Menu Switch** finials, a half-facet turn so flats face the run, a scale-after-rotate
**Transform** pair, **Curve to Mesh** with a station-index **Scale** taper,
**Instance on Points** pickets bent through instance rotation, and **Curve Circle** rings.
