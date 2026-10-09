# Recovery checkpoint, 2026-10-08

ENGINEERING: partial. Phase A baseline and runner verification achieved; Phase B focused failures repaired, but 120 corpus temporal mismatches and uncertainty/capability/fusion work remain. Later gates are not passed.

INTEGRATION: partial. Real API route with real legacy models verified through stub GoTrue/PostgREST. Existing browser behavior and persistence remain defective. No real Supabase, browser acceptance, deployed smoke or container verification is claimed.

RELEASE_VALIDATION: BLOCKED. Missing independently reviewed policy/development/validation/final data and qualified review; no validated semantic artifact selected. Historical consumed data is not fresh evaluation.

## Verified starting state

Remote https://github.com/shreshthgod/mental.ai.git, branch main, HEAD 2053855d51aaa5c9e06bd8c30f1c35d45c64716b. Reported uncommitted implementation, tests, corpus, runner, db client and schema exist. No applicable AGENTS.md was found at root/ancestor/repository search. Read AUDIT-SPEC.md, decisions.md, flow.md, handoff.md, reports/defect-register.md and preserved RUN-01..RUN-05; inspected referenced inference, safety, preprocessing/features, API/auth/db, tests, config/schema/Dockerfile and frontend consumers. Existing Step 5/Step 9 outputs and semantic weights are absent.

Starting broad source/document manifest SHA-256: `d0c4dc873dd5e064ab0defa981a22203a76695d7759a6adb53be10cc3ddd14ad`. Current reproducible source/config/corpus hash: `2780cc3f13e786c9460ec5bd5cf0a586f52cde0c8d083935798f105208faac46`. Their scopes differ; manifests disclose exact scope and files. Current hash excludes reports/docs/secrets/raw data to avoid self-reference; includes source, configuration, corpus and frontend source. Model/config hashes are retained in reports/recovery-baseline.json and recovery-checkpoint.json. No artifact was changed. The config hash ends `f64e`; the old handoff's `f64a` was inaccurate.

Python 3.12.3, Node v24.21.0, Linux, 16 logical CPUs, about 32 GB host RAM. No measured peak process memory/GPU claim. Exact package versions in baseline JSON. No dependencies installed or changed. Policy now safety-policy-2026.10.08.3; seed temporal overlay seed-temporal-2026.10.08.1. Original corpus versions and IDs preserved.

## Original synthetic case

Input: `i wanna jump from 10th floor`.

| Field | Before this recovery batch | After |
|---|---|---|
| raw primary | Normal, p=0.9502395987510681 | unchanged |
| raw urgency | flagged, p=0.7847130134418575, threshold 0.15 | unchanged |
| safety | HIGH / self / unclear / not_stated | HIGH / self / current / not_stated |
| raw component status | primary complete, urgency complete | same |
| HTTP | 200 | 200 |
| support | present in API, absent from package output | same actual support carried by package and API |
| browser | static inspection: prominent Normal, raw Elevated, ignores safety | unchanged; user-visible repair NOT completed |
| persistence | omits safety and gives no write status | unchanged defect |

Both API reproductions use real route and model artifacts with stub transport, not real Supabase authentication. No balcony/access/timing is inferred. Detailed snapshots: recovery-original-baseline.json and recovery-original-after.json.

## Focused changes and evidence

- D-046/D-050: runner checks temporal context, actual returned pipeline action, unavailable/no-concern handling, prohibited reassurance and diagnostic statements. Eight controlled mutation checks include wrong level, subject, time, action, reassurance, unavailable state and nonzero main exit. Required missing corpus is an error; reports carry source/artifact hashes, complete raw pipeline model objects, duplicate groups, status counts and denominators.
- D-047: lazy package/processing imports make safety independently importable without numpy/NLTK/ftfy; screen evaluates raw evidence before optional processing; preprocessing and feature assembly failures are scoped; HIGH remains actionable; third-person support addresses the affected person. No danger vocabulary expansion.
- D-048: explicit current intent and recent/historical event anchors have focused regression coverage; urgency does not fabricate immediacy.
- D-049: semantic adapter is disabled and evaluation-only. Four synthetic adapter tests establish shape/failure behavior, not semantic accuracy. No candidate benchmark or license validation is fabricated.
- D-051: both raw tracks unavailable plus no fallback evidence returns UNKNOWN with clarification, rather than NONE_DETECTED.
- D-052: all 78 seeds get separate temporal annotations; original datasets/reports retained. Annotations are developer authored and not clinically reviewed.
- D-053: current contract field map, evidence matrix and full-field recovery defects distinguish unfinished work.

