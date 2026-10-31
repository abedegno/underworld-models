"""Blender background script for the instructions' end-to-end test: open a model, repaint a 4x4 block of its texture
in a colour the texture already uses, and export it with the settings docs/blender.md gives.

Usage: blender -b -P tools/tests/blender_edit.py -- IN.glb OUT.glb
"""
import sys

import bpy

src, out = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
img = next(i for i in bpy.data.images if i.size[0] > 0)
w, h = img.size
px = list(img.pixels)
# Blender's image rows run bottom to top; the block is the texture's top-left corner in glTF terms
start = px[((h - 1) * w + 0) * 4:((h - 1) * w + 0) * 4 + 4]
other = next(px[i:i + 4] for i in range(0, len(px), 4) if px[i:i + 3] != start[:3] and px[i + 3] > 0)
for y in range(4):
    for x in range(4):
        k = ((h - 1 - y) * w + x) * 4
        px[k:k + 4] = other
img.pixels = px
img.update()
img.pack()   # keep the painted pixels with the file, as the instructions say
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_image_format="AUTO", export_animations=True,
                          export_force_sampling=False, export_apply=False)
print("edited", img.name, w, h, "colour", [round(c, 3) for c in other])
