"""Turns edited models back into the port's files: the reverse of export.py.

Only models whose editable file or MagicaVoxel copy changed since the last export or pack are rebuilt (the manifest
keeps each file's sha1); force rebuilds them all.
- Item, smooth master: the texture's colours become main palette indices (a texel that still shows its old colour
  keeps its old index; any other takes the nearest palette colour), then the voxels are made from the model at 0.01,
  at the model's own size.
- Item, voxel master: the MagicaVoxel copy becomes the port's voxels, nearest palette colour for each, centred on x and
  z with its lowest voxel at y = 0. The smooth model, if any, still makes the port's .glb but never the voxels.
  Editing the MagicaVoxel copy of a smooth item makes it a voxel master.
- Creature: the texture must keep its size and UV layout. A texel still showing its base colour keeps its slot; a
  repainted one takes the slot whose base colour is nearest, preferring its old slot, then the slot most common
  around it. Then every key frame is voxelised at 0.0075.
Colours outside the palette are snapped to it, and the editable file is rewritten with the snapped colours, so it
shows what the port shows.
"""
import json
from pathlib import Path

import numpy as np

from . import export, game, gltf, magica, thumbs, uwvx, voxelise
from .uwvc import used_slots, write_uwvc


class PackError(Exception):
    pass


def distances(colours: np.ndarray, table: np.ndarray) -> np.ndarray:
    return ((colours.reshape(-1, 1, 3).astype(int) - table.reshape(1, -1, 3).astype(int)) ** 2).sum(-1)


def to_indices(tex: np.ndarray, pal: np.ndarray, old: np.ndarray = None):
    """(h, w, 3) colours to palette indices; returns (indices, how many texels were not palette colours)."""
    d = distances(tex[..., :3], pal)
    idx = d.argmin(1).reshape(tex.shape[:2])
    if old is not None and old.shape == idx.shape:
        keep = (tex[..., :3] == pal[old]).all(-1)
        idx[keep] = old[keep]
    return idx.astype(np.uint8), int((d.min(1) > 0).sum())


def recover_slots(tex, old, base):
    """A creature's slots from its edited texture, its old slot map and its base colouring's 32 colours."""
    d = distances(tex[..., :3], base).reshape(*old.shape, len(base))
    slots = old.copy()
    changed = ~(tex[..., :3] == base[old]).all(-1)
    h, w = old.shape
    for y, x in zip(*np.nonzero(changed)):
        cands = np.flatnonzero(d[y, x] == d[y, x].min())
        if old[y, x] in cands:
            continue
        near = old[max(0, y - 1):y + 2, max(0, x - 1):x + 2].ravel()
        counts = [(near == c).sum() for c in cands]
        slots[y, x] = cands[int(np.argmax(counts))]
    return slots.astype(np.uint8), int((d.reshape(-1, len(base)).min(1) > 0).sum())


def uv_set(glb):
    _, pr = voxelise.mesh(glb)
    uv = gltf.accessor(glb, pr["attributes"]["TEXCOORD_0"])
    return {tuple(r) for r in np.round(uv, 4).tolist()}


def extent(model: uwvx.Model, clip: str = None) -> float:
    f = model.clips[clip][0] if clip in model.clips else next(iter(model.clips.values()))[0]
    return float((f[:, :3].max(0).astype(int) - f[:, :3].min(0) + 1).max() * model.size) if len(f) else 0.0


def size_note(mid, old: uwvx.Model, new: uwvx.Model):
    first = next(iter(old.clips))   # the same clip in both, whatever order the new file has them in
    a, b = extent(old, first), extent(new, first)
    if a and abs(b / a - 1) > 0.1:
        return (f"{mid}: warning: its size changed from {a:.3f} to {b:.3f} units across, by more than a tenth; "
                "check it was not scaled by accident")
    return None


