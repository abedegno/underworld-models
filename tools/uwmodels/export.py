"""Turns the port's model files into files people can edit and the site can show.

For each model in a folder of port files (CRnn.glb/.vox creatures, OBJnnn.glb/.vox items):
- port/uw1/: the port files, copied unchanged.
- models/uw1/editable/<id>.glb: the port glb with its palette-number texture turned into colours (items: main
  palette; creatures: the body's base aux palette), mesh, skin and clips untouched. Items with no glb have none.
- models/uw1/voxels/<id>.vox: a MagicaVoxel copy of an item's voxels in colour. Creatures have none: their voxels are
  animation frames, edited through the smooth model.
- site/data/uw1/<id>.uwvc: display voxels (uwvc.py); site/data/uw1/CRnn-<aux>.png: a creature's texture in each of
  its colourings.
- models/uw1/manifest.json: one entry per model.
"""
import colorsys
import csv
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

from . import game, gltf, magica, uwvx
from .uwvc import used_slots, write_uwvc

HUES = [(15, "red"), (40, "orange"), (52, "yellow"), (160, "green"), (200, "cyan"), (260, "blue"), (320, "purple"),
        (360, "red")]


def colour_word(rgb: np.ndarray) -> str:
    """A plain word for the main colour of an image: the most common hue among its colourful pixels, else grey."""
    px = rgb.reshape(-1, 3).astype(float) / 255
    hsv = np.array([colorsys.rgb_to_hsv(*p) for p in px[:: max(1, len(px) // 4000)]])
    lively = hsv[(hsv[:, 1] > 0.25) & (hsv[:, 2] > 0.15)]
    if len(lively) < len(hsv) * 0.1:
        return "grey"
    counts = {}
    for h in lively[:, 0] * 360:
        w = next(word for limit, word in HUES if h < limit)
        counts[w] = counts.get(w, 0) + 1
    return max(counts, key=counts.get)


def sha1(path: Path) -> str:
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()


def read_names(repo: Path) -> dict:
    with open(repo / "models/uw1/names.tsv") as f:
        return {r["id"]: r["name"] for r in csv.DictReader(f, delimiter="\t")}


def base_aux(body: int, types) -> int:
    """The colouring a body's model was made in: that of the lowest-numbered creature type using the body."""
    using = sorted((t, aux) for t, b, aux in types if b == body)
    return using[0][1] if using else 0


def magica_voxels(model: uwvx.Model, pal) -> tuple:
    f = next(iter(model.clips.values()))[0]
    return f[:, :3].astype(int), pal[f[:, 3]]


def run(uw1, src_port, repo, pal=None, aux_for=None, types=None) -> list[str]:
    src_port, repo = Path(src_port), Path(repo)
    pal = game.main_palette(uw1) if pal is None else pal
    aux_for = (lambda body: game.aux_palettes(uw1, body)) if aux_for is None else aux_for
    types = game.creature_types(uw1) if types is None else types
    names = read_names(repo)
    port, editable, voxels, data = (repo / p for p in ("port/uw1", "models/uw1/editable", "models/uw1/voxels",
                                                       "site/data/uw1"))
    for d in (port, editable, voxels, data):
        d.mkdir(parents=True, exist_ok=True)
    for p in sorted(src_port.iterdir()):
        if p.suffix in (".glb", ".vox"):
            shutil.copyfile(p, port / p.name)
    manifest, report = [], []
    for vox in sorted(port.glob("*.vox")):
        mid = vox.stem
        model = uwvx.read(vox)
        glb = port / f"{mid}.glb"
        entry = {"id": mid, "name": names.get(mid, mid), "variant_of": None}
        if mid not in names:
            report.append(f"{mid}: no name in names.tsv")
        if mid.startswith("CR"):
            body = int(mid[2:], 8)
            aux = aux_for(body)
            base = base_aux(body, types)
            g = gltf.read(glb)
            slots = gltf.texture(g)[..., 0]
            gltf.write(gltf.with_texture(g, pal[aux[base][slots]]), editable / f"{mid}.glb")
            auxes = sorted({a for t, b, a in types if b == body})
            changing = [s for s in range(32) if len({int(aux[a][s]) for a in auxes}) > 1]
            moving = np.isin(slots, changing)   # texels whose colour differs between colourings
            pairs = []   # (colouring, its slot-to-colour table), one per aux palette in use
            for a in auxes:
                img = pal[aux[a][slots]]
                Image.fromarray(img).save(data / f"{mid}-{a}.png")
                word = colour_word(img[moving]) if len(auxes) > 1 and moving.any() else ""
                name = names.get(f"{mid}:{a}") or (f"{entry['name']}, {word}" if word else entry["name"])
                pairs.append(({"aux": a, "name": name}, {s: tuple(pal[aux[a][s]]) for s in used_slots(model)}))
            words = [c["name"] for c, _ in pairs]
            seen = {}
            for c, _ in pairs:   # two colourings given the same word get numbers
                if words.count(c["name"]) > 1 and f"{mid}:{c['aux']}" not in names:
                    seen[c["name"]] = seen.get(c["name"], 0) + 1
                    c["name"] += f" {seen[c['name']]}"
            pairs.sort(key=lambda p: p[0]["aux"] != base)   # the base colouring first
            colourings = [c for c, _ in pairs]
            write_uwvc(model, [t for _, t in pairs], data / f"{mid}.uwvc")
            entry.update(kind="creature", master="smooth", colourings=colourings)
        else:
            if glb.exists():
                g = gltf.read(glb)
                gltf.write(gltf.with_texture(g, pal[gltf.texture(g)[..., 0]]), editable / f"{mid}.glb")
            v, c = magica_voxels(model, pal)
            magica.write(voxels / f"{mid}.vox", v, c)
            write_uwvc(model, [{s: tuple(pal[s]) for s in used_slots(model)}], data / f"{mid}.uwvc")
            entry.update(kind="item", master="smooth" if glb.exists() else "voxel", colourings=[],
                         voxel_sha1=sha1(voxels / f"{mid}.vox"))
        manifest.append(entry)
    (repo / "models/uw1/manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return report
