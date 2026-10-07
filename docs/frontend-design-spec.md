# mental.ai - Frontend Design Spec

Cinematic redesign of the mental.ai frontend: a dark, editorial, research-grade
product experience over the verified FastAPI inference backend.

References: TRUST-SAT (`trustsat.mpst.me`, local `SIH26/TRUST-SAT/web`) for
product communication and design tokens; minimal.gallery/denmu for motion and
art direction; React Bits `Grainient` (supplied, copied into this repo) for the
atmospheric WebGL layer.

---

## 1. Product framing

- mental.ai is a **research screening instrument**, not a healthcare product.
- Copy uses: *screening, signals, patterns, urgency, human review, research*.
- Copy never uses: *diagnosis, clinical, doctor, patient, treatment*.
- The site should read as: digital art + research technology + working system.

## 2. Typography

- One primary typeface: **Inter** (system fallback stack), used for everything.
- Monospace for technical micro-labels: ui-monospace stack (`SFMono`, `Cascadia`, `Consolas`).
- Display type: weight 600–650, `letter-spacing: -0.045em`, tight line-height (0.92–1.0).
- Wordmark scale: up to `clamp(4.5rem, 18vw, 15rem)`; letters may bleed past
  viewport edges and sit behind/over the hero object.
- Micro-labels: 11px, uppercase, `letter-spacing: 0.14em`, muted color,
  tabular numerals for all metrics (`font-variant-numeric: tabular-nums`).

## 3. Color

Dark-first. Accent is used as *light*, not paint - the site is nearly
monochrome when animation stops.

| Token | Value | Use |
|---|---|---|
| `--bg` | `#050507` | page base |
| `--bg-raise` | `#0a0a10` | workspace surfaces |
| `--ink` | `#f4f4f6` | primary text |
| `--ink-2` | `#a0a0aa` | secondary text |
| `--ink-3` | `#5c5c66` | faint text / captions |
| `--line` | `rgba(255,255,255,0.08)` | hairlines, editorial grid |
| `--line-2` | `rgba(255,255,255,0.16)` | stronger rules |
| `--violet` | `#7b5cff` | primary accent (from SAT-SA `#5236c9`, lifted for dark bg) |
| `--indigo` | `#4f46e5` | gradient depth |
| `--blue` | `#4d9fff` | analytical accent (from SAT-SA `#1d59c9`, lifted) |
| `--signal` | `#b7a6ff` | glow highlights |
| `--warn` | `#e8b54a` | urgency-elevated state (restrained, not red alarm) |

No green-heavy styling. No neon/cyberpunk. No pink/orange startup gradients.

## 4. Grid

- Fixed editorial grid overlay: 5 hairline columns on desktop
  (`rgba(255,255,255,0.05)`), 2 on mobile. Fades in during intro, persists
  site-wide, `pointer-events: none`, very low contrast.
- Content max width 1320px, generous side padding (5vw / 20px mobile).
- Sections separated by 1px rules and whitespace, not cards.

## 5. Motion

| Layer | Speed | Notes |
|---|---|---|
| Grainient background | ~0.05 time speed, very slow | pauses offscreen / hidden tab |
| Hero object | slow structural drift | one rAF loop, canvas 2D |
| Signal pulses | medium | travel along structure paths |
| Intro assembly | 1.2–2.0s total | per-letter stagger, then settle |
| UI transitions | 150–500ms | `cubic-bezier(0.16, 1, 0.3, 1)` |
| Scroll reveals | 500–700ms | once, via IntersectionObserver |

No scroll hijacking, no bounce loops, no jitter. Numbers count up once when
they enter the viewport.

**Reduced motion**: `prefers-reduced-motion` disables canvas animation (renders
one static frame), collapses the intro to a short fade, disables parallax and
count-up, keeps simple opacity fades. Site must look complete when static.

## 6. Entry composition (`/`)

`/` is the entry experience and doubles as the sign-in page. `/login` renders the
same component, so there is exactly one login surface and deep links behave.

- 100svh on desktop; below 1180px the page becomes a scene band with the
  interface in normal flow beneath it, so nothing is clipped and the page
  scrolls normally.
- Layers back→front, by z-index in one stacking context:
  black base + radial violet halo → Grainient grain → editorial grid (App) →
  **wordmark back plane** → WebGL canvas → **wordmark front plane** → vignette
  and field annotations → hero copy + credentials → nav (App).
