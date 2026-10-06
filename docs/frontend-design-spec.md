# Vantage - Frontend Design Spec

Cinematic redesign of the Vantage frontend: a dark, editorial, research-grade
product experience over the verified FastAPI inference backend.

References: TRUST-SAT (`trustsat.mpst.me`, local `SIH26/TRUST-SAT/web`) for
product communication and design tokens; minimal.gallery/denmu for motion and
art direction; React Bits `Grainient` (supplied, copied into this repo) for the
atmospheric WebGL layer.

---

## 1. Product framing

- Vantage is a **research screening instrument**, not a healthcare product.
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

## 6. Hero composition (`/`)

- 100svh, no scroll needed to understand the product.
- Layers back→front: black base → Grainient (near-black indigo/violet/blue,
  subtle) → editorial grid → hero canvas (signal structure) → giant VANTAGE
  wordmark interleaved with the structure (some letters behind, copy in front)
  → nav → hero copy → scroll cue.
- Intro timeline: 0.0 black · 0.2 letters assemble (staggered, blur→sharp,
  slight rotation, converge) · ~0.9 nav · ~1.0 hero object emerges · ~1.3 copy
  · ~1.5 CTA. Intro runs once per session (sessionStorage), skipped elsewhere.
- Pointer parallax: subtle camera/structure/light response. Expensive, not
  gamey.

### Hero object - "Signal Structure"

Canvas 2D with real 3D projection (perspective, depth fog, additive glow -
no WebGL dependency for the object itself):

- Central core node; two branching paths that converge - an abstraction of
  TEXT → {CONDITION, URGENCY} → REVIEW, never drawn as a flowchart.
- Gyroscopic rings of nodes, thin luminous edges, small particle field.
- Layered life: slow rotation · signals traveling along edges · particles
  emerging/fading · a soft pulse event every ~6–9s.
- Colors: white/violet/blue on black; glow via additive blending + shadowBlur,
  used sparingly for performance.
- Mobile: reduced node/particle counts, smaller radius.

## 7. Navigation

Flat, transparent, tiny, editorial. Left: `VANTAGE` wordmark (small). Right:
`SCREEN · RESEARCH · METHODOLOGY(→/research#method) · ABOUT(→/#limits)` + a
restrained `START →` text-link CTA. No pill navbar. After scroll: hairline
bottom border + 8px blur backdrop. Mobile: compact menu overlay.

## 8. Landing sections (order)

1. **Hero** (above).
2. **Statement** - "Language contains signals. Vantage makes them visible."
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
6. **What Vantage is not** - limitations as strong typography:
   NOT A DIAGNOSIS / NOT A CLINICAL DECISION / NOT AUTONOMOUS CRISIS RESPONSE.
   Proxy labels, public datasets, human review routing.
7. **CTA** - START SCREENING →.
8. **Footer** - minimal: name, one-line description, section links.

## 9. `/screen` - screening workspace

Calmer than landing: dark raised surface, faint grid, no Grainient.

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
