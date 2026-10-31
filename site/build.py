"""Builds the site into an output folder: the pages, the model files they show, and data/models.json.

Usage: python site/build.py REPO OUT
Variants come from variants/uw1/<name>/: a variant.json ({"name", "author", "of"}), the variant's <id>.glb files,
and its display voxels in site/data/uw1/variants/<name>/<id>.uwvc (pack.py writes them). A variant that is missing a
file is skipped with a message, and the rest of the site is still built.
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from uwmodels import gltf  # noqa: E402
from uwmodels.uwvc import read_uwvc  # noqa: E402

GITHUB = "https://github.com/abedegno/underworld-models/blob/main/"


def clips_of(glb: Path, uwvc: Path):
    if glb and glb.exists():
        names = gltf.clip_names(gltf.read(glb))
        if names:
            return names
    return list(read_uwvc(uwvc)[0].clips) if uwvc.exists() else []


def faithful(repo: Path, e: dict) -> dict:
    mid = e["id"]
    glb = repo / f"models/uw1/editable/{mid}.glb"
    vox = repo / f"models/uw1/voxels/{mid}.vox"
    uwvc = repo / f"site/data/uw1/{mid}.uwvc"
    smooth = glb.exists()   # a voxel-master item may still have a smooth model to show
    source = f"models/uw1/editable/{mid}.glb" if e["master"] == "smooth" else f"models/uw1/voxels/{mid}.vox"
    return {
        "key": mid, "id": mid, "kind": e["kind"], "name": e["name"], "variant_of": None, "master": e["master"],
        "thumb": f"thumbs/uw1/{mid}.png",
        "shot": f"shots/uw1/{mid}.png" if (repo / f"shots/uw1/{mid}.png").exists() else None,
        "smooth": f"models/uw1/editable/{mid}.glb" if smooth else None,
        "voxels": f"data/uw1/{mid}.uwvc",
        "clips": clips_of(glb, uwvc) if e["kind"] == "creature" else [],
        "colourings": [{"name": c["name"], "texture": f"data/uw1/{mid}-{c['aux']}.png"} for c in e["colourings"]],
        "download": source, "github": GITHUB + source,
        "howto": GITHUB + ("docs/blender.md" if source.endswith(".glb") else "docs/magicavoxel.md"),
    }


def variants(repo: Path, known: dict, report: list) -> list:
    out = []
    root = repo / "variants/uw1"
    for vdir in sorted(root.glob("*/")) if root.exists() else []:
        try:
            info = json.loads((vdir / "variant.json").read_text())
            if not isinstance(info, dict) or not isinstance(info.get("of", []), list):
                raise ValueError('it must be an object with "of", a list of model ids')
        except (OSError, ValueError) as err:
            report.append(f"variants/uw1/{vdir.name}: skipped, its variant.json cannot be used ({err})")
            continue
        for mid in info.get("of", []):
            try:
                entry = variant_entry(repo, vdir, info, str(mid), known)
            except Exception as err:   # a broken file in one variant must never stop the site's build
                entry = f"skipped, it cannot be read ({type(err).__name__}: {err})"
            if isinstance(entry, str):
                report.append(f"variants/uw1/{vdir.name}/{mid}: {entry}")
            else:
                out.append(entry)
    return out


def variant_entry(repo, vdir, info, mid, known):
    """A variant's models.json entry, or a string saying why it is skipped."""
    glb, uwvc = vdir / f"{mid}.glb", repo / f"site/data/uw1/variants/{vdir.name}/{mid}.uwvc"
    thumb = repo / f"site/thumbs/uw1/variants/{vdir.name}/{mid}.png"
    if mid not in known:
        return "skipped, no faithful model of that name"
    missing = [p.name for p in (glb, uwvc, thumb) if not p.exists()]
    if missing:
        return f"skipped, missing {', '.join(missing)}"
    gltf.read(glb)
    read_uwvc(uwvc)
    base = known[mid]
    rel = f"variants/uw1/{vdir.name}/{mid}.glb"
    return {**base, "key": f"{vdir.name}/{mid}", "name": f"{base['name']} ({info.get('name', vdir.name)})",
            "variant_of": base["name"], "author": info.get("author"), "master": "smooth",
            "thumb": f"thumbs/uw1/variants/{vdir.name}/{mid}.png", "smooth": rel,
            "voxels": f"data/uw1/variants/{vdir.name}/{mid}.uwvc",
            "clips": clips_of(glb, uwvc) if base["kind"] == "creature" else [],
            "colourings": [], "download": rel, "github": GITHUB + rel, "howto": GITHUB + "docs/blender.md"}


def build(repo: Path, out: Path) -> list:
    repo, out = Path(repo), Path(out)
    report = []
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(repo / "site", out, ignore=shutil.ignore_patterns("build.py", "__pycache__"))
    for sub in ("models/uw1/editable", "models/uw1/voxels", "shots/uw1"):
        if (repo / sub).exists():
            shutil.copytree(repo / sub, out / sub)
    manifest = json.loads((repo / "models/uw1/manifest.json").read_text())
    entries = [faithful(repo, e) for e in manifest]
    known = {e["id"]: e for e in entries}
    vs = variants(repo, known, report)
    for v in vs:
        dst = out / v["smooth"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo / v["smooth"], dst)
    (out / "data").mkdir(exist_ok=True)
    order = sorted(entries, key=lambda e: e["name"].lower())
    with_variants = []
    for e in order:
        with_variants.append(e)
        with_variants += [v for v in vs if v["id"] == e["id"]]
    (out / "data/models.json").write_text(json.dumps(with_variants, separators=(",", ":")))
    (out / ".nojekyll").write_text("")
    return report


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    for line in build(Path(sys.argv[1]), Path(sys.argv[2])):
        print(line)
