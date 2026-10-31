"""MagicaVoxel .vox files (version 150): one model, its voxels and their colours.

MagicaVoxel is z up and the port is y up, so a port voxel (x, y, z) is stored as (x, z, y). Colours are stored in the
file's own 255-entry palette, holding only the colours the model uses.
"""
import struct
from pathlib import Path

import numpy as np


def _chunk(cid: bytes, content: bytes, children: bytes = b"") -> bytes:
    return cid + struct.pack("<ii", len(content), len(children)) + content + children


def write(path, voxels, colours):
    """voxels: (n, 3) ints from 0 to 255 in port axes (y up); colours: (n, 3) uint8."""
    v = np.asarray(voxels, int).reshape(-1, 3)
    c = np.asarray(colours, np.uint8).reshape(-1, 3)
    if len(v) and (v.min() < 0 or v.max() > 255):
        raise ValueError("MagicaVoxel models are at most 256 voxels a side")
    table, idx = np.unique(c, axis=0, return_inverse=True)
    if len(table) > 255:
        raise ValueError(f"{len(table)} colours; a MagicaVoxel model holds at most 255")
    m = v[:, [0, 2, 1]]
    size = (m.max(0) + 1) if len(m) else np.ones(3, int)
    xyzi = np.c_[m, idx.reshape(-1) + 1].astype(np.uint8)
    rgba = np.zeros((256, 4), np.uint8)
    rgba[:len(table), :3] = table
    rgba[:len(table), 3] = 255
    body = (_chunk(b"SIZE", struct.pack("<3i", *size.tolist()))
            + _chunk(b"XYZI", struct.pack("<i", len(xyzi)) + xyzi.tobytes())
            + _chunk(b"RGBA", rgba.tobytes()))
    Path(path).write_bytes(b"VOX " + struct.pack("<i", 150) + _chunk(b"MAIN", b"", body))


def read(path):
    """Returns (voxels (n, 3) in port axes, colours (n, 3) uint8) of the file's first model."""
    d = Path(path).read_bytes()
    if d[:4] != b"VOX ":
        raise ValueError(f"{path}: not a MagicaVoxel file")
    at = 20   # after the header and the MAIN chunk's own header
    xyzi, rgba = None, None
    while at < len(d):
        cid = d[at:at + 4]
        n, kids = struct.unpack_from("<ii", d, at + 4)
        content = d[at + 12:at + 12 + n]
        if cid == b"XYZI" and xyzi is None:
            k = struct.unpack_from("<i", content)[0]
            xyzi = np.frombuffer(content, np.uint8, k * 4, 4).reshape(k, 4)
        elif cid == b"RGBA":
            rgba = np.frombuffer(content, np.uint8, 1024).reshape(256, 4)
        at += 12 + n + kids
    if xyzi is None:
        raise ValueError(f"{path}: no voxels")
    if rgba is None:
        raise ValueError(f"{path}: no colour palette (MagicaVoxel's default palette is not supported)")
    v = xyzi[:, :3].astype(int)[:, [0, 2, 1]]
    return v, rgba[xyzi[:, 3].astype(int) - 1, :3].copy()
