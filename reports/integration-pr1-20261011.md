# Owner and PR #1 integration record

The unified application retains the owner's published recovery work and all nine existing PR commits. Integration took place on `integration/mental-ai-main-pr1` in a separate worktree. No main update, production migration, account creation, deployment, force push, reset, rebase or history rewrite was performed. The branch is intended for both humans' review through the existing draft PR, not a clinical or production release.

Application reconciliation commit: `5a3d27089543f72494a259282c9c0b3e3a674f82`. Subsequent documentation records the result without changing application behavior. The eventual publication SHA and current CI links are recorded in PR #1's description.

## Original state and recovery

Original branch: `main`. Original local and remote main HEAD: `95570b0ab33457b268ea30595fbb3158c3d310cd`. The working tree and index were clean: no staged, unstaged or untracked source changes. There was one local branch, no local-only commits, no stashes, no additional worktrees and no unreachable commits reported by `git fsck --no-reflogs --unreachable`. Reflog inspection accounted for the earlier Vantage clone and the owner's subsequent publication commits.

Ignored files included private `.env` and `web/.env.local`, a development log, dependency directories, caches, screenshots, compiled frontend files and build metadata. No additional ignored application source was found. Environment variable names and dependency configuration were reviewed without printing private values. Installed dependencies were reused only for Python checks; root and frontend Node dependencies were installed separately in the integration worktree.

Recovery materials are locally retained under `.git/integration-backups/20261011-pr1/` in the owner's original repository:

- `owner-history.bundle`: complete original history, verified with `git bundle verify`.
- `owner-working-tree.tar.gz`: source, models, configuration and relevant ignored local files; all 445 archived files were reread and SHA-256 verified.
- `manifest.json`, branch/reflog/worktree/status records, and empty staged/unstaged binary patches.
- `refs/backup/mental-ai/20261011-owner-main` points to the original main HEAD.
- `refs/backup/mental-ai/20261011-pr1-input` points to the fetched original PR HEAD.

Generated dependency/cache/bytecode directories were excluded from the tar archive and remain untouched in the original checkout. Tracked bytecode is recoverable from the Git bundle. No stash was used. A final audit verified that all 445 backed-up original files, both private environment files, the original HEAD and its clean working-tree state remained unchanged. Backup metadata and private files are not committed or published.

## Fresh refs and contribution inventory

Selected remote: `origin`, whose fetch and push URL is `https://github.com/shreshthgod/mental.ai.git`.

| Input | Verified SHA |
|---|---|
| Remote main | `95570b0ab33457b268ea30595fbb3158c3d310cd` |
| Remote PR feature | `4998f77d25427abcb9b65d4aa1a000c71489ff7f` |
| Actual merge base | `78ac6da4d49ac35d65e00ca82b25245560695fa3` |

Main has one unique commit, `95570b0`, adding the session file. The feature has nine unique commits: `a9071e6`, `0d54eca`, `7081f39`, `99b2087`, `c0fda2a`, `cbc5332`, `af19365`, `2eff3f0` and `4998f77`. No owner-only unpublished commit or working-tree application patch was present.

The owner's application work is already an ancestor of the PR, including `2053855` (project update), `ae15d97` (safety, API, persistence and login recovery) and `78ac6da` (publication/recovery checkpoint). Its improvements include raw-before-optional safety handling, independent component failure, schema 1.0, authoritative snapshot persistence, account authorization, input/rate/deadline/readiness boundaries, Supabase key handling, session restoration and OAuth integration, original-case UI safety presentation, isolated verification and hosting preparation. The inference, auth, database, frontend, migration, dependency and hosting changes were inspected rather than assuming main-only application changes existed.

PrathamKapoor's nine commits supply the entry sequence/handover refinements, emotion research module and evaluations, private local-rule path, explicit local-history/personalization/server consent, inspection/deletion controls, account-switch check-in isolation, evaluation correction, honest unavailable outputs, extension roadmap and review workflow. All existing PR trees, reports and tests remain represented; intermediate sculpture experiments are retained in history while the PR's approved final original sculpture remains in the application.

## Merge and reconciliation

1. A separate housekeeping worktree started from fresh main. Commit `e5370a181c1ec8736e20cd560ecb112aa148ef51` removed the accidental session artifact and added its exact ignore rule.
2. The integration worktree started from the full PR HEAD. Normal merge `104dad6` incorporated `origin/main`.
3. Normal merge `654ce1c` incorporated the isolated housekeeping commit, preserving both parent histories.
4. Commit `5a3d270` reconciled the interacting frontend behaviors and expanded their regression checks.

