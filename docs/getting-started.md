# Getting started

This guide assumes Blender 5.2 or newer and no prior experience with Geometry Nodes.

## The idea in one paragraph

Each asset is a **Geometry Nodes modifier** on an object. The modifier is a small program made of nodes.
It builds the shape from the values in its panel (length, height, seed, and so on) every time you change
one. Nothing is baked: change a value and the shape rebuilds.

## 1. Get a file

Every family is one self-contained file in [`assets/`](../assets/), e.g. `Fences.blend` or `Vessels.blend`.
Everything a family needs is inside it, including the parts it borrows from other families. Download just
the one you want.

## 2. Bring it into your scene

**Append** copies the asset into your project (recommended):

1. **File → Append…**
2. Browse to the downloaded `.blend`, open it, then open the **Object** folder.
3. Pick an item (every one starts with **GNL •**) and click **Append**.

The object appears at the 3D cursor. To bring in several at once, Shift-click or Ctrl-click in the file list.

**Or use the Asset Browser.** In **Edit → Preferences → File Paths → Asset Libraries**, add the folder that
holds the `.blend` files. Then in any project, open an **Asset Browser** editor, choose that library, set
the import method to **Append**, and drag items into the viewport.

## 3. Change it

1. Select the object (click it, or click its name in the **Outliner**, top right).
2. Open the **Properties** editor's **Modifier** tab: the blue wrench icon.
3. The controls are grouped into collapsible **panels**. Drag a number, flip a checkbox, pick from a menu.

Hover over any control to read what it does.

### A first example: a fence along your own path

1. Append **GNL • Rustic Fence** from `Fences.blend`.
2. Add a curve: **Shift A → Curve → Bézier**. Press `Tab` to edit it and shape it (`G` to move points),
   then `Tab` again to finish.
3. On the fence, set **Path → Path** to your curve (use the dropdown or the eyedropper).
4. Optional: set **Ground** to your terrain mesh. Every post drops onto it.
5. Change **Surface → Seed** for a different fence, and open **Decay** to age it.

## Seeds and decay

Most assets have a **Seed**: the same seed always gives the same result, and a different seed gives a
different but equally valid one. Many also have a separate **Decay Seed** with decay amounts, so you can
reshuffle the ruin without changing the thing being ruined. See [Seeds and variation](concepts/seeds-and-variation.md).

## Using the node groups in your own graphs

Every family also ships its **node groups** (in the file's **NodeTree** folder when appending). Add one
inside your own Geometry Nodes graph with **Shift A → Group**, then wire it up like any other node. Each
family's README documents its groups' inputs and outputs.

## Two things worth knowing

- **Appending twice** from different files can give you two copies of a shared part (e.g. `GNL • Panel`
  and `GNL • Panel.001`). That's harmless: they are identical copies.
- **Material Preview** (`Z` → Material Preview) uses Blender's built-in studio lighting, which glass and
  metal reflect. For your scene's own lights, open the shading popover (the arrow beside the shading
  buttons) and tick **Scene World** and **Scene Lights**.
