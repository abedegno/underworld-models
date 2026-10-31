# Improving a smooth model in Blender

These steps were tested with Blender 5.2. Blender is free from blender.org.

## Opening the model

1. Download the model's `.glb` file from its page on the site, or take it from `models/uw1/editable/`.
2. In Blender, choose File, then New, then General, and delete the starting cube, camera and light (select all with A, then press X).
3. Choose File, then Import, then glTF 2.0 (.glb/.gltf), and open the file.

A creature comes in with its skeleton and all of its animations. You can play an animation by choosing it in the Action editor and pressing the space bar.

## Painting colours

1. Select the model and switch to the Texture Paint workspace with the tab at the top of the window.
2. Paint on the model or on the image. Pick colours from the model itself, by holding S over the model to sample its colour. An object's colours are snapped to the game's palette later, and a creature's to the colours already on it, so a creature can only use those.
3. When you have finished, go to the Image Editor and choose Image, then Pack. Packing keeps your painted pixels with the file. If you skip it, the export may save the old texture.

Keep the texture's size. Don't move, add or remove UVs, which set how the texture is laid over the model. For a creature, `tools/pack.py` refuses a texture whose size or UV layout changed.

## Changing the shape

You can move, add or remove geometry in Edit Mode. For a creature, keep the parts that move with each bone weighted to the same bones, and keep the UVs as they are.

Keep the model's size unless the size is the fault you are fixing. The models are in the port's units, where a dungeon square is 1.2 wide. `tools/pack.py` warns when a model's size changes by more than a tenth.

## Saving the model

Choose File, then Export, then glTF 2.0 (.glb/.gltf), and set these options in the export window:

- Format: glTF Binary (.glb).
- Data, then Mesh: keep UVs ticked.
- Material, then Images: Automatic.
- Animation: ticked, and under Animation, then Sampling, untick Always Sample Animations. Sampling adds a key for every frame and gives the creature's voxels many more frames than the original.

Save the file over the one you downloaded, with the same name, e.g., `CR00.glb`, and put it back in `models/uw1/editable/`. Then open a pull request as [CONTRIBUTING.md](../CONTRIBUTING.md) describes.

Blender lists a creature's animations in alphabetical order when it exports them. The tools put them back in the original order, so you don't need to.

## Checking your change

If you own the game, run `tools/pack.py` as [CONTRIBUTING.md](../CONTRIBUTING.md) describes. For a texture change it prints a note like:

```
CR00: 16 texels repainted
```

A note that colours were snapped means some colours you used are not ones the model can have, and the nearest that it can have were used instead. For an object those are the game's 256 colours, and for a creature the 32 colours already on it.
