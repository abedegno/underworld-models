"""Turns a textured model into the port's voxels, as the private pipeline's itempack.py (items) and portpack.py
(creatures) did, but keeping the model's own size and colours: nothing is resized or recoloured here.

Surface sampling: every triangle is sampled on a barycentric grid fine enough (0.4 voxel) that no voxel it crosses is
missed; each sample takes the texel under its UV (glTF UVs, v down), and each voxel the most common texel value of its
samples. Items: values are main palette indices, every value counts, and the lowest voxel row is clamped to y = 0.
Creatures: values are aux palette slots, slot 0 is empty, and every key frame of every clip is posed and voxelised;
the looping clips' repeated last key is left out.
"""
import numpy as np

from . import gltf, uwvx

LOOPS = ("idle", "idle_combat", "walking")


def q2m(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def trs(t, r, s):
    m = np.eye(4)
    m[:3, :3] = q2m(r) * np.array(s, float)[None]
    m[:3, 3] = t
    return m


def local(node):
    if "matrix" in node:
        return np.array(node["matrix"], float).reshape(4, 4).T
    return trs(node.get("translation", [0, 0, 0]), node.get("rotation", [0, 0, 0, 1]), node.get("scale", [1, 1, 1]))


def parents(j):
    return {c: i for i, nd in enumerate(j["nodes"]) for c in nd.get("children", [])}


def world(j, i, loc=None, par=None, memo=None):
    loc = loc if loc is not None else [local(nd) for nd in j["nodes"]]
    par = par if par is not None else parents(j)
    memo = {} if memo is None else memo
    if i not in memo:
        memo[i] = (world(j, par[i], loc, par, memo) if i in par else np.eye(4)) @ loc[i]
    return memo[i]


def mesh(glb):
    """The model's one mesh primitive: (node index, primitive). Several meshes or primitives are refused."""
    j = glb.json
    nodes = [i for i, nd in enumerate(j["nodes"]) if "mesh" in nd]
    prims = [p for i in nodes for p in j["meshes"][j["nodes"][i]["mesh"]]["primitives"]]
    if len(nodes) != 1 or len(prims) != 1:
        raise ValueError(f"{len(nodes)} mesh nodes and {len(prims)} parts; a model must be one mesh of one material")
    return nodes[0], prims[0]


def samples(P, F, UV, vs):
    tri, tuv = P[F], UV[F]
    e = np.max([np.linalg.norm(tri[:, a] - tri[:, (a + 1) % 3], axis=1) for a in range(3)], 0)
    ks = np.maximum(np.ceil(e / (vs * 0.4)).astype(int), 1)
    ps, us = [], []
    for k in np.unique(ks):
        m = ks == k
        a, b = np.meshgrid(np.arange(k + 1), np.arange(k + 1))
        keep = a + b <= k
        w = np.c_[a[keep], b[keep], k - a[keep] - b[keep]] / k
        ps.append(np.einsum("sk,tkc->tsc", w, tri[m]).reshape(-1, 3))
        us.append(np.einsum("sk,tkc->tsc", w, tuv[m]).reshape(-1, 2))
    return np.concatenate(ps), np.concatenate(us)


def lookup(values, uv):
    h, w = values.shape
    return values[np.clip((uv[:, 1] * h).astype(int), 0, h - 1), np.clip((uv[:, 0] * w).astype(int), 0, w - 1)]


def cells(p, s, vs, kinds, floor=False):
    c = np.floor(p / vs).astype(int)
    if floor:
        c[:, 1] = np.maximum(c[:, 1], 0)
    key, inv = np.unique(c, axis=0, return_inverse=True)
    cnt = np.zeros((len(key), kinds), int)
    np.add.at(cnt, (inv.ravel(), s.astype(int)), 1)
    return key, cnt.argmax(1)


def frame_bytes(key, slot, o):
    return np.c_[key - o, slot].astype(np.uint8)


def check_grid(keys):
    allv = np.concatenate(keys)
    o = allv.min(0)
    if (allv.max(0) - o).max() >= 256:
        raise ValueError("the model is more than 256 voxels across; it is far too big")
    return o


def item(glb, index_texture: np.ndarray, vs: float = 0.01) -> uwvx.Model:
    """An item's voxels from its glb (positions in the mesh node's world space) and its index texture (h, w)."""
    i, pr = mesh(glb)
    V = gltf.accessor(glb, pr["attributes"]["POSITION"]).astype(float)
    M = world(glb.json, i)
    V = (np.c_[V, np.ones(len(V))] @ M.T)[:, :3]
    UV = gltf.accessor(glb, pr["attributes"]["TEXCOORD_0"]).astype(float)
    F = gltf.accessor(glb, pr["indices"]).reshape(-1, 3).astype(int)
    p, u = samples(V, F, UV, vs)
    key, slot = cells(p, lookup(index_texture, u), vs, 256, floor=True)
    o = check_grid([key])
    return uwvx.Model(vs, tuple(int(x) for x in o), {"still": [frame_bytes(key, slot, o)]})


def creature(glb, slots: np.ndarray, vs: float = 0.0075) -> uwvx.Model:
    """Every key frame of every clip of a skinned creature, voxelised with its slot map (h, w)."""
    j = glb.json
    i, pr = mesh(glb)
    if "skin" not in j["nodes"][i]:
        raise ValueError("a creature's mesh must be skinned")
    acc = lambda k: gltf.accessor(glb, k)
    V = acc(pr["attributes"]["POSITION"]).astype(float)
    UV = acc(pr["attributes"]["TEXCOORD_0"]).astype(float)
    JO = acc(pr["attributes"]["JOINTS_0"]).astype(int)
    WE = acc(pr["attributes"]["WEIGHTS_0"]).astype(float)
    F = acc(pr["indices"]).reshape(-1, 3).astype(int)
    skin = j["skins"][j["nodes"][i]["skin"]]
    joints = skin["joints"]
    IBM = (acc(skin["inverseBindMatrices"]).reshape(-1, 4, 4).transpose(0, 2, 1) if "inverseBindMatrices" in skin
           else np.tile(np.eye(4), (len(joints), 1, 1)))
    par = parents(j)
    rest = [(nd.get("translation", [0, 0, 0]), nd.get("rotation", [0, 0, 0, 1]), nd.get("scale", [1, 1, 1]))
            for nd in j["nodes"]]

    def pose(over):
        loc = [trs(*over.get(n, rest[n])) for n in range(len(j["nodes"]))]
        memo = {}
        S = np.stack([world(j, jn, loc, par, memo) @ IBM[k] for k, jn in enumerate(joints)])
        Mv = (S[JO] * WE[..., None, None]).sum(1)
        return np.einsum("vij,vj->vi", Mv, np.c_[V, np.ones(len(V))])[:, :3]

    def vox(P):
        p, u = samples(P, F, UV, vs)
        s = lookup(slots, u)
        keep = s > 0
        return cells(p[keep], s[keep], vs, 32)

    clips = []
    for an in j.get("animations", []):
        chans, times = {}, None
        for ch in an["channels"]:
            sm = an["samplers"][ch["sampler"]]
            times = acc(sm["input"]).ravel()
            chans.setdefault(ch["target"]["node"], {})[ch["target"]["path"]] = acc(sm["output"])
        keys = len(times) - 1 if an.get("name") in LOOPS and len(times) > 1 else len(times)
        frames = []
        for f in range(keys):
            over = {}
            for node, paths in chans.items():
                t0, r0, s0 = rest[node]
                over[node] = tuple(paths[k][min(f, len(paths[k]) - 1)] if k in paths else d
                                   for k, d in (("translation", t0), ("rotation", r0), ("scale", s0)))
            frames.append(vox(pose(over)))
        clips.append((an.get("name", ""), frames))
    o = check_grid([k for _, fr in clips for k, _ in fr])
    return uwvx.Model(vs, tuple(int(x) for x in o), {n: [frame_bytes(k, s, o) for k, s in fr] for n, fr in clips})
