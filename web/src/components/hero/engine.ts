/**
 * Vantage Signal Structure - procedural canvas engine.
 *
 * An abstract "neural sculpture": a double signal strand (the two-model
 * branch), two gyroscopic node rings, and an ambient particle field -
 * rendered in canvas 2D with real 3D perspective projection, depth fog,
 * additive glow sprites, traveling signal pulses and periodic pulse events.
 *
 * One rAF loop. Pauses when hidden / offscreen. Pointer-reactive parallax.
 */

export interface SignalStructureOptions {
  reducedMotion: boolean;
  /** ms after start() before the structure begins emerging. */
  emergeDelayMs?: number;
  /** 0..1 quality scale (mobile ~0.55). */
  quality?: number;
}

interface Node3 {
  // Base coordinates are recomputed per frame by group transforms.
  kind: "core" | "strandA" | "strandB" | "rung" | "ringA" | "ringB" | "dust";
  // strand: t along axis; ring: angle; dust: fixed
  a: number; // angle or axial t
  r: number; // radius
  y: number; // axial position (strands) or plane offset
  size: number;
  bright: number; // 0..1 base brightness
  wobble: number;
}

interface Edge {
  i: number;
  j: number;
  alpha: number;
  hue: 0 | 1; // 0 violet, 1 blue
}

interface Pulse {
  edge: number;
  t: number;
  speed: number;
  hue: 0 | 1;
  dir: 1 | -1;
}

function mulberry32(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const VIOLET: [number, number, number] = [123, 92, 255];
const BLUE: [number, number, number] = [77, 159, 255];
const WHITE: [number, number, number] = [235, 232, 255];

function makeGlowSprite(rgb: [number, number, number]): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d")!;
  const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, `rgba(${rgb[0]},${rgb[1]},${rgb[2]},0.9)`);
  grad.addColorStop(0.25, `rgba(${rgb[0]},${rgb[1]},${rgb[2]},0.32)`);
  grad.addColorStop(1, `rgba(${rgb[0]},${rgb[1]},${rgb[2]},0)`);
  g.fillStyle = grad;
  g.fillRect(0, 0, 64, 64);
  return c;
}

