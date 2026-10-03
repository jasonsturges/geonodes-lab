# Catalog

Every production family, what's inside, and where its ideas came from. Families arrive here as they're
ported from the NodesLab prototype onto the [authoring patterns](authoring.md).

| Family | File | Objects | Building-block groups | Origin |
| --- | --- | --- | --- | --- |
| [Vessels](../generators/vessels/README.md) | `Vessels.blend` | Florence Flask, Erlenmeyer Flask, Test Tube, Graduated Cylinder, Pipette, Apothecary Jar, Potion Bottle, Wine Bottle, Vessel From Curve, Vase Profile | Vessel, Lathe, Vessel Shell, Liquid Fill, 8 Silhouettes | three-low-poly `vesselProfiles.ts` |
| [Timber](../generators/timber/README.md) | `Timber.blend` | Weathered Plank, Hewn Timber | Weathered Plank, Hewn Timber; 3 wood materials | three-low-poly `WeatheredPlankGeometry`, `createHewnTimberGeometry` |
| [Ironwork](../generators/ironwork/README.md) | `Ironwork.blend` | Picket, Post, Scroll, Panel, Twisted Bar, Fleur-de-lis, Double Scroll, Ornamental Rail, Ivy Iron, Overthrow | the same, plus Collar, Ivy Leaf, Tendril; forged and rusted iron | three-low-poly fence geometry; website graveyard and windowsill ironwork |
| [Masonry](../generators/masonry/README.md) | `Masonry.blend` | Brick Pier | Brick Pier (with a Top output); 4 materials | website graveyard `BrickPierGeometry.ts` (three-low-poly `QuoinStackGeometry`) |
| [Fences](../generators/fences/README.md) | `Fences.blend` | Rustic Fence, Iron Fence, Gateway | Path Stations, Rustic Fence, Iron Fence, Gateway (Hewn Timber, Panel, Post, Overthrow, Brick Pier travel inside) | three-low-poly `RusticFence`; website graveyard `Enclosure.ts`, `Gateway.ts` |
| [Windows](../generators/windows/README.md) | `Windows.blend` | Diamond Lattice, Gregorian Lattice, Window Pane, Diamond Window, Gregorian Window | the same, plus Opening Profile, Window Frame, Opening Boundary Offset | three-low-poly `ArchProfile.ts`, `DiamondLatticeWindow`, `GregorianLatticeWindow` |
| [Molding](../generators/molding/README.md) | `Molding.blend` | Corner Molding, Surface Molding, Molding Run | the same, plus Corner / Surface Molding Profile | three-low-poly `MoldingProfiles.ts`, `SurfaceProfiles.ts`, `MoldingGeometry` |
| [Floors](../generators/floors/README.md) | `Floors.blend` | Hardwood Floor | Hardwood Floor (Floor Laying and Resolve Floor Offcuts inside) | three-low-poly `HardwoodFloor` |

## Planned

- **Studies:** a keep / port / retire inventory of the NodesLab prototype's studies, with keepers ported
  onto these patterns.
- **More from three-low-poly and the website:** plank, flagstone and hexagonal tile floors; walls with
  quoin patterns (alternating, balanced, straight); the piano keyboard and bells; and other factories.

Origins:
- **[three-low-poly](https://github.com/jasonsturges/three-low-poly):** the author's Three.js geometry library.
- **The author's website:** Three.js scenes and lab experiments that incubate many of these designs.

GeoNodes Lab overlaps both, and deviates wherever Blender can do better.
