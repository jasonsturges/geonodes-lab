# Seeds and variation

GeoNodes Lab's main idea: **one graph, endlessly many individual results.** A fence of fifty posts should
be fifty different posts, but the *same* fifty every time you open the file. Seeds give both.

## What a seed is

A **seed** is just a number. Every random choice in a graph is made from a hash of *what* is being
decided and *the seed*:

- The same seed always reproduces the same result: in Blender, on another machine, after reopening.
- Any other seed gives a different, equally valid result.
- Seeds are not "better" or "worse"; they are simply different draws.

## Two kinds of randomness

| Want | Node | Gives |
| --- | --- | --- |
| One independent value per *thing* (each post's height, each brick's tone, which leaf gets a tendril) | **White Noise Texture** (4D), fed (thing index, channel) and W = Seed | Unrelated values: neighbours share nothing |
| Values that change *smoothly* across space (a board's wandering edge, a log's lumps, a vine's sway) | **Noise Texture** (4D), fed a position and W = Seed | Coherent values: neighbours move together |

The **channel** number keeps decisions independent. A post's height (channel 3) and its lean (channel 5)
come from different streams, so a tall post isn't also always a leaning one.

## Independent seeds: layout, shape, color, decay

Assets split their randomness into separately seeded concerns, so you can change one without disturbing
the others:

- **Seed:** the layout and the shape of each member.
- **Decay Seed:** *which* members are damaged and how. Decay amounts (Missing, Bent, Dropped, Ruin) scale
  the damage. At zero, the decay seed is inert and changes nothing.
- **Color or tone:** a per-member value (often a `tone` or `tint` attribute) that materials read for slight
  variation, independent of geometry.

A good test of an asset: change the decay seed and confirm nothing intact moves. The checks do exactly this.

## Ranges, not just noise

Variation is always bounded by a control you can see: *Height Variation 0.07* means ±7%; *Max Bend 0.35*
means up to 0.35 radians either way. Exact values are available too: most warps have **Randomize Warp**,
and turning it off makes each one exactly the number you typed. That's useful for measured work and for checks.

## Decay: the derelict concept

Decay is a first-class feature, not an afterthought. It removes, bends, drops or rusts members of an
otherwise intact layout:
- missing rails, pickets, spokes or bricks;
- bent pickets and dropped rails;
- a failed hinge or a fallen cap;
- rust.

Because decay draws from its own seed and never moves what remains, you can design the intact object
first, then dial in exactly as much ruin as the scene needs.

## Reproducibility, honestly

Results are reproducible **within Blender**. They don't match the random sequences of other programs.
Ported designs (e.g. from three-low-poly) keep the *rules*, not the exact random numbers. Where a port
is fully deterministic (no randomness), the checks compare it with the original point for point.
