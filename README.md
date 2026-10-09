# MENTAL.AI

Existing research application with authenticated text screening, limited support routing, raw classifier details and account/device history. This system is not a diagnosis or confirmation of safety. The local engineering and existing-app integration have been repaired; independent release validation and real-provider/deployment verification remain incomplete. See `reports/recovery-final-report.md`, `reports/requirements-evidence.md` and `handoff.md` for measured evidence and blockers. Historical README claims are preserved in `reports/readme-before-final-reconciliation.md`, not treated as rerun results.

## Current connected behavior

The existing login/navigation/layout lead to a four-question check-in. Its ordered original answers prefill one editable text field; nothing is analyzed automatically and there is no conversation memory. Authenticated submissions run independent raw-text safety before optional NLP/raw models, then fuse evidence under declared limited capability. Schema1.0 validates the result before bounded account saving. The existing Screen headline and guidance use safety; raw primary and urgency remain unchanged research details. Device history/check-in are scoped to the adopted account. Server history preserves the authoritative snapshot; old rows without snapshots are legacy/unassessed. Save failures remain visible and do not erase support.

For `i wanna jump from 10th floor`, actual primary remains Normal at0.9502395987510681 and urgency0.7847130134418575; final HIGH/self/current with immediacy not_stated. The main browser headline is Urgent support. No balcony, access, timing, diagnosis or notification is inferred. Semantic assessment is disabled; most supported results are degraded and no-match inputs may require clarification or return UNKNOWN. Regional resources are not guessed from language.

## Local setup

Python3.12 was exercised locally. Install the existing ML/runtime requirements and prepare NLTK resources before serving:

```bash
python3 -m pip install -r 'Step 12 - Packaging/package/requirements.txt' -r api/requirements-runtime.txt
python3 scripts/prepare_runtime_resources.py --output nltk_data
npm install
```

The resource installer uses private home staging because NLTK rejects untrusted writable download ancestors. No request downloads resources/packages. Configure backend variable names from `.env.example` securely; never publish env files. Backend Supabase requires URL, publishable and server-only secret key. Browser configuration uses only VITE_SUPABASE_URL/VITE_SUPABASE_PUBLISHABLE_KEY and optional VITE_API_URL. Read `docs/SUPABASE.md` before applying any schema/migration. Existing valid data must be preserved.

```bash
npm run dev
```

The existing development arrangement serves Vite5173 and API8000; Vite proxies `/api` to unprefixed local routes. The prepared hosting wrapper `main:app` mounts the same API at `/api`. Docker/Vercel/deployed builds have not been verified here and no deployment occurred.

The launcher validates ports and waits for `/ready` with `ready=true`; `/health` HTTP200 alone is insufficient. `API_PORT` and `WEB_PORT` overrides connect the same proxy, and an occupied web port fails instead of silently moving. `DEV_STARTUP_TIMEOUT_SECONDS` defaults60 (1..300); `DEV_BACKEND_LOG` optionally selects the local log. Exiting stops the launcher-owned backend.

For actual local app/model checks with synthetic identities and in-memory provider only:

```bash
npm run dev:isolated
```

This explicitly selects the loopback-only synthetic server and blanks browser SDK configuration. Regular `npm run dev` retains configured real authentication. No real-provider/RLS verification is implied.

## Verification

```bash
PYTHONPATH='Step 12 - Packaging/package:.' python3 -m pytest tests -q
PYTHONPATH='Step 12 - Packaging/package:.' python3 scripts/run_safety_corpus.py --layer both
PYTHONPATH='Step 12 - Packaging/package:.' python3 scripts/run_safety_corpus.py --layer both --temporal-review
python3 scripts/generate_contract_types.py --check
npm --prefix web run qa:contract
npm run typecheck
npm run lint
npm run build
python3 scripts/verify_project.py --report reports/program-offline-verification.json
```

The unchanged default corpus still exits1: temporal annotation conflicts and conservative uncertainty/routing disagreements remain. The separate proposed temporal review is diagnostic developer annotation, not an independently reviewed evaluation. Do not tune from consumed holdouts or relabel correct expectations to get a passing score. See `docs/EVALUATION-COVERAGE.md`.

For isolated browser acceptance, in separate local terminals:

