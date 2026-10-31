import json

import numpy as np
import pytest

from synth import AUX, PAL, TYPES, creature_texture, item_texture, make_repo
from uwmodels import export, gltf, magica, uwvx
from uwmodels.uwvc import read_uwvc


@pytest.fixture
def repo(tmp_path):
    src, repo = make_repo(tmp_path)
    export.run(None, src, repo, pal=PAL, aux_for=AUX.get, types=TYPES)
    return src, repo


def manifest(repo):
    return {m["id"]: m for m in json.loads((repo / "models/uw1/manifest.json").read_text())}


def test_item_texture_is_palette_colours(repo):
    _, r = repo
    tex = gltf.texture(gltf.read(r / "models/uw1/editable/OBJ090.glb"))[..., :3]
    assert np.array_equal(tex, PAL[item_texture()[..., 0]])


def test_creature_keeps_clips_and_skin(repo):
    src, r = repo
    a, b = gltf.read(src / "CR00.glb"), gltf.read(r / "models/uw1/editable/CR00.glb")
    assert gltf.clip_names(b) == ["idle", "walking"]
    assert len(b.json["skins"][0]["joints"]) == len(a.json["skins"][0]["joints"]) == 2
    tex = gltf.texture(b)[..., :3]
    assert np.array_equal(tex, PAL[AUX[0][0][creature_texture()[..., 0]]])


def test_creature_colourings_written(repo):
    from PIL import Image
    _, r = repo
    m = manifest(r)["CR00"]
    assert [c["aux"] for c in m["colourings"]] == [0, 1]
    for aux in (0, 1):
        img = np.asarray(Image.open(r / f"site/data/uw1/CR00-{aux}.png"))[..., :3]
        assert np.array_equal(img, PAL[AUX[0][aux][creature_texture()[..., 0]]])


def test_voxel_only_item_is_voxel_master(repo):
    m = manifest(repo[1])
    assert m["OBJ0c1"]["master"] == "voxel" and m["OBJ090"]["master"] == "smooth"
    assert m["CR00"]["master"] == "smooth" and m["CR00"]["kind"] == "creature"
    assert m["OBJ090"]["name"] == "lantern"
    assert not (repo[1] / "models/uw1/editable/OBJ0c1.glb").exists()


def test_magica_source_matches_port_voxels(repo):
    src, r = repo
    v, c = magica.read(r / "models/uw1/voxels/OBJ090.vox")
    port = uwvx.read(src / "OBJ090.vox").clips["still"][0]
    assert {tuple(x) for x in v.tolist()} == {tuple(x) for x in port[:, :3].tolist()}
    assert {tuple(x) for x in c.tolist()} == {tuple(PAL[s]) for s in port[:, 3]}
    assert not (r / "models/uw1/voxels/CR00.vox").exists()
    assert len(manifest(r)["OBJ090"]["voxel_sha1"]) == 40


def test_uwvc_has_only_used_colours(repo):
    _, r = repo
    model, colourings = read_uwvc(r / "site/data/uw1/CR00.uwvc")
    assert list(model.clips) == ["idle", "walking"]
    assert len(colourings) == 2
    assert sorted(colourings[1]) == [1, 2]
    assert colourings[1][2] == tuple(PAL[AUX[0][1][2]])


def test_port_files_copied_byte_identical(repo):
    src, r = repo
    for p in src.iterdir():
        assert (r / "port/uw1" / p.name).read_bytes() == p.read_bytes()


def test_editable_material_has_no_glow(tmp_path):
    # two Meshy bodies came with emissiveFactor 1 and specular extensions: they showed plain white in the viewer
    src, repo = make_repo(tmp_path)
    p = src / "CR00.glb"
    g = gltf.read(p)
    g.json["materials"][0].update(emissiveFactor=[1, 1, 1], extensions={"KHR_materials_specular": {}, "KHR_materials_ior": {}})
    g.json["extensionsUsed"] = ["KHR_materials_specular", "KHR_materials_ior"]
    gltf.write(g, p)
    export.run(None, src, repo, pal=PAL, aux_for=AUX.get, types=TYPES)
    j = gltf.read(repo / "models/uw1/editable/CR00.glb").json
    m = j["materials"][0]
    assert "emissiveFactor" not in m and "emissiveTexture" not in m and "extensions" not in m
    assert "extensionsUsed" not in j
    assert m["pbrMetallicRoughness"]["baseColorTexture"] == {"index": 0}
    assert (repo / "port/uw1/CR00.glb").read_bytes() == p.read_bytes()   # the port's own file is left as it is
