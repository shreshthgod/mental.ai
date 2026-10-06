/**
 * Vantage Sculpture - WebGL hero engine (vanilla Three.js).
 *
 * A massive dark-chrome sculpture abstracting the Vantage architecture:
 * two intertwined solid ribbons (the dual signal paths), three beveled
 * gyroscopic rings (precision machine components), and a polished core -
 * rendered in a procedural dark-studio environment with traveling
 * signal lights. No external assets; the reflection environment is
 * generated at runtime via PMREM from a tiny emissive-strip scene.
 *
 * One render loop. Pauses offscreen / hidden tab. Pointer parallax.
 * Reduced motion renders a single composed frame.
 */
import * as THREE from "three";

export interface SculptureOptions {
  reducedMotion: boolean;
  /** ms after start() before the sculpture begins materializing. */
  emergeDelayMs?: number;
  /** 0..1 quality scale (mobile ~0.6). */
  quality?: number;
}

const CHROME_DARK = 0x232329;
const CHROME_MID = 0x2e2e36;
const CHROME_RING = 0x36363f;
const VIOLET = 0x7b5cff;
const BLUE = 0x4d9fff;

/** Procedural dark studio: black void + a few bright emissive strips. */
function buildStudioEnvironment(renderer: THREE.WebGLRenderer): THREE.Texture {
  const env = new THREE.Scene();
  env.background = new THREE.Color(0x010102);

  const strip = (
    w: number,
    h: number,
    color: THREE.Color,
    pos: [number, number, number],
    rot: [number, number, number]
  ) => {
    const m = new THREE.Mesh(
      new THREE.PlaneGeometry(w, h),
      new THREE.MeshBasicMaterial({ color, side: THREE.DoubleSide })
    );
    m.position.set(...pos);
    m.rotation.set(...rot);
    env.add(m);
  };

  // Key strip - large soft white overhead-left
  strip(10, 2.4, new THREE.Color(5.5, 5.5, 5.8), [-5, 6, 3], [-0.5, 0.5, 0.15]);
  // Long thin white rim strip right
  strip(0.7, 9, new THREE.Color(4.2, 4.4, 4.8), [6.5, 0.5, -1], [0, -1.05, 0]);
  // Deep blue wash low-left
  strip(7, 1.6, new THREE.Color(0.35, 0.62, 2.6), [-4.5, -4.2, -2.5], [0.6, 0.6, 0]);
  // Violet accent behind
  strip(5, 1.1, new THREE.Color(1.35, 0.8, 3.2), [2.5, 3.2, -6], [0.15, -0.35, 0]);
  // Faint neutral floor bounce
  strip(12, 3, new THREE.Color(0.5, 0.52, 0.6), [0, -7, 1.5], [1.35, 0, 0]);

  const pmrem = new THREE.PMREMGenerator(renderer);
  const rt = pmrem.fromScene(env, 0.05);
  pmrem.dispose();
  return rt.texture;
}

/** Intertwined ribbon pair - a breathing double sweep, not a DNA poster. */
function ribbonCurve(phase: number): THREE.CatmullRomCurve3 {
  const pts: THREE.Vector3[] = [];
  const TURNS = 1.35;
  const HEIGHT = 4.6;
  const N = 90;
  for (let i = 0; i <= N; i++) {
    const t = i / N;
    const ang = t * TURNS * Math.PI * 2 + phase;
    // radius breathes: wider at the waist, tighter at the ends
    const r = 0.62 + Math.sin(t * Math.PI) * 0.35 + Math.sin(t * Math.PI * 3 + phase) * 0.06;
    const y = (t - 0.5) * HEIGHT;
    pts.push(new THREE.Vector3(Math.cos(ang) * r, y, Math.sin(ang) * r));
  }
  return new THREE.CatmullRomCurve3(pts, false, "centripetal");
}

