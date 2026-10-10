/**
 * MENTAL.AI Hero Sculpture — Rotating Metallic Spiral Spring DNA (Three.js).
 *
 * Art-directed metallic kinetic sculpture:
 *   - Intertwined double-helix strands (Alpha & Beta helices) in polished dark chrome / titanium.
 *   - Metallic horizontal connecting rungs (DNA base-pair crossbars) with sphere caps and jewel accents.
 *   - Sweeping outer spiral spring ribbon winding around the DNA core.
 *   - Continuous, silky-smooth 360-degree rotation along the Y-axis.
 *   - Ultra-crisp specular highlights derived from procedural studio lighting environment.
 *   - Zero stutter / zero glitch rendering with frame-rate independent delta time.
 */
import * as THREE from "three";
import { buildStudioEnvironment } from "./studioEnv";

export interface NeuralSculptureOptions {
  reducedMotion: boolean;
  emergeDelayMs?: number;
  quality?: number;
  framing?: NeuralFraming;
}

export interface NeuralFraming {
  x?: number;
  y?: number;
  scale?: number;
}

const FRAME_W = 6.4;
const FRAME_H = 6.8;

// High-fidelity metallic titanium / chrome tints
const CHROME_TITANIUM = 0x22262e;
const CHROME_POLISHED = 0x323844;
const CHROME_DARK = 0x16181f;
const JEWEL_ACCENT = 0x7b5cff;
const JEWEL_CYAN = 0x4d9fff;

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
    return null;
  }

  const quality = opts.quality ?? 1;
  const framing: Required<NeuralFraming> = {
    x: opts.framing?.x ?? 0.5,
    y: opts.framing?.y ?? 0.5,
    scale: opts.framing?.scale ?? 1,
  };

  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 60);
  camera.position.set(0, 0.08, 6.2);

  const envMap = buildStudioEnvironment(renderer);
  scene.environment = envMap;

  // ---------------- Metallic Materials ----------------
  // Primary dark titanium chrome for main DNA strands
  const primaryHelixMat = new THREE.MeshPhysicalMaterial({
    color: CHROME_TITANIUM,
    metalness: 0.98,
    roughness: 0.14,
    clearcoat: 1.0,
    clearcoatRoughness: 0.06,
    envMapIntensity: 1.85,
  });

  // Secondary polished chrome for outer spiral spring ribbon
  const spiralSpringMat = new THREE.MeshPhysicalMaterial({
    color: CHROME_POLISHED,
    metalness: 0.96,
    roughness: 0.12,
    clearcoat: 1.0,
    clearcoatRoughness: 0.05,
    envMapIntensity: 2.1,
  });

  // Connecting DNA rungs (crossbars)
  const rungMat = new THREE.MeshPhysicalMaterial({
    color: CHROME_DARK,
    metalness: 0.94,
    roughness: 0.2,
    clearcoat: 0.85,
    clearcoatRoughness: 0.1,
    envMapIntensity: 1.5,
  });

  // Spherical junction node caps
  const nodeMat = new THREE.MeshPhysicalMaterial({
    color: 0x2c323d,
    metalness: 0.98,
    roughness: 0.08,
    clearcoat: 1.0,
    clearcoatRoughness: 0.04,
    envMapIntensity: 2.2,
  });

  // Emissive jewel accents on alternating rungs
  const jewelMat = new THREE.MeshStandardMaterial({
    color: 0x141028,
    metalness: 0.8,
    roughness: 0.25,
    emissive: new THREE.Color(JEWEL_ACCENT),
    emissiveIntensity: 0.85,
  });

  const jewelCyanMat = new THREE.MeshStandardMaterial({
    color: 0x0f1d2d,
    metalness: 0.8,
    roughness: 0.25,
    emissive: new THREE.Color(JEWEL_CYAN),
    emissiveIntensity: 0.85,
  });

  // Root group for all sculpture components
  const group = new THREE.Group();
  scene.add(group);

  // Inner rotating DNA group
  const dnaGroup = new THREE.Group();
  group.add(dnaGroup);

  // ---------------- Double Helix & Spring Geometry (Spaced out, Bigger, Thicker) ----------------
  const DNA_HEIGHT = 6.4;
  const DNA_TURNS = 1.35;
  const DNA_RADIUS = 1.75;

  function createHelixCurve(phaseOffset: number): THREE.CatmullRomCurve3 {
    const pts: THREE.Vector3[] = [];
    const N = 80;
    for (let i = 0; i <= N; i++) {
      const t = i / N;
      const angle = t * DNA_TURNS * Math.PI * 2 + phaseOffset;
      // Waist taper: wider at center, tapered gently toward ends
      const r = DNA_RADIUS * (0.88 + 0.24 * Math.sin(t * Math.PI));
      const y = (t - 0.5) * DNA_HEIGHT;
      pts.push(new THREE.Vector3(Math.cos(angle) * r, y, Math.sin(angle) * r));
    }
    return new THREE.CatmullRomCurve3(pts, false, "centripetal");
  }

  // Alpha and Beta helical curves (180 deg / PI phase offset)
  const curveAlpha = createHelixCurve(0);
  const curveBeta = createHelixCurve(Math.PI);

  const tubularSegs = quality < 1 ? 160 : 260;
  const radialSegs = quality < 1 ? 14 : 22;
  const strandRadius = 0.15; // Prominent, thick metallic strands

  const geomAlpha = new THREE.TubeGeometry(curveAlpha, tubularSegs, strandRadius, radialSegs, false);
  const meshAlpha = new THREE.Mesh(geomAlpha, primaryHelixMat);
  dnaGroup.add(meshAlpha);

  const geomBeta = new THREE.TubeGeometry(curveBeta, tubularSegs, strandRadius, radialSegs, false);
  const meshBeta = new THREE.Mesh(geomBeta, primaryHelixMat);
  dnaGroup.add(meshBeta);

  // ---------------- Horizontal DNA Connecting Rungs (Spaced Out & Thicker) ----------------
  const RUNGS_COUNT = 10; // Spaced out rungs
  const nodeGeom = new THREE.SphereGeometry(0.14, quality < 1 ? 14 : 20, quality < 1 ? 14 : 20);
  const jewelGeom = new THREE.CylinderGeometry(0.09, 0.09, 0.22, 16);

  for (let i = 0; i < RUNGS_COUNT; i++) {
    const t = 0.07 + (i / (RUNGS_COUNT - 1)) * 0.86;
    const pA = curveAlpha.getPointAt(t);
    const pB = curveBeta.getPointAt(t);

    const mid = new THREE.Vector3().addVectors(pA, pB).multiplyScalar(0.5);
    const dir = new THREE.Vector3().subVectors(pB, pA);
    const length = dir.length();

    // Horizontal bar (thick, substantial cylinder)
    const rungGeom = new THREE.CylinderGeometry(0.075, 0.075, length, 16);
    const rungMesh = new THREE.Mesh(rungGeom, rungMat);
    rungMesh.position.copy(mid);
    rungMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize());
    dnaGroup.add(rungMesh);

    // Junction sphere nodes at strand endpoints
    const nodeA = new THREE.Mesh(nodeGeom, nodeMat);
    nodeA.position.copy(pA);
    dnaGroup.add(nodeA);

    const nodeB = new THREE.Mesh(nodeGeom, nodeMat);
    nodeB.position.copy(pB);
    dnaGroup.add(nodeB);

    // Jewel accent in center
    const activeJewelMat = i % 2 === 0 ? jewelMat : jewelCyanMat;
    const jewelMesh = new THREE.Mesh(jewelGeom, activeJewelMat);
    jewelMesh.position.copy(mid);
    jewelMesh.quaternion.copy(rungMesh.quaternion);
    dnaGroup.add(jewelMesh);
  }

  // ---------------- Outer Metallic Spiral Spring Ribbon (Spaced out & Thicker) ----------------
  function createSpiralSpringCurve(): THREE.CatmullRomCurve3 {
    const pts: THREE.Vector3[] = [];
    const N = 110;
    const SPRING_TURNS = 1.75; // Graceful, spaced outer coiling
    const SPRING_RADIUS = 2.15; // Generously encasing the DNA
    for (let i = 0; i <= N; i++) {
      const t = i / N;
      const angle = t * SPRING_TURNS * Math.PI * 2 + 0.45;
      const r = SPRING_RADIUS * (0.88 + 0.24 * Math.sin(t * Math.PI));
      const y = (t - 0.5) * (DNA_HEIGHT * 1.06);
      pts.push(new THREE.Vector3(Math.cos(angle) * r, y, Math.sin(angle) * r));
    }
    return new THREE.CatmullRomCurve3(pts, false, "centripetal");
  }

  const springCurve = createSpiralSpringCurve();
  const springGeom = new THREE.TubeGeometry(
    springCurve,
    tubularSegs,
    0.11, // Thicker ribbon tube
    quality < 1 ? 10 : 14,
    false
  );
  const springMesh = new THREE.Mesh(springGeom, spiralSpringMat);
  // Slightly scale on Z to create a flattened, beveled metallic ribbon profile
  springMesh.scale.set(1, 1, 0.55);
  dnaGroup.add(springMesh);

  // ---------------- Studio Direct Lighting ----------------
  const keyLight = new THREE.DirectionalLight(0xffffff, 2.4);
  keyLight.position.set(4, 5, 4);
  scene.add(keyLight);

  const fillLight = new THREE.DirectionalLight(0x8fa8ff, 1.2);
  fillLight.position.set(-4, -2, 3);
  scene.add(fillLight);

  const rimLight = new THREE.DirectionalLight(0xb4d0ff, 2.0);
  rimLight.position.set(0, -4, -4);
  scene.add(rimLight);

  // Floating micro-particulate ambient field
  const dustGeom = new THREE.BufferGeometry();
  const dustCount = 80;
  const dustPos = new Float32Array(dustCount * 3);
  for (let i = 0; i < dustCount * 3; i += 3) {
    dustPos[i] = (Math.random() - 0.5) * 8;
    dustPos[i + 1] = (Math.random() - 0.5) * 7;
    dustPos[i + 2] = (Math.random() - 0.5) * 5;
  }
  dustGeom.setAttribute("position", new THREE.BufferAttribute(dustPos, 3));
  const dustMat = new THREE.PointsMaterial({
    size: 0.038,
    color: 0x9fb8ff,
    transparent: true,
    opacity: 0.35,
    blending: THREE.AdditiveBlending,
  });
  const dust = new THREE.Points(dustGeom, dustMat);
  scene.add(dust);

  // ---------------- Runtime Loop & Positioning ----------------
  let running = false;
  let raf = 0;
  let t0 = performance.now();
  let last = t0;
  let visible = true;
  let tabActive = true;

  let pointerX = 0;
  let pointerY = 0;
  let smoothX = 0;
  let smoothY = 0;

  let baseX = 0;
  let baseY = 0;
  let baseScale = 1;
  let contract = 0;

  let lastW = 0;
  let lastH = 0;

  function resize() {
    const host = canvas.parentElement ?? canvas;
    const w = Math.max(1, host.clientWidth || canvas.clientWidth);
    const h = Math.max(1, host.clientHeight || canvas.clientHeight);
    if (w === lastW && h === lastH) return;
    lastW = w;
    lastH = h;

    renderer.setPixelRatio(window.devicePixelRatio || 1);
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

  function frame(now: number) {
    raf = requestAnimationFrame(frame);
    const time = (now - t0) / 1000;
    const dt = Math.min(0.033, (now - last) / 1000);
    last = now;
    if (!visible || !tabActive) return;

    smoothX += (pointerX - smoothX) * 0.04;
    smoothY += (pointerY - smoothY) * 0.04;

    // Slow, stately, continuous 360-degree rotation of the DNA spiral spring (0.18 rad/s)
    dnaGroup.rotation.y += dt * 0.18;

    // Gentle micro-undulation along other axes without nervous wobbling
    group.rotation.x = Math.sin(time * 0.05) * 0.02 + smoothY * 0.04;
    group.rotation.z = Math.cos(time * 0.04) * 0.015 + smoothX * 0.04;
    group.position.y = baseY + Math.sin(time * 0.08) * 0.03;
    group.position.x = baseX;

    group.scale.setScalar(baseScale * (1 - contract * 0.06));

    camera.position.x = Math.sin(time * 0.025) * 0.12 + smoothX * 0.18;
    camera.position.y = Math.cos(time * 0.03) * 0.06 - smoothY * 0.1;
    camera.lookAt(0, 0, 0);

    dust.rotation.y = time * 0.005;

    renderer.render(scene, camera);
  }

  function drawStatic() {
    group.rotation.set(0.06, -0.25, 0);
    group.position.set(baseX, baseY, 0);
    group.scale.setScalar(baseScale);
    camera.position.set(0.08, 0.12, camera.position.z);
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
    setFocus(v: number) {
      contract = v;
    },
  };
}

export type NeuralSculptureHandle = NonNullable<ReturnType<typeof createNeuralSculpture>>;