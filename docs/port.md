# Using the models in the UnderworldGodot port

UnderworldGodot is a port of Ultima Underworld to the Godot engine, by Hank Morgan and others, at github.com/hankmorgan/UnderworldGodot. The model settings are not part of the port itself. They exist only on a fork, as an experiment:

- Fork: github.com/abedegno/UnderworldGodot
- Branch: `feat/critter-models`

The models stay in this repo. You point the port at your copy of this repo, and the port reads them from there.

## Settings

The port keeps its settings in `settings.json` in Godot's user folder for the game (on a Mac, `~/Library/Application Support/Godot/app_userdata/Underworld/settings.json`). Add these to the `enhancements` section:

```
"crittermodels": "model",
"itemmodels": "model"
```

Each setting is `"off"` (the sprites, the default), `"model"` (the smooth models) or `"voxel"` (the voxel models). Then set `modelpath`, at the top level, to the `port` folder of your copy of this repo, e.g.:

```
"modelpath": "/Users/you/underworld-models/port"
```

The port looks for `uw1/CRnn.glb` and `uw1/CRnn.vox` for creatures and `uw1/OBJnnn.glb` and `uw1/OBJnnn.vox` for objects. A model it can't find or can't read is drawn as its sprite.

To try a variant, point `modelpath` at the variant's `port` folder instead, e.g., `variants/uw1/hires/port`. The port then shows the variant's models and the sprites for everything else.
