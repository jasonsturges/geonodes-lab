"""Run independent checks for families and/or studies, each in a background Blender process.

    python3 scripts/check.py all
    python3 scripts/check.py ironwork 027
"""
import sys
from _targets import resolve, run

args = [a for a in sys.argv[1:] if not a.startswith('--')] or ['all']
for script in resolve(args, 'check'):
    run(script)
print('All requested checks passed.')