- The two wordmark planes are what make the sculpture and the type occupy the
  same space: identical metrics, and the front plane paints only the middle run
  of letters. The container must not create a stacking context (no transform,
  filter, opacity or blend mode) or both planes would trap on one side of the
  metal.
- Intro timeline: 0.0 black · 0.15 letters assemble (staggered, blur→sharp,
  slight rotation) · 0.32 canvas emerges from darkness · 0.38 copy · 0.43
  credentials. Runs once per session (sessionStorage), skipped on return visits.
- Pointer parallax: rAF-coalesced, ~4% easing per frame, capped at a few pixels
  of perceived movement.

### Entry object - "Neural Signal" (`components/hero/neural.ts`)

Three.js. Six strands threaded past an invisible core - three tubes, two
flattened ribbons (a tube scaled on one axis), one thin emissive wire - built
from `CatmullRomCurve3` + `TubeGeometry` with per-strand control-point
perturbation, so no two share a silhouette and nothing closes into a torus knot.

- Material: `MeshPhysicalMaterial`, metalness 0.86–0.9, roughness 0.26–0.31,
  clearcoat 0.75–0.85. Base tints are dark grey, **not** near-black: for a metal
  the base colour is the specular reflectance, and a near-black albedo renders as
  a void regardless of lighting. The form reads as dark chrome because the
  environment is a black void with a few bright strips.
- Environment: procedural PMREM bake of emissive planes
  (`components/hero/studioEnv.ts`), shared with the About hero.
- Lighting: dim violet rim, blue edge, low white key, minimal fill. The strips
  do the modelling; the lights only shape the silhouette.
- Motion: per-strand breathing injected via `onBeforeCompile` (two low-frequency
  sines on `transformed`, driven by one shared uniform - GPU-side, no per-frame
  allocation), plus group drift ≤0.11 rad, camera drift, and a violet bead that
  rides one strand every ~4–7s.
- Cost control: DPR capped at 1.75 (1.25 on mobile), single rAF loop, paused on
  `document.hidden` and when the canvas leaves the viewport, one composed frame
  under reduced motion, full disposal on unmount.
- Fallback: WebGL → existing 2D `engine.ts` signal structure → the CSS halo.
  Login never depends on any of the three; verified by `qa:entry`.

## 7. Navigation

Flat, transparent, tiny, editorial. Left: `Mental.ai` wordmark (small). Right:
`SCREEN · RESEARCH · METHODOLOGY(→/research#method) · ABOUT(→/about#limits)` + a
light rectangular `LOGIN` CTA when signed out, or `HELLO, <FIRST NAME> ▾` with
an account panel (restart screening · log out) when signed in. No pill navbar. After scroll: hairline
bottom border + 8px blur backdrop. Mobile: compact menu overlay.

## 8. About page sections (`/about`, order)

1. **Hero** (above).
2. **Statement** - "Language contains signals. mental.ai makes them visible."
   Editorial typographic interlude: SEE THE SIGNAL → LANGUAGE → PATTERN → REVIEW.
3. **Pipeline** - numbered technical sequence 01 INPUT · 02 CLEAN ·
   03 PREPROCESS · 04 FEATURES · 05 MODELS · 06 REVIEW as a horizontal/vertical
   line-and-number composition with progressive line reveal on scroll. No cards.
4. **Dual signal** - animated SVG/canvas composition: one language input
   branching to CONDITION SIGNAL (7-class) and URGENCY SIGNAL (independent
   safety net), converging to HUMAN REVIEW. Urgency is explicitly *not* one of
   the seven classes.
5. **Research metrics** - huge tabular numbers, verified only:
   `53,043` primary records · `232,074` urgency records · `0.6926` primary
   macro-F1 · `0.987` suicide recall @ 0.15 · plus `0.9431` macro-F1 @ 0.5 and
   `0.8981` @ 0.15 explained as a deliberate recall-first trade-off.
6. **What mental.ai is not** - limitations as strong typography:
   NOT A DIAGNOSIS / NOT A CLINICAL DECISION / NOT AUTONOMOUS CRISIS RESPONSE.
   Proxy labels, public datasets, human review routing.
7. **CTA** - START SCREENING →.
8. **Footer** - minimal: name, one-line description, section links.

## 9. `/screen` - check-in then workspace

Behind the gate. Calmer than the entry: dark raised surface, faint grid, no
Grainient. Two stages in one route.

