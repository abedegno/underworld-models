"""Exports the port's model files into this repo: editable models, MagicaVoxel copies, display voxels, manifest.

Usage: python tools/export.py UW1_DIR SRC_PORT_DIR [REPO=.]
UW1_DIR is your own copy of Ultima Underworld (its colours are read from it, never copied into the repo).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from uwmodels import export  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    for line in export.run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3] if len(sys.argv) > 3 else ".")):
        print(line)
