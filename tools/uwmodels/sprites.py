"""Reads UW1's creature sprites and object icons from the player's own copy of the game, as UnderworldGodot does.

- Creature page files, CRIT/CRxxPAGE.N00 and .N01 (xx the body in octal): critterloader.cs ReadPageFileUW1. A slot
  base and slot list name the animations (GetUW1AnimName), each animation lists 8 frame numbers (255 for none), then
  come the aux palettes (32 main-palette indices each) and the frames: width, height, hotspot x and y, compression
  (6 means 5-bit pixels, else 4-bit), a 16-bit count of pixel values and the run-length data (Ua_image_decode_rle,
  from Underworld Adventures). A pixel value is a slot in the aux palette; 0 is transparent.
- DATA/OBJECTS.GR: grloader.cs. Images of type 0x4 (8-bit, main palette indices), 0x8 (4-bit run-length) and 0xA
  (4-bit), the 4-bit ones through a 16-entry aux palette from DATA/ALLPALS.DAT. Index 0 is transparent.
"""
import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .game import _find, main_palette

VIEWS = ["rear", "rear_right", "right", "front_right", "front", "front_left", "left", "rear_left"]
NAMES = {0x0: "idle_combat", 0x1: "attack_bash", 0x2: "attack_slash", 0x3: "attack_stab", 0x5: "attack_secondary",
         0x7: "walking_towards", 0xC: "death", 0xD: "cast", 0x2F: "unknown_anim_47"}
NAMES.update({0x20 + v: f"idle_{n}" for v, n in enumerate(VIEWS)})
NAMES.update({0x28 + v: f"walking_{n}" for v, n in enumerate(VIEWS[:7])})   # 0x2f is not walking_rear_left
NAMES.update({0x50 + v: f"ethereal_anim_{0x50 + v}" for v in range(8)})
NAMES.update({0x80 + v: f"walking_{n}" for v, n in enumerate(VIEWS)})


def anim_name(n: int) -> str:
    return NAMES.get(n, "unknown_anim")


@dataclass
class Frame:
    width: int
    height: int
    hot_x: int
    hot_y: int
    slots: np.ndarray   # (height, width) uint8, 0 transparent


@dataclass
class Page:
    slotbase: int
    anims: dict
    aux: np.ndarray
    frames: list


def decode_rle(data: bytes, start: int, bits: int, count: int, datalen: int) -> np.ndarray:
    """UW1's run-length sprite data, as critterloader.cs Ua_image_decode_rle decodes it; returns `count` values."""
    out = np.zeros(count, np.uint8)
    pos, avail, raw = start, 0, 0
    mask = ((1 << bits) - 1) << (8 - bits)
    pix = stage = cnt = record = repeat = 0
    while datalen > 0 and pix < count:
        if avail < bits:
            nib = (((raw & mask) >> (8 - avail)) << (bits - avail)) if avail > 0 else 0
            raw = data[pos] if pos < len(data) else 0
            pos += 1
            shift = 8 - (bits - avail)
            nib |= raw >> shift
            raw = (raw << (8 - shift)) & 0xFF
            avail = shift
        else:
            nib = (raw & mask) >> (8 - bits)
            avail -= bits
            raw = (raw << bits) & 0xFF
        datalen -= 1
        if stage == 0:
            if nib == 0:
                stage = 1
            else:
                cnt, stage = nib, 6
        elif stage == 1:
            cnt, stage = nib, 2
        elif stage == 2:
            cnt = (cnt << 4) | nib
            stage = 3 if cnt == 0 else 6
        elif stage in (3, 4, 5):
            cnt = (cnt << 4) | nib
            stage += 1
        if stage < 6:
            continue
        if record == 0:   # repeat record: its count
            if cnt == 1:
                record = 3   # no repeat; a run follows
            elif cnt == 2:
                record = 2   # several repeat records
            else:
                record = 1
                continue   # the next value is the colour to repeat
        elif record == 1:
            n = min(cnt, count - pix)
            out[pix:pix + n] = nib
            pix += n
            if repeat == 0:
                record = 3
            else:
                repeat -= 1
                record = 0
        elif record == 2:
            repeat, record = cnt - 1, 0
        elif record == 3:   # run record: copy the next cnt values
            record = 4
            continue
        elif record == 4:
            out[pix] = nib
            pix += 1
            cnt -= 1
            if cnt == 0:
                record = 0
            else:
                continue
        stage = 0
    return out


