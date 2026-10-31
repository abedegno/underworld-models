// Tests of the sprite logic: node --test site/js/
import { test } from "node:test";
import assert from "node:assert/strict";
import { viewFor, animFor, frameAt } from "./spritelogic.js";

const deg = d => (d * Math.PI) / 180;

test("the camera in front sees the front view", () => assert.equal(viewFor(0), 4));
test("the sides and the back", () => {
  assert.equal(viewFor(-Math.PI / 2), 2);
  assert.equal(viewFor(Math.PI / 2), 6);
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
