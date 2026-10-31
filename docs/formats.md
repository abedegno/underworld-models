# File formats

## Port voxels (`port/uw1/*.vox`)

The port's voxel files start with "UWVX". They are not MagicaVoxel files, although they share the `.vox` ending. All numbers are little-endian.

- 4 bytes: "UWVX"
- 1 byte: version, 1
- 4 bytes: the voxel size, a float, in port units (0.0075 for creatures, 0.01 for objects)
- 3 times 2 bytes: x, y and z of the grid's first voxel, counted in voxels, as signed numbers
- 1 byte: the number of clips

Then, for each clip:

- 1 byte: the length of the clip's name, then the name
- 1 byte: the number of frames, then each frame

Each frame is a 4-byte voxel count followed by 4 bytes per voxel: x, y, z and the voxel's slot. Objects have one clip, "still", of one frame. A slot is a palette number. For an object it is a colour of the game's main palette, and for a creature it is one of the 32 entries of the creature's own palette, which the game changes between creatures that share a body.

## Port models (`port/uw1/*.glb`)

The port's `.glb` files are ordinary glTF models whose texture holds palette numbers instead of colours, in the red channel (and the same in green and blue). The port colours them with the game's palette when it draws them. They look dark red in other viewers, which is why the editable copies in `models/uw1/editable/` exist.

## Display voxels (`site/data/uw1/*.uwvc`)

The site's voxel files are a port voxel file with "UWVC" in place of "UWVX", followed by the colours the model needs:

- 1 byte: the number of colourings
- for each colouring, 2 bytes giving the number of entries, then 4 bytes per entry: the slot, then its red, green and blue

Only the slots the model uses are listed.

## The manifest (`models/uw1/manifest.json`)

The manifest lists every model, with its name, kind, colourings and master copy (`smooth` or `voxel`). It also keeps a checksum of each editable file, so `tools/pack.py` can tell which models changed.