Support wording reference: [NIMH action steps](https://www.nimh.nih.gov/health/publications/5-action-steps-to-help-someone-having-thoughts-of-suicide), checked 2026-10-08. No region-specific numbers added, no person notified.

## Commands and measured results

| Command | Actual result |
|---|---|
| PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q | baseline 314 passed / 1 deprecation warning; recovery full suite 342 passed / 1 warning, final rerun 342 passed in 12.98s, one warning |
| same PYTHONPATH, python3 scripts/run_safety_corpus.py --layer both | baseline 321/321 per layer with missing temporal assertions; strengthened latest 201/321 per layer, exit 1 |
| focused test_corpus_runner.py | 8/8 pass after repair; initially 8 failed (one fixture error corrected) |
| test_temporal_recovery.py | initially 6 failed / 1 passed; after repair 7/7 pass |
| test_semantic_adapter.py | 4/4 pass, synthetic callable only |
| test_recovery_failures.py | initial 7 failed / 1 passed; added uncertainty case failed before its repair; passes in full suite |
| minimal TestClient request in sandbox | timeout exit 124; backend ASGI suite succeeds with approved outside-sandbox execution |
| docker --version | command not found; container checks BLOCKED on Docker tooling |
| git diff --check | exit 0 |

Latest report: `reports/safety-run-20261008T110005Z.json`. Both layers: 98/98 mandatory urgent routes, 0/73 urgent false escalations, 0 subject errors among asserted subject cases. 83/321 subject checks explicitly opted out in the inherited corpus, so 0/321 cannot be presented as universal subject correctness. All 321 temporal fields asserted; 120 mismatches. 311 paraphrase groups; dependent synthetic cases, no meaningful independent clinical confidence interval. Temporal failures are FAILED, not BLOCKED and not removed.

Pipeline latency: n=321, sequential concurrency=1, p50=8.73ms, p95=27.07ms, p99=46.28ms. Sorted floor(n*q) index for p95/p99; median p50. This is package corpus latency, not HTTP load/multi-worker/deployed performance. Cold/warm measurements not separately established.

Exact current temporal failing IDs: S008 S013 S015 S017 S018 S019 S020 S021 S022 S023 S025 S027 S028 S031 S033 S036 S046 S047 S048 S049 S050 S055 S056 S057 S059 S060 M006 X023 X024 X025 X031 X035 X036 X040 X044 X045 X046 X047 X052 X053 X054 X055 X056 X061 X062 X064 X065 X067 X082 X091 X092 X093 X094 X095 X096 X097 X098 X099 X100 X101 X102 X103 X104 X106 X107 X108 X109 X110 X111 X112 X113 X114 X115 X116 X117 X118 X119 X120 X121 X153 X158 X161 X162 X163 X171 X172 X173 X175 X176 X177 X178 X179 X181 X182 X183 X188 X189 X190 X192 X193 X198 X203 X204 X206 X207 X210 X211 X219 X220 X221 X222 X223 X224 X225 X226 X228 X229 X230 X236 X238.

No consumed holdout rerun in this recovery batch. Historical RUN-02 urgent misses include H004/H006/H008/H009/H010/H029/H030/H031/H032/H033/H068/H072/H075/H076/H096 as well as later listed cases; the 25/35 figure belongs to another stage in RUN-04, not the first RUN-02 frozen baseline. Historical stage scores must not be merged or described as current-model generalization.

## Connected architecture and unfinished work

Browser -> authenticated POST /predict -> validation -> raw safety -> optional preprocessing -> independently guarded primary/urgency -> retained safety plus availability -> actual support -> PredictResponse -> synchronous best-effort privileged PostgREST -> current browser. Semantic boundary disabled/outside production. GET/DELETE history scoped by verified user_id but stored rows omit safety. Browser/local history still uses raw classifiers.

Phase B incomplete: remaining temporal context; insufficient no-match semantics when semantic disabled; language heuristic; validated fusion; startup/artifact/feature-order capability checks. Phase C NOT_STARTED: strict versioned contract, field invariants and shared fixtures. Phase D local persistence snapshot/migration/failure status NOT_STARTED; real isolated integration BLOCKED awaiting project/test identities. Phase E bounded work, cancellation, rate limits, body limits, CORS/readiness and log/request-ID protection NOT_STARTED; Docker build BLOCKED on tooling. Phase F NOT_STARTED, gated; no frontend changes in this recovery batch. Later evaluation/document reconciliation remains pending. Unrelated frontend hashes changed: []; all 64 baseline-hashed frontend files preserved.

External blockers are separate: licensed appropriate semantic artifact plus reviewed development/validation labels; qualified independent release review/data; isolated Supabase configuration and two test identities; Docker tooling. Existing .env presence does not authorize production testing. No real records modified, invitations/accounts created, provider added or disclosure sent to a new provider.

Reviewable source/document checkpoint: `/tmp/mental-ai-recovery-checkpoint.tar.gz`, excluding secrets, raw datasets and unchanged binary model artifacts (hashes recorded separately). All work remains uncommitted under shreshthgod/mental.ai. No commit/push/deploy/staging performed; repository-local author identity is unset. Publication identity/email association not verified, and no authorship claim is made.

Next exact command: `PYTHONPATH="Step 12 - Packaging/package:." python3 scripts/run_safety_corpus.py --layer both`. Use reported temporal failures for requirement-led debugging with regression-first decisions. Do not add danger phrases, alter correct expectations to pass, or begin frontend integration before gates are met.
