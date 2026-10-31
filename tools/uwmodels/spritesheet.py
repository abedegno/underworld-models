"""Writes the original sprites as picture sheets for the site, from the player's own copy of UW1.

- site/sprites/uw1/CRnn-<aux>.png: every frame of a creature body in one colouring, frames left to right in rows of
  16 cells, each frame placed so that its hotspot lands on the same anchor in its cell (so the sprite does not jump
  between frames); a pixel whose colour is main palette index 0 is transparent.
- site/sprites/uw1/CRnn.json: the cell size, the anchor, the columns, the scale (0.015 port units a sprite pixel)
  and each animation's frames, its list cut at its first missing frame.
- site/sprites/uw1/OBJnnn.png: an item's icon from OBJECTS.GR, as the port draws it on the floor.
These pictures are the game's artwork (site/sprites/NOTICE.md); no game file is copied.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

from . import game, sprites

COLUMNS = 16
CREATURE_SCALE = 0.015


def layout(frames):
    ax = max(f.hot_x for f in frames)
    ay = max(f.hot_y for f in frames)
    offs = [(ax - f.hot_x, ay - f.hot_y) for f in frames]
    cw = max(ox + f.width for f, (ox, _) in zip(frames, offs))
    ch = max(oy + f.height for f, (_, oy) in zip(frames, offs))
    return cw, ch, ax, ay, offs


def sheet(frames, aux_row: np.ndarray, pal) -> Image.Image:
    cw, ch, _, _, offs = layout(frames)
    cols = min(COLUMNS, len(frames))
    rows = (len(frames) + COLUMNS - 1) // COLUMNS
    img = np.zeros((rows * ch, cols * cw, 4), np.uint8)
    for k, (f, (ox, oy)) in enumerate(zip(frames, offs)):
        x0, y0 = (k % COLUMNS) * cw + ox, (k // COLUMNS) * ch + oy
        cell = img[y0:y0 + f.height, x0:x0 + f.width]
        idx = aux_row[f.slots]
        on = idx > 0   # main palette index 0 is transparent, as the port's sprites draw it
        cell[on, :3] = pal[idx[on]]
        cell[on, 3] = 255
    return Image.fromarray(img)


def export(uw1, repo, pal=None, body_reader=None, icons=None) -> list:
    repo = Path(repo)
    pal = game.main_palette(uw1) if pal is None else pal
    body_reader = body_reader or (lambda body: sprites.read_body(uw1, body))
    icons = sprites.read_gr(uw1) if icons is None else icons
    out = repo / "site/sprites/uw1"
    out.mkdir(parents=True, exist_ok=True)
    report = []
    for e in json.loads((repo / "models/uw1/manifest.json").read_text()):
        mid = e["id"]
        if e["kind"] == "item":
            Image.fromarray(icons[int(mid[3:], 16)]).save(out / f"{mid}.png")
            continue
        anims, aux, frames = body_reader(int(mid[2:], 8))
        cw, ch, ax, ay, _ = layout(frames)
        colourings = {}
        for c in e["colourings"]:
            a = c["aux"]
            if a >= len(aux):
                report.append(f"{mid}: colouring {a} is not among the page's {len(aux)} aux palettes; skipped")
                continue
            sheet(frames, aux[a], pal).save(out / f"{mid}-{a}.png")
            colourings[str(a)] = f"{mid}-{a}.png"
        cut = {n: idx[:idx.index(-1)] if -1 in idx else idx for n, idx in anims.items()}
        (out / f"{mid}.json").write_text(json.dumps({
            "cell": [cw, ch], "anchor": [ax, ay], "columns": COLUMNS, "scale": CREATURE_SCALE,
            "anims": {n: v for n, v in cut.items() if v}, "colourings": colourings}, indent=1) + "\n")
    return report
