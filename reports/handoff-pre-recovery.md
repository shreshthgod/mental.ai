# Handoff: MENTAL.AI backend audit, 2026-10-08

## 1. Current Phase

- **Phase**: Phase F (handoff), completing Phase A–E.
- **Subphase**: none; the session is at its end.
- **Objective**: establish a tested backend safety contract for
  `i wanna jump from 10th floor`, repair confirmed defects, and report measured
  limits honestly.
- **Status**: **partial**.
  - Backend engineering work complete within its stated scope.
  - **Product release BLOCKED.** The generalization measurement (section 7) shows
    the routing layer misses a large share of high-risk phrasings it has not
    been shown. The frontend also cannot display the authoritative result yet
    (section 9).

## 2. Work Completed

**Reproduced the reported failure at both layers.** At package and authenticated
API layer, `primary.predicted_class == "Normal"` at p=0.950 while
`urgency.flagged == True` at p=0.785 (threshold 0.15). The safety layer now
returns `HIGH`.

**Found that the existing 78-case corpus was not testing the shipped path.**
`scripts/run_safety_corpus.py` hardcoded `urgency_flagged=False`, so it exercised
a code path the service never takes. Engine-only reported 78/78; the real
pipeline reported 66/78, failing on every benign control the classifier fires on.

**Why this mattered, non-obvious**: a green suite was hiding a false-positive
storm. Every repair below was written as a failing test first.

**Repaired 35 numbered defects** (`reports/defect-register.md`, `decisions.md`
D-001..D-042). Highest-impact: the model flag no longer routes (D-001); an
impossible probability of 5.0 is no longer published (D-026); "Ich möchte heute
sterben" no longer returns NONE_DETECTED (D-011); whitespace-only input is a 422
not a 500 (D-005); a Supabase outage is a 503 not a 500 (D-006b); `/health` and
`/ready` verify rather than assert (D-007); advertised env settings are honoured
(D-008).

**Grew the corpus from 78 to 321 regression cases** across 42 families, then
built **two sealed holdouts** (96 and 83 cases) and ran each once.

**What I found that is worse than the original bug**: on genuinely unseen
phrasings, the rule layer routes only 25/35 urgent cases correctly on holdout-1
and 15/30 on holdout-2. See section 7.

## 3. Files Changed

| Path | What changed | Why it matters |
|---|---|---|
| `Step 12 - Packaging/package/mental_health_screening/safety.py` | Policy engine: model-flag demotion, vocabulary/context repairs, language check, negation scope, fiction priority, location guard, typo/leet normalization, probability-independent | The authoritative routing layer |
| `Step 12 - Packaging/package/mental_health_screening/inference.py` | `None` for a failed urgency track; probability range validation; `URGENCY_THRESHOLD` honoured; `max_text_length` parameter | Honest model reporting; operable threshold |
| `api/api.py` | Whitespace 422; Supabase outage 503; `/health` and `/ready` verification; `MAX_TEXT_LENGTH` honoured; `db.SupabaseError` handled | Contract correctness |
| `.env.example` | Documents the now-enforced bounds for both settings | Removes the advertised-but-dead setting |
| `scripts/run_safety_corpus.py` | Two layers; exact subject assertion; real prohibited checks; coverage + metrics; `--include-holdout` | The suite can now fail |
| `scripts/generate_corpus_expansion.py` | New. Authors 243 cases from the oracle | Coverage without expectation drift |
| `scripts/build_holdout.py`, `scripts/build_holdout2.py` | New. Sealed evaluation corpora | Unbiased estimate |
| `tests/safety_corpus/expansion.json` | New. 243 cases | Regression coverage |
| `tests/safety_corpus/holdout.json`, `holdout2.json` | New. 96 + 83 cases | Evaluation only |
| `tests/test_safety_contract.py` | New. 75 tests | Policy regressions |
| `tests/test_api_contract.py`, `tests/_supabase_stub.py` | New. 125 tests | API/security/failure contract |
| `tests/test_metamorphic.py` | New. 33 tests | Metamorphic relations and fault injection |
| `tests/test_safety.py` | Two expectations corrected (D-002, D-003) | They encoded the old behaviour |
| `decisions.md`, `flow.md`, `handoff.md`, `reports/defect-register.md` | Documentation | Rule 9 |

