// Reads the site's display voxel files (tools/uwmodels/uwvc.py): the port's voxels with the colours they need.
// "UWVC", version byte 1, f32 voxel size, s16 x0, y0, z0, u8 clip count; per clip a u8-length name, a u8 frame
// count and its frames (u32 voxel count, then x, y, z, slot bytes); then a u8 colouring count and per colouring a
// u16 entry count and entries of slot, r, g, b.
export function readUwvc(buffer) {
  const d = new DataView(buffer);
  const b = new Uint8Array(buffer);
  if (String.fromCharCode(b[0], b[1], b[2], b[3]) !== "UWVC" || b[4] !== 1) throw new Error("not a display voxel file");
  const size = d.getFloat32(5, true);
  const origin = [d.getInt16(9, true), d.getInt16(11, true), d.getInt16(13, true)];
  let at = 16;
  const clips = new Map();
  for (let c = 0, n = b[15]; c < n; c++) {
    const len = b[at];
    const name = new TextDecoder().decode(b.subarray(at + 1, at + 1 + len));
    const frames = [];
    let count = b[at + 1 + len];
    at += 2 + len;
    for (let f = 0; f < count; f++) {
      const k = d.getUint32(at, true);
      frames.push(b.subarray(at + 4, at + 4 + k * 4));
      at += 4 + k * 4;
    }
    clips.set(name, frames);
  }
  const colourings = [];
  for (let c = 0, n = b[at++]; c < n; c++) {
    const k = d.getUint16(at, true);
    at += 2;
    const table = new Map();
    for (let i = 0; i < k; i++, at += 4) table.set(b[at], [b[at + 1], b[at + 2], b[at + 3]]);
    colourings.push(table);
  }
  return { size, origin, clips, colourings };
}