export function createSculpture(canvas: HTMLCanvasElement, opts: SculptureOptions) {
  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      powerPreference: "high-performance",
    });
  } catch {
    return null; // caller falls back to the canvas engine
  }

  const quality = opts.quality ?? 1;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.04;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 60);
  camera.position.set(0, 0.12, 5.4);

  scene.environment = buildStudioEnvironment(renderer);

  // ---------------- Materials ----------------
  const ribbonMat = new THREE.MeshStandardMaterial({
    color: CHROME_DARK,
    metalness: 1.0,
    roughness: 0.23,
    envMapIntensity: 0.95,
  });
  const ribbonMatB = new THREE.MeshStandardMaterial({
    color: CHROME_MID,
    metalness: 1.0,
    roughness: 0.28,
    envMapIntensity: 0.9,
  });
  const ringMat = new THREE.MeshStandardMaterial({
    color: CHROME_RING,
    metalness: 1.0,
    roughness: 0.3,
    envMapIntensity: 0.85,
  });
  const coreMat = new THREE.MeshStandardMaterial({
    color: 0x1b1b21,
    metalness: 1.0,
    roughness: 0.14,
    envMapIntensity: 1.1,
  });
  const metals = [ribbonMat, ribbonMatB, ringMat, coreMat];

  // ---------------- Geometry ----------------
  const seg = quality < 1 ? 120 : 220;
  const rad = quality < 1 ? 14 : 24;
  const group = new THREE.Group();

  const curveA = ribbonCurve(0);
  const curveB = ribbonCurve(Math.PI);
  const ribbonA = new THREE.Mesh(new THREE.TubeGeometry(curveA, seg, 0.145, rad, false), ribbonMat);
  const ribbonB = new THREE.Mesh(new THREE.TubeGeometry(curveB, seg, 0.125, rad, false), ribbonMatB);
  group.add(ribbonA, ribbonB);

  // Gyroscopic rings - thick, beveled by geometry, mechanically related
  const ringSeg = quality < 1 ? 96 : 180;
  const ring1 = new THREE.Mesh(new THREE.TorusGeometry(1.32, 0.085, 20, ringSeg), ringMat);
  ring1.rotation.set(1.15, 0.1, 0.22);
  const ring2 = new THREE.Mesh(new THREE.TorusGeometry(1.78, 0.055, 18, ringSeg), ringMat);
  ring2.rotation.set(1.42, -0.2, -0.35);
  const ring3 = new THREE.Mesh(new THREE.TorusGeometry(0.92, 0.11, 20, ringSeg), ringMat);
  ring3.position.set(0.1, -0.2, -0.85);
  ring3.rotation.set(0.35, 0.55, 0.1);
  group.add(ring1, ring2, ring3);

  // Polished core - the convergence point
  const core = new THREE.Mesh(new THREE.IcosahedronGeometry(0.3, 3), coreMat);
  core.position.set(0, 0.05, 0);
  group.add(core);

  group.rotation.x = 0.06;
  scene.add(group);

  // Signal markers - small emissive beads + a traveling point light each
  const markerMatA = new THREE.MeshBasicMaterial({ color: new THREE.Color(2.2, 1.9, 4.5) });
  const markerMatB = new THREE.MeshBasicMaterial({ color: new THREE.Color(1.6, 2.6, 4.6) });
  const markerGeo = new THREE.SphereGeometry(0.045, 12, 12);
  const markerA = new THREE.Mesh(markerGeo, markerMatA);
  const markerB = new THREE.Mesh(markerGeo, markerMatB);
  const lightA = new THREE.PointLight(VIOLET, 0, 3.2, 2);
  const lightB = new THREE.PointLight(BLUE, 0, 3.2, 2);
  markerA.visible = markerB.visible = false;
  group.add(markerA, markerB, lightA, lightB);

  // Studio dust - secondary atmosphere only
  const dustN = quality < 1 ? 40 : 80;
  const dustPos = new Float32Array(dustN * 3);
  for (let i = 0; i < dustN; i++) {
    const th = Math.random() * Math.PI * 2;
    const rr = 1.2 + Math.random() * 2.4;
    dustPos[i * 3] = Math.cos(th) * rr;
    dustPos[i * 3 + 1] = (Math.random() - 0.5) * 4.4;
    dustPos[i * 3 + 2] = Math.sin(th) * rr - 0.6;
  }
  const dustGeo = new THREE.BufferGeometry();
  dustGeo.setAttribute("position", new THREE.BufferAttribute(dustPos, 3));
  const dust = new THREE.Points(
    dustGeo,
    new THREE.PointsMaterial({ color: 0x8fa8d8, size: 0.014, transparent: true, opacity: 0.4, sizeAttenuation: true })
  );
  scene.add(dust);

  // ---------------- Lights ----------------
  const key = new THREE.DirectionalLight(0xffffff, 0);
  key.position.set(-4, 5, 4);
  const rim = new THREE.DirectionalLight(0x9d86ff, 0);
  rim.position.set(3.5, 1.5, -4.5);
  const fill = new THREE.DirectionalLight(0xcfe0ff, 0);
  fill.position.set(2.5, -3, 3.5);
  const sweep = new THREE.PointLight(0xffffff, 0, 9, 2);
  sweep.position.set(-4, 1.6, 2.6);
  scene.add(key, rim, fill, sweep);

  // ---------------- Runtime state ----------------
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
  let sweepDone = false;
  let nextSignal = 3.5;
  let signalAT = -1;
  let signalBT = -1;
  let rimPulseT = -1;

  const TARGET_ENV = [0.95, 0.9, 0.85, 1.1];
  const TARGET_KEY = 2.0;
  const TARGET_RIM = 1.5;
  const TARGET_FILL = 0.55;

  function resize() {
    const parent = canvas.parentElement;
    const rect = parent ? parent.getBoundingClientRect() : { width: 300, height: 300 };
    const dprCap = quality < 1 ? 1.25 : 1.5;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, dprCap));
    renderer.setSize(Math.max(1, rect.width), Math.max(1, rect.height), false);
    camera.aspect = Math.max(0.2, rect.width / Math.max(1, rect.height));
    // keep the sculpture massive but composed across aspect ratios
    const tanHalf = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
    camera.position.z = THREE.MathUtils.clamp(1.75 / (tanHalf * camera.aspect), 5.2, 8.4);
    camera.updateProjectionMatrix();
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

  function applyEmergence(e: number, time: number) {
    // materials emerge from darkness
    for (let i = 0; i < metals.length; i++) metals[i].envMapIntensity = TARGET_ENV[i] * e;
    key.intensity = TARGET_KEY * e;
    rim.intensity = TARGET_RIM * e;
    fill.intensity = TARGET_FILL * e;
    group.scale.setScalar(0.94 + e * 0.06);
    // one-time light sweep across the fresh metal (1.0s window inside emergence)
    if (!sweepDone && e > 0.25) {
      const sp = Math.min(1, (e - 0.25) / 0.6);
      sweep.position.set(-4 + sp * 8, 1.6 - sp * 2.2, 2.6 - sp * 0.8);
      sweep.intensity = Math.sin(sp * Math.PI) * 26 * (opts.reducedMotion ? 0 : 1);
      if (sp >= 1) {
        sweepDone = true;
        sweep.intensity = 0;
      }
    }
    dust.material.opacity = 0.4 * e;
    void time;
  }

  function frame(now: number) {
    raf = requestAnimationFrame(frame);
    const time = (now - t0) / 1000;
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    if (!visible || !tabActive) return;

    // emergence (materialize out of darkness)
    const start = (opts.emergeDelayMs ?? 0) / 1000;
    const et = (time - start) / 2.0;
    emerged = et <= 0 ? 0 : et >= 1 ? 1 : 1 - Math.pow(1 - et, 3);
    applyEmergence(emerged, time);

    // pointer smoothing
    smoothX += (pointerX - smoothX) * 0.04;
    smoothY += (pointerY - smoothY) * 0.04;

    // Layer 1 - structural drift (slow oscillation, never a product spin)
    group.rotation.y = Math.sin(time * 0.05) * 0.14 + smoothX * 0.16;
    group.rotation.x = 0.06 + Math.sin(time * 0.037) * 0.03 + smoothY * 0.09;
    group.position.y = 0.2 + Math.sin(time * 0.08) * 0.05;

    // Layer 2 - rings operate independently
    ring1.rotation.z += dt * 0.045;
    ring2.rotation.z -= dt * 0.03;
    ring3.rotation.y += dt * 0.06;
    core.rotation.y -= dt * 0.05;
    core.rotation.x += dt * 0.02;

    // Layer 3 - camera drift
    camera.position.x = Math.sin(time * 0.028) * 0.16 + smoothX * 0.22;
    camera.position.y = 0.12 + Math.cos(time * 0.033) * 0.08 + smoothY * -0.12;
    camera.lookAt(0, 0, 0);

    // Layer 5 - signal events: a bead of light travels each ribbon
    if (emerged > 0.85 && time > nextSignal) {
      nextSignal = time + 3.6 + Math.random() * 2.8;
      if (Math.random() > 0.45) signalAT = 0;
      else signalBT = 0;
      if (Math.random() > 0.75) rimPulseT = time;
    }
    const advance = (st: number, curve: THREE.CatmullRomCurve3, marker: THREE.Mesh, light: THREE.PointLight) => {
      if (st < 0) return -1;
      const nt = st + dt / 2.6; // ~2.6s per traversal
      if (nt >= 1) {
        marker.visible = false;
        light.intensity = 0;
        return -1;
      }
      const p = curve.getPointAt(nt);
      marker.position.copy(p);
      light.position.copy(p);
      marker.visible = true;
      const env = Math.sin(nt * Math.PI);
      light.intensity = 7.5 * env;
      (marker.material as THREE.MeshBasicMaterial).opacity = env;
      return nt;
    };
    signalAT = advance(signalAT, curveA, markerA, lightA);
    signalBT = advance(signalBT, curveB, markerB, lightB);

    // occasional soft rim pulse - the machine "reacts"
    if (rimPulseT > 0) {
      const age = time - rimPulseT;
      if (age > 1.6) rimPulseT = -1;
      else rim.intensity = TARGET_RIM * emerged + Math.sin((age / 1.6) * Math.PI) * 1.1;
    }

    // dust drift
    dust.rotation.y = time * 0.008;

    renderer.render(scene, camera);
  }

  function drawStatic() {
    applyEmergence(1, 0);
    group.rotation.set(0.1, -0.22, 0);
    group.position.y = 0.2;
    ring1.rotation.z = 0.4;
    ring2.rotation.z = -0.3;
    camera.position.set(0.1, 0.16, camera.position.z);
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
        if (o instanceof THREE.Mesh) {
          o.geometry.dispose();
          const m = o.material;
          if (Array.isArray(m)) m.forEach((x) => x.dispose());
          else m.dispose();
        }
      });
      scene.environment?.dispose();
      renderer.dispose();
    },
    setPointer(x: number, y: number) {
      pointerX = x;
      pointerY = y;
    },
  };
}

export type SculptureHandle = NonNullable<ReturnType<typeof createSculpture>>;
