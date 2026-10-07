/**
 * MENTAL.AI entry sculpture - original neural signal form (vanilla Three.js).
 *
 * Six flowing strands of glossy near-black metal, threaded past an invisible
 * core: three tubes, two flattened ribbons and one thin emissive signal wire.
 * The reference intent is cognitive signal - pathways that loop, cross and
 * gather - rather than a mechanical gyroscope, so the curves are deliberately
 * asymmetric and never close into a torus knot.
 *
 * Why the material is this dark: the form is defined by reflected light, not by
 * a lit surface. A near-black base with a tight clearcoat means only the curves
 * facing a strip of the environment come forward, and everything else stays in
 * the dark. That high-contrast reading is the whole look.
 *
 * Motion is deliberately near-subliminal: a slow group drift, each strand
 * breathing on its own phase, and a bead of light that travels one strand every
 * few seconds. Nothing spins as a unit.
 *
 * Lifecycle mirrors components/hero/sculpture.ts: one render loop, paused when
 * the tab is hidden or the canvas scrolls out of view, a single composed frame
 * under reduced motion, and full disposal on unmount.
 */
import * as THREE from "three";
import { buildStudioEnvironment } from "./studioEnv";

export interface NeuralSculptureOptions {
  reducedMotion: boolean;
  /** ms after start() before the metal begins materializing out of darkness. */
  emergeDelayMs?: number;
  /** 0..1 quality scale; mobile runs lower. */
  quality?: number;
  /**
   * Where the form sits inside whatever box the canvas occupies.
   *
   * Fractions of the canvas, not world units: the stage this lives in is a
   * grid column, so its width and aspect change with the window, and the form
   * has to hold its place in the composition rather than in the world. The
   * renderer converts these into world offsets using the visible extents it
   * computes for the current aspect, so one description works at every size.
   */
  framing?: NeuralFraming;
}

export interface NeuralFraming {
  /** Horizontal centre of the visual mass, 0..1 across the canvas. */
  x?: number;
  /** Vertical centre of the visual mass, 0..1 down the canvas. */
  y?: number;
  /** Multiplies the size the form would otherwise occupy. */
  scale?: number;
}

/**
 * The frame the form is composed into, in world units.
 *
 * Both axes are sized from the geometry rather than from a camera distance, so
 * the form occupies the same share of the stage whether the stage is 1.8:1 or
 * 0.9:1. Distance is then derived from whichever axis binds, which is why a
 * narrow column pulls the camera back instead of cropping the silhouette.
 */
const FRAME_W = 5.9;
const FRAME_H = 5.75;

/**
 * Base tints.
 *
 * Not near-black: for a metal the base colour is the specular reflectance, and
 * a value of #050509 reflects under 2% of the environment, which renders as a
 * black void no matter how good the lighting is. The form reads as dark chrome
 * because the environment is a black void with a few bright strips, not because
 * the albedo is black.
 */
const BASE = 0x1d1d25;
const MID = 0x26262f;
const VIOLET = 0x7b5cff;
const BLUE = 0x4d9fff;

/**
 * Deterministic pseudo-random, so a resize rebuilds the same sculpture rather
 * than a different one.
 */
function rand(i: number, salt: number): number {
  const x = Math.sin(i * 91.7 + salt * 37.13) * 43758.5453;
  return x - Math.floor(x);
}

/**
 * One strand: a path that drifts off-axis, swells through the middle and
 * tucks back toward the core. Control points are perturbed per index so no two
 * strands share a silhouette.
 */
function strandCurve(index: number, spec: StrandSpec): THREE.CatmullRomCurve3 {
  const pts: THREE.Vector3[] = [];
  const count = spec.points;
  const phase = rand(index, 1) * Math.PI * 2;
  const tilt = (rand(index, 2) - 0.5) * 1.5;
  const lift = (rand(index, 3) - 0.5) * 1.3;

  for (let i = 0; i < count; i++) {
    const t = i / (count - 1);
    const a = phase + t * spec.turns * Math.PI * 2;
    // Radius pinches at both ends and swells at the waist: a closed loop would
    // read as a ring, this reads as something passing through.
    const waist = Math.sin(t * Math.PI);
    const r = spec.radius * (0.55 + waist * 0.75) * (0.85 + rand(index, 4) * 0.3);
    const y = (t - 0.5) * spec.height + Math.sin(t * Math.PI * 2 + phase) * spec.wave;
    pts.push(
      new THREE.Vector3(
        Math.cos(a) * r + tilt * waist,
        y + lift * waist,
        // Depth is compressed so strands overlap in the frame instead of
        // lining up as a flat spiral.
        Math.sin(a) * r * spec.depth
      )
    );
  }
  return new THREE.CatmullRomCurve3(pts, false, "centripetal");
}

