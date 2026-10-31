import os
import struct
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from rle import encode_rle
from uwmodels import sprites

UW1 = os.environ.get("UW1_DIR")
needs_game = pytest.mark.skipif(not UW1, reason="needs UW1_DIR, the player's own UW1 folder")


def page(slotbase, anims, frames, pals=1):
    """A page file: anims is a list of (slot, [8 frame indices or 255]); frames a list of (slots (h, w), hx, hy)."""
    nslots = max(s for s, _ in anims) + 1
    enabled = {s for s, _ in anims}
    head = bytearray([slotbase, nslots] + [0 if s in enabled else 255 for s in range(nslots)])
    head.append(len(anims))
    for _, idx in sorted(anims):
        head += bytes(idx)
    head.append(pals)
    head += bytes(range(32)) * pals
    head += bytes([len(frames), 0])
    table_at = len(head)
    head += b"\0" * (2 * len(frames))
    for k, (img, hx, hy) in enumerate(frames):
        struct.pack_into("<H", head, table_at + 2 * k, len(head))
        data, n = encode_rle(img, 4)
        head += bytes([img.shape[1], img.shape[0], hx, hy, 8]) + struct.pack("<H", n) + data
    return bytes(head)


def test_rle_round_trip_4_and_5_bits():
    rng = np.random.default_rng(3)
    for bits in (4, 5):
        px = rng.integers(0, 2 ** bits, 300)
        px[40:60] = 7   # a long repeat
        data, n = encode_rle(px, bits)
        assert np.array_equal(sprites.decode_rle(data, 0, bits, len(px), n), px)


def test_read_page_synthetic():
    a = np.array([[0, 1, 1], [2, 2, 0]], np.uint8)
    b = np.arange(20, dtype=np.uint8).reshape(4, 5) % 16
    p = sprites.read_page(page(0x20, [(0, [0, 1] + [255] * 6), (1, [1] + [255] * 7)], [(a, 1, 2), (b, 2, 4)]))
    assert p.slotbase == 0x20
    assert p.anims == {"idle_rear": [0, 1, -1, -1, -1, -1, -1, -1], "idle_rear_right": [1, -1, -1, -1, -1, -1, -1, -1]}
    assert [(f.width, f.height, f.hot_x, f.hot_y) for f in p.frames] == [(3, 2, 1, 2), (5, 4, 2, 4)]
    assert np.array_equal(p.frames[0].slots, a) and np.array_equal(p.frames[1].slots, b)
    assert p.aux.shape == (1, 32)


def test_body_merges_pages_first_wins(tmp_path):
    crit = tmp_path / "CRIT"
    crit.mkdir()
    one = np.full((2, 2), 3, np.uint8)
    two = np.full((2, 2), 9, np.uint8)
    (crit / "CR00PAGE.N00").write_bytes(page(0x20, [(0, [0] + [255] * 7)], [(one, 1, 2)]))
    (crit / "CR00PAGE.N01").write_bytes(page(0x20, [(0, [0] + [255] * 7), (1, [0] + [255] * 7)], [(two, 1, 2)]))
    anims, aux, frames = sprites.read_body(tmp_path, 0)
    assert frames[anims["idle_rear"][0]].slots[0, 0] == 3   # page 0's
    assert frames[anims["idle_rear_right"][0]].slots[0, 0] == 9   # only on page 1
    assert len(frames) == 2


@needs_game
def test_goblin_idle_has_8_views():
    anims, aux, frames = sprites.read_body(Path(UW1), 0)
    for v in ("rear", "rear_right", "right", "front_right", "front", "front_left", "left", "rear_left"):
        f = anims[f"idle_{v}"]
        assert f[0] >= 0 and (frames[f[0]].slots > 0).any(), v


@needs_game
def test_goblin_has_model_clips():
    anims, _, _ = sprites.read_body(Path(UW1), 0)
    assert {"idle_combat", "attack_bash", "death"} <= set(anims)


@needs_game
def test_objects_gr_lantern():
    icons = sprites.read_gr(Path(UW1))
    lantern = icons[0x90]
    assert lantern.shape[0] <= 16 and lantern.shape[1] <= 16 and lantern.shape[2] == 4
    assert (lantern[..., 3] > 0).any()
    known = Path(os.environ.get("UWMODELS_ICONS", "")) / "obj090.png"
    if known.is_file():   # the icons exported for the models, from the port
        want = np.asarray(Image.open(known).convert("RGBA"))
        assert np.array_equal(want[..., 3] > 0, lantern[..., 3] > 0)
        assert np.array_equal(want[want[..., 3] > 0][:, :3], lantern[lantern[..., 3] > 0][:, :3])