```bash
PYTHONPATH='Step 12 - Packaging/package:.' python3 tests/serve_synthetic_api.py --isolated-development
cd web
VITE_SUPABASE_URL='' VITE_SUPABASE_PUBLISHABLE_KEY='' VITE_API_URL='/api' npm run dev -- --host 127.0.0.1 --strictPort
node scripts/screenqa.mjs
```

This helper serves actual routes/models on loopback with an in-memory provider STUB and synthetic identities, never real accounts. Failure responses are explicitly shared-fixture overrides. Chromium is required; the installed helper can use an existing compatible cache. Reports identify mocked versus actual layers. Avoid running other QA scripts against real accounts without an explicitly isolated environment.

`npm run verify` performs offline dependency/resource/configured-artifact and actual original-case observations, returns nonzero for required failures, and reports independent validation BLOCKED. It does not retrain historical experiments, authenticate, download or write to a provider. Opt-in `--api-url http://127.0.0.1:8000` also checks public liveness/readiness.

Broader isolated browser checks executed in the latest program audit include authflow47/47, entryqa310/310 and screenqa35/35, plus manual interaction/failure screenshot journeys (exit0, not counted as assertion suites). See reports/program-audit-report.md for exact synthetic environment and scope. Built public-route QA uses `web/scripts/publicqa.mjs` against an isolated Vite preview; SDK config must be blank during that build too. Existing visual design is preserved; the precise containment/copy corrections are recorded below.

The public-route audit additionally corrected mobile research intrinsic-width containment while preserving its one-column arrangement, plus misleading public reviewer/threshold copy. Colors/fonts/assets/animations/navigation/login and SVG geometry are unchanged. One research CSS minimum and five public content files intentionally changed; see D101/D102 instead of interpreting preservation as zero content changes. Built-route result12/12 is scoped engineering evidence.

## Authentication, storage and operations

FastAPI delegates bearer verification to Supabase GoTrue on every private request; it does not sign application HMAC tokens. Login/refresh/session/history/deletion keep trusted identity and explicit owner filters. Secret keys bypass RLS, so application scoping remains required. New non-JWT application keys travel in apikey; actual user JWTs identify the account separately. Real RLS/grants/network behavior is not established by stubs.

Prediction and saving each have a serial worker with8 admitted jobs, caller deadlines30s and12s. Late synchronous work retains capacity until completion; cancellation does not forcibly stop it. Provider network timeout defaults10s, validated up to30s. Same-host SQLite prediction limits are30 requests/60s per verified owner; separate replicas require shared ingress limits. Login's existing IP limiter is per process. Character cap defaults10000 (validated1000..100000), HTTP bytes12*cap+4096; `/configuration` is the consumer source. `/live` is cheap; `/ready` uses a bounded ten-second freshness probe and publishes degradation. `/health` also reports artifact state. No promised reviewer workflow or durable asynchronous saving exists.

The additive snapshot migration is prepared, not remotely applied. Bounded synchronous saving reports saved only with returned row id, not_saved on rejection/unadmitted work, unconfirmed on uncertain writes/deadlines. No automatic write retry. Historical research scripts, artifacts, original corpus identities and execution reports are preserved. Model probabilities are proxy-label classifier values, not calibrated clinical probabilities. True multi-turn memory, reliable unrestricted language comprehension, clinical generalization, deployed performance and independent release validation are unsupported/unverified.

Supabase/login continuation: Google preference/callback/provider errors and QA diagnostic privacy corrected under D104–D107, with24 module,13 dev/13 compiled SDK,47 email and35 screen browser checks. D108–D109 now install supplied project locally and verify public settings/health/configured UI; intended email/confirmation and Google provider setup remain blocked. Normal preview http://127.0.0.1:5199/login; no hosted deployment change. See reports/supabase-live-config-report.md for current evidence. See [setup and boundaries](docs/SUPABASE.md) and [actual results](reports/auth-integration-report.md).

D110–D112 install the requested root `@supabase/server`1.9.1 and backend-only JWKS variable. Run `npm run verify:supabase-sdk` after configuring ignored `.env`; it validates actual SDK imports/environment resolution without logging values or making network/account requests. Python authentication remains GoTrue verification. Latest isolated backend486/486, contract55 checks/16states and OAuth24 groups pass; public JWKS200 is metadata, not authenticated integration. See [SDK verification](reports/supabase-server-sdk-report.md) and [owner publication checkpoint](reports/github-publication.json). Credentials must be configured separately in the hosting environment and remain excluded from Git.
