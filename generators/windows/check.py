"""Independent checks for assets/Windows.blend. Never imports the builder.

Five suites, each appending from the saved Windows.blend into a fresh session:
  verify_core               Opening Profile boundaries per style, cutter, Diamond Lattice
  verify_gregorian          Gregorian Lattice: boundary coincidence, fused topology, UVs
  verify_pane               Window Pane: every style in surface and slab modes
  verify_diamond_window     Diamond Window: components, analytic offsets, bar volumes
  verify_gregorian_window   Gregorian Window
Run: python3 scripts/check.py windows
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import verify_core  # noqa: E402
import verify_gregorian  # noqa: E402
import verify_pane  # noqa: E402
import verify_diamond_window  # noqa: E402
import verify_gregorian_window  # noqa: E402

suites = (verify_core, verify_gregorian, verify_pane, verify_diamond_window, verify_gregorian_window)
for suite in suites:
    suite.main()
print(f'Windows: {len(suites)} suites passed')
