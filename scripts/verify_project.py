#!/usr/bin/env python3
"""Offline application checks; failed required checks exit nonzero.

Run from any directory. No credentials, provider calls, training or downloads.
Optional --api-url probes public liveness/readiness only, not authentication.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "Step 12 - Packaging/package"))


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def check_screen_result(result: dict) -> list[Check]:
    """Check actual producer observations, not merely existence of track keys."""
    safety = result.get("safety", {})
    original_ok = (
        safety.get("level") == "HIGH" and safety.get("subject") == "self"
        and safety.get("temporal_context") == "current"
        and safety.get("immediacy") == "not_stated"
        and bool(safety.get("support_action"))
    )
    models_ok = all(result.get(track, {}).get("status") == "complete"
                    for track in ("primary", "urgency"))
    processing_ok = result.get("components", {}).get("preprocessing") == "complete"
    return [
        Check("Original-case safety", "PASSED" if original_ok else "FAILED",
              "Expected HIGH/self/current, unstated immediacy and support action"),
        Check("Preprocessing", "PASSED" if processing_ok else "FAILED",
              "Actual optional preprocessing complete" if processing_ok else "Preprocessing unavailable"),
        Check("Legacy inference", "PASSED" if models_ok else "FAILED",
              "Both real model tracks complete" if models_ok else "One or both model tracks unavailable"),
    ]


def run_checks(artifacts: Path, api_url: str | None) -> list[Check]:
    checks = []
    for package in ("ftfy", "emoji", "contractions", "textstat", "nltk", "numpy",
                    "scipy", "pandas", "sklearn", "xgboost", "fastapi", "pydantic", "uvicorn"):
        try:
            module = importlib.import_module(package)
            version = getattr(module, "__version__", None)
            if version is None:
                version = importlib.metadata.version(package)
            checks.append(Check(f"Dependency {package}", "PASSED", str(version)))
        except Exception as exc:
            checks.append(Check(f"Dependency {package}", "FAILED", type(exc).__name__))
    try:
        import nltk
        # Zip resources must use their actual paths; no request-time download.
        resources = ("tokenizers/punkt", "tokenizers/punkt_tab",
                     "taggers/averaged_perceptron_tagger_eng",
                     "sentiment/vader_lexicon.zip/vader_lexicon/vader_lexicon.txt",
                     "corpora/wordnet.zip/wordnet/")
        for resource in resources:
            try:
                nltk.data.find(resource)
                checks.append(Check(f"NLTK {resource}", "PASSED", "Available locally"))
            except LookupError:
                checks.append(Check(f"NLTK {resource}", "FAILED", "Missing local resource"))
    except Exception as exc:
        checks.append(Check("NLTK resources", "FAILED", type(exc).__name__))
    try:
        config = json.loads((artifacts / "config.json").read_text())
        required = [config["primary_dataset"][key] for key in
                    ("model_file", "tfidf_vectorizer_file", "chi2_selector_file")]
        required += [config["urgency_dataset"][key] for key in ("model_file", "tfidf_vectorizer_file")]
        required += [config[key] for key in ("emotion_lexicon_file", "curated_urgency_keywords_file")]
        missing = [name for name in required if not (artifacts / name).is_file() or
                   (artifacts / name).stat().st_size == 0]
        checks.append(Check("Configured artifacts", "FAILED" if missing else "PASSED",
                            "Missing/empty configured files" if missing else "All configured files present"))
    except Exception as exc:
        checks.append(Check("Configured artifacts", "FAILED", type(exc).__name__))
    try:
        from mental_health_screening.inference import MentalHealthScreener
        result = MentalHealthScreener(artifacts_dir=str(artifacts)).screen("i wanna jump from 10th floor")
        checks.extend(check_screen_result(result))
    except Exception as exc:
        checks.append(Check("Application inference", "FAILED", type(exc).__name__))
    checks.append(Check("Historical training matrices", "NOT_APPLICABLE",
                        "Packaged inference uses frozen artifacts; this command does not reproduce historical training"))
    checks.append(Check("Semantic/release validation", "BLOCKED",
                        "Reviewed policy/data and independent final evaluation are unavailable; semantic candidate disabled"))
    if api_url:
        for path, field in (("live", "alive"), ("ready", "ready")):
            try:
                with urllib.request.urlopen(f"{api_url.rstrip('/')}/{path}", timeout=3) as response:
                    value = json.load(response)
                    ok = value.get(field) is True
                checks.append(Check(f"HTTP {path}", "PASSED" if ok else "FAILED", "Public capability probe"))
            except Exception as exc:
                checks.append(Check(f"HTTP {path}", "FAILED", type(exc).__name__))
    else:
        checks.append(Check("HTTP probes", "NOT_APPLICABLE", "Offline mode; opt in with --api-url for public probes"))
    checks.append(Check("Real provider integration", "NOT_APPLICABLE",
                        "Use explicit isolated-project harness; offline verification does not authenticate or write remotely"))
    return checks


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts-dir", type=Path, default=Path(os.environ.get(
        "ARTIFACTS_DIR", ROOT / "Step 12 - Packaging/package/mental_health_screening/artifacts")))
    parser.add_argument("--api-url")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    checks = run_checks(args.artifacts_dir, args.api_url)
    for check in checks:
        print(f"[{check.status}] {check.name}: {check.detail}")
    counts = {status: sum(c.status == status for c in checks) for status in
              ("PASSED", "FAILED", "BLOCKED", "NOT_APPLICABLE")}
    print(json.dumps(counts, sort_keys=True))
    if args.report:
        from scripts.source_fingerprint import fingerprint
        args.report.write_text(json.dumps({"checks": [asdict(c) for c in checks],
            "counts": counts, "layer": "offline actual-model application checks; optional public HTTP probes",
            "source": fingerprint(ROOT)}, indent=2) + "\n")
    return 1 if counts["FAILED"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
