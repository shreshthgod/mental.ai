"""Offline MiniLM + supervised multi-label heads; never imported by the service."""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Step 12 - Packaging/package"))
REVISION = "6e6b1ff7471be7ed884ff7ce0821c889a3a1b0c9"
MAPPING = {"sadness": "sadness", "anger": "anger", "fear": "fear",
           "happiness": "joy", "excitement": "excitement", "frustration": "annoyance"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=ROOT/".cache/goemotions")
    parser.add_argument("--output", type=Path, default=ROOT/"reports/emotion-experiment.json")
    args = parser.parse_args()
    import numpy as np
    import onnxruntime as ort
    import psutil
    from tokenizers import Tokenizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.multiclass import OneVsRestClassifier
    from sklearn.metrics import f1_score, classification_report
    from mental_health_screening.emotion import EmotionRecognizer
    args.cache.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name in ["train.tsv", "dev.tsv", "test.tsv", "emotions.txt", "LICENSE"]:
        target = args.cache/name
        suffix = "LICENSE" if name == "LICENSE" else f"goemotions/data/{name}"
        if not target.exists():
            urllib.request.urlretrieve(f"https://raw.githubusercontent.com/google-research/google-research/{REVISION}/{suffix}", target)
        hashes[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    labels = list(MAPPING)
    native = (args.cache/"emotions.txt").read_text().splitlines()
    def rows(name):
        with (args.cache/name).open(encoding="utf-8",newline="") as f:
            return list(csv.reader(f, delimiter="\t"))
    # Sampling uses only stable IDs, never text or labels.
    order = lambda row: hashlib.sha256(("42:"+row[2]).encode()).hexdigest()
    train = sorted(rows("train.tsv"), key=order)[:2000]
    dev = sorted(rows("dev.tsv"), key=order)[:400]
    validation, calibration = dev[:200], dev[200:]
    test = sorted(rows("test.tsv"), key=order)[:500]
    splits = {"training":train,"validation":validation,"calibration":calibration,"holdout":test}
    normalized = lambda text: " ".join(text.casefold().split())
    seen = set()
    removed = {}
    for split, data in splits.items():
        unique = []
        for row in data:
            key = normalized(row[0])
            if key not in seen:
                unique.append(row)
                seen.add(key)
        removed[split] = len(data)-len(unique)
        splits[split] = unique
    train,validation,calibration,test = splits.values()
    def targets(data):
        return np.array([[int(native.index(MAPPING[label]) in map(int,row[1].split(",")))
                          for label in labels] for row in data])
    manifest = json.loads((args.artifacts/"manifest.json").read_text())
    for name, digest in manifest["hashes"].items():
        if hashlib.sha256((args.artifacts/name).read_bytes()).hexdigest() != digest:
            raise ValueError("Encoder hash mismatch")
    start = time.perf_counter()
    tok = Tokenizer.from_file(str(args.artifacts/"tokenizer.json"))
    tok.enable_truncation(max_length=128)
    tok.enable_padding()
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 2
    session = ort.InferenceSession(str(args.artifacts/"onnx/model.onnx"), opts, providers=["CPUExecutionProvider"])
    cold_ms = (time.perf_counter()-start)*1000
    def encode(texts):
        result = []
        for i in range(0,len(texts),16):
            enc = tok.encode_batch(texts[i:i+16])
            vals = {"input_ids":np.array([e.ids for e in enc],dtype=np.int64),
                    "attention_mask":np.array([e.attention_mask for e in enc],dtype=np.int64),
                    "token_type_ids":np.array([e.type_ids for e in enc],dtype=np.int64)}
            output = session.run(None,{n.name:vals[n.name] for n in session.get_inputs()})[0]
            mask = vals["attention_mask"][...,None]
            pooled = (output*mask).sum(1)/np.maximum(mask.sum(1),1)
            result.extend(pooled/np.maximum(np.linalg.norm(pooled,axis=1,keepdims=True),1e-9))
        return np.array(result)
    head = OneVsRestClassifier(LogisticRegression(C=1, max_iter=1000, random_state=42))
    start = time.perf_counter()
    head.fit(encode([r[0] for r in train]), targets(train))
    train_s = time.perf_counter()-start
    def infer_texts(texts):
        # No labels or dataset records can enter inference.
        if any(not isinstance(t,str) for t in texts):
            raise TypeError("Text only")
        return head.predict_proba(encode(texts))
    def metrics(y,pred):
        return {"macro_f1":f1_score(y,pred,average="macro",zero_division=0),
                "micro_f1":f1_score(y,pred,average="micro",zero_division=0),
                "exact_subset_accuracy":float(np.mean(np.all(y==pred,axis=1))),
                "per_emotion":classification_report(y,pred,target_names=labels,output_dict=True,zero_division=0)}
    validation_metrics = metrics(targets(validation),infer_texts([r[0] for r in validation])>=0.5)
    calibration_scores = infer_texts([r[0] for r in calibration])
    calibration_brier = float(np.mean((calibration_scores-targets(calibration))**2))
    # Threshold and hyperparameters are fixed before opening holdout labels.
    scores = infer_texts([r[0] for r in test])
    pred = scores >= 0.5
    truth = targets(test)
    recognizer = EmotionRecognizer()
    heuristic = np.array([[int(e in recognizer.analyze(r[0]).primary_emotions) for e in labels] for r in test])
    warm = []
    for row in test[:30]:
        start = time.perf_counter()
        infer_texts([row[0]])
        warm.append((time.perf_counter()-start)*1000)
    report = {"status":"research_only_not_deployed", "dataset_revision":REVISION,"dataset_hashes":hashes,
        "encoder":manifest,"head_sha256":hashlib.sha256(b"".join(e.coef_.tobytes()+e.intercept_.tobytes() for e in head.estimators_)).hexdigest(),"labels":MAPPING,"split_ids":{k:[r[2] for r in v] for k,v in splits.items()},
        "removed_exact_text_duplicates":removed,"parameters":{"C":1,"seed":42,"threshold":0.5,"max_tokens":128},
        "validation":validation_metrics,"calibration_brier_uncalibrated":calibration_brier,
        "holdout":{"candidate":metrics(truth,pred),"heuristic":metrics(truth,heuristic)},
        "errors":{label:{"false_positive_ids":[r[2] for r,t,p in zip(test,truth[:,i],pred[:,i]) if p and not t],
                         "false_negative_ids":[r[2] for r,t,p in zip(test,truth[:,i],pred[:,i]) if t and not p]} for i,label in enumerate(labels)},
        "heuristic_errors":{label:{"false_positive_ids":[r[2] for r,t,p in zip(test,truth[:,i],heuristic[:,i]) if p and not t],
                                   "false_negative_ids":[r[2] for r,t,p in zip(test,truth[:,i],heuristic[:,i]) if t and not p]} for i,label in enumerate(labels)},
        "abstention":{"rule":"No label above fixed 0.5 threshold","fraction":float(np.mean(~pred.any(axis=1))),
                      "caveat":"Empty prediction conflates uncertainty and out-of-ontology emotions; not a validated abstention policy"},
        "runtime":{"cold_load_ms":cold_ms,"warm_p50_ms":float(np.median(warm)),"warm_p95_ms":float(np.percentile(warm,95)),
                   "training_seconds":train_s,"process_rss_bytes":psutil.Process().memory_info().rss,
                   "encoder_download_bytes":sum((args.artifacts/n).stat().st_size for n in manifest["hashes"]),
                   "offline_python":True,"offline_browser":"not_tested"},
        "versions":{n:importlib.metadata.version(n) for n in ["onnxruntime","tokenizers","numpy","scikit-learn","psutil"]},
        "legacy_baselines":"Condition and urgency models use different label spaces; emotion F1 is not applicable",
        "hybrid":{"status":"unavailable","reason":"No independently validated fusion"},
        "limitations":["English Reddit sample; six overlapping labels only, not the full product ontology",
                       "Frozen embeddings plus supervised heads, not encoder fine-tuning",
                       "No Hindi/Hinglish validation, clinical validation, calibration fit or browser parity",
                       "Public encoder pretraining overlap cannot be excluded"]}
    args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"holdout":report["holdout"],"runtime":report["runtime"]},indent=2))


if __name__ == "__main__":
    main()
