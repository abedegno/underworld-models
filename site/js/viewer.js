// A model's page: the smooth model (its glb, with its clips and colourings) or its voxels, turned with the mouse.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { readUwvc } from "./uwvc.js";

const $ = id => document.getElementById(id);
const FRAME_SECONDS = 1 / 8;   // voxel clips step at eight frames a second: one key frame per sprite frame

const params = new URLSearchParams(location.search);   // id, and optionally view=voxels, colouring=N, clip=name
const key = params.get("id");
const models = await (await fetch("data/models.json")).json();
const m = models.find(x => x.key === key);
if (!m) fail(`No model called ${key}.`);

document.title = `${m.name} · Underworld Models`;
$("name").textContent = m.name;
$("meta").textContent = [m.kind === "creature" ? "Creature" : "Item", m.id, m.variant_of ? `variant of ${m.variant_of}` : ""]
  .filter(Boolean).join(" · ");
$("back").href = m.kind === "item" ? "./?kind=item" : "./";
$("shot").src = m.shot || "";
if (!m.shot) $("shot").closest("figure").hidden = true;
$("download").href = m.download;
$("howto").href = m.howto;
$("github").href = m.github;

const view = $("view");
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
view.append(renderer.domElement);
const scene = new THREE.Scene();
scene.add(new THREE.HemisphereLight(0xffffff, 0x444444, 2.2));
const sun = new THREE.DirectionalLight(0xffffff, 1.6);
sun.position.set(1, 2, 1.5);
scene.add(sun);
const camera = new THREE.PerspectiveCamera(30, 1, 0.01, 100);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

let smooth = null, mixer = null, action = null, voxels = null, playing = true, showing = "smooth";
const clock = new THREE.Clock();

function fail(text) {
  $("error").textContent = text;
  $("error").hidden = false;
  throw new Error(text);
}

function fit(object) {
  object.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(object, true);   // precise: a skinned mesh's posed vertices
  const size = box.getSize(new THREE.Vector3()), centre = box.getCenter(new THREE.Vector3());
  const r = Math.max(size.x, size.y, size.z) || 1;
  controls.target.copy(centre);
  camera.position.copy(centre).add(new THREE.Vector3(0.55, 0.35, 1).normalize().multiplyScalar(r * 2.9));
  camera.near = r / 100;
  camera.far = r * 100;
  camera.updateProjectionMatrix();
  controls.update();
}

