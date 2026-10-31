"""Reads colours from the player's own copy of UW1. Nothing read here is ever written into the repo as a table.

- PALS.DAT: the main palette, 256 colours of three 0..63 values; palette 0 is the one models use.
- CRIT/CRxxPAGE.N00: a creature body's aux palettes, 32 main-palette indices each, as the port's critterloader.cs
  ReadPageFileUW1 reads them (xx is the body's number in octal).
- CRIT/ASSOC.ANM: from byte 256, two bytes for each of the 64 creature types (object 0x40 + n): body, aux palette.
"""
from pathlib import Path

import numpy as np


def _find(root: Path, *parts) -> Path:
    """Finds a file case-insensitively, since copies of the game differ in case."""
    p = Path(root)
    for part in parts:
        hits = [c for c in p.iterdir() if c.name.lower() == part.lower()] if p.is_dir() else []
        if not hits:
            raise FileNotFoundError(f"{Path(root, *parts)} not found; is {root} a UW1 folder?")
        p = hits[0]
    return p


def main_palette(uw1: Path) -> np.ndarray:
    d = _find(uw1, "DATA", "PALS.DAT").read_bytes()[:768]
    return (np.frombuffer(d, np.uint8).reshape(256, 3).astype(np.uint16) * 4).clip(0, 255).astype(np.uint8)


def aux_palettes(uw1: Path, body: int) -> np.ndarray:
    d = _find(uw1, "CRIT", f"CR{body:02o}PAGE.N00").read_bytes()
    a = 1
    n = d[a]
    a += 1 + n
    segs = d[a]
    a += 1 + 8 * segs
    count = d[a]
    a += 1
    return np.frombuffer(d, np.uint8, 32 * count, a).reshape(count, 32).copy()


def creature_types(uw1: Path) -> list[tuple[int, int, int]]:
    d = _find(uw1, "CRIT", "ASSOC.ANM").read_bytes()
    return [(0x40 + n, d[256 + 2 * n], d[257 + 2 * n]) for n in range(64)]
