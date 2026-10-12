"""Re-run the consumed development benchmark without simulated model outputs."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Step 12 - Packaging/package"))
sys.path.insert(0, str(ROOT))
import numpy as np
from sklearn.metrics import classification_report, f1_score
from mental_health_screening.emotion import EmotionRecognizer, EMOTION_CATEGORIES
from mental_health_screening.safety import evaluate as evaluate_safety, POLICY_VERSION


def predict_text(text: str, screener=None, recognizer=None) -> dict:
    """Inference receives text, never an evaluation record."""
    if not isinstance(text, str):
        raise TypeError("Inference accepts text only")
    screen = screener.screen(text) if screener is not None else None
    safety = evaluate_safety(text, urgency_flagged=False)
    emotions = (recognizer or EmotionRecognizer()).analyze(text)
    return {
        "condition": screen["primary"].get("predicted_class") if screen else None,
        "urgency_flag": screen["urgency"].get("flagged") if screen else None,
        "legacy_safety": screen["safety"].get("level") if screen else None,
        "legacy_status": "complete" if screen and all(screen[k].get("status") == "complete" for k in ("primary", "urgency")) else "unavailable",
        "model_version": getattr(screener, "model_version", None),
        "safety_raw": safety.level, "policy_version": POLICY_VERSION,
        "contextual": {"status": "unavailable", "reason": "No validated classifier artifact"},
        "fusion": {"status": "unavailable", "reason": "No validated contextual classifier"},
        "emotions": sorted(emotions.primary_emotions),
        "emotion_version": "lexical-cues-v1-unvalidated",
    }


def safety_metrics(cases, predictions, key):
    if any(p[key] is None for p in predictions):
        return {"status": "unavailable"}
    high = {"HIGH", "IMMEDIATE"}
    fn = [c["id"] for c,p in zip(cases,predictions) if c["expected_safety"] in high and p[key] not in high]
    fp = [c["id"] for c,p in zip(cases,predictions) if c["expected_safety"] not in high and p[key] in high]
    total = sum(c["expected_safety"] in high for c in cases)
    return {"crisis_cases": total, "crisis_recall": (total-len(fn))/total if total else None,
            "false_negative_ids": fn, "false_positive_ids": fp,
            "false_positive_definition": "Predicted HIGH/IMMEDIATE for any other expected level"}


def run_evaluation(dataset=None, output=None, rules_only=False):
    dataset = Path(dataset or ROOT / "evaluation/contextual_benchmark_v1.json")
    output = Path(output or ROOT / "reports/contextual-ml-evaluation-corrected.json")
    data = json.loads(dataset.read_text(encoding="utf-8"))
    cases = data["cases"]
    screener = None
    if not rules_only:
        from mental_health_screening.inference import MentalHealthScreener
        screener = MentalHealthScreener()
    predictions, latencies = [], []
    recognizer = EmotionRecognizer()
    for case in cases:
        start = time.perf_counter()
        predictions.append(predict_text(case["text"], screener, recognizer))
        latencies.append((time.perf_counter()-start)*1000)
    labels = list(EMOTION_CATEGORIES)
    true = np.array([[int(e in c["expected_emotions"]) for e in labels] for c in cases])
    pred = np.array([[int(e in p["emotions"]) for e in labels] for p in predictions])
    indices = [i for i,p in enumerate(predictions) if p["condition"] is not None]
    condition = {"status": "unavailable"}
    if indices:
        condition = classification_report([cases[i]["expected_condition"] for i in indices],
            [predictions[i]["condition"] for i in indices], output_dict=True, zero_division=0)
    report = {
        "status": "research_challenge" if data.get("split") == "challenge" else "corrected_development_only",
        "dataset_split": data.get("split", "consumed_development"), "independent_holdout": False,
        "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(), "cases": len(cases),
        "limitations": ["Previously inspected examples; no generalization claim",
            "Condition labels are scenario annotations, not clinical ground truth",
            "Emotion scores are lexical counts, not calibrated probabilities"],
        "contextual": {"status": "unavailable"}, "validated_hybrid": {"status": "unavailable"},
        "condition": condition, "legacy_config": getattr(screener, "config", None),
        "safety": {key:safety_metrics(cases,predictions,key) for key in ["legacy_safety","safety_raw"]},
        "emotion": {"macro_f1": f1_score(true,pred,average="macro",zero_division=0),
            "micro_f1": f1_score(true,pred,average="micro",zero_division=0),
            "exact_subset_accuracy": float(np.mean(np.all(true == pred,axis=1))),
            "per_emotion": classification_report(true,pred,target_names=labels,output_dict=True,zero_division=0),
            "errors": {e:{"false_positive_ids":[c["id"] for c,p in zip(cases,predictions) if e in p["emotions"] and e not in c["expected_emotions"]],
                          "false_negative_ids":[c["id"] for c,p in zip(cases,predictions) if e not in p["emotions"] and e in c["expected_emotions"]]} for e in labels}},
        "latency_ms": {"p50": float(np.median(latencies)), "p95": float(np.percentile(latencies,95))},
        "records": [{"id":c["id"],"category":c["category"],"prediction":p} for c,p in zip(cases,predictions)],
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:report[k] for k in ["status","cases","safety","latency_ms"]},indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset",type=Path)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--rules-only",action="store_true")
    args = parser.parse_args()
    run_evaluation(args.dataset,args.output,args.rules_only)
