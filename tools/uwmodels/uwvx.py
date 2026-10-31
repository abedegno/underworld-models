"""The port's voxel files (UWVX), as UnderworldGodot's crittermodel.cs and itemmodel.cs read them.

"UWVX", version byte 1, f32 voxel size, s16 x0, y0, z0 (the grid's first voxel, in voxels), u8 clip count; per clip a
u8-length name and a u8 frame count, followed by that clip's frames; per frame a u32 voxel count and x, y, z, slot as bytes. A voxel's slot is a
palette number: an index into the main palette for items, into the creature type's 32-entry aux palette for creatures.
"""
import struct
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class Model:
    size: float
    origin: tuple
    clips: dict = field(default_factory=dict)   # name -> list of (n, 4) uint8 arrays: x, y, z, slot


def parse(d: bytes, at: int = 0):
    """Reads a model from bytes at an offset; returns (model, offset after it)."""
    if d[at:at + 4] != b"UWVX" or d[at + 4] != 1:
        raise ValueError("not a version 1 UWVX voxel file")
    size = struct.unpack_from("<f", d, at + 5)[0]
    origin = struct.unpack_from("<3h", d, at + 9)
    count = d[at + 15]
    at += 16
    clips = {}
    for _ in range(count):
        n = d[at]
        name, frames = d[at + 1:at + 1 + n].decode(), d[at + 1 + n]
        at += 2 + n
        clips[name] = []
        for _ in range(frames):
            k = struct.unpack_from("<I", d, at)[0]
            clips[name].append(np.frombuffer(d, np.uint8, k * 4, at + 4).reshape(k, 4).copy())
            at += 4 + k * 4
    return Model(size, tuple(origin), clips), at


def read(path) -> Model:
    d = Path(path).read_bytes()
    m, end = parse(d)
    if end != len(d):
        raise ValueError(f"{path}: {len(d) - end} bytes after the last frame")
    return m


def tobytes(m: Model) -> bytes:
    out = bytearray(b"UWVX\x01" + struct.pack("<f3hB", m.size, *m.origin, len(m.clips)))
    for name, frames in m.clips.items():
        b = name.encode()
        out += bytes([len(b)]) + b + bytes([len(frames)])
        for f in frames:
            f = np.asarray(f, np.uint8).reshape(-1, 4)
            out += struct.pack("<I", len(f)) + f.tobytes()
    return bytes(out)


def write(m: Model, path):
    Path(path).write_bytes(tobytes(m))