## 4. Current Architecture / State

`POST /predict` → `require_session()` → `PredictRequest` validation →
`MentalHealthScreener.screen()` → independent primary and urgency model tracks
(non-fatal, `unavailable` on fault) → `safety.evaluate()` on a minimally
normalized copy of the **raw** text → `PredictResponse` carrying an
authoritative `safety` object beside honest `primary` and `urgency` objects →
best-effort persistence to Supabase.

Runtime state: `safety-policy-2026.10.08.2`, corpus
`safety-corpus-2026.10.08.1` + `safety-corpus-2026.10.08.2-expansion`, holdouts
`safety-holdout-2026.10.08.1` and `.2`.

Artifact SHA-256 (unchanged this session):

```
0e90561f45eb47079b53647199d5c11369d7dfb66d4d49e42654d925b8b7f64a  config.json
c7c168043c227b641b6254878851451b646845366562592fd50cb6ac5f5271b4  curated_urgency_keywords.json
dc42e67e9cc60e177a8cd08f0766feb08fcb021a8e306ad44bd38f4c01bc05a0  emotion_lexicon.json
58e17570b99117b4edbe8b7d872c9068883699e2ca778ddf6d318f08555c398e  primary_chi2_selector.pkl
29b00aaa4186642134818bbb4d7590097ee82b9dead4f58c394a805364140f1d  primary_tfidf_vectorizer.pkl
4c9d64d1aae41aced3dce83db3325c6d7f7952446edf8836412417b6842b6fdd  primary_xgboost.pkl
1c9536d756320a86fec3c7818f654d68af27e1c82fd3dad140e207f5ef503b15  urgency_logreg.pkl
8a0e2f35067c8b867c7b771ebcfe9672332e9c5afc9060e2353bdcd985d03509  urgency_tfidf_vectorizer.pkl
```

Runtime class and feature order, measured: urgency classes
`['non-suicide','suicide']` (suicide index 1); label encoder
`['Anxiety','Bipolar','Depression','Normal','Personality disorder','Stress','Suicidal']`;
38 handcrafted features in config order; primary width 1538 = 1500 chi2 + 38;
urgency vectorizer 30000-dim; deployed threshold 0.15.

## 5. Decisions Made

D-001 … D-042 in `decisions.md`; every ID is anchored there. The ones a later
session must not undo by accident: **D-001** (model flag is evidence only),
**D-003** (`immediacy` enum), **D-026** (probability range), **D-036** (the runner
must execute the shipped layer), **D-040** (holdouts run once, reported as found),
**D-042** (frontend untouched).

## 6. Requirements and Constraints

- Backend-first. No frontend file was changed (D-042).
- No test-set tuning; the historical test-split threshold sweep stays historical
  (D-039).
- Raw model outputs are preserved and never rewritten; the safety decision is
  separate.
- No credential, real disclosure or model-attribution trailer appears in any
  file. `.env` is gitignored and was read only for presence, never printed.
- Synthetic data only. The corpora are generated, self-authored, and marked not
  clinically reviewed.
- No commit was authorized, so no commit was created. Everything is uncommitted.

## 7. Testing and Verification

Commands run, with actual results:

| Command | Result |
|---|---|
| `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q` | **314 passed**, 1 warning, 9.3s |
| `… python3 scripts/run_safety_corpus.py --layer both` | **321/321**, engine and pipeline; 0 missed urgent; 0 benign FP; latency p50 5.9 / p95 21.5 / p99 30.3 ms, n=321 |
| `… python3 scripts/run_safety_corpus.py --layer engine --include-holdout` | 421/500 including holdouts |
| `python3 scripts/generate_corpus_expansion.py` | 243 cases, 315 distinct normalised inputs |
| `python3 scripts/build_holdout.py` / `build_holdout2.py` | 96 and 83 sealed cases |

Test counts: `test_service.py` 45, `test_safety_contract.py` 75,
`test_api_contract.py` 125, `test_safety.py` 36, `test_metamorphic.py` 33.

### Measured results, by corpus role: this is the important table