There were no textual merge conflicts. Main's application tree equals the common ancestor; its only added file was session metadata. Both input HEADs and the owner's earlier application commits are ancestors of the integration branch. No cherry-picking, squashing, selecting whole files as ours/theirs or authorship normalization was used.

Behavioral reconciliation addressed these concrete problems:

| Area | Evidence and resolution |
|---|---|
| Mounted account switch | A new browser regression timed out waiting for account B's cloud record. History loading now depends on the verified account and aborts/guards old requests. Previous text, results and consent still clear on switching. |
| Cloud history after private analysis | The PR replaced displayed account history with device-only history after submission. A shared in-memory record merge now retains fetched cloud records and newly acknowledged server snapshots without implicitly persisting them locally. |
| Cloud-only saving | Consented server saving immediately displays the acknowledged snapshot even when device saving is off. The message accurately says it was not saved on this device. The regression checks storage contents and retained history without deleting existing records. |
| Inference mode changes | Cancelling through a mode button previously left the analyzing phase active. Selection now cancels the display request, clears stale presentation and resets server consent. A delayed-response regression verifies subsequent local analysis and fresh consent. Server work already received may still finish. |
| Different input limits | Local rules always enforce their own 10,000-code-point cap; the legacy server uses its independently configured limit. A browser regression supplies a 15,000-character server limit. |
| Keyboard login after reveal | The owner's keyboard suite observed no focused field while the PR hid the auth stage. The existing no-scroll autofocus now waits until the panel is revealed. Entrance timings, assets and CSS are unchanged. |
| Existing server/browser checks | The owner's screening script originally timed out waiting for `/predict` because the new default is private mode. It now explicitly selects server mode and consents to server submission, device saving and check-in saving before testing the retained behaviors. Auth checks wait for the approved sign-in reveal. |
| Canvas regression measurement | The original test could include a canvas's default uninitialized buffer, and its fixed sampling deadline could expire before a slow software-GPU handover. Sampling now continues through settlement, records engine/timestamps, requires initialized pre/post frames and enforces constant initialized buffer size, scene width, joint movement and no remount. No renderer or asset was changed. |

QA outputs now go to ignored screenshots or explicit temporary paths, preserving earlier committed reports rather than overwriting historical evidence. CI retains the contributor's checks and additionally installs the owner's root lockfile, runs OAuth module checks and exercises the owner’s email and actual-model server flows against the isolated provider stub.

## Feature-preservation matrix

All rows below remain in the integrated application or its explicitly identified research/future scope.

