// Which sprite the game shows, as UnderworldGodot draws UW1 creatures (src/npc/npc.cs SetAnimSpriteUW1), with no
// page or DOM code so it can be tested on its own.

// Views as the port names them (critterloader.cs AppendAngleToAnimationName): 4 is the front.
export const VIEWS = ["rear", "rear_right", "right", "front_right", "front", "front_left", "left", "rear_left"];
const STEP = Math.PI / 4;
const LOOPS = new Set(["idle", "idle_combat", "walking"]);   // crittermodel.cs Loops: the others hold their last frame
export const FPS = 8;   // one frame of a sequence each eighth of a second

// The view seen from a camera at `angle` round the model: 0 in front of it (on its +z side, which the models
// face), growing anticlockwise seen from above.
export function viewFor(angle) {
  return (((4 + Math.round(angle / STEP)) % 8) + 8) % 8;
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

// The frame shown `t` seconds into a clip whose frames are `frames`.
export function frameAt(frames, clip, t) {
  const i = Math.floor(Math.max(t, 0) * FPS);
  return frames[LOOPS.has(clip) ? i % frames.length : Math.min(i, frames.length - 1)];
}
