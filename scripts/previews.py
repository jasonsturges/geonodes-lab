"""Make small committed preview.jpg images from the full-size (ignored) preview.png renders.

Run with system Python on macOS: python3 scripts/previews.py
Builders render preview.png; this writes a 1280px-wide JPEG beside each one so READMEs and
GitHub can show it without committing multi-megabyte PNGs. Uses macOS `sips`.
"""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WIDTH = 1280
QUALITY = 80


def main():
    if not shutil.which('sips'):
        sys.exit('sips not found: this helper uses macOS image tools')
    total = 0
    for png in sorted(ROOT.glob('*/**/preview.png')):
        if 'renders' in png.parts:
            continue
        jpg = png.with_suffix('.jpg')
        if jpg.exists() and jpg.stat().st_mtime >= png.stat().st_mtime:
            total += jpg.stat().st_size
            continue
        subprocess.run(['sips', '--resampleWidth', str(WIDTH), '-s', 'format', 'jpeg',
                        '-s', 'formatOptions', str(QUALITY), str(png), '--out', str(jpg)],
                       check=True, capture_output=True)
        total += jpg.stat().st_size
        print(f'{jpg.relative_to(ROOT)}  {jpg.stat().st_size // 1024} KB')
    print(f'Total committed previews: {total // 1024} KB')


if __name__ == '__main__':
    main()