| Feature / source | Original files | Final reconciliation | Verification and remaining limit |
|---|---|---|---|
| Owner recovery: email/password sign-in and registration surface | `api/auth.py`, `api/db.py`, `web/src/lib/auth.ts`, `components/login/LoginForm.tsx`, `components/entry/LoginPanel.tsx` | Auth contracts retained; autofocus waits for reveal | Backend auth/provider tests; 47/47 email/session browser checks with stub provider. Live user registration/confirmation not tested. |
| Owner recovery: Google OAuth | `web/src/lib/auth.ts`, `supabase.ts`, `App.tsx`, `LoginPanel.tsx` | Existing SDK flow, return paths and verified identity retained | 24 module groups; 13 development SDK browser groups with intercepted responses. Compiled and genuine-provider scope is recorded separately below. |
| Owner recovery: restoration, refresh, remember scope, logout | `web/src/lib/auth.ts`, `authContext.ts`, `AccountMenu.tsx` | Existing generations and identity adoption unchanged | Email browser suite, expired-mirror server check and SDK callback/logout checks. Real expiry/provider lifecycle remains unverified. |
| Owner recovery: trusted ownership and isolation | `api/api.py`, `auth.py`, `db.py`, `web/src/lib/privateStore.ts` | Backend filters retained; mounted account history reload repaired | Backend owner/persistence tests; rendered A-to-B switch, check-in clearing and session rejection. Real Supabase RLS not tested. |
| Shared original entry and PR approved handover | `Start.tsx`, `Wordmark.tsx`, `styles/entry.css` | PR final sequence, nine glyphs and shared 70/30 movement retained | `reviewqa.mjs`; desktop/mobile visual inspection; 317/317 entry checks. Software-GPU measurements are not product latency benchmarks. |
| Shared original sculpture, shaders, environment and fallback | `components/hero/neural.ts`, `studioEnv.ts`, `engine.ts`, `sculpture.ts`, `entry/NeuralStage.tsx` | Byte-identical to both input trees | Locked geometry regression, stable canvas/no-remount checks, resize/navigation and WebGL fallback tests. |
| Shared typography, gradients and visual assets | `components/GradientWaves/*`, `components/Grainient/*`, fonts and existing hero source | No integration asset/CSS redesign | Ten visual source files byte-identical; final desktop/mobile screenshots inspected. |
| Owner check-in and PR storage choice | `CheckInFlow.tsx`, `web/src/lib/checkin.ts`, `Screen.tsx` | Ordered editable prefill retained; saving remains a separate opt-in | Contract checks and rendered check-in/account-switch/deletion tests. No automatic analysis or conversation memory. |
| Owner legacy trained inference | Packaged `inference.py`, `features.py`, `preprocessing.py`, `artifacts/*` | Actual XGBoost/LR outputs retained behind PR server consent | 497 backend tests, actual HTTP/model original case and runtime verifier; all eight artifacts unchanged. Clinical validity not established. |
| Owner independent safety fusion | `safety.py`, `fusion.py`, `api/contracts.py`, `analysisView.ts` | Raw Normal cannot suppress established HIGH; optional failures remain independent | Original Normal 0.9502395987510681 and urgency 0.7847130134418575 still display Urgent support/HIGH. Existing diagnostic failures remain. |
| Owner authoritative snapshots and legacy rows | `api/db.py`, `api/api.py`, `web/src/lib/history.ts` | Exact safety snapshots retained; in-memory cloud/device reconciliation repaired | HTTP read-back, recorded-state reload, legacy/unavailable fixtures and cloud-only save test. Server original disclosure is not returned in history. |
| Owner account-history deletion | `DELETE /screenings`, `api/db.py` | Authenticated owner-scoped endpoint retained | Backend deletion/owner tests. Current UI still offers device deletion; account deletion API is separate. |
| Owner request validation and bounded failures | `body_limit.py`, `limits.py`, `execution.py`, `contracts.py`, `web/src/lib/api.ts` | Unchanged contracts, capacity, limits and deadlines | Backend suite; rendered 401/429/422, unavailable, timeout, cancel and stale responses. Distributed ingress and termination of synchronous work are not implemented. |
| Owner configuration/readiness | `api/api.py`, `start-dev.sh`, `SystemStatus.tsx` | Server readiness retained; local input limit separated | Runtime verifier 24 required checks pass; POSIX launcher tests run. Readiness does not prove external providers or clinical capability. |
| Owner Supabase schema/migration | `supabase/schema.sql`, `migrations/20261008_authoritative_analysis.sql` | Byte-identical; no new/destructive migration | Schema/contract/static review and stub persistence tests. Migration not applied to a real database. |
| Owner hosting and server SDK | `main.py`, `Dockerfile`, `vercel.json`, root package/lockfile, `check_supabase_server.mjs` | Byte-identical; root dependency kept | Production build, mounted-path backend tests and actual SDK import/config smoke with fetch blocked. Docker and hosted runtime not verified. |
| Owner public/research pages and navigation | `pages/Research.tsx`, `Landing.tsx`, `components/landing/*`, chrome/navigation | Retained without integration redesign | Entry/navigation and compiled public-route tests; no promised clinical reviewer workflow added. |
| PR private local rules | `web/src/lib/onDeviceInference.ts`, `Screen.tsx` | Default private path retained; independent cap and mode cancellation repaired | Network-blocked module tests plus rendered browser sentinel checks. No trained browser model, silent fallback, raw/embedding/score upload or diagnostic probability. |
| PR explicit server inference consent | `Screen.tsx`, `docs/PRIVACY.md` | Owner's working server flow retained behind informed opt-in | Unconsented submission sends no `/predict`; consented actual-model tests pass. Service may retain text and snapshots as disclosed. |
| PR local saving, inspection and deletion | `history.ts`, `CheckInFlow.tsx`, `PersonalizationControls.tsx` | Separate check-in/result choices retained; fetched cloud rows never implicitly persist | Private module and workspace browser regressions, cloud-only saving and deletion checks. Browser data remains unencrypted and account-scoped. |
| PR opt-in welcome personalization | `personalization.ts`, `PersonalizationControls.tsx`, `CheckInFlow.tsx` | Disabled-by-default versioned consent, theme inspection/disable/deletion retained | Module and rendered consent/theme/deletion/account tests. Themes are sensitive coarse rules, not clinical assessments. |
| PR emotion research API | Packaged `emotion.py`, `__init__.py`, `inference.py` | Separate heuristic cue analysis retained, not fused into clinical screening | Emotion tests and text-only evaluation reruns. Scores are lexical counts; browser emotion classification stays disabled. |
| PR evaluation integrity and experiment evidence | `evaluation/*`, `reports/model-review.md`, corrected/invalid reports, `tests/test_evaluation_boundary.py` | Leakage correction and unavailable contextual/hybrid tracks retained | Label-mutation boundary tests; 24-case and 14-case reruns. Original 500-case experiment is preserved evidence, not newly trained or independently revalidated. |
| PR review automation and regression tests | `.github/workflows/review.yml`, new Python/browser/module tests | All retained and expanded with owner integration paths | Local suites pass; remote CI result belongs to exact published HEAD and is reported in PR description. |
| PR extension/privacy direction | `docs/BROWSER_EXTENSION_ROADMAP.md`, `PRIVACY.md` | Future explicit setup/startup, greeting, downloads, approved contexts, pause/disable/delete and consented scores retained | Documentation review only. No extension, covert monitoring, keylogging or score-sync implementation claimed. |