| Corpus | n | pass | urgent cases | urgent routed urgent | benign controls | benign FP |
|---|---|---|---|---|---|---|
| Seeds (mandatory, Part 5) | 78 | 78 | 34 | **34/34** | 12 | **0** |
| Expansion (regression) | 243 | 243 | 64 | **64/64** | 61 | **0** |
| Holdout-1 (consumed) | 96 | 55 | 35 | **25/35** | 33 | 1 |
| Holdout-2 (post-fix eval) | 83 | 45 | 30 | **15/30** | 25 | 0 |

Level distribution over all 500: HIGH 146, IMMEDIATE 26, CONCERNING 74,
NEEDS_CLARIFICATION 18, NONE_DETECTED 220, UNKNOWN 16.
Language: en 452, hinglish 20, hi 15, other 13.

**How to read this.** The 0% miss rate on seeds and expansion is *not* a
generalization estimate: both were used while repairing the engine. The
holdouts are the only unbiased numbers available: **29% and 50% of urgent cases
missed on unseen phrasings.** Concrete examples that still return NONE_DETECTED:
"I have resolved to put an end to this", "There is an easy way out and I am going
to use it", "I am perched on the parapet outside", "I swallowed a handful of
tablets half an hour ago", "My partner has me cornered and I am terrified".

### NOT tested / not claimed

- No deployed smoke test. All API testing is ASGI `TestClient` over the real app
  with **Supabase stubbed** (`tests/_supabase_stub.py`). It proves our routing,
  validation, auth and failure behaviour; it proves nothing about Supabase.
- No clinician or expert review. All labels are generated and marked
  `generated_not_clinically_reviewed`.
- No calibration, and no probability is a clinical risk probability.
- `eval_urgency()`'s historical macro-F1 is not re-presented (D-039).
- Single machine, single process, 321 sequential requests. No multi-worker,
  load, or timeout-rate measurement. The p99 is dominated by a ~3.2s first-call
  cold start.
- Docker build not executed here; NLTK downloads in the Dockerfile are unverified
  in this environment.

## 8. Known Issues / Risks

**Confirmed, measured:**

1. **Generalization (highest).** 29–50% of urgent holdout cases are missed.
   Cause: the layer is a documented rule set over surface features, so it
   generalises only within the phrasings it was written for. This is a design
   limit, not a bug, and it is the reason product release is blocked.
2. **Latin-script non-English is imperfect.** "Ich will heute nicht mehr
   weiterleben" contains the English function word "will" and passes the
   function-word check, returning NONE_DETECTED (holdout-2 K064).
3. **The urgency classifier over-fires**: 67 of 78 seed cases at threshold
   0.15. It is no longer allowed to route (D-001) but it is still reported, and
   any consumer reading `urgency.flagged` will reproduce the false positives.
4. **Frontend cannot show the safety result.** See section 9.
5. **`cleaned_text` / `lemmatized_text` echoed**: stored-XSS surface if a consumer
   renders them as markup. Backend guarantee is JSON content type (D-041).
6. **NLTK data lives outside the repo** (`~/nltk_data`). Present locally and
   installed by the Dockerfile at build time; `corpora/omw-1.4` is absent, which
   only affects non-English lemmatization.

**Possible, not verified:** rate limiting on `/predict` (only login is
throttled); `MAX_TEXT_LENGTH` at the boundary of a reverse proxy's body limit;
CORS behaviour against a real split-origin deployment; `db.get_client()` thread
safety under uvicorn workers.

## 9. Unfinished Work