def read_page(data: bytes) -> Page:
    at = 0
    slotbase, nslots = data[0], data[1]
    at = 2
    enabled = [i for i in range(nslots) if data[at + i] != 255]
    at += nslots
    nsegs = data[at]
    at += 1
    anims = {}
    for i in range(nsegs):
        idx = [-1 if b == 255 else b for b in data[at:at + 8]]
        at += 8
        anims.setdefault(anim_name(slotbase + enabled[i]), idx)
    npals = data[at]
    at += 1
    aux = np.frombuffer(data, np.uint8, 32 * npals, at).reshape(npals, 32).copy()
    at += 32 * npals
    nframes = data[at]
    at += 2
    frames = []
    for i in range(nframes):
        off = struct.unpack_from("<H", data, at + 2 * i)[0]
        w, h, hx, hy, comp = data[off:off + 5]
        n = struct.unpack_from("<H", data, off + 5)[0]
        px = decode_rle(data, off + 7, 5 if comp == 6 else 4, w * h, n)
        frames.append(Frame(w, h, min(hx, w), min(hy, h), px.reshape(h, w)))
    return Page(slotbase, anims, aux, frames)


def read_body(uw1: Path, body: int):
    """A body's animations (name -> 8 indices into frames, -1 for none), aux palettes and frames, both pages merged;
    a name on both pages keeps page 0's."""
    anims, frames, aux = {}, [], None
    for n in ("N00", "N01"):
        try:
            p = read_page(_find(uw1, "CRIT", f"CR{body:02o}PAGE.{n}").read_bytes())
        except FileNotFoundError:
            continue
        base = len(frames)
        frames += p.frames
        aux = p.aux if aux is None else aux
        for name, idx in p.anims.items():
            anims.setdefault(name, [-1 if i < 0 else i + base for i in idx])
    if aux is None:
        raise FileNotFoundError(f"no page files for body {body:02o}")
    return anims, aux, frames


def read_gr(uw1: Path, name: str = "OBJECTS.GR") -> list:
    """Every image of a .GR file as (h, w, 4) RGBA, index 0 transparent."""
    d = _find(uw1, "DATA", name).read_bytes()
    pal = main_palette(uw1)
    allpals = _find(uw1, "DATA", "ALLPALS.DAT").read_bytes()
    out = []
    for i in range(struct.unpack_from("<H", d, 1)[0]):
        off = struct.unpack_from("<I", d, 3 + 4 * i)[0]
        if off + 3 > len(d):   # out of range, as the port's loader allows for: no image
            out.append(np.zeros((1, 1, 4), np.uint8))
            continue
        kind, w, h = d[off], d[off + 1], d[off + 2]
        if kind == 0x4:
            idx = np.frombuffer(d, np.uint8, w * h, off + 3).reshape(h, w)
        elif kind in (0x8, 0xA):
            aux = np.frombuffer(allpals, np.uint8, 16, d[off + 3] * 16)
            n = struct.unpack_from("<H", d, off + 4)[0]
            if kind == 0x8:
                nib = decode_rle(d, off + 6, 4, w * h, 2 * n)
            else:
                raw = np.frombuffer(d, np.uint8, (w * h + 1) // 2, off + 6)
                nib = np.stack([raw >> 4, raw & 15], 1).ravel()[:w * h]
            idx = aux[nib].reshape(h, w)
        else:
            out.append(np.zeros((1, 1, 4), np.uint8))
            continue
        rgba = np.zeros((h, w, 4), np.uint8)
        rgba[..., :3] = pal[idx]
        rgba[..., 3] = np.where(idx > 0, 255, 0)
        out.append(rgba)
    return out
