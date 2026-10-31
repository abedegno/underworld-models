import json
import re
import sys
from pathlib import Path

import pytest

from synth import AUX, PAL, TYPES, make_repo
from uwmodels import export, thumbs

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "site"))
import build  # noqa: E402


@pytest.fixture
def repo(tmp_path):
    src, repo = make_repo(tmp_path)
    shutil_site(repo)
    export.run(None, src, repo, pal=PAL, aux_for=AUX.get, types=TYPES)
    (repo / "site/thumbs/uw1").mkdir(parents=True, exist_ok=True)
    (repo / "shots/uw1").mkdir(parents=True, exist_ok=True)
    for p in (repo / "site/data/uw1").glob("*.uwvc"):
        img = thumbs.render(p, px=128)
        img.save(repo / f"site/thumbs/uw1/{p.stem}.png")
        img.save(repo / f"shots/uw1/{p.stem}.png")
    return repo


def shutil_site(repo):
    import shutil
    shutil.copytree(ROOT / "site", repo / "site", ignore=shutil.ignore_patterns("data", "thumbs", "__pycache__"))


def models(out):
    return json.loads((out / "data/models.json").read_text())


def test_models_json_complete(repo, tmp_path):
    out = tmp_path / "out"
    assert build.build(repo, out) == []
    ms = models(out)
    assert {m["id"] for m in ms} == {"OBJ090", "OBJ0c1", "CR00"}
    for m in ms:
        for k in ("thumb", "shot", "voxels", "download"):
            assert (out / m[k]).exists(), (m["id"], k)
        assert (m["smooth"] is None) == (m["id"] == "OBJ0c1")
        if m["smooth"]:
            assert (out / m["smooth"]).exists()
    cr = next(m for m in ms if m["id"] == "CR00")
    assert cr["clips"] == ["idle", "walking"] and len(cr["colourings"]) == 2
    assert all((out / c["texture"]).exists() for c in cr["colourings"])
    assert next(m for m in ms if m["id"] == "OBJ0c1")["download"].endswith("voxels/OBJ0c1.vox")


def test_broken_variant_skipped(repo, tmp_path):
    good, bad = repo / "variants/uw1/shiny", repo / "variants/uw1/broken"
    for d in (good, bad):
        d.mkdir(parents=True)
    (good / "variant.json").write_text('{"name": "shiny", "author": "someone", "of": ["OBJ090"]}')
    (bad / "variant.json").write_text('{"name": "broken", "author": "someone", "of": ["OBJ090"]}')
    import shutil
    shutil.copyfile(repo / "models/uw1/editable/OBJ090.glb", good / "OBJ090.glb")
    for sub in ("site/data/uw1/variants/shiny", "site/thumbs/uw1/variants/shiny"):
        (repo / sub).mkdir(parents=True)
    shutil.copyfile(repo / "site/data/uw1/OBJ090.uwvc", repo / "site/data/uw1/variants/shiny/OBJ090.uwvc")
    shutil.copyfile(repo / "site/thumbs/uw1/OBJ090.png", repo / "site/thumbs/uw1/variants/shiny/OBJ090.png")
    out = tmp_path / "out"
    report = build.build(repo, out)
    assert len(report) == 1 and "broken/OBJ090" in report[0] and "OBJ090.glb" in report[0]
    keys = [m["key"] for m in models(out)]
    assert "shiny/OBJ090" in keys and "broken/OBJ090" not in keys
    v = next(m for m in models(out) if m["key"] == "shiny/OBJ090")
    assert v["variant_of"] == "lantern" and (out / v["smooth"]).exists()


def test_scripts_pinned():
    for page in (ROOT / "site").glob("*.html"):
        text = page.read_text()
        urls = re.findall(r'(?:src|href)="(https?://[^"]+)"', text) + re.findall(r'"(https://cdn[^"]+)"', text)
        for url in urls:
            if "cdn" in url or url.endswith(".js"):
                assert re.search(r"@\d+\.\d+\.\d+/", url), (page.name, url)


def test_no_file_over_15mb_in_site(repo, tmp_path):
    out = tmp_path / "out"
    build.build(repo, out)
    assert all(p.stat().st_size <= 15 * 1024 * 1024 for p in out.rglob("*") if p.is_file())


def test_broken_variants_never_stop_the_build(repo, tmp_path):
    import shutil
    a, b, c = (repo / f"variants/uw1/{n}" for n in ("cut", "listy", "badvox"))
    for d in (a, b, c):
        d.mkdir(parents=True)
    good = (repo / "models/uw1/editable/OBJ090.glb").read_bytes()
    (a / "variant.json").write_text('{"name": "cut", "of": ["OBJ090"]}')
    (a / "OBJ090.glb").write_bytes(good[:30])   # a truncated glb
    (b / "variant.json").write_text('["OBJ090"]')   # json, but not an object
    (c / "variant.json").write_text('{"name": "badvox", "of": ["CR00"]}')
    shutil.copyfile(repo / "models/uw1/editable/OBJ090.glb", c / "CR00.glb")   # no clips: the voxels give them
    for n, mid in (("cut", "OBJ090"), ("badvox", "CR00")):
        for sub, ext in (("site/data/uw1/variants", ".uwvc"), ("site/thumbs/uw1/variants", ".png")):
            (repo / sub / n).mkdir(parents=True, exist_ok=True)
        (repo / f"site/thumbs/uw1/variants/{n}/{mid}.png").write_bytes((repo / "site/thumbs/uw1/OBJ090.png").read_bytes())
    (repo / "site/data/uw1/variants/cut/OBJ090.uwvc").write_bytes((repo / "site/data/uw1/OBJ090.uwvc").read_bytes())
    (repo / "site/data/uw1/variants/badvox/CR00.uwvc").write_bytes(b"UWVC\x01")   # truncated
    out = tmp_path / "out"
    report = build.build(repo, out)
    assert len(report) == 3, report
    assert {m["id"] for m in models(out)} == {"OBJ090", "OBJ0c1", "CR00"}
