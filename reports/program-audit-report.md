# Whole-program continuation audit, 2026-10-09

ENGINEERING: partial. The local application repairs below are verified; declared semantic capability and unchanged diagnostic annotation/routing disagreements still prevent complete assessment claims.

INTEGRATION: partial. Actual local app, built frontend, HTTP and models were exercised with synthetic provider transport. Real isolated Supabase/schema/RLS/auth lifecycle, Docker/hosting/deployed/shared-ingress verification remain blocked.

RELEASE_VALIDATION: blocked. Reviewed policy/semantic/language/final data, qualified independent review and complete licensing/provenance are unavailable. No clinical/generalization guarantee, publication or deployment.

## What was wrong and what changed

This continuation audited paths beyond the earlier recovery checkpoint. D098 fixes `npm run verify`: it formerly printed failures and exited0, checked inference keys rather than availability, declared preprocessing verified unconditionally, used cwd-relative paths and misread zipped VADER. It now executes actual original-case safety/preprocessing/raw models, configured files/resources, uses honest statuses and fails nonzero. Offline mode never contacts providers/downloads/retrains; optional public HTTP probes require --api-url. Actual offline22/22 required checks pass, public HTTP mode24/24; independent review remains BLOCKED.

D099 fixes one-command boot: /health200 falsely stood for required readiness, Vite ignored custom API_PORT, and a hard primary-artifact check disabled functioning safety fallback. Launcher now validates ports/budget, requires /ready JSON, connects the proxy, uses strict loopback web binding and stops its owned backend on exit/signals. Explicit `npm run dev:isolated` selects existing synthetic in-memory provider and blanks SDK config. Regular dev keeps configured auth. Controlled child tests genuinely failed before correction and pass afterward; actual backend8127/frontend5199 started and later exited130 with owned-backend cleanup. Initial sandbox15s startup failure and Node-global TypeScript error are recorded in D099; existing Vite loadEnv fixed config compatibility without a dependency.

D100 fixes prepared integration-harness cleanup: two concurrent saved acknowledgements could be forgotten if A's safety assertion failed. Actual harness main under pure mocked orchestration reproduced zero cleanup calls. It now registers every known new id with its verified owner before assertions; wrong routing still fails, both exact id/owner cleanup calls occur. No real provider/model/RLS operation was exercised by this regression, and unacknowledged network uncertainty remains.

D101 fixes a measured mobile research bug. Built Chromium at390px measured document529px and grid wrappers505px, then failed the required assertion. The same one-column grid now has an explicit zero minimum; existing code-block scrolling contains long commands. Colors/fonts/spacing/structure/branding/assets/animations/navigation/login are preserved. This intentional CSS containment correction is recorded, not described as zero changed styles.

D102 fixes actual public contract descriptions: About claimed reviewer delivery/human handling of false positives although the app only returns recommendations, and historical0.15 metrics omitted same-test-split selection. Built About assertion failed before correction. Existing text/SVG labels now distinguish raw research details, separate limited support and no notification; historical figures stay unchanged and consumed test selection is disclosed. Actual Step10 `eval_urgency` uses `precision_recall_curve(y_test_bin, proba)`. Effective threshold is reported per analysis, not fabricated from historical page copy. SVG geometry/styles remain.

## Original case and connected architecture

`i wanna jump from 10th floor` still returns HTTP200/HIGH/self/current/not_stated/degraded. Actual raw primary stays Normal0.9502395987510681, urgency0.7847130134418575, threshold0.15. The existing main display reads Urgent support; raw Normal remains a research detail. Synthetic account read-back and reload preserve the authoritative result. No location/access/time/diagnosis/notification is inferred. Before UI showed Normal despite backend HIGH; preserved evidence is reports/browser-original-before.json. Current35-check browser result is reports/browser-acceptance-current.json.

