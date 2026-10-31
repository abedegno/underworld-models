# How to help

Thank you for helping. Every model here can be improved, and you don't need a copy of the game to do it.

## What makes a good change

A change to the faithful set should bring a model closer to its original sprite. Each model's page on the site shows the sprite in the game next to the model, so you can compare the two. Good changes include:

- fixing a shape that differs from the sprite, e.g., a horn that is too short
- fixing a size, so the model stands as big as its sprite in the game
- fixing a colour that is wrong or missing
- fixing an animation that bends or breaks oddly

If you want to add detail or reimagine a model, make it a variant instead (see the end of this page).

## Making a change

1. Find the model on the site and note its name, e.g., `CR00` for the goblin or `OBJ090` for the lantern.
2. Download its file from the model's page, or from `models/uw1/editable/` (smooth models) or `models/uw1/voxels/` (voxel models of objects).
3. Edit it, following [docs/blender.md](docs/blender.md) for a smooth model or [docs/magicavoxel.md](docs/magicavoxel.md) for a voxel model.
4. Put your file back in the same place, with the same name, and open a pull request.
5. In the pull request, say what you changed and why, and attach a screenshot of the model next to the sprite.

A maintainer then builds the port files from your model with `tools/pack.py` and adds them to your pull request. If you own the game, you can run `tools/pack.py` yourself (see below).

## Rules for the files

- Colours are always snapped. An object's colours are snapped to the game's palette of 256 colours. A creature's colours are snapped to the 32 colours of its own palette, which are the colours already on the model, because the game recolours those 32 for each creature that shares the body. So paint a creature only with colours it already has.
- A creature's texture must keep its size and its UV layout, which is how the picture is laid over the model. The tools use the layout to tell apart the parts that change colour between creatures that share a body, e.g., the four goblins. If the size or layout changes, `tools/pack.py` refuses the model.
- Creatures are edited as smooth models only. Their voxels are made from the smooth model for every frame of every animation.
- An object's voxel model can be edited by hand. Once it has been, the voxel model is that object's master copy, and a later change to the smooth model no longer changes its voxels.
- Never add a file from the game, or anything taken from one. The repo's checks fail on game files.

## Building the port files yourself

You need Python 3 and your own copy of Ultima Underworld 1. From the repo's folder:

```
python3 -m venv .venv
.venv/bin/pip install -r tools/requirements.txt
.venv/bin/python tools/pack.py /path/to/your/UW1
```

`tools/pack.py` rebuilds only the models whose files changed, and their pictures for the site, and it prints a note for each one. For example, it tells you how many texels you repainted, how many colours it snapped, and whether a model's size changed by more than a tenth. If it can't use a model, e.g., a creature whose texture changed size, it refuses that model, writes nothing for it, packs the rest, and ends with a list of the models it refused.

## Variants

A variant is a more detailed or reimagined version of a model. An object variant can be anything. A creature variant must keep the faithful model's texture size and UV layout, so it can be repainted and reshaped but not given a new texture layout, because the tools need the layout to give it each creature's colours. Put it in `variants/uw1/<name>/`, where `<name>` is a short name for your set, with the same file name as the model it is based on, e.g., `variants/uw1/hires/CR00.glb`. Add a `variant.json` file beside it:

```
{"name": "high detail", "author": "your name", "of": ["CR00"]}
```

A maintainer builds its port files and its picture for the site with `tools/pack.py --variant <name>`, and the site shows it next to the faithful model. Its port files go in `variants/uw1/<name>/port/uw1/`.
