"""Display voxels for the site: a port voxel file with the colours it needs, so the browser can draw it.

"UWVC" followed by a UWVX file's bytes after its magic, then a u8 colouring count, and per colouring a u16 entry count
and per entry a slot byte and its R, G, B. Only the slots the model uses are listed, never a whole palette.
"""
import struct
from pathlib import Path

import numpy as np

from . import uwvx


def used_slots(model: uwvx.Model) -> list[int]:
    s = set()
    for frames in model.clips.values():
        for f in frames:
            s.update(np.unique(f[:, 3]).tolist())
    return sorted(s)


def write_uwvc(model: uwvx.Model, colourings: list, path):
    """colourings: one {slot: (r, g, b)} per colouring."""
    out = bytearray(b"UWVC" + uwvx.tobytes(model)[4:])
    out.append(len(colourings))
    for c in colourings:
        out += struct.pack("<H", len(c))
        for slot in sorted(c):
            out += bytes([slot, *[int(x) for x in c[slot]]])
    Path(path).write_bytes(bytes(out))


def read_uwvc(path):
    d = Path(path).read_bytes()
    if d[:4] != b"UWVC":
        raise ValueError(f"{path}: not a display voxel file")
    model, at = uwvx.parse(b"UWVX" + d[4:])
    colourings = []
    count = d[at]
    at += 1
    for _ in range(count):
        n = struct.unpack_from("<H", d, at)[0]
        at += 2
        colourings.append({d[at + 4 * i]: tuple(d[at + 4 * i + 1:at + 4 * i + 4]) for i in range(n)})
        at += 4 * n
    return model, colourings
