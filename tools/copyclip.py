"""Gives a clip of each named creature's editable model the motion of another clip; then run tools/pack.py.

Usage: python tools/copyclip.py FROM TO ID [ID ...]   e.g. copyclip.py idle_combat idle CR01 CR02
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from uwmodels import clips, gltf  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    for mid in sys.argv[3:]:
        p = Path("models/uw1/editable") / f"{mid}.glb"
        gltf.write(clips.copy_clip(gltf.read(p), src, dst), p)
        print(f"{mid}: {dst} now moves as {src}")