interface StrandSpec {
  radius: number;
  height: number;
  wave: number;
  turns: number;
  depth: number;
  points: number;
  /** 'tube' | 'ribbon' | 'wire' */
  form: "tube" | "ribbon" | "wire";
}

/**
 * Six strands with unrelated geometry. The two ribbons and the wire are placed
 * on the outer radii so the silhouette is not uniformly tubular.
 */
const STRANDS: StrandSpec[] = [
  { form: "tube", radius: 1.62, height: 3.5, wave: 0.22, turns: 0.82, depth: 0.92, points: 11 },
  { form: "tube", radius: 1.24, height: 3.1, wave: 0.3, turns: -1.05, depth: 1.05, points: 12 },
  { form: "tube", radius: 1.9, height: 2.7, wave: 0.18, turns: 0.66, depth: 0.8, points: 10 },
  { form: "ribbon", radius: 1.45, height: 3.3, wave: 0.26, turns: -0.78, depth: 0.95, points: 11 },
  { form: "ribbon", radius: 1.72, height: 2.9, wave: 0.34, turns: 0.94, depth: 0.86, points: 10 },
  { form: "wire", radius: 1.05, height: 3.6, wave: 0.28, turns: 1.22, depth: 1.1, points: 12 },
];

/**
 * Flattened strand: a tube scaled on one axis reads as a ribbon at a fraction
 * of the geometry and vertex cost of bespoke ribbon geometry, and keeps the
 * same clearcoat response.
 */
function strandMesh(
  curve: THREE.CatmullRomCurve3,
  spec: StrandSpec,
  material: THREE.Material,
  quality: number
): THREE.Mesh {
  const seg = quality < 1 ? 90 : 170;
  const radial = spec.form === "ribbon" ? 8 : quality < 1 ? 10 : 16;
  const thickness = spec.form === "wire" ? 0.018 : spec.form === "ribbon" ? 0.06 : 0.115;
  const mesh = new THREE.Mesh(new THREE.TubeGeometry(curve, seg, thickness, radial, false), material);
  if (spec.form === "ribbon") mesh.scale.set(1, 1, 0.26);
  return mesh;
}

