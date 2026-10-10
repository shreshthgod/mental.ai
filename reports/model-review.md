# Model evaluation review

The original contextual report is invalid and superseded. Expected safety labels were used to fabricate semantic assessments; neither MiniLM inference nor calibrated fusion ran. The former 83.33% contextual-fusion crisis recall is withdrawn. That track is unavailable.

## Comparable development results

The same 24 consumed examples give unchanged heuristic emotion macro-F1 0.3566, micro-F1 0.3448 and exact subset accuracy 25%. No emotion-quality improvement is claimed. The legacy condition macro-F1 is 0.3265; condition annotations in these fixtures are not clinical truth. Original XGBoost and Logistic Regression artifacts and preprocessing are preserved.

Both legacy-fused and independent safety routing detect 1/6 HIGH cases. Five false negatives cover quotation, third-person disclosure, indirect distress and Hinglish. No HIGH false positives occur on that development set. On 14 newly authored challenge cases, the unchanged safety policy detects 2/3 HIGH examples, misses an indirect farewell/preparation disclosure, and escalates a negated statement incorrectly. These small software fixtures do not establish clinical recall. Do not tune on either consumed set.

## Supervised emotion experiment

An actual pinned MiniLM encoder ran locally through ONNX Runtime, followed by six one-vs-rest supervised Logistic Regression heads. Frozen embeddings are not encoder fine-tuning. The GoEmotions data is English Reddit text with human emotion annotations; its social and language biases limit transfer. The source repository's Apache-2.0 license is downloaded and hashed with the data; this experiment is research only. See the [dataset documentation](https://github.com/google-research/google-research/tree/6e6b1ff7471be7ed884ff7ce0821c889a3a1b0c9/goemotions) and [model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2).

Deterministic ID sampling requests 2,000 train, 200 validation, 200 calibration and 500 official test rows. Exact normalized text duplicates are removed across splits, leaving 1,999/200/197/500. IDs, file hashes, pinned revisions, versions and hyperparameters are recorded in `emotion-experiment.json`. C=1 and threshold=0.5 were fixed before holdout evaluation. Calibration examples only measure uncalibrated Brier error; no confidence calibration is fitted. No thresholds were changed after inspecting final results. Pretraining overlap cannot be excluded.

| Method on the same 500 examples and six mapped labels | Macro-F1 | Micro-F1 | Exact subset |
|---|---:|---:|---:|
| Existing heuristic | 0.2021 | 0.1964 | 0.836 |
| MiniLM + supervised heads | 0 | 0 | 0.842 |

The candidate predicts no positive labels: 84 positive label assignments are missed and there are zero false positive labels. Empty predictions on 100% of inputs are a failure, not successful uncertainty handling. The apparently high subset score reflects the many examples with no label in this restricted ontology. The heuristic has 17 false-positive and 73 false-negative label assignments; per-label metrics and IDs are in the report. These six-label scores cannot be compared directly with the nine-label 24-case benchmark. Condition and urgency models have different targets, so an emotion F1 comparison against them is not applicable. Hybrid fusion is unavailable.

Measured locally: encoder cold load 840.9 ms, warm single-input median 7.2 ms and p95 11.5 ms (30 inputs), process RSS 343,994,368 bytes at measurement, download 90,882,527 bytes. RSS is not peak memory. The Python inference runs offline after setup. No trained browser model, browser latency, calibrated abstention, Hindi/Hinglish accuracy or clinical validity has been established.

## Reproduce

```sh
python -m pip install -r evaluation/requirements-emotion.txt
python scripts/fetch_semantic_candidate.py --output .cache/pr1-minilm
python evaluation/emotion_experiment.py --artifacts .cache/pr1-minilm
python evaluation/evaluate_contextual_intelligence.py
python evaluation/evaluate_contextual_intelligence.py --dataset evaluation/review_challenge_v1.json --output reports/review-challenge.json
```

Setup downloads only public artifacts and data. Raw application disclosures are never used in this experiment. Model outputs remain disabled in the product. Next experiments need stronger training/imbalance handling selected on validation, then a new untouched holdout; this holdout is now consumed.

## Browser inference decision

[ONNX Runtime Web](https://onnxruntime.ai/docs/tutorials/web/) can run suitable exported models locally. Exporting XGBoost alone would not preserve this pipeline: NLTK lemmatization, fitted TF-IDF vocabularies, chi-square selection, handcrafted features and label order must also match. There is no verified browser export or parity suite, so this iteration returns null/empty unavailable trained-model outputs rather than approximations. Local English safety rules remain identified as heuristics. Their limited language and context handling is disclosed; unsupported or unknown-language input cannot establish safety.
