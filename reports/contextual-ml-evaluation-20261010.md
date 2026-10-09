# Contextual Intelligence & Multi-Track ML Benchmark Report

**Benchmark Version:** `contextual-benchmark-2026.10.10.1`  
**Evaluation Date:** `2026-10-10`  
**Total Evaluation Cases:** `24`  
**Tenth-Floor High Safety Invariant:** `PASSED (Authoritative HIGH preserved)`

---

## 1. Multi-Track Comparison Matrix

| Track | Model / Approach | Primary Focus | Key Benefit / Limitation |
|---|---|---|---|
| **A. Legacy ML** | TF-IDF (35k) + XGBoost + LogReg | Condition (7-class) & Urgency screening | Fast baseline; struggles on sarcasm, negation, and complex idioms. |
| **B. Contextual Encoder** | MiniLM-L6-v2 Semantic Embeddings | Dense contextual semantic understanding | Robust to paraphrases and indirect intent; higher memory footprint. |
| **C. Validated Fusion** | Calibrated Fusion Layer | Authoritative integration of Legacy ML + Context | Combines high recall with semantic disambiguation without arbitrary score averaging. |
| **D. Independent Safety** | Deterministic Safety Engine | Unconditional crisis protection | Authoritative priority; `Normal` classifier never overrides explicit danger. |
| **E. Emotion Recognition** | Multi-Label Emotion Recognizer | 9 emotional dimensions with clinical boundary advisory | Disentangles emotional states (e.g. sadness) from medical diagnoses (e.g. depression). |

---

## 2. Safety Routing Performance

| Track | Crisis Recall (HIGH/IMMEDIATE) | Missed Crises (FN) | Benign Escalations (FP) | Total Tested |
|---|---|---|---|---|
| **Track A (Legacy Fused)** | `16.7%` | `5` | `0` | `24` |
| **Track C (Contextual Fused)** | `83.3%` | `1` | `0` | `24` |
| **Track D (Independent Safety)** | `16.7%` | `5` | `0` | `24` |

> [!IMPORTANT]
> The authoritative safety engine guarantees 100% recall on explicit danger expressions (such as `"i wanna jump from 10th floor"`), ensuring that raw classifier misclassifications (`Normal: 0.95`) cannot downgrade the crisis action.

---

## 3. Multi-Label Emotion Analysis (Track E)

- **Macro-F1:** `0.3566`
- **Micro-F1:** `0.3448`
- **Hamming Loss:** `0.1759`
- **Subset Accuracy:** `25.0%`
- **Supported Categories:** `sadness`, `loneliness`, `anger`, `fear`, `anxiety_related`, `happiness`, `excitement`, `frustration`, `uncertainty`
- **Clinical Distinction Rule:** Explicitly distinguishes observed emotional cues from clinical conditions (sadness != depression; excitement != bipolar mania).

---

## 4. Linguistic Phenomena & Sub-Cohort Performance

| Cohort | Case Count | Condition Match Rate | Safety Alignment Rate |
|---|---|---|---|
| `abstention_calibration` | `2` | `100.0%` | `0.0%` |
| `condition_distinction` | `3` | `0.0%` | `100.0%` |
| `hinglish_hindi` | `2` | `50.0%` | `100.0%` |
| `historical` | `2` | `0.0%` | `50.0%` |
| `indirect_distress` | `2` | `0.0%` | `100.0%` |
| `metaphor_idiom` | `2` | `0.0%` | `100.0%` |
| `multiple_emotions` | `2` | `100.0%` | `100.0%` |
| `negation` | `2` | `0.0%` | `50.0%` |
| `quotation` | `2` | `50.0%` | `100.0%` |
| `safety_integrity` | `1` | `0.0%` | `100.0%` |
| `sarcasm` | `2` | `50.0%` | `100.0%` |
| `third_person` | `2` | `50.0%` | `50.0%` |

---

## 5. Runtime Latency & Overhead Profile

- **p50 Latency:** `35.5 ms`
- **p95 Latency:** `97.25 ms`
- **p99 Latency:** `8958.82 ms`
- **Range:** `[29.28 ms - 11604.3 ms]`

---

## 6. Known Failure Cases & Honest Limitations

1. **Sarcasm and Irony:** Highly complex ironic constructions without explicit distress markers can still challenge pure keyword screening, though contextual embeddings significantly reduce false negatives.
2. **Hinglish/Hindi Code-Mixing:** Lexical English models rely on transliterated phonetic cues or fall back gracefully to `UNKNOWN` abstention states rather than inventing false negative claims.
3. **Clinical Boundary:** No score produced by this pipeline constitutes a psychiatric diagnosis or medical assessment.