## Verification evidence

Local backend: `PYTHONPATH='Step 12 - Packaging/package:.' NLTK_DATA=<existing prepared resources> PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests -q` completed with **497 passed in 23.46 seconds**, no skipped tests, and one upstream Starlette/httpx deprecation warning. Backend/tests/artifact/evaluation application code has not changed since this run; the final reconciliation changes frontend consumers and their QA.

Frontend `test`, `lint`, `typecheck` and `build` pass on the reconciled code. Tests include 55 shared-contract checks across 16 response states and private inference/consent/deletion/isolation/history reconciliation checks. Both root and web `npm ci` succeeded. Contract type drift check passed. OAuth actual-module checks passed 24 required groups.

Browser checks completed on the reconciled code:

- Entry experience: **317/317** checks across eight desktop, two tablet and four mobile sizes, reduced motion, returning/authenticated visitors, resizing, navigation/remounting and WebGL fallback.
- `reviewqa.mjs`: all desktop/mobile, nine-glyph layering, constant initialized canvas size, joint monotonic scene movement, 70/30 ratio, reduced-motion and local network checks pass; screenshots inspected.
- Expanded `workspaceqa.mjs`: mounted-account history reload, no unconsented storage, independent local limit, preserved displayed cloud history, local raw-text network privacy, opt-in personalization/save, deletion, server gate and logout pass.
- Owner email/session browser suite: **47/47** pass after reveal/focus reconciliation. A resource-contention timeout during an overlapping software-GPU run was followed by a passing isolated run.
- Owner actual-HTTP/model screening suite: **37/37** pass, expanded from 35 with cloud-only saving and inference-mode cancellation/renewed consent. The provider is an in-memory stub; contract/error overrides are explicitly fixtures.
- Google SDK browser suite: **13/13** development groups pass with the actual installed SDK and all provider/API responses intercepted.

Compiled SDK, private/server and public-route verification and the final configured build are recorded in the completion addendum below. Publication status and CI for the exact pushed head are recorded in PR #1. Temporary raw logs, synthetic API records and screenshots are not added to production source or CI user-data artifacts.

## Safety and ML limits preserved

The actual original-case HTTP result remains primary Normal 0.9502395987510681, urgency suicide 0.7847130134418575 with threshold 0.15, and independent/fused HIGH/self/current/not_stated/degraded. The UI headline remains Urgent support, never an unsupported diagnosis or confirmation of safety. Missing/corrupt independent model and preprocessing states are covered by backend and browser regressions; unavailable browser models return null/empty outputs.

The unchanged default 321-case diagnostic exits **1**, with rule engine **259/321** and full pipeline **214/321** passing. Its known temporal annotation and conservative routing disagreements remain; neither labels nor inference were tuned to make it green. Both layers route 98/98 mandatory urgent cases on this specific diagnostic corpus, with 0/73 benign HIGH false positives and no asserted subject errors. These selected software fixtures do not establish clinical recall.

