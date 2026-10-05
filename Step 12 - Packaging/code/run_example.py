"""
Step 12 -- example usage of the packaged module. Run this to sanity-check
the package works end to end after installing requirements.txt + NLTK data
(see README.md).
"""
import sys
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "Step 12 - Packaging" / "package"))
from mental_health_screening.inference import MentalHealthScreener

EXAMPLES = [
    "I've been feeling really down lately and don't want to get out of bed most days.",
    "Just finished a great workout, feeling energized and ready for the week!",
    "I can't stop thinking about ending it all, nothing feels like it matters anymore.",
]

if __name__ == "__main__":
    screener = MentalHealthScreener()
    for text in EXAMPLES:
        result = screener.screen(text)
        print(f"\nInput: {text!r}")
        print(f"  primary_dataset prediction: {result['primary']['predicted_class']}")
        print(f"  urgency_dataset prediction: {result['urgency']['predicted_class']} "
              f"(suicide_probability={result['urgency']['suicide_probability']:.3f}, "
              f"threshold={result['urgency']['decision_threshold_used']})")
