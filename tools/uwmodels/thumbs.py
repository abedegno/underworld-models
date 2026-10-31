"""Still pictures of the models for the site's gallery, drawn from their display voxels.

The first frame of the first clip, seen from the front right and 30 degrees above, without perspective. Each voxel's
three visible faces are flat-shaded (top 100%, front 80%, side 60%) and drawn back to front; the model is fitted to
the picture with a 10% margin on a transparent background.
"""
import math

import numpy as np
from PIL import Image, ImageDraw

from .uwvc import read_uwvc

YAW, PITCH, SS = math.radians(35), math.radians(30), 2
# the camera looks from the front (+z) right (+x) and above (+y)
EYE = np.array([math.sin(YAW) * math.cos(PITCH), math.sin(PITCH), math.cos(YAW) * math.cos(PITCH)])
RIGHT = np.array([math.cos(YAW), 0.0, -math.sin(YAW)])
UP = np.cross(EYE, RIGHT)
CUBE = np.array([[x, y, z] for x in (0, 1) for y in (0, 1) for z in (0, 1)], float)
FACES = [  # (corner indices in drawing order, neighbour offset, shade)
    ((2, 3, 7, 6), (0, 1, 0), 1.0),   # top, y = 1
    ((1, 3, 7, 5), (0, 0, 1), 0.8),   # front, z = 1
    ((4, 5, 7, 6), (1, 0, 0), 0.6),   # side, x = 1
]


def render(uwvc, colouring: int = 0, px: int = 256) -> Image.Image:
    model, colourings = read_uwvc(uwvc)
    frame = next(iter(model.clips.values()))[0].astype(int)
    colours = colourings[min(colouring, len(colourings) - 1)]
    img = Image.new("RGBA", (px * SS, px * SS), (0, 0, 0, 0))
    if not len(frame):
        return img.resize((px, px), Image.LANCZOS)
    filled = {tuple(v) for v in frame[:, :3].tolist()}
    corners = frame[:, None, :3] + CUBE[None]
    sx, sy = corners @ RIGHT, -(corners @ UP)
    lo = np.array([sx.min(), sy.min()])
    span = max(sx.max() - lo[0], sy.max() - lo[1])
    scale = px * SS * 0.8 / span
    off = (px * SS - np.array([sx.max() - lo[0], sy.max() - lo[1]]) * scale) / 2
    draw = ImageDraw.Draw(img)
    for k in np.argsort((frame[:, :3] + 0.5) @ EYE):   # back to front
        v = frame[k]
        rgb = np.array(colours.get(int(v[3]), (255, 0, 255)), float)
        for quad, n, shade in FACES:
            if (v[0] + n[0], v[1] + n[1], v[2] + n[2]) in filled:
                continue
            pts = [((sx[k, c] - lo[0]) * scale + off[0], (sy[k, c] - lo[1]) * scale + off[1]) for c in quad]
            draw.polygon(pts, fill=tuple(int(round(x)) for x in rgb * shade) + (255,))
    return img.resize((px, px), Image.LANCZOS)
