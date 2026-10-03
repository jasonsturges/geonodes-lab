"""Build families (in dependency order) and/or studies, each in a background Blender process.

    python3 scripts/build.py all
    python3 scripts/build.py vessels fences --render
    python3 scripts/build.py 027
    python3 scripts/build.py --list
"""
import sys
from _targets import families, ordered, resolve, run, studies

args = [a for a in sys.argv[1:] if not a.startswith('--')]
if '--list' in sys.argv or not args:
    print('Families (build order):', ', '.join(ordered()) or '—')
    print('Studies:', ', '.join(studies()) or '—')
    sys.exit(0)
extra = ['--render'] if '--render' in sys.argv else []
for script in resolve(args, 'build'):
    run(script, extra)
