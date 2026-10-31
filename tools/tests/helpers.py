"""Builds small glb files for tests, so no test needs a real model."""
import io
import json
import struct

import numpy as np
from PIL import Image

from uwmodels import gltf


def png_bytes(img):
    b = io.BytesIO()
    Image.fromarray(np.asarray(img, np.uint8)).save(b, "PNG")
    return b.getvalue()


def make_glb(positions, uvs, faces, texture, clips=None, joints=0):
    """A one-mesh glb. clips: {name: [times]} adds animations on the first joint's rotation; joints adds a skin."""
    blob = bytearray()
    views, accessors = [], []

    def add(arr, ctype, typ, target=None):
        arr = np.ascontiguousarray(arr)
        while len(blob) % 4:
            blob.append(0)
        view = {"buffer": 0, "byteOffset": len(blob), "byteLength": arr.nbytes}
        if target:
            view["target"] = target
        blob.extend(arr.tobytes())
        views.append(view)
        acc = {"bufferView": len(views) - 1, "componentType": ctype, "count": len(arr), "type": typ}
        if typ == "VEC3" and ctype == 5126:
            acc["min"] = arr.min(0).tolist()
            acc["max"] = arr.max(0).tolist()
        accessors.append(acc)
        return len(accessors) - 1

    pos = add(np.asarray(positions, np.float32), 5126, "VEC3", 34962)
    uv = add(np.asarray(uvs, np.float32), 5126, "VEC2", 34962)
    idx = add(np.asarray(faces, np.uint16).reshape(-1), 5123, "SCALAR", 34963)
    attrs = {"POSITION": pos, "TEXCOORD_0": uv}
    j = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
         "meshes": [{"primitives": [{"attributes": attrs, "indices": idx, "material": 0}]}],
         "materials": [{"pbrMetallicRoughness": {"baseColorTexture": {"index": 0}}}],
         "textures": [{"source": 0}], "images": [], "accessors": accessors, "bufferViews": views,
         "buffers": [{"byteLength": 0}]}
    if joints:
        n = len(positions)
        attrs["JOINTS_0"] = add(np.zeros((n, 4), np.uint8), 5121, "VEC4", 34962)
        w = np.zeros((n, 4), np.float32)
        w[:, 0] = 1
        attrs["WEIGHTS_0"] = add(w, 5126, "VEC4", 34962)
        first = len(j["nodes"])
        j["nodes"] += [{"name": f"Bone{i}"} for i in range(joints)]
        j["nodes"][0]["skin"] = 0
        j["scenes"][0]["nodes"] += list(range(first, first + joints))
        ibm = add(np.tile(np.eye(4, dtype=np.float32).reshape(1, 16), (joints, 1)), 5126, "MAT4")
        j["skins"] = [{"joints": list(range(first, first + joints)), "inverseBindMatrices": ibm}]
        if clips:
            j["animations"] = []
            for name, times in clips.items():
                t = add(np.asarray(times, np.float32).reshape(-1, 1), 5126, "SCALAR")
                accessors[t]["min"] = [float(min(times))]
                accessors[t]["max"] = [float(max(times))]
                r = add(np.tile(np.array([0, 0, 0, 1], np.float32), (len(times), 1)), 5126, "VEC4")
                j["animations"].append({"name": name, "samplers": [{"input": t, "output": r}],
                                        "channels": [{"sampler": 0, "target": {"node": first, "path": "rotation"}}]})
    img = png_bytes(texture)
    while len(blob) % 4:
        blob.append(0)
    views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(img)})
    blob.extend(img)
    j["images"].append({"bufferView": len(views) - 1, "mimeType": "image/png"})
    j["buffers"][0]["byteLength"] = len(blob)
    return gltf.Glb(j, bytes(blob))


def quad(texture, clips=None, joints=0, scale=1.0):
    p = np.array([[-.5, 0, 0], [.5, 0, 0], [.5, 1, 0], [-.5, 1, 0]]) * scale
    t = [[0, 1], [1, 1], [1, 0], [0, 0]]
    return make_glb(p, t, [[0, 1, 2], [0, 2, 3]], texture, clips, joints)
