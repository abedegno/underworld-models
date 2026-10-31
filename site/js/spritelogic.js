// Which sprite the game shows, as UnderworldGodot draws UW1 creatures (src/npc/npc.cs SetAnimSpriteUW1), with no
// page or DOM code so it can be tested on its own.

// Views as the port names them (critterloader.cs AppendAngleToAnimationName): 4 is the front.
export const VIEWS = ["rear", "rear_right", "right", "front_right", "front", "front_left", "left", "rear_left"];
// npc.cs NPCAnimationHeadingTable: the view for each of 32 steps (11.25 degrees) of the camera's turn relative to
// the creature, 16 when the camera faces it. Front, back and sides take 5 steps, the diagonals 3.
const TABLE = [0, 0, 0, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 4, 4, 4, 4, 4, 5, 5, 5, 6, 6, 6, 6, 6, 7, 7, 7, 0, 0];
const STEP = Math.PI / 16;
export const FPS = 8;   // one frame of a sequence each eighth of a second

// The view seen from a camera at `angle` round the model: 0 in front of it (on its +z side, which the models
// face), growing anticlockwise seen from above. The view number rises with the angle, as in the port: from +90
// degrees it is 6, "left".
export function viewFor(angle) {
  // the port truncates the camera's yaw to a step (>> 0xB) and subtracts it, which rounds the turn up
  const step = Math.ceil(angle / STEP - 1e-9);
  return TABLE[(((16 + step) % 32) + 32) % 32];
}

// The animation the game shows for a clip from a view. Sequences below 0x20 other than death (idle_combat and the
// attacks) are drawn only when the creature faces the viewer, ((view + 5) & 7) < 3; from elsewhere the game draws
// the standing sprite for that view.
export function animFor(clip, view) {
  const side = VIEWS[view];
  if (clip === "idle" || clip === "walking") return { name: `${clip}_${side}`, frontOnly: false };
  if (clip === "death") return { name: "death", frontOnly: false };
  if (((view + 5) & 7) < 3) return { name: clip, frontOnly: false };
  return { name: `idle_${side}`, frontOnly: true };
}

// The frame shown `t` seconds into a clip whose frames are `frames`. Every clip repeats, as the 3D model's do on the
// page, so an attack or a death can be watched again and again (in the game only idle, idle_combat and walking
// repeat; the others play once).
export function frameAt(frames, clip, t) {
  return frames[Math.floor(Math.max(t, 0) * FPS) % frames.length];
}

// The clip's time after `dt` more seconds (negative to step back) for an animation of `length` frames, wrapped
// round the clip so that stepping works at once either way.
export function advance(time, dt, clip, length) {
  const t = time + dt, end = length / FPS;
  return length <= 0 ? 0 : ((t % end) + end) % end;
}

// The frame to show: the cell index, or null when the body has no such animation (the game then draws nothing,
// npc.cs SetAnimSpriteUW1), with the animation's name, whether only the front has it, and the view.
export function pick(anims, clip, view, time) {
  const a = animFor(clip, view);
  const frames = anims[a.name];
  return { index: frames && frames.length ? frameAt(frames, clip, time) : null, ...a, view };
}

// Whole sprite pixels per canvas pixel: `px` rounded down, made smaller if the shown animation's frames (`box`, their
// bounds in the cell [x0, y0, x1, y1]) would run off the top or the sides of a w by h canvas whose feet line is at
// feetY (0 to 1 from the top); at least 1. The frames may slide sideways to stay in view (offsetX), so only their
// width counts. Fitting by the animation's frames, not the whole cell, keeps a standing creature as big as it can be
// and steady through an animation.
export function fitScale(px, box, anchor, w, h, feetY) {
  const up = (h * feetY - 4) / Math.max(anchor[1] - box[1], 1);
  const side = (w - 8) / Math.max(box[2] - box[0], 1);
  return Math.max(1, Math.floor(Math.min(px, up, side)));
}

// The cell's left edge: the anchor at the canvas's centre, slid sideways just enough to keep the frames in view.
export function offsetX(w, box, anchor, px) {
  const left = w / 2 - anchor[0] * px;
  const l = left + box[0] * px, r = left + box[2] * px;
  return l < 4 ? left + (4 - l) : r > w - 4 ? left - (r - (w - 4)) : left;
}
