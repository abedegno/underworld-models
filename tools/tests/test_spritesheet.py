import json

import numpy as np
from PIL import Image

from synth import PAL, make_repo, AUX, TYPES
from uwmodels import export, spritesheet
from uwmodels.sprites import Frame


def frame(w, h, hx, hy, v=1):
    return Frame(w, h, hx, hy, np.full((h, w), v, np.uint8))


def test_layout_aligns_hotspots():
    fs = [frame(4, 6, 2, 6), frame(8, 3, 5, 3)]
    cw, ch, ax, ay, offs = spritesheet.layout(fs)
    for f, (ox, oy) in zip(fs, offs):
        assert (ox + f.hot_x, oy + f.hot_y) == (ax, ay)
        assert ox >= 0 and oy >= 0 and ox + f.width <= cw and oy + f.height <= ch


def test_sheet_colours_and_transparency():
    f = Frame(2, 1, 0, 1, np.array([[0, 3]], np.uint8))
    aux = np.arange(32, dtype=np.uint8) + 100
    aux[0] = 0   # as in the game's aux palettes
    img = np.asarray(spritesheet.sheet([f], aux, PAL))
    assert img[0, 0, 3] == 0
    assert tuple(img[0, 1, :3]) == tuple(PAL[103]) and img[0, 1, 3] == 255


def body_reader(body):
    anims = {"idle_front": [0, 1, -1, -1, -1, -1, -1, -1], "attack_bash": [1, -1, 0, -1, -1, -1, -1, -1]}
    return anims, np.stack([np.arange(32), np.arange(32) + 1]).astype(np.uint8), [frame(2, 2, 1, 2), frame(3, 2, 1, 2, 2)]


def setup(tmp_path):
    src, repo = make_repo(tmp_path)
    export.run(None, src, repo, pal=PAL, aux_for=AUX.get, types=TYPES)
    icons = [np.zeros((4, 4, 4), np.uint8) for _ in range(256)]
    icons[0x90][1, 1] = (9, 9, 9, 255)
    return repo, icons


def test_json_lists_stop_at_first_gap(tmp_path):
    repo, icons = setup(tmp_path)
    report = spritesheet.export(None, repo, pal=PAL, body_reader=body_reader, icons=icons)
    j = json.loads((repo / "site/sprites/uw1/CR00.json").read_text())
    assert j["anims"] == {"idle_front": [0, 1], "attack_bash": [1]}
    assert j["scale"] == 0.015 and j["columns"] == 16
    assert set(j["colourings"]) == {"0", "1"}
    assert Image.open(repo / "site/sprites/uw1/CR00-1.png").size == (2 * j["cell"][0], j["cell"][1])
    assert (repo / "site/sprites/uw1/OBJ090.png").exists() and (repo / "site/sprites/uw1/OBJ0c1.png").exists()
    assert report == []


def test_export_skips_missing_aux(tmp_path):
    repo, icons = setup(tmp_path)
    mp = repo / "models/uw1/manifest.json"
    m = json.loads(mp.read_text())
    next(e for e in m if e["id"] == "CR00")["colourings"].append({"aux": 5, "name": "x"})   # the page has 2
    mp.write_text(json.dumps(m))
    report = spritesheet.export(None, repo, pal=PAL, body_reader=body_reader, icons=icons)
    assert any("CR00" in r and "5" in r for r in report)
    assert not (repo / "site/sprites/uw1/CR00-5.png").exists()
    assert (repo / "site/sprites/uw1/CR00-0.png").exists()


def test_transparent_where_the_aux_gives_index_0():
    # the game draws a pixel only where its aux palette entry is not main index 0, whatever the slot
    f = Frame(3, 1, 0, 1, np.array([[0, 4, 5]], np.uint8))
    aux = np.arange(32, dtype=np.uint8) + 100
    aux[0] = aux[4] = 0
    img = np.asarray(spritesheet.sheet([f], aux, PAL))
    assert img[0, 0, 3] == 0 and img[0, 1, 3] == 0 and img[0, 2, 3] == 255
