// The original sprite beside the model: the frame the game would show for the chosen clip, seen from where the
// camera is (or turned separately), drawn with whole pixels at the model's size on screen.
import { VIEWS, viewFor, pick, advance, fitScale, offsetX, FPS } from "./spritelogic.js";

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
                               scale: m.sprite.scale, anims: {}, colourings: {},
                               bounds: [[0, 0, img.width, img.height]] }, "", img, true);
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
    this.shown = { name: "", frontOnly: false, view: 4, index: 0 };
    this.length = 1;   // frames in the animation shown
  }

  setClip(name) { this.clip = name; this.time = 0; }
  async setColouring(aux) {
    const file = this.info.colourings[aux];
    if (!file) return;
    this.sheets[aux] ??= image(this.base + file);   // each sheet fetched once, when first chosen
    this.sheet = await this.sheets[aux];
  }
  step(dt) { this.time = advance(this.time, dt, this.clip, this.length); }
  stepFrame(n) { this.time = advance(Math.floor(this.time * FPS + 1e-6) / FPS, n / FPS, this.clip, this.length); }
  turn(n) { this.view = (this.view + n + 8) % 8; }

  // The frame to show now (shown.index is null when the body has no such animation).
  current(angle) {
    if (this.still) return (this.shown = { name: "", frontOnly: false, view: 4, index: 0 });
    const view = this.separate ? this.view : viewFor(angle);
    this.shown = pick(this.info.anims, this.clip, view, this.time);
    this.length = (this.info.anims[this.shown.name] || [0]).length;
    return this.shown;
  }

  // Draws on `canvas` with one sprite pixel covering `pxPerUnit * scale` canvas pixels (in whole pixels, and smaller
  // if the frame would not fit), the anchor (the creature's
  // feet) at canvas height `feetY` (0 to 1 from the top).
  draw(canvas, angle, pxPerUnit, feetY) {
    const dpr = Math.min(devicePixelRatio, 2);
    const w = Math.round(canvas.clientWidth * dpr), h = Math.round(canvas.clientHeight * dpr);
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
    const g = canvas.getContext("2d");
    g.clearRect(0, 0, w, h);
    g.imageSmoothingEnabled = false;
    const i = this.current(angle).index;
    if (i === null) return;   // the game draws nothing for an animation the body lacks
    const [cw, ch] = this.info.cell, [ax, ay] = this.info.anchor, cols = this.info.columns;
    const box = this.box();
    const px = fitScale(pxPerUnit * dpr * this.info.scale, box, this.info.anchor, w, h, feetY);
    g.drawImage(this.sheet, (i % cols) * cw, Math.floor(i / cols) * ch, cw, ch,
                Math.round(offsetX(w, box, this.info.anchor, px)), Math.round(h * feetY - ay * px), cw * px, ch * px);
  }

  // The bounds of all the frames of the animation shown, so its size stays the same from frame to frame.
  box() {
    const frames = this.still ? [0] : this.info.anims[this.shown.name] || [this.shown.index];
    const b = frames.map(k => this.info.bounds[k]);
    return [Math.min(...b.map(x => x[0])), Math.min(...b.map(x => x[1])),
            Math.max(...b.map(x => x[2])), Math.max(...b.map(x => x[3]))];
  }

  viewName() { return this.still ? "" : `(${VIEWS[this.shown.view].replace("_", " ")} view)`; }
}
