import os
from pathlib import Path

import pytest

from uwmodels import game

UW1 = os.environ.get("UW1_DIR")
needs_game = pytest.mark.skipif(not UW1, reason="needs UW1_DIR, the player's own UW1 folder")


@needs_game
def test_main_palette_shape():
    pal = game.main_palette(Path(UW1))
    assert pal.shape == (256, 3) and pal.dtype.name == "uint8"
    assert pal.max() > 200   # stored as 0..63, scaled by 4


@needs_game
def test_goblin_aux_palettes():
    aux = game.aux_palettes(Path(UW1), 0)
    assert aux.shape[0] >= 4 and aux.shape[1] == 32


@needs_game
def test_goblins_share_body_0():
    types = {t: (body, aux) for t, body, aux in game.creature_types(Path(UW1))}
    assert [types[t] for t in (0x46, 0x4C, 0x4D, 0x4E)] == [(0, 0), (0, 1), (0, 2), (0, 3)]
    assert len(types) == 64
