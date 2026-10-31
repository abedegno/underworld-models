"""Writes the original sprites for the site (site/sprites/uw1/) from your own copy of UW1.

Usage: python tools/sprites.py UW1_DIR [REPO=.]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from uwmodels import spritesheet  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for line in spritesheet.export(Path(sys.argv[1]), Path(sys.argv[2] if len(sys.argv) > 2 else ".")):
        print(line)
