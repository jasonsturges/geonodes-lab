# Use the Molding in Blender

![Preview](preview.jpg)

Open `gallery.blend`: every named section as a short piece facing you end-on, with corner sections in the
front row and surface sections behind. On the right are the two objects themselves:

- **GNL • Corner Molding**: eight solid-backed corner profiles. Crown hangs downward from its origin; turn
  Crown off for base molding that rises upward.
- **GNL • Surface Molding**: seven profiles with one flat supporting back.

Select a piece, then Properties → **Modifiers** (wrench). Change **Profile**,
**Length**, **Height**, **Projection** and **Segments**. Surface Reed also exposes
Reeds and Reed Backing. Material is replaceable. Both remain editable after append;
no Python is needed to evaluate them.

Length follows local X, centered at the origin. The back lies on Y=0 and the front
projects toward −Y. Height follows +Z for surface/base or −Z for crown. Place the
object origin at the wall/floor or wall/ceiling line, then move/rotate the object.
Keep object scale at 1 when you want the controls to represent physical dimensions.

**Adding one piece:** File → Append → `assets/Molding.blend` → Object → **GNL • Corner Molding** or
**GNL • Surface Molding**. The file also holds the standalone modifier groups and the reusable profile
groups (NodeTree → **GNL • Corner Molding Profile** / **Surface Molding Profile**), whose output curve can
be a sweep profile in your own graph.

The gallery's corner samples are all bases, so both rows rise the same way.

The first production contract is a straight solid piece with square ends. Path
following, corner joints, returns and sprung sections are future focused work;
rotating an object is not the same as constructing a sprung cross-section. Reed
uses a small backing to keep the beads connected, unlike the SDK's zero-thickness
valleys. See the [production contract](../../generators/molding/README.md).