export function createSignalStructure(canvas: HTMLCanvasElement, opts: SignalStructureOptions) {
  const context = canvas.getContext("2d");
  if (!context) return { start() {}, stop() {}, destroy() {}, setPointer(_x: number, _y: number) {} };
  const ctx: CanvasRenderingContext2D = context;

  const quality = opts.quality ?? 1;
  const rnd = mulberry32(20261005);
  const sprites = [makeGlowSprite(VIOLET), makeGlowSprite(BLUE), makeGlowSprite(WHITE)];

  // ---------------- Structure construction ----------------
  const nodes: Node3[] = [];
  const edges: Edge[] = [];

  // Core
  nodes.push({ kind: "core", a: 0, r: 0, y: 0, size: 3.2, bright: 1, wobble: 0 });

  // Dual strands - two intertwined paths (condition / urgency abstraction)
  const STRAND_N = Math.round(13 * quality) + 4;
  const strandA: number[] = [];
  const strandB: number[] = [];
  for (let i = 0; i < STRAND_N; i++) {
    const t = i / (STRAND_N - 1); // 0..1 along axis
    const y = (t - 0.5) * 1.5;
    const angA = t * Math.PI * 2.6;
    const jitter = (rnd() - 0.5) * 0.05;
    strandA.push(nodes.length);
    nodes.push({ kind: "strandA", a: angA, r: 0.30 + jitter, y, size: 1.9 + rnd() * 0.9, bright: 0.65 + rnd() * 0.35, wobble: rnd() * Math.PI * 2 });
    strandB.push(nodes.length);
    nodes.push({ kind: "strandB", a: angA + Math.PI, r: 0.30 + jitter, y, size: 1.9 + rnd() * 0.9, bright: 0.65 + rnd() * 0.35, wobble: rnd() * Math.PI * 2 });
    if (i > 0) {
      edges.push({ i: strandA[i - 1], j: strandA[i], alpha: 0.34, hue: 0 });
      edges.push({ i: strandB[i - 1], j: strandB[i], alpha: 0.34, hue: 1 });
    }
    if (i % 2 === 1) edges.push({ i: strandA[i], j: strandB[i], alpha: 0.16, hue: 0 });
  }
  // Core feeds the strands
  edges.push({ i: 0, j: strandA[0], alpha: 0.4, hue: 0 });
  edges.push({ i: 0, j: strandB[0], alpha: 0.4, hue: 1 });
  edges.push({ i: 0, j: strandA[Math.floor(STRAND_N / 2)], alpha: 0.22, hue: 0 });
  edges.push({ i: 0, j: strandB[Math.floor(STRAND_N / 2)], alpha: 0.22, hue: 1 });
  // Strands converge at the top - human review
  const topIdx = nodes.length;
  nodes.push({ kind: "core", a: 0, r: 0, y: 0.92, size: 2.6, bright: 0.95, wobble: 0 });
  edges.push({ i: strandA[STRAND_N - 1], j: topIdx, alpha: 0.4, hue: 0 });
  edges.push({ i: strandB[STRAND_N - 1], j: topIdx, alpha: 0.4, hue: 1 });

  // Ring A - inner gyroscope
  const RINGA_N = Math.round(12 * quality) + 4;
  const ringA: number[] = [];
  for (let i = 0; i < RINGA_N; i++) {
    ringA.push(nodes.length);
    nodes.push({ kind: "ringA", a: (i / RINGA_N) * Math.PI * 2, r: 0.62 + (rnd() - 0.5) * 0.03, y: 0, size: 1.6 + rnd() * 0.8, bright: 0.5 + rnd() * 0.3, wobble: rnd() * Math.PI * 2 });
    if (i > 0) edges.push({ i: ringA[i - 1], j: ringA[i], alpha: 0.3, hue: 0 });
  }
  edges.push({ i: ringA[RINGA_N - 1], j: ringA[0], alpha: 0.3, hue: 0 });

  // Ring B - outer gyroscope with hubs
  const RINGB_N = Math.round(18 * quality) + 6;
  const ringB: number[] = [];
  const hubs: number[] = [];
  for (let i = 0; i < RINGB_N; i++) {
    const hub = i % 6 === 0;
    ringB.push(nodes.length);
    nodes.push({ kind: "ringB", a: (i / RINGB_N) * Math.PI * 2, r: 0.98 + (rnd() - 0.5) * 0.08, y: 0, size: hub ? 2.6 : 1.3 + rnd() * 0.7, bright: hub ? 0.9 : 0.4 + rnd() * 0.3, wobble: rnd() * Math.PI * 2 });
    if (hub) hubs.push(ringB[i]);
    if (i > 0) edges.push({ i: ringB[i - 1], j: ringB[i], alpha: 0.18, hue: 1 });
  }
  edges.push({ i: ringB[RINGB_N - 1], j: ringB[0], alpha: 0.18, hue: 1 });
  // Tendrils: hubs → ring A
  for (let k = 0; k < hubs.length; k++) {
    edges.push({ i: hubs[k], j: ringA[(k * 2 + 1) % RINGA_N], alpha: 0.14, hue: k % 2 ? 1 : 0 });
  }

  // Ambient dust
  const DUST_N = Math.round(56 * quality) + 12;
  const dust: number[] = [];
  for (let i = 0; i < DUST_N; i++) {
    dust.push(nodes.length);
    const th = rnd() * Math.PI * 2;
    const rr = 0.45 + rnd() * 0.95;
    nodes.push({
      kind: "dust",
      a: th,
      r: rr,
      y: (rnd() - 0.5) * 1.7,
      size: 0.7 + rnd() * 0.9,
      bright: 0.18 + rnd() * 0.3,
      wobble: rnd() * Math.PI * 2,
    });
  }

  // ---------------- Runtime state ----------------
  let raf = 0;
  let running = false;
  let visible = true;
  let tabActive = true;
  let w = 0;
  let h = 0;
  let dpr = 1;
  let t0 = 0;
  let last = 0;
  let pointerX = 0;
  let pointerY = 0;
  let smoothX = 0;
  let smoothY = 0;
  let pulses: Pulse[] = [];
  let nextSpawn = 1.2;
  let nextEvent = 5 + rnd() * 3;
  let eventT = -1; // time of last pulse event
  let emerged = 0; // 0..1

  const positions = new Float32Array(nodes.length * 3); // projected: x,y,depth-scale

  function resize() {
    const rect = canvas.getBoundingClientRect();
    dpr = Math.min(window.devicePixelRatio || 1, quality < 1 ? 1.25 : 1.5);
    w = Math.max(1, Math.round(rect.width));
    h = Math.max(1, Math.round(rect.height));
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function nodePosition(n: Node3, time: number, out: [number, number, number]) {
    switch (n.kind) {
      case "core":
        out[0] = 0;
        out[1] = n.y;
        out[2] = 0;
        break;
      case "strandA":
      case "strandB": {
        const ang = n.a + Math.sin(time * 0.11 + n.wobble) * 0.05;
        const rr = n.r + Math.sin(time * 0.23 + n.wobble) * 0.012;
        out[0] = Math.cos(ang) * rr;
        out[1] = n.y;
        out[2] = Math.sin(ang) * rr;
        break;
      }
      case "ringA": {
        const ang = n.a + time * 0.05;
        const tilt = 1.12; // rad from vertical plane
        const x = Math.cos(ang) * n.r;
        const zp = Math.sin(ang) * n.r;
        out[0] = x;
        out[1] = zp * Math.cos(tilt);
        out[2] = zp * Math.sin(tilt);
        break;
      }
      case "ringB": {
        const ang = n.a - time * 0.032;
        const tilt = 1.35;
        const x = Math.cos(ang) * n.r;
        const zp = Math.sin(ang) * n.r;
        out[0] = x;
        out[1] = zp * Math.cos(tilt) + Math.sin(time * 0.07 + n.wobble) * 0.02;
        out[2] = zp * Math.sin(tilt);
        break;
      }
      case "dust": {
        const ang = n.a + time * 0.016;
        out[0] = Math.cos(ang) * n.r;
        out[1] = n.y + Math.sin(time * 0.1 + n.wobble) * 0.05;
        out[2] = Math.sin(ang) * n.r;
        break;
      }
    }
  }

  const p3: [number, number, number] = [0, 0, 0];

  function project(time: number) {
    const S = Math.min(w, h) * 0.44;
    const cx = w / 2;
    const cy = h / 2 - Math.min(w, h) * 0.03;
    smoothX += (pointerX - smoothX) * 0.045;
    smoothY += (pointerY - smoothY) * 0.045;
    const rotY = time * 0.05 + smoothX * 0.35;
    const rotX = 0.34 + smoothY * 0.22 + Math.sin(time * 0.045) * 0.03;
    const cosY = Math.cos(rotY), sinY = Math.sin(rotY);
    const cosX = Math.cos(rotX), sinX = Math.sin(rotX);
    const camDist = 3.1;
    const scale = S * (0.86 + emerged * 0.14);

    for (let i = 0; i < nodes.length; i++) {
      nodePosition(nodes[i], time, p3);
      // rotate Y then X
      const x1 = p3[0] * cosY + p3[2] * sinY;
      const z1 = -p3[0] * sinY + p3[2] * cosY;
      const y1 = p3[1] * cosX - z1 * sinX;
      const z2 = p3[1] * sinX + z1 * cosX;
      const persp = camDist / (camDist - z2);
      positions[i * 3] = cx + x1 * persp * scale;
      positions[i * 3 + 1] = cy + y1 * persp * scale;
      positions[i * 3 + 2] = persp; // ~0.75..1.5 → also depth cue
    }
  }

  function draw(time: number) {
    ctx.clearRect(0, 0, w, h);
    project(time);

    const eventAge = eventT < 0 ? Infinity : time - eventT;
    const eventBoost = eventAge < 2.2 ? Math.max(0, 1 - eventAge / 2.2) : 0;
    const breathe = 0.9 + Math.sin(time * 0.4) * 0.1;

    // ---- edges ----
    ctx.globalCompositeOperation = "source-over";
    ctx.lineWidth = 1;
    for (let e = 0; e < edges.length; e++) {
      const ed = edges[e];
      const i3 = ed.i * 3, j3 = ed.j * 3;
      const depth = (positions[i3 + 2] + positions[j3 + 2]) * 0.5;
      const depthA = Math.min(1.15, Math.max(0.35, depth - 0.35));
      const a = ed.alpha * depthA * emerged * (1 + eventBoost * 0.9);
      if (a < 0.015) continue;
      const c = ed.hue === 0 ? VIOLET : BLUE;
      ctx.strokeStyle = `rgba(${c[0]},${c[1]},${c[2]},${a.toFixed(3)})`;
      ctx.beginPath();
      ctx.moveTo(positions[i3], positions[i3 + 1]);
      ctx.lineTo(positions[j3], positions[j3 + 1]);
      ctx.stroke();
    }

    // ---- pulses ----
    for (const p of pulses) {
      const ed = edges[p.edge];
      const i3 = ed.i * 3, j3 = ed.j * 3;
      const t = p.dir === 1 ? p.t : 1 - p.t;
      const x = positions[i3] + (positions[j3] - positions[i3]) * t;
      const y = positions[i3 + 1] + (positions[j3 + 1] - positions[i3 + 1]) * t;
      const trailT = Math.max(0, Math.min(1, t - 0.14 * p.dir));
      const tx = positions[i3] + (positions[j3] - positions[i3]) * trailT;
      const ty = positions[i3 + 1] + (positions[j3 + 1] - positions[i3 + 1]) * trailT;
      const c = p.hue === 0 ? VIOLET : BLUE;
      ctx.globalCompositeOperation = "lighter";
      const grad = ctx.createLinearGradient(tx, ty, x, y);
      grad.addColorStop(0, `rgba(${c[0]},${c[1]},${c[2]},0)`);
      grad.addColorStop(1, `rgba(${c[0]},${c[1]},${c[2]},${(0.85 * emerged).toFixed(3)})`);
      ctx.strokeStyle = grad;
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.moveTo(tx, ty);
      ctx.lineTo(x, y);
      ctx.stroke();
      const spr = sprites[p.hue];
      const s = 26 * positions[i3 + 2] * 0.7;
      ctx.globalAlpha = 0.9 * emerged;
      ctx.drawImage(spr, x - s / 2, y - s / 2, s, s);
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = "source-over";
    }

    // ---- pulse event ring ----
    if (eventBoost > 0) {
      const coreX = positions[0], coreY = positions[1];
      const prog = Math.min(1, eventAge / 2.2);
      const rad = prog * Math.min(w, h) * 0.4;
      ctx.globalCompositeOperation = "lighter";
      ctx.strokeStyle = `rgba(${VIOLET[0]},${VIOLET[1]},${VIOLET[2]},${(0.22 * (1 - prog)).toFixed(3)})`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(coreX, coreY, rad, 0, Math.PI * 2);
      ctx.stroke();
      ctx.globalCompositeOperation = "source-over";
    }

    // ---- nodes ----
    ctx.globalCompositeOperation = "lighter";
    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i];
      if (n.kind === "dust") continue;
      const i3 = i * 3;
      const depth = positions[i3 + 2];
      const bright = Math.min(1, (n.bright * breathe + eventBoost * 0.7)) * emerged;
      if (bright < 0.03) continue;
      const x = positions[i3], y = positions[i3 + 1];
      const sprite = n.kind === "core" || n.kind === "strandA" ? sprites[2] : sprites[n.kind === "strandB" ? 1 : 0];
      const s = n.size * 12 * depth;
      ctx.globalAlpha = bright * 0.75;
      ctx.drawImage(sprite, x - s / 2, y - s / 2, s, s);
      // crisp core dot
      ctx.globalAlpha = bright;
      ctx.fillStyle = `rgba(${WHITE[0]},${WHITE[1]},${WHITE[2]},1)`;
      ctx.beginPath();
      ctx.arc(x, y, Math.max(0.6, n.size * 0.55 * depth), 0, Math.PI * 2);
      ctx.fill();
    }
    // dust
    for (const i of dust) {
      const n = nodes[i];
      const i3 = i * 3;
      const depth = positions[i3 + 2];
      const tw = 0.55 + Math.sin(time * (0.6 + n.wobble * 0.2) + n.wobble * 7) * 0.45;
      const a = n.bright * tw * depth * 0.5 * emerged;
      if (a < 0.02) continue;
      ctx.globalAlpha = a;
      ctx.fillStyle = `rgba(${BLUE[0]},${BLUE[1]},${BLUE[2]},1)`;
      ctx.beginPath();
      ctx.arc(positions[i3], positions[i3 + 1], n.size * depth, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = "source-over";
  }

  function frame(now: number) {
    raf = requestAnimationFrame(frame);
    const time = (now - t0) / 1000;
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    if (!visible || !tabActive) return;

    // emergence
    const emergeStart = (opts.emergeDelayMs ?? 0) / 1000;
    const et = (time - emergeStart) / 2.2;
    emerged = et <= 0 ? 0 : et >= 1 ? 1 : 1 - Math.pow(1 - et, 3);

    // spawn pulses
    if (time > nextSpawn && emerged > 0.6) {
      nextSpawn = time + 0.6 + rnd() * 1.1;
      if (pulses.length < 6) {
        pulses.push({
          edge: Math.floor(rnd() * edges.length),
          t: 0,
          speed: 0.9 + rnd() * 0.9,
          hue: rnd() > 0.5 ? 1 : 0,
          dir: rnd() > 0.5 ? 1 : -1,
        });
      }
    }
    for (const p of pulses) p.t += dt * p.speed;
    pulses = pulses.filter((p) => p.t <= 1);

    // pulse events
    if (time > nextEvent && emerged > 0.9) {
      nextEvent = time + 6 + rnd() * 3.5;
      eventT = time;
    }

    draw(time);
  }

  // ---- reduced motion: render a single composed frame ----
  function drawStatic() {
    t0 = performance.now();
    emerged = 1;
    draw(14); // a pleasant fixed phase
  }

  const ro = new ResizeObserver(() => {
    resize();
    if (opts.reducedMotion) drawStatic();
  });
  ro.observe(canvas);

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
    },
    setPointer(x: number, y: number) {
      pointerX = x;
      pointerY = y;
    },
  };
}

export type SignalStructureHandle = ReturnType<typeof createSignalStructure>;
