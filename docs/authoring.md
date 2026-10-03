# How this is built (authoring guide)

This is the contract every generator, example, study and check follows. If something here and the code
disagree, one of them is a bug.

## The model

```
authoring/ (shared Python helpers)
        │  used by
        ▼
generators/<family>/build.py ──writes──► assets/<Family>.blend   ◄── the product
        │                                   │
        │ also writes                        │ appended by
        ▼                                   ▼
examples/<family>/gallery.blend      (any user's project)
```

- **Python is the authoring tool, not the runtime.** A builder runs once in a background Blender process
  and places ordinary nodes, wires, materials and objects. The saved `.blend` holds only native data, and
  Blender evaluates it with no Python.
- **The generator is the source of truth.** Never hand-edit an output `.blend` to keep a change. Change the
  recipe and rebuild. (Explore freely in a copy.)

## Rule 1: every asset file is a standalone product

One downloaded file must work on its own. When a family uses another family's parts (fences use timber
logs, ironwork panels and brick piers), the builder **appends those parts from their asset files**, and
they travel inside. Reuse lives in the source; outputs are self-contained.

The cost is duplicated data across files, which is accepted. The benefit is that users can also customize
their copy without affecting anything else.

Consequence: **build order matters.** A family is rebuilt after the families it borrows from.
`scripts/build.py` knows the order (each generator declares `DEPENDS = [...]`).

## Rule 2: one name, one prefix, in one place

`authoring/naming.py` holds the project name and the **`GNL •`** prefix. Every node group, object, material
and catalog takes its name from there: `f'{PREFIX} Rustic Fence'`. Renaming the project means changing one
constant and rebuilding.

Why prefix at all? In a user's file all node groups share one namespace. The prefix avoids collisions with
their own "Fence" or "Post", and groups ours together in **Shift A** and search.

## Node group conventions

- **Units are metres.** Z is up. Each group's README states its **origin** (e.g. "base at Z = 0", "centre of
  the springing line") and its plane (e.g. "panel in XZ").
- **Inputs live in panels** (Shape, Size, Variation, Decay, Surface…). Decay and rarely used detail panels
  start closed.
- **Every input has a description** (the hover tooltip) and a sensible default and range.
- **Seeds:** `Seed` for layout and shape, `Decay Seed` for damage. Decay amounts at 0 leave the result
  untouched. See [Seeds and variation](concepts/seeds-and-variation.md).
- **Materials are inputs**, and the family file supplies defaults.
- **Outputs that assemblies need** are published (e.g. a pier's `Top`), so parents read rather than repeat.
- **Two layers per family:** composable **node groups** (marked as assets) and ready-made **objects**
  wrapping them with materials (also assets). Internal helper groups are not marked.

## Generator layout

```
generators/<family>/
    build.py      entry point: DEPENDS, export_assets(), gallery()
    *.py          one module per member when the family is large (no 1,000-line files)
    check.py      independent checks on the saved asset
    README.md     What's inside · Contract · How it works · Checks
```

Builders use `authoring.graph.Graph`: declare sockets, `finish_io()`, build with its short helpers, then
`layout()`. Write for a reader: one idea per line, named intermediate values, and comments that explain
**why**.

## Examples (galleries)

`examples/<family>/gallery.blend` is written by the family's builder **from a fresh scene that appends
from the saved asset file**, exactly as a user would. It's the family's showroom and its proof of
standalone use. It uses `authoring.presentation`: a floor, flat labels, a three-light studio, a camera,
Material Preview with the scene's own world and lights, and a Cycles preview on the GPU.

## Checks

- **Independent:** a check never imports its builder. Expectations come from oracles: transcriptions of
  source formulas, closed-form measurements, invariants.
- **On the saved file:** generator checks append from `assets/<Family>.blend` into a fresh session that
  already contains an unrelated object (proving append doesn't disturb a project).
- **Never write tracked files.** No re-saving scenes, no timing logs in the repo.
- **Report:** print `<Family>: N cases passed`, and exit non-zero on failure.

What to check, at minimum: closed meshes and outward normals where intended; exact dimensions at
documented settings; counts (members, courses, stations); seed reproducibility; decay independence
(changing the decay seed with decay at 0 changes nothing, and decay never moves intact members).

## Studies

A study is a durable investigation: it asks a question, answers it, and keeps the evidence.

```
studies/<topic>/<NNN>-<name>/
    build.py   check.py   README.md   study.blend   preview.jpg
```

Its README has: **Question · Explore · How it works · Verification · Limits / Next.** Studies may append
production assets. Production never depends on a study. When a study's result becomes a product, its
groups are **promoted** into a generator, and the study keeps its own copy as the record.

## Previews

Builders render full-size `preview.png` (ignored by git). `python3 scripts/previews.py` writes a small
`preview.jpg` beside each one (~70 KB), which READMEs embed and git tracks.

## Commands

```sh
python3 scripts/build.py <family|study-number|all> [--render]   # background Blender, dependency order
python3 scripts/check.py <family|study-number|all>
python3 scripts/previews.py
```

The Blender executable defaults to `/Applications/Blender.app/Contents/MacOS/Blender`. Override with the
`GNL_BLENDER` environment variable.