function resize() {
  const w = view.clientWidth, h = view.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(view);

// --- voxels -----------------------------------------------------------------------------------------------
class Voxels {
  constructor(data) {
    this.data = data;
    this.group = new THREE.Group();
    this.box = new THREE.BoxGeometry(data.size, data.size, data.size);
    this.material = new THREE.MeshLambertMaterial();
    this.meshes = new Map();   // "clip/frame" -> InstancedMesh, built when first shown
    this.colouring = 0;
    this.clip = [...data.clips.keys()][0];
    this.frame = 0;
    this.time = 0;
  }
  mesh(clip, f) {
    const k = `${clip}/${f}/${this.colouring}`;
    if (!this.meshes.has(k)) {
      const v = this.data.clips.get(clip)[f], n = v.length / 4, s = this.data.size, o = this.data.origin;
      const mesh = new THREE.InstancedMesh(this.box, this.material, Math.max(n, 1));
      mesh.count = n;
      const mat = new THREE.Matrix4(), col = new THREE.Color(), table = this.data.colourings[this.colouring];
      for (let i = 0; i < n; i++) {
        mat.makeTranslation((v[4 * i] + o[0] + 0.5) * s, (v[4 * i + 1] + o[1] + 0.5) * s, (v[4 * i + 2] + o[2] + 0.5) * s);
        mesh.setMatrixAt(i, mat);
        const rgb = table.get(v[4 * i + 3]) || [255, 0, 255];
        mesh.setColorAt(i, col.setRGB(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, THREE.SRGBColorSpace));
      }
      this.meshes.set(k, mesh);
    }
    return this.meshes.get(k);
  }
  show() {
    const frames = this.data.clips.get(this.clip);
    this.frame = Math.min(this.frame, frames.length - 1);
    this.group.clear();
    this.group.add(this.mesh(this.clip, this.frame));
  }
  step(dt) {
    const frames = this.data.clips.get(this.clip);
    if (frames.length < 2) return;
    this.time += dt;
    if (this.time >= FRAME_SECONDS) {
      this.time %= FRAME_SECONDS;
      this.frame = (this.frame + 1) % frames.length;
      this.show();
    }
  }
}

async function loadVoxels() {
  if (!voxels) {
    const buffer = await (await fetch(m.voxels)).arrayBuffer();
    voxels = new Voxels(readUwvc(buffer));
    voxels.colouring = Number($("colour").value || 0);
    voxels.clip = voxels.data.clips.has($("clip").value) ? $("clip").value : voxels.clip;
    voxels.show();
  }
  return voxels;
}

// --- the smooth model --------------------------------------------------------------------------------------
async function loadSmooth() {
  if (!smooth) {
    const gltf = await new GLTFLoader().loadAsync(m.smooth);
    smooth = gltf.scene;
    smooth.traverse(o => {
      if (o.isSkinnedMesh) o.frustumCulled = false;   // its bounds are those of the bind pose, not the clip's
      if (o.isMesh && o.material.emissive) o.material.emissive.setRGB(0, 0, 0);   // a glow would wash the colours out to white
      if (o.isMesh && o.material.map) {
        o.material.map.magFilter = THREE.NearestFilter;   // keep the texture's pixels crisp, as the game's are
        o.material.metalness = 0;
        o.material.roughness = 1;
      }
    });
    if (gltf.animations.length) {
      mixer = new THREE.AnimationMixer(smooth);
      smooth.userData.clips = gltf.animations;
    }
  }
  return smooth;
}

function playClip(name) {
  if (mixer) {
    const clip = smooth.userData.clips.find(c => c.name === name);
    if (action) action.stop();
    if (clip) {
      action = mixer.clipAction(clip);
      action.reset().play();
      action.paused = !playing;
    }
  }
  if (voxels && voxels.data.clips.has(name)) {
    voxels.clip = name;
    voxels.frame = 0;
    voxels.show();
  }
}

async function setColouring(i) {
  if (voxels) {
    voxels.colouring = i;
    voxels.show();
  }
  const c = m.colourings[i];
  if (smooth && c) {
    const res = await fetch(c.texture);
    if (!res.ok) throw new Error(`${c.texture}: ${res.status}`);
    const tex = new THREE.Texture(await createImageBitmap(await res.blob(), { imageOrientation: "none" }));
    tex.needsUpdate = true;
    tex.flipY = false;
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.magFilter = THREE.NearestFilter;
    smooth.traverse(o => { if (o.isMesh && o.material.map) { o.material.map = tex; o.material.needsUpdate = true; } });
  }
}

async function showMode(mode) {
  showing = mode;
  $("smooth").setAttribute("aria-pressed", String(mode === "smooth"));
  $("voxels").setAttribute("aria-pressed", String(mode === "voxels"));
  const object = mode === "smooth" ? await loadSmooth() : (await loadVoxels()).group;
  scene.remove(...scene.children.filter(o => o.userData.model));
  object.userData.model = true;
  scene.add(object);
  fit(object);   // before the colouring's texture arrives, so a slow one never leaves the view empty
  if (mode === "smooth" && m.colourings.length) setColouring(Number($("colour").value || 0));
}

// --- controls ----------------------------------------------------------------------------------------------
const clipNames = m.clips || [];
if (clipNames.length > 1 || m.kind === "creature") {
  $("clipRow").hidden = $("play").hidden = false;
  $("clip").replaceChildren(...clipNames.map(n => new Option(n.replaceAll("_", " "), n)));
  $("clip").addEventListener("change", () => playClip($("clip").value));
  if (clipNames.includes(params.get("clip"))) $("clip").value = params.get("clip");
  $("play").addEventListener("click", () => {
    playing = !playing;
    $("play").textContent = playing ? "Pause" : "Play";
    if (action) action.paused = !playing;
  });
}
if (m.colourings.length > 1) {
  $("colourRow").hidden = false;
  $("colour").replaceChildren(...m.colourings.map((c, i) => new Option(c.name, String(i))));
  $("colour").addEventListener("change", () => setColouring(Number($("colour").value)));
  if (params.has("colouring") && m.colourings[Number(params.get("colouring"))]) $("colour").value = params.get("colouring");
}
if (!m.smooth) {
  $("smooth").disabled = true;
  $("smooth").title = "This item has voxels only";
}
$("smooth").addEventListener("click", () => showMode("smooth"));
$("voxels").addEventListener("click", () => showMode("voxels"));

try {
  await showMode(m.smooth && params.get("view") !== "voxels" ? "smooth" : "voxels");
  if (clipNames.length) playClip($("clip").value);
} catch (e) {
  fail(`The model could not be loaded: ${e.message}`);
}

renderer.setAnimationLoop(() => {
  const dt = clock.getDelta();
  if (playing) {
    if (mixer && showing === "smooth") mixer.update(dt);
    if (voxels && showing === "voxels") voxels.step(dt);
  }
  controls.update();
  renderer.render(scene, camera);
});