Existing login -> trusted server verification/generation -> owner-scoped check-in/editor -> configured limit/authenticated byte-bounded API -> owner admission/rate -> independent raw safety -> optional guarded NLP/raw models -> fusion with semantic disabled -> schema1.0 -> bounded one-attempt acknowledged core save -> common validated support adapter -> recorded owner-scoped history. The launcher/preview route to this same local service. Public copy describes this contract rather than inventing reviewer delivery. Production semantic adapter is not invoked. No genuine conversation memory/durable queue/automatic notification exists.

## Commands and measured outcomes

| Command / layer | Actual outcome |
|---|---|
| `PYTHONPATH='Step 12 - Packaging/package:.' python3 -m pytest tests/test_project_verifier.py -q` |2 passed2.80s; old exit0 failure reproduced, unavailable observations rejected|
| same prefix `python3 -m pytest tests/test_dev_launcher.py -q` |2 passed1.06s; controlled child/health fixtures, not real network proof|
| same prefix `python3 -m pytest tests/test_isolated_harness_cleanup.py tests/test_project_verifier.py tests/test_dev_launcher.py -q` |5 passed4.19s; harness pure mocked orchestration; one existing TestClient warning|
| same prefix `python3 -m pytest tests -q`, approved outside sandbox |486 passed17.92s, one existing Starlette/httpx deprecation; real models/routes where specified, provider/inference overrides explicit. Earlier485 passed24.44s before D100|
| `python3 scripts/verify_project.py --report reports/program-offline-verification.json` |22 PASSED/0 FAILED/1 BLOCKED/3 NOT_APPLICABLE, exit0; local actual observations only|
| same plus `--api-url http://127.0.0.1:8127 --report reports/program-http-verification.json` |24 PASSED/0 FAILED/1 BLOCKED/2 NOT_APPLICABLE, exit0; public /live and /ready, not auth/provider proof|
| `API_PORT=8127 WEB_PORT=5199 DEV_STARTUP_TIMEOUT_SECONDS=30 npm run dev:isolated` |Actual loopback API ready + Vite5199/proxy; process exit130 and backend cleanup verified|
| `npm --prefix web run qa:contract` |55 checks/16 shared response states pass; actual modules, mocked SDK/fetch/storage|
| from web, synthetic QA config: `node scripts/authflow.mjs http://127.0.0.1:5199` |47/47 required browser checks, zero console errors; actual HTTP with synthetic GoTrue transport|
| same `node scripts/entryqa.mjs http://127.0.0.1:5199` |310/310 layout/render/keyboard/fallback/greeting checks across14 resolutions and WebGL/reduced-motion paths; existing design tested|
| same `node scripts/screenqa.mjs http://127.0.0.1:5199` |35/35, actual original+five controls, shared response overrides, history/timeout/cancel/accounts; provider STUB|
| same `node scripts/failure.mjs ...` and `node scripts/interaction.mjs ...` |Each exits0, screenshot/manual observation journeys; not counted as assertion suites. Unreachable API shows OFFLINE/error and unverifiable session redirects; check-in prefill/support/history observed|
| `VITE_SUPABASE_URL='' VITE_SUPABASE_PUBLISHABLE_KEY='' VITE_API_URL='/api' npm run build` |Latest193 modules/10.97s; tsc and Vite build pass, SDK-disabled isolated output|
| `VITE_DEV_PROXY_TARGET=http://127.0.0.1:8127 npm --prefix web run preview -- --host 127.0.0.1 --port 5200 --strictPort` |Built frontend preview; later process exit130 verified|
| from web `node scripts/publicqa.mjs http://127.0.0.1:5200` |12/12 grouped desktop/mobile route checks, no uncaught errors; required overflow/copy assertions failed before fixes. Source and built-asset hashes in reports/browser-built-routes.json; About screenshot inspected|
| `npm run typecheck`, `npm run lint`, `python3 scripts/generate_contract_types.py --check`, `git diff --check` |Passed; latest build also typechecks current JSX. No runtime dependency/model/schema change in this continuation|
| same PYTHONPATH `python3 scripts/run_safety_corpus.py --layer both` |Current-source repeat exits1, engine259/321/full pipeline214/321. reports/safety-run-20261009T041432Z.json; preserved consumed regression, no tuning/new independent claim|
| `python3 scripts/verify_supabase_isolated.py --check-config` |exit2 BLOCKED, missing isolated project/pre-provisioned identity variable names only; no network|