The rerun consumed 24-case development benchmark retains heuristic emotion macro-F1 **0.3566001899335232**, legacy condition macro-F1 **0.32653061224489793**, and safety detection **1/6** HIGH cases with five false negatives. The 14-case hand-authored challenge retains **2/3** HIGH cases detected, one indirect-disclosure miss and one negated-statement false positive. They are not new independent holdouts.

The preserved 500-case emotion experiment remains heuristic macro-F1 **0.2020833333333333**, supervised MiniLM-head macro-F1 **0**, and **84** missed positive label assignments. No experiment retraining, threshold tuning, new model deployment or quality improvement is claimed. The old contaminated contextual report remains invalid/superseded; unsupported contextual/fusion/product-emotion components remain unavailable or disabled. All original model artifacts are unchanged.

## Authentication, privacy, schema and deployment boundaries

Public read-only genuine Supabase checks return settings HTTP 200, email enabled, confirmation required, Google disabled, and JWKS HTTP 200 with one public key and no private parameters. Backend/browser project and publishable-key configuration match. These observations do not verify a user's identity, email confirmation, OAuth consent, RLS, table grants or private history.

`verify_supabase_isolated.py --check-config` exits **2/BLOCKED**: the explicitly isolated project and two pre-provisioned test identities are missing. No actual account, email, private user record, schema or production data was written. The additive owner migration is identified and retained unchanged, not applied. Authentication/RLS/live database behavior must be tested separately with isolated credentials.

Private inference receives only text, performs local rules and sends no raw writing, embeddings, reconstructable text or scores. Auth, configuration, service health and authenticated history remain separate network flows. Optional legacy inference submits and can persist text only after the separate consent control. Check-in, result-history and theme saving each require their own choice. The module tests forbid fetch/XHR/WebSocket; rendered and compiled checks inspect actual requests and storage.

The actual root `@supabase/server` import/configuration smoke passes with **zero fetch calls**, using the owner's private configuration without printing values. Python identity verification still uses GoTrue. Known backend secrets/passwords were scanned against every tracked integrated file and compiled frontend assets with **zero matches**. Environment files remain ignored/private, and reviewed screenshots contain only anonymous/synthetic UI.

Frontend production compilation, packaged model availability, local API routes/readiness and required dependency imports are verified. Docker tooling is absent; no image build or hosted platform/runtime smoke was performed. Existing Docker/Vercel configurations and lockfiles are unchanged. No deployment was manually initiated. Any existing external preview automation triggered by a PR push is separate from a verified hosted application.

`npm audit` reports two moderate entries in the existing React Router dependency tree; the available fix is a major version migration. No unrelated dependency migration was performed. Repository/data/model provenance and qualified safety/language review, clinical validation/calibration, reliable indirect-crisis handling, distributed operational limits, browser trained-model parity and independent release validation remain unresolved. Passing builds and synthetic provider tests do not remove these blockers.

## Session artifact, portable paths and authorship

`:memory:.ses` is a 51-byte, two-line session artifact. Its provenance and existing owner handoff explicitly distinguish it from application source; no runtime reference or required dependency was found. Its contents were retained privately in the original checkout, archive and original Git ref, and are not quoted here. A normal corrective commit removes it from the integrated tree and adds an exact ignore rule. No prior owner commit was rewritten and no change was pushed to main. Main will retain the problematic path until an approved normal update; the combined PR tree passes filename/reserved-name/case-collision checks for Windows paths. Native Windows execution was not performed in this Linux session.

Existing owner commits remain `shreshthgod <shreshthnmims.it@gmail.com>` and PR commits remain `PrathamKapoor <prathamkapoor027@gmail.com>`. GitHub commit APIs map both identities to their respective human accounts. The authenticated GitHub user is the owner; new integration and housekeeping commits use the same verified repository-local owner identity. No collaborator changes, AI co-authors, generated-by trailers, amendments or history rewriting were introduced.

## File retention and review handoff

Before the report addendum, tree comparison found all PR paths retained, all owner paths retained except the deliberate session artifact, all eight packaged artifacts unchanged, and all ten original visual source files unchanged. Backend/API/schema/deployment/root-dependency/frontend-lockfile paths are byte-identical to the owner input; the PR's backend difference adds the separate emotion recognizer method/import without replacing inference behavior. Every modified production source path was reviewed. No production subsystem, migration, model or existing test file was deleted.

The full final added/modified/removed inventory and publication state are recorded below. Original historical reports remain untouched. The integration worktree and local housekeeping/recovery refs remain available for inspection; the owner's original checkout stays on its original main commit.

