# Catalog

Every production family, what's inside, and where its ideas came from. Families arrive here as they're
ported from the NodesLab prototype onto the [authoring patterns](authoring.md).

| Family | File | Objects | Building-block groups | Origin |
| --- | --- | --- | --- | --- |
| [Vessels](../generators/vessels/README.md) | `Vessels.blend` | Florence Flask, Erlenmeyer Flask, Test Tube, Graduated Cylinder, Pipette, Apothecary Jar, Potion Bottle, Wine Bottle, Vessel From Curve, Vase Profile | Vessel, Lathe, Vessel Shell, Liquid Fill, 8 Silhouettes | three-low-poly `vesselProfiles.ts` |
| [Timber](../generators/timber/README.md) | `Timber.blend` | Weathered Plank, Hewn Timber | Weathered Plank, Hewn Timber; 3 wood materials | three-low-poly `WeatheredPlankGeometry`, `createHewnTimberGeometry` |
| [Ironwork](../generators/ironwork/README.md) | `Ironwork.blend` | Picket, Post, Scroll, Panel, Twisted Bar, Fleur-de-lis, Double Scroll, Ornamental Rail, Ivy Iron, Overthrow | the same, plus Collar, Ivy Leaf, Tendril; forged and rusted iron | three-low-poly fence geometry; website graveyard and windowsill ironwork |
| [Masonry](../generators/masonry/README.md) | `Masonry.blend` | Brick Pier | Brick Pier (with a Top output); 4 materials | website graveyard `BrickPierGeometry.ts` (three-low-poly `QuoinStackGeometry`) |
| *(more porting in progress)* | | | | |

## Planned, in order

1. **Fences**: Path Stations, the rustic fence, the iron fence and the gateway.
2. **Windows, Molding, Hardwood Floor**: modernized from the prototype.

Origins:
- **[three-low-poly](https://github.com/jasonsturges/three-low-poly):** the author's Three.js geometry library.
- **The author's website:** Three.js scenes and lab experiments that incubate many of these designs.

GeoNodes Lab overlaps both, and deviates wherever Blender can do better.
