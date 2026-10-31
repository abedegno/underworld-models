// Tests of the sprite logic: node --test site/js/
import { test } from "node:test";
import assert from "node:assert/strict";
import { viewFor, animFor, frameAt, advance, pick, fitScale, offsetX, FPS } from "./spritelogic.js";

const deg = d => (d * Math.PI) / 180;

test("the camera in front sees the front view", () => assert.equal(viewFor(0), 4));
test("the sides and the back", () => {
  // checked against the goblin, which holds its club in its right hand: from the model's left (+x, angle +90
  // degrees) the club is hidden behind the body, and so it is in the sprite the game names "right" (view 2)
  assert.equal(viewFor(Math.PI / 2), 2);
  assert.equal(viewFor(-Math.PI / 2), 6);
  assert.equal(viewFor(Math.PI), 0);
  assert.equal(viewFor(-Math.PI), 0);
});
test("halfway between two views is stable", () => assert.equal(viewFor(deg(22.5)), viewFor(deg(22.5) + 1e-9)));
test("idle and walking turn with the view", () => {
  assert.deepEqual(animFor("idle", 2), { name: "idle_right", frontOnly: false });
  assert.deepEqual(animFor("walking", 7), { name: "walking_rear_left", frontOnly: false });
});
test("attacks only from the front, else the standing view", () => {
  assert.deepEqual(animFor("attack_bash", 4), { name: "attack_bash", frontOnly: false });
  assert.deepEqual(animFor("attack_bash", 0), { name: "idle_rear", frontOnly: true });
  assert.deepEqual(animFor("idle_combat", 3), { name: "idle_combat", frontOnly: false });
  assert.deepEqual(animFor("idle_combat", 6), { name: "idle_left", frontOnly: true });
});
test("death from every side", () => assert.equal(animFor("death", 0).name, "death"));
test("frames at eight a second, looping or holding", () => {
  assert.equal(frameAt([5, 6, 7], "walking", 0.15), 6);   // the second eighth of a second
  assert.equal(frameAt([5, 6, 7], "walking", 0.4), 5);   // 3.2 frames in: the 3-frame loop is back at its start
  assert.equal(frameAt([5, 6, 7], "attack_bash", 9), 7);   // held on the last frame
  assert.equal(frameAt([5], "idle", 3), 5);
});

// From the final review: the port's 32-step table (npc.cs NPCAnimationHeadingTable), not 8 equal sectors
test("views follow the port's table", () => {
  assert.equal(viewFor(deg(22.5)), 4);   // the port still shows the front here
  assert.equal(viewFor(deg(-22.5)), 4);
  assert.equal(viewFor(deg(35)), 3);   // past 33.75 degrees: the diagonal
  assert.equal(viewFor(deg(-35)), 5);
  assert.equal(viewFor(deg(60)), 3);   // the front-right diagonal runs from 33.75 to 67.5 degrees
  assert.equal(viewFor(deg(70)), 2);   // then the side, for 56.25 degrees
  assert.equal(viewFor(deg(135)), 1);
});
test("time held on the last frame, so stepping back works at once", () => {
  assert.equal(advance(0, 5, "attack_bash", 5), 4 / FPS);   // held, not left running on
  assert.equal(advance(4 / FPS, -1 / FPS, "attack_bash", 5), 3 / FPS);
  assert.equal(advance(0, -1 / FPS, "attack_bash", 5), 0);
  assert.ok(Math.abs(advance(0, -1 / FPS, "walking", 4) - 3 / FPS) < 1e-9);   // a loop wraps back
  assert.ok(Math.abs(advance(3 / FPS, 2 / FPS, "walking", 4) - 1 / FPS) < 1e-9);
});
test("an animation the body lacks shows nothing, as the port", () => {
  const anims = { idle_front: [0, 1], attack_bash: [2, 3] };
  assert.deepEqual(pick(anims, "attack_slash", 4, 0), { index: null, name: "attack_slash", frontOnly: false, view: 4 });
  assert.equal(pick(anims, "attack_bash", 4, 1 / FPS).index, 3);
  assert.equal(pick(anims, "attack_slash", 0, 0).index, null);   // from behind the game shows idle_rear, also missing here
});
test("the sprite fits its canvas, in whole pixels", () => {
  // box: the shown animation's frames' bounds in the cell [x0, y0, x1, y1]; anchor [x, y]
  assert.equal(fitScale(3.6, [10, 4, 30, 56], [20, 56], 400, 400, 0.9), 3);   // whole pixels
  assert.equal(fitScale(9, [10, 4, 30, 56], [20, 56], 400, 400, 0.9), 6);   // the top would be cut off: (360 - 4) / 52
  assert.equal(fitScale(0.3, [10, 4, 30, 56], [20, 56], 400, 400, 0.9), 1);
  assert.equal(fitScale(9, [0, 10, 88, 56], [50, 56], 500, 1000, 0.9), 5);   // a wide swing: (500 - 8) / 88
  assert.equal(fitScale(9, [30, 10, 60, 56], [50, 56], 500, 1000, 0.9), 9);   // the same cell, a narrow frame
});
test("the frames slide sideways only to stay in view", () => {
  assert.equal(offsetX(400, [10, 4, 30, 56], [20, 56], 3), 140);   // the anchor at the centre
  assert.equal(offsetX(400, [0, 4, 100, 56], [90, 56], 3), 4);   // the left edge kept in view
});
