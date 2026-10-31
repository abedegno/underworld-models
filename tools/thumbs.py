"""Draws the gallery's still pictures, site/thumbs/uw1/<id>.png (variants' in variants/<name>/), from the display voxels.

Usage: python tools/thumbs.py [id ...]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from uwmodels import thumbs  # noqa: E402

if __name__ == "__main__":
    data, out = Path("site/data/uw1"), Path("site/thumbs/uw1")
    for p in sorted(data.rglob("*.uwvc")):   # variants' are in data/uw1/variants/<name>/
        if len(sys.argv) > 1 and p.stem not in sys.argv[1:]:
            continue
        dst = out / p.relative_to(data).with_suffix(".png")
        dst.parent.mkdir(parents=True, exist_ok=True)
        thumbs.render(p).save(dst)
