"""A small synthetic port folder and game colours for tests: a made-up palette, not the game's."""
import numpy as np

from helpers import quad
from uwmodels import gltf, uwvx

PAL = np.stack([np.arange(256), 255 - np.arange(256), (np.arange(256) * 7) % 256], 1).astype(np.uint8)
AUX = {0: np.stack([np.arange(32) + 10, np.arange(32) + 100]).astype(np.uint8)}
TYPES = [(0x46, 0, 0), (0x4C, 0, 1)]
NAMES = "id\tname\nOBJ090\tlantern\nOBJ0c1\tgrass tufts\nCR00\tgoblin\n"


def item_texture():
    return np.repeat(np.array([[20, 21, 22, 23]] * 4, np.uint8)[..., None], 3, 2)


def creature_texture():
    t = np.array([[0, 1, 2, 3]] * 4, np.uint8)
    return np.repeat(t[..., None], 3, 2)


def make_port(d):
    d.mkdir(parents=True, exist_ok=True)
    gltf.write(quad(item_texture()), d / "OBJ090.glb")
    uwvx.write(uwvx.Model(0.01, (-1, 0, -1), {"still": [np.array([[0, 0, 0, 20], [1, 0, 1, 23]], np.uint8)]}),
               d / "OBJ090.vox")
    uwvx.write(uwvx.Model(0.01, (0, 0, 0), {"still": [np.array([[0, 0, 0, 30], [0, 1, 0, 31]], np.uint8)]}),
               d / "OBJ0c1.vox")
    gltf.write(quad(creature_texture(), clips={"idle": [0, 1], "walking": [0, .5, 1]}, joints=2), d / "CR00.glb")
    f = np.array([[0, 0, 0, 1], [0, 1, 0, 2]], np.uint8)
    uwvx.write(uwvx.Model(0.0075, (0, 0, 0), {"idle": [f, f[:1]], "walking": [f]}), d / "CR00.vox")
    return d


def make_repo(tmp):
    src = make_port(tmp / "src")
    repo = tmp / "repo"
    (repo / "models/uw1").mkdir(parents=True)
    (repo / "models/uw1/names.tsv").write_text(NAMES)
    return src, repo
