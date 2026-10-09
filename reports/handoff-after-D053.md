# Recovery handoff, 2026-10-08

## 1. Current Phase

Phase B recovery, partial. Phase A baseline/runner gate achieved; engineering routing gate not passed. ENGINEERING partial; INTEGRATION partial; RELEASE_VALIDATION BLOCKED.

## 2. Work Completed

D-046..D-053: verified dirty baseline, strengthened runner with controlled mutations, raw safety before optional processing, third-person support, focused temporal corrections, honest failure abstention, disabled semantic boundary, separate seed temporal overlay and evidence documentation. No danger vocabulary expansion.

## 3. Files Changed

See reports/recovery-report.md and reports/recovery-checkpoint.json manifest. Production edits: package __init__.py/inference.py/safety.py and api/api.py; runner/fingerprint scripts; four focused test modules; temporal overlay; docs and reports. Earlier frontend changes preserved.

## 4. Current Architecture / State

Raw safety now precedes optional lossy processing; support text travels from screen to API. Legacy model values unchanged. Semantic adapter disabled/outside production. API still blocks async runtime with synchronous inference/storage; persistence and browser omit authoritative safety. Policy safety-policy-2026.10.08.3. Corpus seed/expansion versions unchanged; seed-temporal-2026.10.08.1 overlay.

## 5. Decisions Made

Appended D-046..D-053. Preserve D-001 until evidence-based fusion supersedes it. D-007 readiness and D-042 frontend boundary not superseded. D-039/D-040 consumed/leakage warnings retained. Prior D-045 documentation gaps not retrospectively claimed fixed.

## 6. Requirements and Constraints

Backend first; no frontend design/integration edit, deployment, real-user testing, accounts, collaborators or commits. All source under shreshthgod/mental.ai. Synthetic annotations not clinically reviewed. Requirements matrix reports FAILED/NOT_STARTED work honestly.

## 7. Testing and Verification

Baseline 314 pytest passes. Latest full recovery suite 342 passed in 12.98s, one deprecation warning; approved outside-sandbox execution required because minimal TestClient stalls in sandbox. Corpus command PYTHONPATH="Step 12 - Packaging/package:." python3 scripts/run_safety_corpus.py --layer both: latest reports/safety-run-20261008T110005Z.json, exit 1, 201/321 per layer, 98/98 urgent, 0/73 urgent false escalations, 120 temporal mismatches. 83 subject opt-outs. Actual raw model inference and real API route; Supabase transport stubbed. No real integration/browser/container/deployed/load/clinical verification. Exact commands and latency method in recovery-report.md.

## 8. Known Issues / Risks

Confirmed: temporal failures; no validated semantic fusion/capability; function-word language heuristic; safety not persisted; raw Normal still prominent; missing persistence status; synchronous async route; unvalidated request ID; fixed Field length cap; readiness probe accepts failed optional tracks; no predict rate limiter. Docker command absent. No generalization/clinical claim.

## 9. Unfinished Work

Exact temporal failures: S008 S013 S015 S017 S018 S019 S020 S021 S022 S023 S025 S027 S028 S031 S033 S036 S046 S047 S048 S049 S050 S055 S056 S057 S059 S060 M006 X023 X024 X025 X031 X035 X036 X040 X044 X045 X046 X047 X052 X053 X054 X055 X056 X061 X062 X064 X065 X067 X082 X091 X092 X093 X094 X095 X096 X097 X098 X099 X100 X101 X102 X103 X104 X106 X107 X108 X109 X110 X111 X112 X113 X114 X115 X116 X117 X118 X119 X120 X121 X153 X158 X161 X162 X163 X171 X172 X173 X175 X176 X177 X178 X179 X181 X182 X183 X188 X189 X190 X192 X193 X198 X203 X204 X206 X207 X210 X211 X219 X220 X221 X222 X223 X224 X225 X226 X228 X229 X230 X236 X238. See requirements-evidence.md for independent pending contract/persistence/runtime/frontend/evaluation work. Those local tasks are not falsely marked BLOCKED. External blockers: suitable licensed semantic artifact/reviewed development labels and independent release policy/data review; isolated Supabase/test identities; Docker tooling.

## 10. Next Subphase

Continue Phase B, reproduce individual temporal/context/failure defects and write focused regressions. Next exact command: PYTHONPATH="Step 12 - Packaging/package:." python3 scripts/run_safety_corpus.py --layer both. Do not start Phase F before prior engineering gates pass or genuine external blockers are recorded.

## 11. Critical Context

HEAD 2053855d51aaa5c9e06bd8c30f1c35d45c64716b, main, remote https://github.com/shreshthgod/mental.ai.git. Starting manifest d0c4dc873dd5e064ab0defa981a22203a76695d7759a6adb53be10cc3ddd14ad; current source/config/corpus 2780cc3f13e786c9460ec5bd5cf0a586f52cde0c8d083935798f105208faac46, exact scope/manifest/model hashes in recovery-checkpoint.json. Existing dirty implementation present. Do not reset/clean/discard. No commit/push/staging/deploy; repository-local identity unset. .env never printed or archived. Earlier handoff preserved in reports/handoff-pre-recovery.md. Historical config hash typo corrected by actual measured hash; no model changed.

## 12. Agent Instructions

Read documents and matrix first. Preserve all historical corpora/reports and earlier frontend changes. No holdout tuning or danger-vocabulary expansion. Do not use 342 unit passes to hide the failing corpus. No validated semantic performance inferred from adapter tests. Use approved outside-sandbox pytest command for ASGI tests; keep Supabase stub explicit. Do not publish or modify real records without authorization. Update decisions/flow alongside focused fixes; retain exact evidence and failing IDs.