## Completion addendum

All local integration gates completed before publication. Fixed-build verification passed **13/13** compiled Google SDK groups, **3/3** compiled private/consent/actual-model server groups, and **12/12** compiled public-route/protected-route/API-proxy checks. SDK/provider responses are intercepted in the Google suite; email, server inference and saving use actual HTTP/model routes with the synthetic provider. The compiled private path sends no text submission and has no implicit local persistence; the explicit server path preserves HIGH despite raw Normal and stores no device record without consent.

The owner's private root/browser environment files were copied with their existing restrictive permissions into the integration worktree after isolated tests, without changing their original files or committing their values. A final build using the owner's genuine public browser configuration completed **196 modules in 9.20 seconds**. The existing configured-browser checks then passed **6/6** using only real public Supabase settings plus public local API reads; no password/account/history/write request occurred. This validates configuration and accurate disabled-Google messaging, not live user authentication or database permissions. Temporary testing builds were replaced by this configured build.

Source/configuration/corpus fingerprint (excluding documentation, reports, secrets and raw datasets): `1cf202c15d8501e139c4782e5312766235a8e19556c6d8e66105b6d7c8246e02`. The eight artifact hashes and complete before/after path inventories are retained in the local preservation audit. Original-state, ancestry, portable-path and secret scans passed again after the configured build.

Final comparison against the original owner/main tree: **27 added, 22 modified, 1 removed, 313 unchanged files**. Against the original PR tree: **1 added, 16 modified, 0 removed, 345 unchanged files**. The only removed file is the recoverable session artifact. All production, migration, model and test paths from the two inputs remain present.

Added relative to original main:

```text
.github/workflows/review.yml
Step 12 - Packaging/package/mental_health_screening/emotion.py
docs/BROWSER_EXTENSION_ROADMAP.md
docs/PRIVACY.md
evaluation/contextual_benchmark_v1.json
evaluation/emotion_experiment.py
evaluation/evaluate_contextual_intelligence.py
evaluation/requirements-emotion.txt
evaluation/review_challenge_v1.json
reports/contextual-ml-evaluation-20261010.json
reports/contextual-ml-evaluation-20261010.md
reports/contextual-ml-evaluation-corrected.json
reports/emotion-experiment.json
reports/git-reconciliation-20261009.md
reports/integration-pr1-20261011.md
reports/model-review.md
reports/pr1-review.md
reports/review-challenge.json
tests/test_emotion_analysis.py
tests/test_evaluation_boundary.py
tests/test_landing_preservation.py
web/scripts/privateqa.mjs
web/scripts/reviewqa.mjs
web/scripts/workspaceqa.mjs
web/src/components/screen/PersonalizationControls.tsx
web/src/lib/onDeviceInference.ts
web/src/lib/personalization.ts
```

Modified relative to original main:

```text
.gitignore
README.md
Step 12 - Packaging/package/mental_health_screening/__init__.py
Step 12 - Packaging/package/mental_health_screening/inference.py
tests/test_artifact_availability.py
tests/test_dev_launcher.py
web/package.json
web/scripts/auth.mjs
web/scripts/authflow.mjs
web/scripts/contractqa.mjs
web/scripts/entryqa.mjs
web/scripts/oauthbrowserqa.mjs
web/scripts/publicqa.mjs
web/scripts/screenqa.mjs
web/src/components/entry/Wordmark.tsx
web/src/components/screen/CheckInFlow.tsx
web/src/lib/history.ts
web/src/pages/Screen.tsx
web/src/pages/Start.tsx
web/src/styles/entry.css
web/src/styles/screen.css
web/src/styles/tokens.css
```

The new integration changes relative to the PR are the report, README clarification, exact session ignore rule, three production consumer files (`history.ts`, `Screen.tsx`, `Start.tsx`), two privacy/roadmap clarifications, review workflow and eight QA helpers/scripts. No owner backend, migration, dependency lockfile, PR emotion/evaluation implementation or original visual asset was replaced.

PR: https://github.com/shreshthgod/mental.ai/pull/1. Fresh pre-publication observations found it open, Draft and mergeable. Publication uses a normal fast-forward update of the existing feature ref only after re-fetching and comparing its expected head. CI and final mergeability must be checked against the new head; the PR description records their observed result. No final merge into main or auto-merge is authorized by this integration record. The combined implementation is ready for both humans' review, with the documented safety, genuine-provider, database, hosting and release-validation blockers still open.