**Stage 1 - check-in** (`components/screen/CheckInFlow.tsx`). Four prompts, one
per screen, `STEP n OF 4`, starting with `BEFORE ANYTHING ELSE` / "How are you
today?". Answers are browser-local and are never transmitted from this screen;
completing it flattens them into the editor text and opens stage 2. A saved
check-in is restored from storage, so a reload does not re-ask. `Restart
check-in` in the stage-2 header clears it and returns here.

**Stage 2 - workspace.**

- Title `SCREEN`, subtitle "Submit language for signal analysis."
- Large multiline textarea (the dominant element), character count `n / 10000`
  (backend `PredictRequest` max_length=10000), client-side validation:
  empty and >10000 never submit.
- `ANALYZE →` triggers a cinematic staged sequence (LANGUAGE → FEATURES →
  CONDITION → URGENCY → REVIEW) rendered **while the real `POST /predict`
  request is in flight**. The stages are visual only - the UI never claims the
  backend reports per-stage progress, and shows no fake percentages.
- Results render as an analytical instrument:
  - `ANALYSIS COMPLETE` + request id + service version.
  - `CONDITION SIGNAL`: predicted class (large) + the model's own
    `class_probabilities` rendered as thin bars (real API values only).
  - `URGENCY SIGNAL`: `NOT ELEVATED` / `ELEVATED - HUMAN REVIEW RECOMMENDED`
    from `flagged`, with `suicide_probability` and the `decision_threshold_used`
    shown verbatim. Elevated uses `--warn`, never an alarm.
  - Provenance caveat from the API response shown verbatim.
  - Disclaimer strip: research screening result, proxy labels, not a diagnosis.
- States: idle · validating · analyzing · success · validation-error ·
  server-error (with message) · unavailable (`/health` fails: "ANALYSIS
  UNAVAILABLE - the screening service could not be reached").
- System status chip (SCREEN page + footer): polls `/health` and `/ready`;
  never hardcoded.

## 10. `/research` - research publication page

Numbered publication-style sections (01 PROBLEM · 02 DATA · 03 PIPELINE ·
04 FEATURES · 05 MODELS · 06 EVALUATION · 07 EXPLAINABILITY · 08 LIMITATIONS ·
09 REPRODUCIBILITY). Content sourced only from repository documents
(`README.md`, `docs/MODEL_CARD.md`, `REPRODUCIBILITY.md`,
`FINAL_DELIVERABLE.md`, `artifacts/config.json`). Interactive methodology
pipeline with per-stage hover explanations. Global SHAP explainability is
described as *global model* analysis - never as per-instance explanation.

## 11. API integration

Single client `web/src/lib/api.ts`:

```
health():  GET {base}/health
ready():   GET {base}/ready
predict(): POST {base}/predict {text} → PredictResponse
```

- `base` = `import.meta.env.VITE_API_URL ?? "/api"`; Vite dev proxy forwards
  `/api/*` → `http://localhost:8000/*` (backend stays unmodified - no CORS
  change needed in dev; production sets `VITE_API_URL` or reverse-proxies).
- AbortController timeout (30s), typed errors (`validation | server |
  unavailable | timeout`), no raw text logged, request id surfaced from
  `X-Request-ID`.
- No mock/demo/fallback predictions anywhere. If the API fails, the UI shows
  an honest error state.

## 12. Accessibility & responsive

- Semantic landmarks, labelled canvas (`role="img"` + description), focus
  styles, skip link, aria-live for analysis/result state changes.
- Breakpoints: ≥1280 desktop grid/hero · 768–1279 reduced scale · <768
  stacked, simplified structure, menu overlay. Hero must remain composed at
  390×844.
- QA screenshots at 1440×900, 1280×800, 1024×768, 768×1024, 390×844.

## 13. Stack

Vite + React 18 + TypeScript, react-router-dom, `ogl` (Grainient only).
No UI framework, no Tailwind - hand-written CSS from these tokens.
Canvas 2D hero engine (no three.js). Playwright (dev-only) for visual QA.

## 14. Performance budget

- One rAF loop per canvas; pause on `document.hidden` and when offscreen
  (IntersectionObserver); DPR capped at 1.5 (1.25 mobile).
- Route-level code splitting for `/screen` and `/research`; Grainient and the
  hero engine load only on `/`.
- No large images; fonts via system stack + Inter from Fontsource-style local
  import avoided - use `font-family` stack with Inter if installed, else
  system-ui (keeps first paint instant).
