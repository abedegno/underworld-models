"""Reads and writes binary glTF (.glb) containers: the JSON, the one buffer, accessors and the first texture.

Only what the tools need; no scene maths. Images must live in buffer views (as every model here does), not in URIs.
"""
import io
import json
import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

COMPONENTS = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
WIDTHS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}


@dataclass
class Glb:
    json: dict
    bin: bytes


def read(path) -> Glb:
    d = Path(path).read_bytes()
    if d[:4] != b"glTF":
        raise ValueError(f"{path}: not a glb file")
    n = struct.unpack("<I", d[12:16])[0]
    j = json.loads(d[20:20 + n])
    rest = d[20 + n:]
    blob = rest[8:8 + struct.unpack("<I", rest[:4])[0]] if len(rest) >= 8 else b""
    if j.get("buffers"):
        blob = blob[:j["buffers"][0]["byteLength"]]   # the BIN chunk is padded to 4 bytes
    return Glb(j, blob)


def write(glb: Glb, path):
    j = dict(glb.json)
    blob = bytes(glb.bin) + b"\0" * (-len(glb.bin) % 4)
    j["buffers"] = [dict(j["buffers"][0], byteLength=len(glb.bin))]
    js = json.dumps(j, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    out = struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(js) + 8 + len(blob))
    out += struct.pack("<I4s", len(js), b"JSON") + js + struct.pack("<I4s", len(blob), b"BIN\0") + blob
    Path(path).write_bytes(out)


def view_bytes(glb: Glb, i: int) -> bytes:
    v = glb.json["bufferViews"][i]
    o = v.get("byteOffset", 0)
    return glb.bin[o:o + v["byteLength"]]


def accessor(glb: Glb, i: int) -> np.ndarray:
    a = glb.json["accessors"][i]
    if "sparse" in a or "bufferView" not in a:
        raise ValueError(f"accessor {i}: sparse or empty accessors are not supported")
    dt = np.dtype(COMPONENTS[a["componentType"]])
    k = WIDTHS[a["type"]]
    v = glb.json["bufferViews"][a["bufferView"]]
    start = v.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = v.get("byteStride") or dt.itemsize * k
    raw = np.frombuffer(glb.bin, np.uint8, (a["count"] - 1) * stride + dt.itemsize * k, start)
    rows = np.lib.stride_tricks.as_strided(raw, (a["count"], dt.itemsize * k), (stride, 1))
    return np.ascontiguousarray(rows).view(dt).reshape(a["count"], k)


def texture(glb: Glb) -> np.ndarray:
    """The first image as (h, w, 3) RGB, whatever mode it was saved in (another editor may save an indexed or grey
    PNG). The port's own textures repeat a palette number in all three channels."""
    img = glb.json["images"][0]
    return np.asarray(Image.open(io.BytesIO(view_bytes(glb, img["bufferView"]))).convert("RGB"))


def with_views(glb: Glb, replace: dict) -> Glb:
    """A copy with the given buffer views' bytes replaced ({view index: bytes}) and the buffer laid out afresh."""
    j = json.loads(json.dumps(glb.json))
    blob = bytearray()
    for i, v in enumerate(j["bufferViews"]):
        data = replace.get(i, view_bytes(glb, i))
        blob.extend(b"\0" * (-len(blob) % 4))
        v["byteOffset"] = len(blob)
        v["byteLength"] = len(data)
        blob.extend(data)
    j["buffers"][0]["byteLength"] = len(blob)
    return Glb(j, bytes(blob))


def with_texture(glb: Glb, img: np.ndarray) -> Glb:
    b = io.BytesIO()
    Image.fromarray(np.asarray(img, np.uint8)).save(b, "PNG")
    g = with_views(glb, {glb.json["images"][0]["bufferView"]: b.getvalue()})
    g.json["images"][0]["mimeType"] = "image/png"
    return g


def clip_names(glb: Glb) -> list[str]:
    return [a.get("name", "") for a in glb.json.get("animations", [])]
