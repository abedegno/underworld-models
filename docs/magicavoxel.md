# Improving an object's voxels in MagicaVoxel

Each object has a voxel model in `models/uw1/voxels/`, e.g., `OBJ090.vox` for the lantern. MagicaVoxel is a free voxel editor from ephtracy.github.io. The files use MagicaVoxel's own format, version 150, so they open in MagicaVoxel and in other voxel editors that read it.

Creatures have no voxel model to edit. Their voxels are made from the smooth model for every animation frame, so you improve a creature in Blender instead (see [blender.md](blender.md)).

## Editing

1. Open the object's `.vox` file in MagicaVoxel.
2. Add, remove or recolour voxels. Use the colours already in the file's palette where you can, because every colour is snapped to the game's palette of 256 colours later.
3. Keep each voxel's size. One voxel is 0.01 of the port's units, where a dungeon square is 1.2 wide, so one voxel is half a pixel of the object's sprite in the game.
4. Save the file with the same name, and put it back in `models/uw1/voxels/`.

You don't need to keep the model in place. The tools stand it on the floor and centre it when they build the port's file.

## What happens next

Once you have changed an object's voxel model, the voxel model is that object's master copy. A later change to its smooth model then changes only the port's smooth model, never its voxels.

If you own the game, run `tools/pack.py` as [CONTRIBUTING.md](../CONTRIBUTING.md) describes. It prints a note when the voxel model becomes the master copy, and tells you how many voxels had colours outside the palette.
