# Building blocks: patterns used throughout

The same handful of node patterns come up in almost every asset. Knowing them makes any graph here
readable. Open a family's node group (select the object, open a **Geometry Nodes** editor, select a group
node, `Tab` to enter, `Tab` to leave) and you'll find these.

## Stations: points placed by rule

Most assets start as **points**, placed by arithmetic on their **Index**:

- **Points** with a *Count* and a position computed from Index (e.g. `x = (index + 0.5) × pitch`).
- **Mesh Line**, then **Set Position** from Index, then **Mesh to Curve**, when the points are a profile.
  An **Index Switch** picks fixed points, and math builds arcs.
- **Curve to Points** / **Resample Curve** when the points follow a curve: even spacing along any path.
  **GNL • Path Stations** packages this for fences.

## Instances vs. For Each

| Situation | Use | Example |
| --- | --- | --- |
| Every copy is identical | **Instance on Points** (+ **Realize Instances**) | Iron posts, rings, bricks (one cube scaled per brick) |
| Every copy is different (its own seed, length, shape) | **For Each Element** zone | Rustic posts and rails (each a unique log), iron fence panels (each bay its own length and decay) |

Instance rotation and scale can still vary per copy. Only the *geometry* is shared.

## Orienting things along curves

- **Align Rotation to Vector** turns an object's axis toward a direction (a spoke, a rail, a leaf).
- Two alignments in a row fix it completely: first "point along this", then "face that way". Ivy leaves
  use this to sit on any vine, flat or climbing a post.

## Overprovision and filter

Nodes have no `while` loop. When a source algorithm lays items until something runs out (bricks along a
course, ending on a cut closer), the graph makes **one point per possible slot**, computes each slot's
position and size in closed form, and **Delete Geometry** removes the slots the loop would never have laid.
The brick pier lays brick for brick what its original loop did.

## Measure, then fit

A **Bounding Box** of generated geometry is a value you can compute with. The overthrow measures a scroll's
natural width to pre-shrink its bar, so scrolls stay delicate at any size. The medallion slides each
C-scroll until its edge touches the stem.

## Sweeps

**Curve to Mesh** sweeps a profile along a path: bars, rails, scrolls, vines. Its **Scale** input (a field)
tapers along the path. A closed **Curve Circle** as the path turns a profile into a lathe (vessels). See
[Curves](curves.md).

## Outputs that other assets read

Assets publish useful values as **outputs**, e.g. a pier's **Top**, so assemblies seat parts by reading
them instead of repeating the arithmetic. The gateway stands its overthrow on the piers' Top.
