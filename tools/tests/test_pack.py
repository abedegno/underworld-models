import json
import shutil

import numpy as np
import pytest

from synth import AUX, PAL, TYPES, make_repo
from uwmodels import export, gltf, magica, pack, uwvx


def setup(tmp_path, aux=AUX):
    src, repo = make_repo(tmp_path)
    export.run(None, src, repo, pal=PAL, aux_for=aux.get, types=TYPES)
    return repo


def go(repo, aux=AUX, **kw):
    return pack.run(None, repo, pal=PAL, aux_for=aux.get, types=TYPES, **kw)


def entry(repo, mid):
    return next(m for m in json.loads((repo / "models/uw1/manifest.json").read_text()) if m["id"] == mid)


def snapshot(repo):
    return {p.relative_to(repo): p.read_bytes() for p in (repo / "port").rglob("*") if p.is_file()}


def edit_texture(repo, mid, fn):
    p = repo / f"models/uw1/editable/{mid}.glb"
    g = gltf.read(p)
    t = gltf.texture(g)[..., :3].copy()
    gltf.write(gltf.with_texture(g, fn(t)), p)


def test_unchanged_round_trip_is_identical(tmp_path):
    repo = setup(tmp_path)
    before = snapshot(repo)
    report = go(repo)
    assert snapshot(repo) == before
    assert not any("snapped" in r for r in report)


def test_forced_pack_is_stable(tmp_path):
    repo = setup(tmp_path)
    go(repo, force=True)
    once = {k: uwvx.read(repo / k) if k.suffix == ".vox" else gltf.texture(gltf.read(repo / k))
            for k in snapshot(repo)}
    go(repo, force=True)
    for k, was in once.items():
        if k.suffix == ".vox":
            assert uwvx.tobytes(uwvx.read(repo / k)) == uwvx.tobytes(was), k
        else:
            assert np.array_equal(gltf.texture(gltf.read(repo / k)), was), k


def test_painted_colour_snaps_and_reports(tmp_path):
    repo = setup(tmp_path)

    def paint(t):
        t[0, 0] = (1, 2, 3)
        return t
    edit_texture(repo, "OBJ090", paint)
    report = go(repo)
    idx = gltf.texture(gltf.read(repo / "port/uw1/OBJ090.glb"))[..., 0]
    want = int(((PAL.astype(int) - (1, 2, 3)) ** 2).sum(1).argmin())
    assert idx[0, 0] == want and idx[0, 1] == 21
    assert any("OBJ090" in r and "1 texel" in r and "snapped" in r for r in report)


def test_creature_shared_colour_keeps_old_slot(tmp_path):
    aux = {0: AUX[0].copy()}
    aux[0][0][2] = aux[0][0][1]   # slots 1 and 2 share a colour in the base colouring
    repo = setup(tmp_path, aux)
    shared = PAL[aux[0][0][1]]

    def paint(t):
        t[0, 3] = shared   # a slot-3 texel repainted in the shared colour; its neighbour is slot 2
        return t
    edit_texture(repo, "CR00", paint)
    go(repo, aux)
    slots = gltf.texture(gltf.read(repo / "port/uw1/CR00.glb"))[..., 0]
    assert slots[1, 1] == 1 and slots[1, 2] == 2   # untouched texels keep their slots
    assert slots[0, 3] == 2


def test_creature_refuses_changed_texture_size(tmp_path):
    repo = setup(tmp_path)
    edit_texture(repo, "CR00", lambda t: np.repeat(np.repeat(t, 2, 0), 2, 1))
    with pytest.raises(pack.PackError, match="CR00.*texture size"):
        go(repo)


def test_creature_refuses_changed_uvs(tmp_path):
    repo = setup(tmp_path)
    p = repo / "models/uw1/editable/CR00.glb"
    g = gltf.read(p)
    i = g.json["meshes"][0]["primitives"][0]["attributes"]["TEXCOORD_0"]
    uv = gltf.accessor(g, i).copy()
    uv[0] = (0.3, 0.3)
    g = gltf.with_views(g, {g.json["accessors"][i]["bufferView"]: uv.astype(np.float32).tobytes()})
    gltf.write(g, p)
    with pytest.raises(pack.PackError, match="CR00.*UV layout"):
        go(repo)


def test_size_change_warns(tmp_path):
    repo = setup(tmp_path)
    p = repo / "models/uw1/editable/OBJ090.glb"
    g = gltf.read(p)
    i = g.json["meshes"][0]["primitives"][0]["attributes"]["POSITION"]
    v = gltf.accessor(g, i) * 1.5
    g = gltf.with_views(g, {g.json["accessors"][i]["bufferView"]: v.astype(np.float32).tobytes()})
    gltf.write(g, p)
    report = go(repo)
    assert any("OBJ090" in r and "size" in r for r in report)


def test_voxel_master_never_overwritten(tmp_path):
    repo = setup(tmp_path)
    shutil.copyfile(repo / "models/uw1/editable/OBJ090.glb", repo / "models/uw1/editable/OBJ0c1.glb")
    before = (repo / "port/uw1/OBJ0c1.vox").read_bytes()
    report = go(repo, force=True)
    assert (repo / "port/uw1/OBJ0c1.vox").read_bytes() == before
    assert (repo / "port/uw1/OBJ0c1.glb").exists()   # the new smooth model is used for the port's model mode only
    assert entry(repo, "OBJ0c1")["master"] == "voxel"


def test_magica_edit_switches_master(tmp_path):
    repo = setup(tmp_path)
    src = repo / "models/uw1/voxels/OBJ090.vox"
    v, c = magica.read(src)
    c[0] = PAL[40]
    magica.write(src, v, c)
    report = go(repo)
    assert entry(repo, "OBJ090")["master"] == "voxel"
    assert any("OBJ090" in r and "voxel" in r for r in report)
    m = uwvx.read(repo / "port/uw1/OBJ090.vox").clips["still"][0]
    assert 40 in m[:, 3].tolist()
    # the smooth model no longer writes this item's voxels
    edit_texture(repo, "OBJ090", lambda t: t[::-1].copy())
    before = (repo / "port/uw1/OBJ090.vox").read_bytes()
    go(repo)
    assert (repo / "port/uw1/OBJ090.vox").read_bytes() == before


def test_variant_packs_into_its_own_folder(tmp_path):
    repo = setup(tmp_path)
    vdir = repo / "variants/uw1/shiny"
    vdir.mkdir(parents=True)
    shutil.copyfile(repo / "models/uw1/editable/OBJ090.glb", vdir / "OBJ090.glb")
    (vdir / "variant.json").write_text('{"name": "shiny", "author": "someone", "of": ["OBJ090"]}')
    before = snapshot(repo)
    go(repo, variant="shiny")
    assert {k: v for k, v in snapshot(repo).items() if k.parts[0] == "port"} == before
    assert (vdir / "port/OBJ090.glb").exists() and (vdir / "port/OBJ090.vox").exists()