export function createNeuralSculpture(
  canvas: HTMLCanvasElement,
  opts: NeuralSculptureOptions
) {
  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      powerPreference: "high-performance",
    });
  } catch {
    // No WebGL. The caller falls back to the 2D canvas engine.
    return null;
  }

  const quality = opts.quality ?? 1;
  const framing: Required<NeuralFraming> = {
    x: opts.framing?.x ?? 0.5,
    y: opts.framing?.y ?? 0.5,
    scale: opts.framing?.scale ?? 1,
  };
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.08;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 60);
  camera.position.set(0, 0.1, 5.6);

  const envMap = buildStudioEnvironment(renderer);
  scene.environment = envMap;

  // ---------------- Materials ----------------
  const bodyMat = new THREE.MeshPhysicalMaterial({
    color: BASE,
    metalness: 0.9,
    roughness: 0.26,
    clearcoat: 0.85,
    clearcoatRoughness: 0.2,
    envMapIntensity: 1.0,
  });
  const ribbonMat = new THREE.MeshPhysicalMaterial({
    color: MID,
    metalness: 0.86,
    roughness: 0.31,
    clearcoat: 0.75,
    clearcoatRoughness: 0.26,
    envMapIntensity: 0.95,
  });
  const wireMat = new THREE.MeshStandardMaterial({
    color: 0x1a1430,
    metalness: 0.6,
    roughness: 0.35,
    emissive: new THREE.Color(VIOLET).multiplyScalar(0.5),
    envMapIntensity: 0.9,
  });
  const coreMat = new THREE.MeshPhysicalMaterial({
    color: 0x14141b,
    metalness: 1,
    roughness: 0.16,
    clearcoat: 1,
    clearcoatRoughness: 0.12,
    envMapIntensity: 1.35,
  });
  const surfaces = [bodyMat, ribbonMat, wireMat, coreMat];

  /**
   * Organic displacement injected into the vertex shader.
   *
   * Rotating a static form reads as a product turntable. Two low-frequency sine
   * waves along the strand, each on its own phase, make the metal look like it
   * is carrying something. Implemented as an onBeforeCompile patch rather than
   * CPU vertex updates so the per-frame cost stays on the GPU.
   */
  const waveUniform = { value: 0 };
  function applyBreathing(material: THREE.Material, amount: number, key: string) {
    material.onBeforeCompile = (shader) => {
      shader.uniforms.uWave = waveUniform;
      shader.uniforms.uAmount = { value: amount };
      shader.vertexShader = shader.vertexShader
        .replace(
          "#include <common>",
          `#include <common>
           uniform float uWave;
           uniform float uAmount;`
        )
        .replace(
          "#include <begin_vertex>",
          `#include <begin_vertex>
           float w = sin(transformed.y * 1.7 + uWave * 1.1)
                   + sin(transformed.y * 3.1 - uWave * 0.7) * 0.5;
           transformed.x += w * uAmount;
           transformed.z += cos(transformed.y * 2.2 + uWave * 0.9) * uAmount * 0.6;`
        );
    };
    // Distinct key per amount so patched programs do not share a cache slot.
    material.customProgramCacheKey = () => `neural-breath-${key}-${amount}`;
  }
  applyBreathing(bodyMat, 0.03, "body");
  applyBreathing(ribbonMat, 0.024, "ribbon");
  applyBreathing(wireMat, 0.016, "wire");

  // ---------------- Geometry ----------------
  const group = new THREE.Group();
  const curves: THREE.CatmullRomCurve3[] = [];
  const strandMeshes: THREE.Mesh[] = [];

  STRANDS.forEach((spec, i) => {
    const curve = strandCurve(i, spec);
    curves.push(curve);
    const material = spec.form === "ribbon" ? ribbonMat : spec.form === "wire" ? wireMat : bodyMat;
    const mesh = strandMesh(curve, spec, material, quality);
    mesh.rotation.y = rand(i, 7) * Math.PI;
    mesh.rotation.x = (rand(i, 8) - 0.5) * 0.5;
    group.add(mesh);
    strandMeshes.push(mesh);
  });

  // Convergence point: a small polished node the strands appear to gather around.
  const core = new THREE.Mesh(new THREE.IcosahedronGeometry(0.26, quality < 1 ? 2 : 3), coreMat);
  core.position.set(0.05, 0.02, 0);
  group.add(core);

  // One bead of light per signal event, riding a random strand.
  const beadMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(1.5, 0.85, 4.4) });
  const bead = new THREE.Mesh(new THREE.SphereGeometry(0.036, 12, 12), beadMat);
  const beadLight = new THREE.PointLight(VIOLET, 0, 3.4, 2);
  bead.visible = false;
  group.add(bead, beadLight);
  const edgeLight = new THREE.PointLight(BLUE, 0, 3, 2);
  edgeLight.visible = false;
  group.add(edgeLight);

  scene.add(group);

  // Faint motes for depth; secondary atmosphere only.
  const dustN = quality < 1 ? 34 : 64;
  const dustPos = new Float32Array(dustN * 3);
  for (let i = 0; i < dustN; i++) {
    const th = rand(i, 20) * Math.PI * 2;
    const rr = 1.4 + rand(i, 21) * 2.8;
    dustPos[i * 3] = Math.cos(th) * rr;
    dustPos[i * 3 + 1] = (rand(i, 22) - 0.5) * 4.6;
    dustPos[i * 3 + 2] = Math.sin(th) * rr - 0.8;
  }
  const dustGeo = new THREE.BufferGeometry();
  dustGeo.setAttribute("position", new THREE.BufferAttribute(dustPos, 3));
  const dust = new THREE.Points(
    dustGeo,
    new THREE.PointsMaterial({
      color: 0x93a9d6,
      size: 0.016,
      transparent: true,
      opacity: 0.34,
      sizeAttenuation: true,
    })
  );
  scene.add(dust);

  // ---------------- Lighting ----------------
  // Everything is dim on purpose: the studio strips in the environment do the
  // modelling, these only shape the silhouette and give the edges colour.
  const key = new THREE.DirectionalLight(0xffffff, 0);
  key.position.set(-4, 5, 4);
  const rim = new THREE.DirectionalLight(0x9d86ff, 0);
  rim.position.set(3.5, 1.5, -4.5);
  const edge = new THREE.DirectionalLight(0x5fa8ff, 0);
  edge.position.set(-3.5, -2.4, -3);
  const fill = new THREE.DirectionalLight(0xdfe6ff, 0);
  fill.position.set(2.2, -1.6, 4.2);
  scene.add(key, rim, edge, fill);

  const TARGET_ENV = [0.95, 0.88, 0.65, 1.15];
  const TARGET = { key: 1.05, rim: 0.95, edge: 0.7, fill: 0.26 };

  // ---------------- Runtime ----------------
  let raf = 0;
  let running = false;
  let visible = true;
  let tabActive = true;
  let pointerX = 0;
  let pointerY = 0;
  let smoothX = 0;
  let smoothY = 0;
  let t0 = 0;
  let last = 0;
  let emerged = 0;
  let nextSignal = 2.4;
  let signalT = -1;
  let signalCurve = 0;
  let contract = 0;
  // Placement in world space, derived from the stage's current visible extents.
  let baseX = 0;
  let baseY = 0;
  let baseScale = 1;

  /**
   * Re-frame for the box the canvas actually occupies.
   *
   * Measures the host element rather than the window, so the composition is
   * stated in fractions of the visual stage: the camera backs off until the
   * form fits on both axes, and the group is then slid to the requested point
   * in the frame. A narrow column therefore gets a smaller, further-back form
   * at the same relative position instead of a cropped one.
   */
  function resize() {
    const host = canvas.parentElement ?? canvas;
    const rect = host.getBoundingClientRect();
    const dprCap = quality < 1 ? 1.25 : 1.75;
    const w = Math.max(1, rect.width);
    const h = Math.max(1, rect.height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, dprCap));
    renderer.setSize(w, h, false);
    const aspect = Math.max(0.2, w / h);
    camera.aspect = aspect;
    const tanHalf = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
    const distV = FRAME_H / (2 * tanHalf);
    const distH = FRAME_W / (2 * tanHalf * aspect);
    camera.position.z = THREE.MathUtils.clamp(Math.max(distV, distH), 6, 16);
    camera.updateProjectionMatrix();

    const visibleH = 2 * camera.position.z * tanHalf;
    const visibleW = visibleH * aspect;
    baseX = (framing.x - 0.5) * visibleW;
    baseY = (0.5 - framing.y) * visibleH;
    baseScale = framing.scale;
  }

  const ro = new ResizeObserver(() => {
    resize();
    if (opts.reducedMotion) drawStatic();
  });
  ro.observe(canvas.parentElement ?? canvas);

  const io = new IntersectionObserver(
    (entries) => {
      visible = entries[0]?.isIntersecting ?? true;
    },
    { threshold: 0.02 }
  );
  io.observe(canvas);

  const onVis = () => {
    tabActive = !document.hidden;
  };
  document.addEventListener("visibilitychange", onVis);

  function applyEmergence(e: number) {
    for (let i = 0; i < surfaces.length; i++) surfaces[i].envMapIntensity = TARGET_ENV[i] * e;
    key.intensity = TARGET.key * e;
    rim.intensity = TARGET.rim * e;
    edge.intensity = TARGET.edge * e;
    fill.intensity = TARGET.fill * e;
    dust.material.opacity = 0.34 * e;
  }

  function frame(now: number) {
    raf = requestAnimationFrame(frame);
    const time = (now - t0) / 1000;
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    if (!visible || !tabActive) return;

    const start = (opts.emergeDelayMs ?? 0) / 1000;
    const et = (time - start) / 2.2;
    emerged = et <= 0 ? 0 : et >= 1 ? 1 : 1 - Math.pow(1 - et, 3);
    applyEmergence(emerged);
    waveUniform.value = time * (opts.reducedMotion ? 0 : 0.6);

    smoothX += (pointerX - smoothX) * 0.04;
    smoothY += (pointerY - smoothY) * 0.04;

    // Breathing: each strand on its own phase, so the cluster never pulses
    // as one object.
    for (let i = 0; i < strandMeshes.length; i++) {
      const m = strandMeshes[i];
      const ph = i * 1.7;
      m.rotation.y += dt * 0.012 * (i % 2 === 0 ? 1 : -1);
      m.rotation.z = Math.sin(time * 0.06 + ph) * 0.035;
      m.position.y = Math.sin(time * 0.09 + ph) * 0.045;
    }
    core.rotation.y -= dt * 0.045;
    core.rotation.x += dt * 0.02;

    // Whole-form drift, deliberately tiny. The resting position is the one
    // resize() derived from the stage, so the drift never fights the framing.
    group.rotation.y = Math.sin(time * 0.045) * 0.11 + smoothX * 0.15;
    group.rotation.x = Math.sin(time * 0.031) * 0.045 + smoothY * 0.08;
    group.position.y = baseY + Math.sin(time * 0.07) * 0.05;
    group.position.x = baseX;

    // Contracting toward the centre while the greeting is on screen.
    group.scale.setScalar(baseScale * (1 - contract * 0.06));

    camera.position.x = Math.sin(time * 0.026) * 0.14 + smoothX * 0.2;
    camera.position.y = Math.cos(time * 0.031) * 0.07 - smoothY * 0.1;
    camera.lookAt(0, 0, 0);

    // Signal event: a bead rides one strand and lights it as it passes.
    if (emerged > 0.9 && !opts.reducedMotion && time > nextSignal) {
      nextSignal = time + 3.8 + rand(Math.floor(time * 10), 33) * 3;
      signalCurve = Math.floor(rand(Math.floor(time * 7), 34) * curves.length);
      signalT = 0;
    }
    if (signalT >= 0) {
      const nt = signalT + dt / 3.1;
      if (nt >= 1) {
        signalT = -1;
        bead.visible = false;
        beadLight.intensity = 0;
        edgeLight.visible = false;
      } else {
        const p = curves[signalCurve].getPointAt(nt);
        bead.position.copy(p);
        beadLight.position.copy(p);
        const env = Math.sin(nt * Math.PI);
        bead.visible = true;
        beadLight.intensity = 7 * env;
        // A second, dimmer light on the opposite side keeps the edge from
        // reading as a single coloured dot.
        edgeLight.position.set(-p.x * 0.6, -p.y * 0.6, p.z * 0.4);
        edgeLight.intensity = 2.2 * env;
        edgeLight.visible = true;
      }
    }

    dust.rotation.y = time * 0.007;

    renderer.render(scene, camera);
  }

  function drawStatic() {
    applyEmergence(1);
    waveUniform.value = 0;
    group.rotation.set(0.08, -0.2, 0);
    group.position.set(baseX, baseY, 0);
    group.scale.setScalar(baseScale);
    camera.position.set(0.08, 0.14, camera.position.z);
    camera.lookAt(0, 0, 0);
    renderer.render(scene, camera);
  }

  resize();

  return {
    start() {
      if (running) return;
      running = true;
      if (opts.reducedMotion) {
        drawStatic();
        return;
      }
      t0 = performance.now();
      last = t0;
      raf = requestAnimationFrame(frame);
    },
    stop() {
      running = false;
      cancelAnimationFrame(raf);
    },
    destroy() {
      running = false;
      cancelAnimationFrame(raf);
      ro.disconnect();
      io.disconnect();
      document.removeEventListener("visibilitychange", onVis);
      scene.traverse((o) => {
        if (o instanceof THREE.Mesh || o instanceof THREE.Points) {
          o.geometry.dispose();
          const m = o.material;
          if (Array.isArray(m)) m.forEach((x) => x.dispose());
          else m.dispose();
        }
      });
      envMap.dispose();
      renderer.dispose();
    },
    setPointer(x: number, y: number) {
      pointerX = x;
      pointerY = y;
    },
    /** 0..1: pull the form inward and let the glow lift, for the greeting. */
    setFocus(v: number) {
      contract = v;
    },
  };
}

export type NeuralSculptureHandle = NonNullable<ReturnType<typeof createNeuralSculpture>>;