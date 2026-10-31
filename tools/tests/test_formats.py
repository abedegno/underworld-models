import os
import struct
from pathlib import Path

import numpy as np
import pytest

from helpers import make_glb, quad
from uwmodels import gltf, magica, uwvx


def test_uwvx_round_trip(tmp_path):
    a = np.array([[1, 2, 3, 4], [5, 6, 7, 8], [0, 0, 0, 31]], np.uint8)
    m = uwvx.Model(0.0075, (-3, 0, 2), {"idle": [a, np.zeros((0, 4), np.uint8)], "walking": [a[:1]]})
    p = tmp_path / "a.vox"
    uwvx.write(m, p)
    raw = p.read_bytes()
    assert raw[:4] == b"UWVX" and raw[4] == 1
    back = uwvx.read(p)
    assert back.size == pytest.approx(0.0075) and back.origin == (-3, 0, 2)
    assert list(back.clips) == ["idle", "walking"]
    assert np.array_equal(back.clips["idle"][0], a) and len(back.clips["idle"][1]) == 0
    uwvx.write(back, tmp_path / "b.vox")
    assert (tmp_path / "b.vox").read_bytes() == raw


@pytest.mark.skipif(not os.environ.get("UWMODELS_PORT"), reason="needs UWMODELS_PORT, a folder of port files")
def test_uwvx_reads_port_file():
    m = uwvx.read(Path(os.environ["UWMODELS_PORT"]) / "CR00.vox")
    assert list(m.clips)[0].startswith("idle")
    assert all(f.shape[1] == 4 for frames in m.clips.values() for f in frames)
    for p in sorted(Path(os.environ["UWMODELS_PORT"]).glob("*.vox")):
        assert uwvx.tobytes(uwvx.read(p)) == p.read_bytes(), p.name


def test_magica_round_trip(tmp_path):
    rng = np.random.default_rng(1)
    vox = rng.integers(0, 20, (10, 3))
    vox = np.unique(vox, axis=0)
    cols = np.array([[255, 0, 0], [0, 255, 0], [0, 0, 255]], np.uint8)[np.arange(len(vox)) % 3]
    p = tmp_path / "m.vox"
    magica.write(p, vox, cols)
    raw = p.read_bytes()
    assert raw[:4] == b"VOX " and struct.unpack("<i", raw[4:8])[0] == 150
    i = raw.index(b"XYZI")
    first = np.frombuffer(raw, np.uint8, 4, i + 16)
    assert (first[0], first[1], first[2]) == (vox[0][0], vox[0][2], vox[0][1])   # MagicaVoxel is z up
    v2, c2 = magica.read(p)
    got = {tuple(v) + tuple(c) for v, c in zip(v2.tolist(), c2.tolist())}
    assert got == {tuple(v) + tuple(c) for v, c in zip(vox.tolist(), cols.tolist())}


def test_magica_rejects_256_colours(tmp_path):
    vox = np.array([[i % 16, i // 16, 0] for i in range(256)])
    cols = np.array([[i, 0, 0] for i in range(256)], np.uint8)
    with pytest.raises(ValueError):
        magica.write(tmp_path / "m.vox", vox, cols)


def test_magica_rejects_too_big(tmp_path):
    with pytest.raises(ValueError):
        magica.write(tmp_path / "m.vox", np.array([[0, 0, 0], [256, 0, 0]]), np.zeros((2, 3), np.uint8))


def test_glb_texture_round_trip(tmp_path):
    tex = np.zeros((4, 4, 3), np.uint8)
    g = quad(tex)
    new = np.arange(48, dtype=np.uint8).reshape(4, 4, 3)
    g2 = gltf.with_texture(g, new)
    p = tmp_path / "q.glb"
    gltf.write(g2, p)
    back = gltf.read(p)
    assert np.array_equal(gltf.texture(back)[..., :3], new)
    assert np.allclose(gltf.accessor(back, 0), gltf.accessor(g, 0))
    assert back.json["buffers"][0]["byteLength"] == len(back.bin)


def test_accessor_stride():
    g = quad(np.zeros((2, 2, 3), np.uint8))
    # rewrite the positions as an interleaved view: x, y, z then 4 bytes of padding per vertex
    pos = gltf.accessor(g, 0).astype(np.float32)
    inter = np.zeros((4, 4), np.float32)
    inter[:, :3] = pos
    j = g.json
    j["bufferViews"].append({"buffer": 0, "byteOffset": len(g.bin), "byteLength": inter.nbytes, "byteStride": 16})
    j["accessors"][0]["bufferView"] = len(j["bufferViews"]) - 1
    g2 = gltf.Glb(j, g.bin + inter.tobytes())
    assert np.allclose(gltf.accessor(g2, 0), pos)


def test_clip_names():
    g = quad(np.zeros((2, 2, 3), np.uint8), clips={"idle": [0, 1], "walking": [0, .5]}, joints=1)
    assert gltf.clip_names(g) == ["idle", "walking"]
