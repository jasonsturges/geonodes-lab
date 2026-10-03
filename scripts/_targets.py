"""Shared by build.py and check.py: find families and studies, order families by dependency.

Run with system Python. No Blender or third-party packages are needed here; each build or check runs
in its own background Blender process.
"""
import ast
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BLENDER = os.environ.get('GNL_BLENDER', '/Applications/Blender.app/Contents/MacOS/Blender')


def families():
    """{family: [dependencies]} from each generators/<family>/build.py's DEPENDS list."""
    found = {}
    for build in sorted((ROOT / 'generators').glob('*/build.py')):
        depends = []
        for node in ast.parse(build.read_text()).body:
            if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == 'DEPENDS' for t in node.targets):
                depends = ast.literal_eval(node.value)
        found[build.parent.name] = depends
    return found


def ordered(selection=None):
    """Families in dependency order (all, or `selection` plus nothing else)."""
    graph, order, seen = families(), [], set()

    def visit(name, trail=()):
        if name in trail:
            raise SystemExit(f'Dependency cycle: {" → ".join((*trail, name))}')
        if name in seen:
            return
        for dep in graph.get(name, ()):
            visit(dep, (*trail, name))
        seen.add(name)
        order.append(name)
    for name in graph:
        visit(name)
    return [f for f in order if selection is None or f in selection]


def studies():
    """{'molding-return': directory, ...}: studies are addressed by their folder name."""
    return {build.parent.name: build.parent for build in sorted((ROOT / 'studies').glob('*/*/build.py'))}


def run(script, extra=()):
    if not Path(BLENDER).is_file():
        raise SystemExit(f'Blender not found at {BLENDER}; set GNL_BLENDER')
    command = [BLENDER, '--background', '--factory-startup', '--python-exit-code', '1',
               '--python', str(script)]
    if extra:
        command += ['--', *extra]
    print(f'→ {Path(script).relative_to(ROOT)}', flush=True)
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    lines = [line for line in (result.stdout + result.stderr).splitlines()
             if any(k in line for k in ('passed', 'PASS', 'Error', 'Traceback', 'assert', 'Saved'))]
    for line in lines[-8:]:
        print('   ', line)
    if result.returncode:
        print((result.stdout + result.stderr)[-3000:])
        raise SystemExit(f'Failed: {script}')


def resolve(targets, kind):
    """Turn command-line targets ('all', family names, study names) into scripts to run."""
    fams, stds = families(), studies()
    scripts = []
    wanted = set(targets)
    if 'all' in wanted:
        wanted = set(fams) | set(stds)
    for family in ordered([t for t in wanted if t in fams]):
        scripts.append(ROOT / 'generators' / family / f'{kind}.py')
    for name in sorted(t for t in wanted if t in stds):
        scripts.append(stds[name] / f'{kind}.py')
    unknown = [t for t in wanted if t not in fams and t not in stds]
    if unknown:
        raise SystemExit(f'Unknown target(s): {unknown}. Families: {sorted(fams)}; studies: {sorted(stds)}')
    return [s for s in scripts if s.exists()]
