# GeoNodes Lab

**Procedural assets for Blender, built entirely with Geometry Nodes, where every copy comes out different.**

Fences that follow your path and settle onto your terrain. Brick piers laid course by course. Forged
ironwork, hewn timber, glass vessels. Each one is driven by a **seed**, so a row of fifty posts is
fifty individual posts, and an optional **decay** seed ages any of them into a ruin without moving
what still stands.

Everything is native Blender: no add-on to install and no Python needed to use it. Download a `.blend`,
append what you want, and change it from the modifier panel.

## Use it in 30 seconds

1. Download a family file from [`assets/`](assets/), for example `Fences.blend`. Each file stands alone.
2. In your project: **File → Append** → choose the file → **Object** → pick e.g. **GNL • Rustic Fence**.
3. Select it, open the **Modifier** tab (the wrench icon), and change its controls.
   To make it follow your own curve, set **Path** to any curve object in your scene.

Prefer browsing? Add the `assets` folder as an **Asset Library** (Preferences → File Paths → Asset
Libraries) and drag items in from the Asset Browser. Full walkthrough:
[Getting started](docs/getting-started.md).

## What's inside

| Family | File | Highlights |
| --- | --- | --- |
| [Vessels](generators/vessels/README.md) | `Vessels.blend` | Eight lathed glass vessels with liquid, or one from any curve you draw |

Every family has a ready-to-use **object**, the **node groups** behind it (for building your own
graphs), a **gallery scene** in [`examples/`](examples/), and a **How it works** section in its README.

## How the repository is organized

| Folder | What it is | Who it's for |
| --- | --- | --- |
| [`assets/`](assets/) | The `.blend` files you download and append. **This is the product.** | Everyone |
| [`examples/`](examples/) | Gallery scenes made by appending from `assets/`, the way you would | Everyone |
| [`docs/`](docs/) | Getting started, concepts, Blender gotchas, the catalog | Everyone |
| [`generators/`](generators/) | Python recipes that *write* each asset file | Contributors |
| [`studies/`](studies/) | Experiments: investigations that inform the assets, kept as records | Contributors, the curious |
| [`authoring/`](authoring/) | Shared Python helpers used by the recipes | Contributors |
| [`scripts/`](scripts/) | Build, check and preview launchers | Contributors |

The Python never ships inside the `.blend` files: it runs once, at build time, to place ordinary nodes.
See [How this is built](docs/authoring.md).

## Requirements

Blender **5.2** or newer.

## License

[ISC](LICENSE.md): use it for anything; keep the notice.
