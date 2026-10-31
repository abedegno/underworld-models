# Underworld Models

Fan-made 3D models of the creatures and objects of Ultima Underworld (1992), made to stay true to the game's own sprites.

You can see every model in your browser at **https://abedegno.github.io/underworld-models/**. There you can turn each model, play a creature's animations, switch between the smooth model and the voxel version, and compare it with a picture of the original in the game.

## What is here

The repo holds 26 creature bodies with their animations and 185 floor object models, which cover all 211 kinds of object you can find lying in the dungeon. Some kinds share a model, e.g., all the runestones.

- `models/uw1/editable/` has the smooth models, in ordinary colours, for editing in Blender.
- `models/uw1/voxels/` has the objects' voxel models, for editing in MagicaVoxel.
- `port/uw1/` has the files the UnderworldGodot port loads (see [docs/port.md](docs/port.md)).
- `variants/uw1/` is for more detailed or reimagined versions (see below).
- `shots/uw1/` has a picture of each original sprite, taken in the game, to judge the models against.
- `tools/` has the scripts that turn the editable models into port files and back.
- `site/` is the website.

## Faithful models and variants

The models in `models/` and `port/` follow the original sprites as closely as we can manage: the same shape, size, colours and movement. That set is the faithful set, and a change to it should bring a model closer to its sprite.

More detailed or reimagined versions are welcome too. They go in `variants/uw1/<your variant's name>/`, and the site shows them next to the model they are based on. A variant never replaces a faithful model.

## How to help

See [CONTRIBUTING.md](CONTRIBUTING.md). In short, you download a model, improve it in Blender ([docs/blender.md](docs/blender.md)) or MagicaVoxel ([docs/magicavoxel.md](docs/magicavoxel.md)), and send a pull request with a screenshot. You don't need a copy of the game to do so.

## Licence

The project's own work in this repo is licensed under the Creative Commons Attribution-ShareAlike 4.0 licence (CC BY-SA 4.0), in [LICENSE](LICENSE). You may use and change the models if you credit this project and share your changes under the same licence.

The licence covers only this project's own work. Ultima Underworld, its creatures, objects and artwork belong to their owners, and the models copy the designs and colours of the game's sprites. Nothing here grants any right to those designs. This is a fan project, and it is not connected with or approved by the owners of Ultima Underworld.

The repo holds no files from the game, and nothing extracted from them. The tools read the game's colours from your own copy of the game when you run them, and never copy them into the repo.

## How the models were made

Each model started from its sprite. A picture of the sprite was repainted as a larger image, a 3D model was made from that image with Meshy, and the model was then sized, posed and coloured to match the sprite in the game's own palette. Creatures were rigged and given the animations of the PlayStation version of the game. The small objects that are flat or thin were built straight from their sprites as voxels.