Synthetic browser config `/tmp/mental-ai-qa-config` contained only Alice fixture values from tests/_supabase_stub.py. No repository credentials/accounts were used. Those manual scripts are deliberately distinguished from required assertion suites. No sample counts are combined into a safety score.

Current default corpus preserves62 temporal errors and107 pipeline required failures. Urgent98/98 routed urgently; benign urgent escalation0/73; subject0/238 asserted with83 opt-outs. Pipeline benign14/73 NONE,37/73 clarification,22/73 UNKNOWN; all44/321 UNKNOWN and61/321 clarification. The previously executed separate developer temporal proposal run remains321/321 engine/252/321 pipeline with69 disagreements; it was not rerun here or merged with default. Exact IDs remain in checkpoint/handoff. Old consumed holdouts25/35 and15/30 represent different stages. Local semantic candidate remains disabled after consumed C13/18 labels,5/6 urgent and1/6 benign urgent escalation. None supplies independent clinical validity or independent binomial confidence intervals.

## Fingerprints, files, ownership and limits

Remote https://github.com/shreshthgod/mental.ai.git, branch main, HEAD2053855d51aaa5c9e06bd8c30f1c35d45c64716b. Dirty source/config/corpus fingerprint `30d6523f8776b689e2d75ca5b54324e9420145afd261e4964a9f07ccad1ded06`. Scope now includes root package.json/start-dev.sh under D099; older hashes retain older scope. ConfigSHA256 `0e90561f45eb47079b53647199d5c11369d7dfb66d4d49e42654d925b8b7f64e`; policy safety-policy-2026.10.09.6; response1.0. Model/artifact hashes unchanged, complete manifest and actual versions in reports/recovery-final-checkpoint.json. Source fingerprint excludes reports/docs/env/raw sensitive datasets; documentation hashes recorded separately. Historical reports/experiments/corpus cases were preserved; new repeats are separate files.

Newly changed meaningful files are scripts/verify_project.py/source_fingerprint.py/verify_supabase_isolated.py, start-dev.sh, root package.json, web/vite.config.ts, three focused Python test modules, web/scripts/publicqa.mjs, research.css and the five public content files named D102. Decisions/flow/matrix/defect/README/Supabase/handoff/report/checkpoints updated. Unrelated dirty entry/login styles and components remain untouched. Expanded40 component/style/App/main/Vite paths compared: four intentional text files, one research containment property and one proxy config changed;34 match baseline bytes. Research.tsx has intentional copy changes separately. No colors/fonts/assets/animation/SVG geometry/nav/login changes introduced.

No staged paths, commits, pushes, migrations, deployment, collaborator/account/email actions or real-user testing. Repository-local publication identity/email association remains unverified; no identity was set or used. Ownership remains shreshthgod/mental.ai; excluded paper/research/.tex paths were not staged. Preview/backend stopped. Privileged-key bundle scan remains part of final checkpoint and prints no values.

Real isolated provider/RLS/schema/refresh/SDK/network needs an isolated configured project, applied test migration and two pre-provisioned identities/expectedids, genuine expired token and controlled faults. Docker/platform/project/deployed/shared-ingress tooling/access and reviewed semantic/policy/language/final-data/licensing evidence are missing. Local tests do not establish those. Historical training was not rerun; packaged artifacts are the shipped application. Arbitrary language/semantic understanding, clinical calibration, deployed load and genuine memory remain unsupported/unverified.

Next concrete independent work is the real isolated harness once those secure external inputs exist: `python3 scripts/verify_supabase_isolated.py --check-config`, then the opt-in command documented in docs/SUPABASE.md. Independent reviewed evaluation must precede semantic enabling/release; do not deploy automatically or change correct labels/expand phrases to manufacture success.