1. **Frontend consumption** (blocked on this phase's boundary, D-042).
   Required changes, none made:
   - `web/src/lib/api.ts`: add `SafetyResult` to `PredictResponse`; make
     `PrimaryResult.predicted_class` and `UrgencyResult.predicted_class` /
     `suicide_probability` nullable, because the backend now returns null when a
     track is unavailable. Today a model fault would render `null` into the UI.
   - `web/src/pages/Screen.tsx`: read `safety` **first**. The headline currently
     renders `primary.predicted_class`, so the user still sees "Normal" for the
     reported input.
   - `Screen.tsx` urgency block: when `urgency.status === "unavailable"`, it
     prints "No elevated urgency signal detected at the deployed 0.15 threshold".
     That is **false reassurance in exactly the failure case**: the most
     serious consumer defect found. It must show the unavailable state instead.
   - `Screen.tsx`: `maxLength={MAX_TEXT_LENGTH + 1000}` allows 11,000 characters
     where the service rejects 10,001+ with 422.
   - Replace the hardcoded "deployed 0.15 recall-first threshold" copy with the
     response's `decision_threshold_used`, now that the threshold is operable.
   - Handle `analysis_status: "unsupported"` and `"degraded"` distinctly.
   - Render `cleaned_text` / `lemmatized_text` as text only, never as markup.
2. **Routing generalization.** The measured miss rate is the release blocker.
   Adding more patterns is the wrong response (D-040). The defensible options
   are a clinician-reviewed rule set with declared language coverage, or a
   properly trained and independently evaluated classifier. Neither can be
   validated in this environment.
3. **No independent labels exist.** Every label here is generated. Any claim of
   clinical validity requires reviewed data that the repository does not contain.
4. **`eval_urgency()` threshold contamination** is documented (D-039) but the
   script is unchanged. Re-deriving 0.15 on train/validation would change the
   deployed threshold and needs its own decision.
5. **Multi-turn is unsupported.** `/predict` accepts one `text` field. M001–M006
   and the multi-turn corpus family are executed as combined text and must be
   read that way.

## 10. Next Subphase

Phase G: frontend consumption, **after** an explicit decision on the
generalization blocker. Before starting, resolve section 9 item 2, because
changing the routing approach would change the contract the frontend reads.

## 11. Critical Context

- **Repository**: shreshthgod/mental.ai. Starting revision
  `2053855d51aaa5c9e06bd8c30f1c35d45c64716b`, branch `main`, tracking
  `origin/main`. **Working tree is dirty and all of this session's work is
  uncommitted** alongside pre-existing uncommitted frontend changes from earlier
  work. Do not reset or discard them.
- **Ownership**: `git remote -v` → `https://github.com/shreshthgod/mental.ai.git`.
  Repository-local git identity was **not** configured or changed this session and
  **no commit was created**, so authorship is unverified and no publishing
  occurred. See the checklist item below.
- **Credentials**: `.env` exists and is gitignored, and contains SUPABASE values.
  Never print it. Supabase was stubbed for all API testing.
- **Corpus versions**: seeds `safety-corpus-2026.10.08.1`; expansion
  `safety-corpus-2026.10.08.2-expansion`; holdouts
  `safety-holdout-2026.10.08.1` and `safety-holdout-2026.10.08.2`; policy
  `safety-policy-2026.10.08.2`.
- **Case IDs**: S001–S072, M001–M006 (mandatory, unchanged); X001–X243
  (regression); H001–H096 (holdout-1, consumed); K001–K083 (holdout-2).
- **Unresolved failing IDs**: holdout-1 `H001 H003 H005 H007 H028 H059 H070
  H081 H090 H094`, benign FP `H051`; holdout-2 `K001 K002 K003 K004 K005 K006
  K007 K009 K010 K031 K032 K058 K059 K069 K080`. All are recorded, none hidden.
- **Next exact command**:
  `PYTHONPATH="Step 12 - Packaging/package:." python3 scripts/run_safety_corpus.py --layer both`
  then
  `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`.
- **Environment blocker**: none. Deps are installed; artifacts load; NLTK
  resources resolve locally.
- **Execution records** kept in `reports/`: `RUN-01` through `RUN-05`, each the
  evidence behind a claim in section 7, described in
  `reports/defect-register.md`. Intermediate run files were pruned.

## 12. Agent Instructions

1. Read `decisions.md`, `flow.md` and this file before touching anything.
2. **Do not re-tune against either holdout.** They are consumed. A new claim needs
   a new independently authored holdout (D-040).
3. Do not add routing patterns to chase a holdout score. If a case looks missed,
   first ask whether the pattern set is the right approach at all.
4. Never rewrite `primary` or `urgency` to make a UI look right (D-042, and the
   original design decision it protects).
5. Keep raw model outputs honest: `null` means unavailable, never `0.0` and never
   a fabricated label (D-026, D-006).
6. Every change needs a regression test written **first**, and a decision entry.
7. Keep the runner honest: it must exercise the shipped layer (D-036).
8. Do not commit unless explicitly asked, and then only as `shreshthgod`, with no
   attribution trailers, no collaborators, and no `paper/`, `research/` or `.tex`
   paths staged.
9. Never state "all cases verified", "100% safe" or "clinically validated". The
   measured generalization number in section 7 is the current truth.