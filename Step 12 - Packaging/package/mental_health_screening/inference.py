"""
Step 12 -- packaged inference module for Phase 1's text pipeline.

Bundles the two winning models from Steps 9-10 (primary_dataset's XGBoost,
urgency_dataset's Logistic Regression at its tuned 0.15 threshold) plus
every artifact needed to go from a raw text string to a prediction: the
fitted TF-IDF vectorizers, the chi2 selector, the curated urgency-keyword
list, and the custom emotion lexicon. Preprocessing (preprocessing.py) and
handcrafted feature extraction (features.py) reuse the pipeline's Step 4/5/7
logic exactly, copied rather than imported so this package has no
dependency on the pipeline sandbox.

IMPORTANT -- read before using: both models are trained on proxy labels
(subreddit of origin, via Pushshift), not clinician-verified diagnoses (see
the paper-details doc, items 53-56). This is a screening signal, not a
diagnostic tool, and the urgency_dataset output specifically is designed to
be reviewed by a person, not acted on automatically -- see the threshold
rationale in artifacts/config.json.

Usage:
    from mental_health_screening.inference import MentalHealthScreener
    screener = MentalHealthScreener()
    result = screener.screen("some raw text")
    # result = {
    #   "primary": {"predicted_class": "...", "class_probabilities": {...}},
    #   "urgency": {"predicted_class": "...", "suicide_probability": 0.0,
    #               "decision_threshold_used": 0.15, "flagged": bool},
    #   "cleaned_text": "...", "lemmatized_text": "...",
    # }
"""
import os
import json
import pickle
import numpy as np
import scipy.sparse as sp

from .preprocessing import clean_and_lemmatize
from .features import extract_handcrafted_features

_ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")


class MentalHealthScreener:
    def __init__(self, artifacts_dir: str = _ARTIFACTS_DIR):
        with open(os.path.join(artifacts_dir, "config.json")) as f:
            self.config = json.load(f)
        self._feature_order = self.config["handcrafted_feature_order"]

        with open(os.path.join(artifacts_dir, self.config["primary_dataset"]["tfidf_vectorizer_file"]), "rb") as f:
            self._primary_vectorizer = pickle.load(f)
        with open(os.path.join(artifacts_dir, self.config["primary_dataset"]["chi2_selector_file"]), "rb") as f:
            self._primary_chi2 = pickle.load(f)
        with open(os.path.join(artifacts_dir, self.config["primary_dataset"]["model_file"]), "rb") as f:
            bundle = pickle.load(f)
            self._primary_model = bundle["model"]
            self._primary_label_encoder = bundle["label_encoder"]

        with open(os.path.join(artifacts_dir, self.config["urgency_dataset"]["tfidf_vectorizer_file"]), "rb") as f:
            self._urgency_vectorizer = pickle.load(f)
        with open(os.path.join(artifacts_dir, self.config["urgency_dataset"]["model_file"]), "rb") as f:
            self._urgency_model = pickle.load(f)
        self._urgency_threshold = self.config["urgency_dataset"]["decision_threshold"]
        self._urgency_classes = list(self._urgency_model.classes_)
        # Verify all expected artifacts exist and are loadable
        required_artifacts = [
            ("primary_model", self.config["primary_dataset"]["model_file"]),
            ("urgency_model", self.config["urgency_dataset"]["model_file"]),
            ("primary_vectorizer", self.config["primary_dataset"]["tfidf_vectorizer_file"]),
            ("urgency_vectorizer", self.config["urgency_dataset"]["tfidf_vectorizer_file"]),
            ("primary_chi2", self.config["primary_dataset"]["chi2_selector_file"]),
        ]
        for purpose, filename in required_artifacts:
            artifact_path = os.path.join(artifacts_dir, filename)
            if not os.path.isfile(artifact_path):
                raise FileNotFoundError(f"Required artifact missing for {purpose}: {artifact_path}")
        self._suicide_idx = self._urgency_classes.index("suicide")

    def _build_primary_features(self, cleaned_text, lemmatized_text, handcrafted):
        X_tfidf = self._primary_vectorizer.transform([lemmatized_text])
        X_tfidf_red = self._primary_chi2.transform(X_tfidf)
        X_hand = sp.csr_matrix(
            np.array([[handcrafted[c] for c in self._feature_order]], dtype=np.float32)
        )
        return sp.hstack([X_tfidf_red, X_hand], format="csr")

    def screen(self, raw_text: str) -> dict:
        # Input validation
        if raw_text is None:
            raise ValueError("Input text is None")
        if not isinstance(raw_text, str):
            raise ValueError(f"Input must be a string, got {type(raw_text).__name__}")
        if len(raw_text.strip()) == 0:
            raise ValueError("Input text is empty")
        if len(raw_text) > 10000:
            raise ValueError("Input text exceeds maximum length of 10,000 characters")
        cleaned, lemmatized = clean_and_lemmatize(raw_text)
        handcrafted = extract_handcrafted_features(cleaned, lemmatized)

        # --- primary_dataset (7-class) ---
        X_primary = self._build_primary_features(cleaned, lemmatized, handcrafted)
        try:
            primary_proba = self._primary_model.predict_proba(X_primary)[0]
        except Exception as exc:
            raise RuntimeError(f"Primary model prediction failed: {exc}") from exc
        primary_pred_idx = int(np.argmax(primary_proba))
        primary_pred = self._primary_label_encoder.inverse_transform([primary_pred_idx])[0]
        primary_classes = self._primary_label_encoder.inverse_transform(
            np.arange(len(primary_proba))
        )
        primary_result = {
            "predicted_class": primary_pred,
            "class_probabilities": {c: float(p) for c, p in zip(primary_classes, primary_proba)},
        }

        # --- urgency_dataset (binary, tuned threshold) ---
        X_urgency = self._urgency_vectorizer.transform([lemmatized])
        try:
            urgency_proba_all = self._urgency_model.predict_proba(X_urgency)[0]
        except Exception as exc:
            raise RuntimeError(f"Urgency model prediction failed: {exc}") from exc
        suicide_proba = float(urgency_proba_all[self._suicide_idx])
        urgency_pred = "suicide" if suicide_proba >= self._urgency_threshold else "non-suicide"
        urgency_result = {
            "predicted_class": urgency_pred,
            "suicide_probability": suicide_proba,
            "decision_threshold_used": self._urgency_threshold,
            "flagged": urgency_pred == "suicide",
        }

        return {
            "primary": primary_result,
            "urgency": urgency_result,
            "cleaned_text": cleaned,
            "lemmatized_text": lemmatized,
            "provenance_caveat": self.config["provenance_caveat"],
        }
