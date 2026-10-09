# Local semantic candidate: isolated engineering experiment

Production status: **disabled**. `semantic.assess()` remains an adapter boundary; the application does not call this experimental classifier.

Candidate: frozen `sentence-transformers/all-MiniLM-L6-v2`, revision `10dbd2f06a8baf40ad285b037edda610c1b9a57c`, CPU ONNX embeddings plus a fitted LogisticRegression (`C=1`, seed 42, argmax, no validation tuning). The official card labels it Apache-2.0 and English, with 384-dimensional embeddings and a 256-wordpiece limit. It was trained for sentence similarity, not safety routing. Pretraining uses mixed sentence-pair sources; underlying dataset licenses and overlap have not been independently established. [Model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)

Exact model SHA-256: `6fd5d72fe4589f189f8ebc006442dbb529bb7ce38f8082112682524616046452` (90,405,214-byte ONNX file). Tokenizer/config/card hashes are in `reports/semantic-candidate-20261008-v1.json`. The CPU runtime needs no training framework. [ONNX Runtime installation](https://onnxruntime.ai/docs/install/)

Isolated dependencies: `evaluation/requirements-semantic.txt`; installed in `/tmp/mental-ai-semantic-env`. Existing application packages/artifacts were not upgraded. Artifact setup is an explicit download script, never request-time work. Inference is local; no disclosures are uploaded. Inputs over 256 wordpieces are rejected rather than silently truncated.

Data: `evaluation/semantic-development-v1.json`, 36 synthetic development rows and 18 synthetic validation rows, developer-labeled and not clinically reviewed. The classifier is actually fitted on development embeddings; the published encoder is not retrained. Validation was authored before inference and is not used for threshold/model selection. No existing regression/consumed-holdout rows are fitted. Exact normalized cross-split/corpus overlaps: 0. Shared semantic families and developer labels mean these are engineering observations, not independent generalization evidence.

| Validation measure | Current rules, policy .4 | Experimental encoder classifier |
|---|---|---|
| Correct three-category support label | 10/18 | 13/18 |
| Urgent cases labelled urgent | 1/6 | 5/6 |
| Benign cases falsely urgent | 0/6 | 1/6 |

The candidate misses the excess-medication urgent case and falsely escalates a benign rooftop-garden statement. It also mishandles recovery/other concern cases. It supplies no validated subject/time/capability assessment and has no clinical probability/calibration. These results do not justify enabling it, although they demonstrate a feasible local semantic path with a measurable tradeoff.

Measured on Python 3.12.3 / Linux, CPUExecutionProvider, two intra-op threads, concurrency 1: one cold-load sample 288.31 ms; 18 warm inference samples p50 10.19 ms, p95/p99 14.84 ms (sorted floor(n*q) index capped; median p50). Peak whole-process RSS 322,512 KiB, includes imports, encoder and fitting. No GPU/multi-worker/HTTP/deployed load claim.

Commands:

```bash
python3 -m venv --system-site-packages /tmp/mental-ai-semantic-env
/tmp/mental-ai-semantic-env/bin/python -m pip install -r evaluation/requirements-semantic.txt
python3 scripts/fetch_semantic_candidate.py --output /tmp/mental-ai-semantic-artifacts
/tmp/mental-ai-semantic-env/bin/python scripts/evaluate_semantic_candidate.py --artifacts /tmp/mental-ai-semantic-artifacts --output reports/semantic-candidate-20261008-v1.json
```

A reproducibility rerun of this frozen candidate is not a new independent observation. Reviewed development/validation labels, policy and independent final review remain BLOCKED external requirements. No classifier is selected for production.

Current-policy reproducibility (D096): reports/semantic-candidate-20261009-reproducibility.json runs the same pinned candidate/data/settings against independent engine policy .6, not production fusion. Baseline remains10/18 labels and1/6 urgent; candidate13/18,5/6 urgent,1/6 benign urgent escalation. Cold load241.49ms(n1),warm n18 p506.82/p95-p998.47ms, whole-process peakRSS322684KiB (CPU2threads,concurrency1). Repeat consumed-C observation, no tuning or independent final evidence; candidate stays disabled. Original .4 report preserved.
