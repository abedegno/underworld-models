// The original sprite beside the model: the frame the game would show for the chosen clip, seen from where the
// camera is (or turned separately), drawn with whole pixels at the model's size on screen.
import { VIEWS, viewFor, animFor, frameAt, FPS } from "./spritelogic.js";

async function get(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: ${res.status}`);
  return res;
}

async function image(url) {
  return createImageBitmap(await (await get(url)).blob());
}

export class SpritePanel {
  // Loads the sprite of model entry `m` in colouring `aux` (a creature's other colourings load when chosen).
  static async load(m, aux) {
    if (!m.sprite) return null;
    if (m.sprite.image) {   // an item: its icon, one picture
      const img = await image(m.sprite.image);
      return new SpritePanel({ cell: [img.width, img.height], anchor: [img.width / 2, img.height], columns: 1,
                               scale: m.sprite.scale, anims: {}, colourings: {} }, "", img, true);
    }
    const info = await (await get(m.sprite.json)).json();
    const base = m.sprite.json.slice(0, m.sprite.json.lastIndexOf("/") + 1);
    const first = info.colourings[aux] ? aux : Object.keys(info.colourings)[0];
    return new SpritePanel(info, base, await image(base + info.colourings[first]), false);
  }

  constructor(info, base, sheet, still) {
    this.info = info;
    this.base = base;
    this.sheets = {};
    this.still = still;
    this.sheet = sheet;
    this.clip = "idle";
    this.time = 0;
    this.separate = false;
    this.view = 4;
    this.shown = { name: "", frontOnly: false, view: 4 };
  }

  setClip(name) { this.clip = name; this.time = 0; }
  async setColouring(aux) {
    const file = this.info.colourings[aux];
    if (!file) return;
    this.sheets[aux] ??= image(this.base + file);   // each sheet fetched once, when first chosen
    this.sheet = await this.sheets[aux];
  }
  step(dt) { this.time += dt; }
  stepFrame(n) { this.time = Math.max(0, (Math.floor(this.time * FPS + 1e-6) + n) / FPS); }
  turn(n) { this.view = (this.view + n + 8) % 8; }

  // The frame to show now: [cell index, the animation's name, whether the game shows it only from the front].
  current(angle) {
    if (this.still) return [0, "", false];
    const view = this.separate ? this.view : viewFor(angle);
    const a = animFor(this.clip, view);
    const frames = this.info.anims[a.name];
    this.shown = { ...a, view };
    // an animation the body lacks: the game draws the page's first image
    return [frames && frames.length ? frameAt(frames, this.clip, this.time) : 0, a.name, a.frontOnly];
  }

  // Draws on `canvas` with one sprite pixel covering `pxPerUnit * scale` canvas pixels, the anchor (the creature's
  // feet) at canvas height `feetY` (0 to 1 from the top).
  draw(canvas, angle, pxPerUnit, feetY) {
    const dpr = Math.min(devicePixelRatio, 2);
    const w = Math.round(canvas.clientWidth * dpr), h = Math.round(canvas.clientHeight * dpr);
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
    const g = canvas.getContext("2d");
    g.clearRect(0, 0, w, h);
    g.imageSmoothingEnabled = false;
    const [i] = this.current(angle);
    const [cw, ch] = this.info.cell, [ax, ay] = this.info.anchor, cols = this.info.columns;
    const px = Math.max(1, pxPerUnit * dpr * this.info.scale);
    g.drawImage(this.sheet, (i % cols) * cw, Math.floor(i / cols) * ch, cw, ch,
                Math.round(w / 2 - ax * px), Math.round(h * feetY - ay * px), cw * px, ch * px);
  }

  viewName() { return this.still ? "" : `(${VIEWS[this.shown.view].replace("_", " ")} view)`; }
}
