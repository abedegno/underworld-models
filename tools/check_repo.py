"""Fails on anything in the repo that looks like a game file, or is too big for it.

The repo holds fan-made models only: no file from Ultima Underworld itself, and nothing extracted from one (palettes,
sprites, icons, strings). This guard runs in CI on every push and pull request.
Usage: python tools/check_repo.py [root]
"""
import fnmatch
import subprocess
import sys
from pathlib import Path

from PIL import Image

GAME_FILES = ["*.dat", "*.gr", "*.ark", "*.anm", "*.pak", "*.byt", "*.tr", "*.n0?", "cr*page*", "*.sys", "*.voc",
              "*.xmi", "uw.ad", "uw.mt", "*.exe", "*.com", "*.gog", "*.ins", "*.cue"]
MAX_BYTES = 15 * 1024 * 1024
SKIP = {".git", ".venv", "__pycache__", ".pytest_cache", "_site", ".superpowers"}
ICON_SIDE = 64


def files(root: Path):
    """Every file that is or could be committed: in a git repo, tracked and untracked files not ignored."""
    if (root / ".git").exists():
        r = subprocess.run(["git", "-C", str(root), "ls-files", "-co", "--exclude-standard", "-z"], capture_output=True)
        if r.returncode == 0:
            return sorted(root / f for f in r.stdout.decode().split("\0") if f)
    return sorted(root.rglob("*"))   # not a git repo: every file, less the SKIP folders


def problems(root: Path) -> list[str]:
    root = Path(root)
    found = []
    for p in files(root):
        rel = p.relative_to(root)
        if any(part in SKIP for part in rel.parts) or not p.is_file():
            continue
        name = p.name.lower()
        if any(fnmatch.fnmatch(name, g) for g in GAME_FILES):
            found.append(f"{rel}: looks like a game file; game files must never be committed")
        elif p.stat().st_size > MAX_BYTES:
            found.append(f"{rel}: {p.stat().st_size // (1024 * 1024)} MB, over the 15 MB limit")
        else:
            try:   # any picture, whatever its name, by its content
                with Image.open(p) as im:
                    w, h = im.size
            except Exception:
                if name.endswith(".png"):
                    found.append(f"{rel}: not a readable PNG")
                continue
            if w <= ICON_SIDE and h <= ICON_SIDE and rel.parts[:2] != ("site", "sprites"):   # sprites go there only
                found.append(f"{rel}: {w}x{h} picture, small enough to be a sprite or icon export")
    return found


if __name__ == "__main__":
    found = problems(Path(sys.argv[1] if len(sys.argv) > 1 else "."))
    for f in found:
        print(f)
    sys.exit(1 if found else 0)