def from_magica(path, pal, old: uwvx.Model = None) -> tuple:
    v, c = magica.read(path)
    if not len(v):
        raise PackError(f"{path.name}: the MagicaVoxel model is empty")
    idx, snapped = to_indices(c.reshape(-1, 1, 3), pal)
    idx = idx.ravel()
    if old is not None:   # where a voxel kept its colour, keep its old index (two palette entries can look the same)
        f = next(iter(old.clips.values()))[0]
        was = {tuple(r[:3]): r[3] for r in f.astype(int).tolist()}
        for k, (p, col) in enumerate(zip(v.tolist(), c)):
            s = was.get(tuple(p))
            if s is not None and (pal[s] == col).all():
                idx[k] = s
    v = v - v.min(0)
    w = v.max(0) + 1
    origin = (-int(w[0] // 2), 0, -int(w[2] // 2))
    return uwvx.Model(0.01, origin, {"still": [np.c_[v, idx].astype(np.uint8)]}), snapped


def in_clip_order(glb, names):
    """The glb with its clips in the given order (Blender exports them alphabetically); clips not named go last."""
    anims = glb.json.get("animations", [])
    rank = {n: i for i, n in enumerate(names)}
    glb.json["animations"] = sorted(anims, key=lambda a: rank.get(a.get("name"), len(rank)))
    return glb


class Packer:
    def __init__(self, uw1, repo, pal=None, aux_for=None, types=None, force=False):
        self.repo = Path(repo)
        self.pal = game.main_palette(uw1) if pal is None else pal
        self.aux_for = (lambda body: game.aux_palettes(uw1, body)) if aux_for is None else aux_for
        self.types = game.creature_types(uw1) if types is None else types
        self.force = force
        self.names = export.read_names(self.repo)
        self.report = []
        self.refused = []
        r = self.repo
        self.port, self.editable, self.voxels, self.data = (r / "port/uw1", r / "models/uw1/editable",
                                                            r / "models/uw1/voxels", r / "site/data/uw1")
        self.thumbs = r / "site/thumbs/uw1"

    def changed(self, path: Path, known) -> bool:
        return path.exists() and (self.force or export.sha1(path) != known)

    def snapped(self, mid, n, what="texels", creature=False):
        if n:
            where = "this creature's 32 colours" if creature else "the game's palette"
            self.report.append(f"{mid}: {n} {what[:-1] if n == 1 else what} not among {where}, snapped to the "
                               "nearest of them")

    def thumb(self, uwvc: Path, dst: Path):
        dst.parent.mkdir(parents=True, exist_ok=True)
        thumbs.render(uwvc).save(dst)

    def repainted(self, mid, new, old):
        if old is not None and old.shape == new.shape:
            n = int((new != old).sum())
            if n:
                self.report.append(f"{mid}: {n} {'texel' if n == 1 else 'texels'} repainted")

    def write_vox(self, mid, model, out: Path):
        old = out / f"{mid}.vox"
        note = size_note(mid, uwvx.read(old), model) if old.exists() else None
        if note:
            self.report.append(note)
        uwvx.write(model, old)

    def item_glb(self, mid, src: Path, out: Path, faithful: bool):
        g = gltf.read(src)
        tex = gltf.texture(g)[..., :3]
        portglb = self.port / f"{mid}.glb"
        old = gltf.texture(gltf.read(portglb))[..., 0] if portglb.exists() else None
        idx, n = to_indices(tex, self.pal, old)
        self.repainted(mid, idx, old)
        self.snapped(mid, n)
        gltf.write(gltf.with_texture(g, np.repeat(idx[..., None], 3, 2)), out / f"{mid}.glb")
        if faithful and n:
            gltf.write(gltf.with_texture(g, self.pal[idx]), src)
        return g, idx

    def item(self, e):
        mid = e["id"]
        src_vox, src_glb = self.voxels / f"{mid}.vox", self.editable / f"{mid}.glb"
        vox_edited = src_vox.exists() and export.sha1(src_vox) != e.get("voxel_sha1")
        if vox_edited and e["master"] == "smooth":
            e["master"] = "voxel"
            self.report.append(f"{mid}: its MagicaVoxel model was edited, so its voxels are now the master; the smooth "
                               "model no longer makes them")
        if self.changed(src_glb, e.get("editable_sha1")):
            if "editable_sha1" not in e:
                self.report.append(f"{mid}: a new smooth model, used by the port's model mode")
            g, idx = self.item_glb(mid, src_glb, self.port, True)
            e["editable_sha1"] = export.sha1(src_glb)
            if e["master"] == "smooth":
                self.write_vox(mid, voxelise.item(gltf.read(self.port / f"{mid}.glb"), idx), self.port)
                e["voxel_sha1"] = export.item_display(mid, uwvx.read(self.port / f"{mid}.vox"), self.pal,
                                                      self.voxels, self.data)
                self.thumb(self.data / f"{mid}.uwvc", self.thumbs / f"{mid}.png")
        if e["master"] == "voxel" and (vox_edited or self.force):
            model, n = from_magica(src_vox, self.pal, uwvx.read(self.port / f"{mid}.vox"))
            self.snapped(mid, n, "voxels")
            self.write_vox(mid, model, self.port)
            if n:   # rewrite the MagicaVoxel copy in palette colours
                magica.write(src_vox, model.clips["still"][0][:, :3], self.pal[model.clips["still"][0][:, 3]])
            export.item_uwvc(mid, model, self.pal, self.data)
            e["voxel_sha1"] = export.sha1(src_vox)
            self.thumb(self.data / f"{mid}.uwvc", self.thumbs / f"{mid}.png")

    def creature_slots(self, mid, g, base):
        old_glb = gltf.read(self.port / f"{mid}.glb")
        old = gltf.texture(old_glb)[..., 0]
        tex = gltf.texture(g)[..., :3]
        if tex.shape[:2] != old.shape:
            raise PackError(f"{mid}.glb: the texture size changed from {old.shape[1]}x{old.shape[0]} to "
                            f"{tex.shape[1]}x{tex.shape[0]}; a creature's texture must keep its size and UV layout "
                            "(see docs/blender.md)")
        if uv_set(g) != uv_set(old_glb):
            raise PackError(f"{mid}.glb: the UV layout changed; a creature's texture must keep its size and UV layout, "
                            "or its colourings can no longer be told apart (see docs/blender.md)")
        return recover_slots(tex, old, base)

    def creature(self, e, src: Path, out: Path, faithful: bool):
        mid = e["id"]
        body = int(mid[2:], 8)
        aux = self.aux_for(body)
        base = export.base_aux(body, self.types)
        g = in_clip_order(gltf.read(src), gltf.clip_names(gltf.read(self.port / f"{mid}.glb")))
        slots, n = self.creature_slots(mid, g, self.pal[aux[base]])
        self.repainted(mid, slots, gltf.texture(gltf.read(self.port / f"{mid}.glb"))[..., 0])
        self.snapped(mid, n, creature=True)
        gltf.write(gltf.with_texture(g, np.repeat(slots[..., None], 3, 2)), out / f"{mid}.glb")
        size = uwvx.read(self.port / f"{mid}.vox").size
        model = voxelise.creature(gltf.read(out / f"{mid}.glb"), slots, size)
        self.write_vox(mid, model, out)
        if faithful:
            if n:
                gltf.write(gltf.with_texture(g, self.pal[aux[base][slots]]), src)
            e["colourings"] = export.creature_display(mid, e["name"], model, slots, aux, base, self.types, self.pal,
                                                      self.data, self.names)
            e["editable_sha1"] = export.sha1(src)
            self.thumb(self.data / f"{mid}.uwvc", self.thumbs / f"{mid}.png")

    def run(self, ids=None):
        path = self.repo / "models/uw1/manifest.json"
        manifest = json.loads(path.read_text())
        for e in manifest:
            if ids and e["id"] not in ids:
                continue
            try:
                if e["kind"] == "item":
                    self.item(e)
                elif self.changed(self.editable / f"{e['id']}.glb", e.get("editable_sha1")):
                    self.creature(e, self.editable / f"{e['id']}.glb", self.port, True)
            except (PackError, ValueError, OSError) as err:   # refuse this model only; the others still pack
                self.refuse(e["id"], err)
        path.write_text(json.dumps(manifest, indent=1) + "\n")
        return self.report

    def refuse(self, mid, err):
        self.refused.append(mid)
        self.report.append(f"{mid}: refused, nothing written for it: {err}")

    def variant(self, name, ids=None):
        vdir = self.repo / "variants/uw1" / name
        if not vdir.is_dir():
            raise PackError(f"no variant folder variants/uw1/{name}")
        out = vdir / "port/uw1"   # the port reads <modelpath>/uw1/, so modelpath is the variant's port folder
        out.mkdir(parents=True, exist_ok=True)
        data = self.data / "variants" / name   # the site's display voxels
        data.mkdir(parents=True, exist_ok=True)
        known = {e["id"]: e for e in json.loads((self.repo / "models/uw1/manifest.json").read_text())}
        for src in sorted(vdir.glob("*.glb")):
            mid = src.stem
            if (ids and mid not in ids) or mid not in known:
                if mid not in known:
                    self.report.append(f"{name}/{src.name}: no faithful model of that name; skipped")
                continue
            try:
                if known[mid]["kind"] == "item":
                    _, idx = self.item_glb(mid, src, out, False)
                    model = voxelise.item(gltf.read(out / f"{mid}.glb"), idx)
                    self.write_vox(mid, model, out)
                    export.item_uwvc(mid, model, self.pal, data)
                else:
                    self.creature(dict(known[mid]), src, out, False)
                    body = int(mid[2:], 8)
                    base = self.aux_for(body)[export.base_aux(body, self.types)]
                    model = uwvx.read(out / f"{mid}.vox")
                    write_uwvc(model, [{s: tuple(self.pal[base[s]]) for s in used_slots(model)}], data / f"{mid}.uwvc")
                self.thumb(data / f"{mid}.uwvc", self.thumbs / "variants" / name / f"{mid}.png")
            except (PackError, ValueError, OSError) as err:
                self.refuse(f"{name}/{mid}", err)
        return self.report


def run(uw1, repo, ids=None, pal=None, aux_for=None, types=None, variant=None, force=False) -> list:
    p = Packer(uw1, repo, pal, aux_for, types, force)
    return p.variant(variant, ids) if variant else p.run(ids)
