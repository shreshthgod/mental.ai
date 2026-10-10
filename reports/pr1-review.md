# PR #1 review evidence

Branch: `feat/on-device-intelligence-product-refinement`. Upstream main remains `78ac6da4d49ac35d65e00ca82b25245560695fa3`.

## Identity

All eight original feature commits were inspected and normalized to author and committer `PrathamKapoor <prathamkapoor027@gmail.com>`. Each rewritten commit retains its original tree and timestamps. The original feature ref is backed up locally as `backup/pr1-before-review-20261010`; upstream commits were not rewritten. The corrective commit uses the same identity. No co-author or generated-by trailers were added.

The connected GitHub profile reports `PrathamKapoor` and the requested email. The Git credential's authenticated login also resolves to `PrathamKapoor`. The private `/user/emails` endpoint returns HTTP 404 for this credential, so its `verified` flag could not be independently retrieved.

| Original | Normalized |
|---|---|
| `8a67341ba677` | `a9071e6d95f3` |
| `3d642c5c2af2` | `0d54ecae734c` |
| `3db4e16ced52` | `7081f39de9d9` |
| `6c9c2bb74bad` | `99b20879651c` |
| `bf6efc378a45` | `c0fda2ab9711` |
| `7d6cd85a8baa` | `cbc5332151f2` |
| `9a40f41c65cc` | `af19365a2a68` |
| `ff3536f333d7` | `2eff3f01fb64` |

## Verification

- `python -m pytest tests -q`: 495 passed, two POSIX launcher tests skipped on Windows; one upstream Starlette/AnyIO deprecation warning.
- `npm --prefix web test`: 55 shared-contract checks plus private inference/consent/deletion/isolation regressions passed.
- `npm --prefix web run lint`, `typecheck`, and `build`: passed.
- `cd web && node scripts/reviewqa.mjs`: browser checks passed at 1440×900, 1280×720 and 390×844, plus reduced motion. All glyphs above the sculpture; monotonic shared scene movement; stable canvas dimensions; 70/30 final desktop ratio; no remount or horizontal overflow. Screenshots in ignored `web/shots/review-settled-*.png` were visually inspected.
- `cd web && node scripts/workspaceqa.mjs`: rendered account switch, private-text network inspection, separate local-save/personalization choices, deletion, server consent and logout passed against a synthetic API.
- `python evaluation/evaluate_contextual_intelligence.py --rules-only --output .cache/evaluation-smoke.json`: passed with unavailable legacy/contextual/hybrid tracks correctly identified.
- The original sculpture source matches upstream/main exactly; regression tests preserve its hash and original letter poses/durations. The full wordmark foreground is an explicitly requested layering correction. Handover uses one shared transform, retaining final scene width rather than resizing WebGL on each frame.

Source comments were shortened in the new emotion/browser modules, entry orchestration and modified check-in code. Unsupported taxonomy attribution, claimed calibrated heuristics, guarantees and unmeasured extension specifications were removed. Necessary safety, provenance, accessibility and contract comments remain. Historical baseline files are not broadly reformatted.

## Remaining limits

See `model-review.md` for comparable scores and error IDs, and `../docs/PRIVACY.md` for data paths. No model-quality improvement is claimed. Trained browser outputs and product emotion classification remain unavailable. Safety rules miss indirect disclosures and can over-escalate negation; English support is limited. No clinical validation, deployment-wide privacy audit or browser model parity is established. Derived-score sync is not implemented.

The production build succeeds locally. The new GitHub workflow still needs a remote run; live auth, hosted provider configuration and production deployment are not validated by synthetic browser tests. The PR remains Draft and is not merged.

## Files changed in this correction

- `.github/workflows/review.yml`
- `.gitignore`
- `README.md`
- `Step 12 - Packaging/package/mental_health_screening/emotion.py`
- `docs/BROWSER_EXTENSION_ROADMAP.md`
- `docs/PRIVACY.md`
- `evaluation/contextual_benchmark_v1.json`
- `evaluation/emotion_experiment.py`
- `evaluation/evaluate_contextual_intelligence.py`
- `evaluation/requirements-emotion.txt`
- `evaluation/review_challenge_v1.json`
- `reports/contextual-ml-evaluation-20261010.json`
- `reports/contextual-ml-evaluation-20261010.md`
- `reports/contextual-ml-evaluation-corrected.json`
- `reports/emotion-experiment.json`
- `reports/git-reconciliation-20261009.md`
- `reports/model-review.md`
- `reports/review-challenge.json`
- `tests/test_evaluation_boundary.py`
- `tests/test_landing_preservation.py`
- `web/package.json`
- `web/scripts/contractqa.mjs`
- `web/scripts/entryqa.mjs`
- `web/scripts/privateqa.mjs`
- `web/scripts/reviewqa.mjs`
- `web/scripts/workspaceqa.mjs`
- `web/src/components/entry/Wordmark.tsx`
- `web/src/components/hero/neural.ts`
- `web/src/components/screen/CheckInFlow.tsx`
- `web/src/components/screen/PersonalizationControls.tsx`
- `web/src/lib/history.ts`
- `web/src/lib/onDeviceInference.ts`
- `web/src/lib/personalization.ts`
- `web/src/pages/Screen.tsx`
- `web/src/pages/Start.tsx`
- `web/src/styles/entry.css`
- `web/src/styles/screen.css`
