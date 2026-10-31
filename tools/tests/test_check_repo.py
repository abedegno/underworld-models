from pathlib import Path

import numpy as np
from PIL import Image

from check_repo import problems


def write(root, rel, data=b"x"):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


def png(root, rel, w, h):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.zeros((h, w, 4), np.uint8)).save(p)


def test_flags_game_files(tmp_path):
    for rel in ["DATA/PALS.DAT", "CRIT/CR00PAGE.N00", "OBJECTS.GR", "x.ark", "ASSOC.ANM"]:
        write(tmp_path, rel)
    found = problems(tmp_path)
    assert len(found) == 5
    for name in ["PALS.DAT", "CR00PAGE.N00", "OBJECTS.GR", "x.ark", "ASSOC.ANM"]:
        assert any(name in f for f in found)


def test_flags_large_file(tmp_path):
    write(tmp_path, "port/uw1/big.glb", b"\0" * (16 * 1024 * 1024))
    found = problems(tmp_path)
    assert len(found) == 1 and "big.glb" in found[0]


def test_flags_tiny_png_outside_site(tmp_path):
    png(tmp_path, "models/obj090.png", 16, 16)
    found = problems(tmp_path)
    assert len(found) == 1 and "obj090.png" in found[0]


def test_clean_tree(tmp_path):
    write(tmp_path, "README.md", b"hello")
    write(tmp_path, "port/uw1/OBJ090.glb", b"glTF")
    png(tmp_path, "site/thumbs/uw1/OBJ090.png", 256, 256)
    assert problems(tmp_path) == []


def test_ignores_git_and_venv(tmp_path):
    write(tmp_path, ".git/objects/x.dat")
    write(tmp_path, ".venv/lib/thing.dat")
    assert problems(tmp_path) == []
