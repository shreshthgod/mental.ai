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
import logging
import pickle
import hashlib
import numpy as np

from mental_health_screening.safety import POLICY_VERSION, evaluate as evaluate_safety, support_action
import scipy.sparse as sp
from .fusion import fuse
from .emotion import EmotionRecognizer, EmotionAnalysis

def clean_and_lemmatize(raw_text):
    from .preprocessing import clean_and_lemmatize as process
    return process(raw_text)


def extract_handcrafted_features(cleaned, lemmatized, **options):
    from .features import extract_handcrafted_features as extract
    return extract(cleaned, lemmatized, **options)


logger = logging.getLogger("mental_health_screening.inference")

_ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")


def _assert_valid_probabilities(probs: np.ndarray, track: str) -> None:
    """
    Reject a probability vector that cannot be a probability vector.

    Checks finite, non-negative, and at most 1.0. Raising here means the track
    reports `status: unavailable` with null values, which is honest; returning
    the number would publish a measurement that does not exist.
    """
    if not np.all(np.isfinite(probs)):
        raise ValueError(f"{track} model produced non-finite probabilities")
    if np.any(probs < 0.0):
        raise ValueError(f"{track} model produced a negative probability")
    if np.any(probs > 1.0):
        raise ValueError(f"{track} model produced a probability above 1.0")
    if probs.ndim != 1 or not len(probs) or not np.isclose(np.sum(probs), 1.0, atol=1e-5):
        raise ValueError(f"{track} model produced an invalid probability distribution")


class MentalHealthScreener:
    def __init__(self, artifacts_dir: str = _ARTIFACTS_DIR, max_text_length: int = 10000):
        self.max_text_length = int(max_text_length)
        with open(os.path.join(artifacts_dir, "config.json")) as f:
            self.config = json.load(f)
        self._feature_order = self.config["handcrafted_feature_order"]
        self._feature_options = {
            "urgency_lexicon": os.path.join(artifacts_dir, self.config["curated_urgency_keywords_file"]),
            "emotion_lexicon": os.path.join(artifacts_dir, self.config["emotion_lexicon_file"]),
        }
        self._urgency_threshold = self._configured_urgency_threshold()
        self._primary_model = self._urgency_model = None
        self._primary_vectorizer = self._primary_chi2 = self._primary_label_encoder = None
        self._urgency_vectorizer = None
        self._urgency_classes = []
        self._suicide_idx = None
        try:
            with open(os.path.join(artifacts_dir, self.config["primary_dataset"]["tfidf_vectorizer_file"]), "rb") as f:
                self._primary_vectorizer = pickle.load(f)
            with open(os.path.join(artifacts_dir, self.config["primary_dataset"]["chi2_selector_file"]), "rb") as f:
                self._primary_chi2 = pickle.load(f)
            with open(os.path.join(artifacts_dir, self.config["primary_dataset"]["model_file"]), "rb") as f:
                bundle = pickle.load(f)
                self._primary_model = bundle["model"]
                self._primary_label_encoder = bundle["label_encoder"]
        except Exception as exc:
            self._primary_model = None
            logger.warning("primary_initialization_unavailable error_type=%s", type(exc).__name__)
        try:
            with open(os.path.join(artifacts_dir, self.config["urgency_dataset"]["tfidf_vectorizer_file"]), "rb") as f:
                self._urgency_vectorizer = pickle.load(f)
            with open(os.path.join(artifacts_dir, self.config["urgency_dataset"]["model_file"]), "rb") as f:
                self._urgency_model = pickle.load(f)
            self._urgency_classes = list(self._urgency_model.classes_)
            self._suicide_idx = self._urgency_classes.index("suicide")
        except Exception as exc:
            self._urgency_model = None
            logger.warning("urgency_initialization_unavailable error_type=%s", type(exc).__name__)
        required_artifacts = [
            ("primary_model", self.config["primary_dataset"]["model_file"]),
            ("urgency_model", self.config["urgency_dataset"]["model_file"]),
            ("primary_vectorizer", self.config["primary_dataset"]["tfidf_vectorizer_file"]),
            ("urgency_vectorizer", self.config["urgency_dataset"]["tfidf_vectorizer_file"]),
            ("primary_chi2", self.config["primary_dataset"]["chi2_selector_file"]),
        ]
        # Fingerprint the actual serialized raw models, vectorizers, selector
        # and their feature/class configuration. This is not a clinical version.
        model_hashes = {}
        for filename in ["config.json", self.config["curated_urgency_keywords_file"], self.config["emotion_lexicon_file"]] + [filename for _, filename in required_artifacts]:
            try:
                with open(os.path.join(artifacts_dir, filename), "rb") as source:
                    model_hashes[filename] = hashlib.sha256(source.read()).hexdigest()
            except OSError:
                model_hashes[filename] = None
        self.model_version = "sha256:" + hashlib.sha256(
            json.dumps(model_hashes, sort_keys=True).encode()).hexdigest()
        self._emotion_recognizer = EmotionRecognizer(self._feature_options.get("emotion_lexicon"))

    def analyze_emotions(self, text: str) -> EmotionAnalysis:
        """Analyze multi-label emotional cues separated from clinical conditions."""
        return self._emotion_recognizer.analyze(text)

    def _configured_urgency_threshold(self) -> float:
        """
        The urgency decision threshold.

        `URGENCY_THRESHOLD` was documented in .env.example and read nowhere, so
        an operator who raised it to reduce false positives got 0.15 and no
        error (D-008). It is now honored. An unparseable or out-of-range value
        raises at construction rather than being silently ignored, because a
        threshold is safety-relevant: quietly using a different one than the
        operator asked for is worse than refusing to start.
        """
        packaged = float(self.config["urgency_dataset"]["decision_threshold"])
        raw = os.environ.get("URGENCY_THRESHOLD", "").strip()
        if not raw:
            return packaged
        try:
            value = float(raw)
        except ValueError as exc:
            raise ValueError(
                f"URGENCY_THRESHOLD={raw!r} is not a number; unset it to use the "
                f"packaged threshold {packaged}"
            ) from exc
        if not 0.0 < value <= 1.0:
            raise ValueError(
                f"URGENCY_THRESHOLD={value} is out of range; it must be in (0, 1]"
            )
        logger.warning(
            "urgency_threshold_overridden packaged=%s configured=%s", packaged, value
        )
        return value

    def _build_primary_features(self, cleaned_text, lemmatized_text, handcrafted):
        if list(handcrafted) != self._feature_order:
            raise ValueError("Handcrafted feature order disagrees with extraction contract")
        X_tfidf = self._primary_vectorizer.transform([lemmatized_text])
        X_tfidf_red = self._primary_chi2.transform(X_tfidf)
        values = np.array([[handcrafted[c] for c in self._feature_order]], dtype=np.float32)
        if not np.all(np.isfinite(values)):
            raise ValueError("Nonfinite handcrafted measurement")
        X_hand = sp.csr_matrix(values)
        return sp.hstack([X_tfidf_red, X_hand], format="csr")

    def screen(self, raw_text: str) -> dict:
        # Input validation
        if raw_text is None:
            raise ValueError("Input text is None")
        if not isinstance(raw_text, str):
            raise ValueError(f"Input must be a string, got {type(raw_text).__name__}")
        if len(raw_text.strip()) == 0:
            raise ValueError("Input text is empty")
        if len(raw_text) > self.max_text_length:
            raise ValueError(
                f"Input text exceeds maximum length of {self.max_text_length:,} characters"
            )
        # Evaluate raw-text evidence before any optional, lossy processing.
        try:
            safety = evaluate_safety(raw_text).to_dict()
        except Exception as exc:
            logger.warning("safety_evaluation_unavailable error_type=%s", type(exc).__name__)
            safety = {
                "level": "UNKNOWN", "subject": "unclear", "temporal_context": "unclear",
                "immediacy": "unclear", "evidence_codes": ["SAFETY_EVALUATION_FAILED"],
                "summary": "Safety assessment unavailable.", "needs_clarification": True,
                "review_recommended": True, "analysis_status": "unavailable",
                "policy_version": POLICY_VERSION, "language_support": "unknown",
            }
        cleaned = lemmatized = None
        try:
            cleaned, lemmatized = clean_and_lemmatize(raw_text)
        except Exception as exc:
            logger.warning("preprocessing_unavailable error_type=%s", type(exc).__name__)


        # --- primary_dataset (7-class) ---
        # The condition track is now non-fatal. Previously an exception here
        # aborted the whole call, which meant a classifier fault also removed
        # the urgency and safety output. Safety routing must not depend on the
        # condition model succeeding. Unavailable is reported as unavailable,
        # never as a fabricated label or a zero probability.
        primary_status = "complete"
        try:
            if cleaned is None or lemmatized is None:
                raise RuntimeError("Preprocessing unavailable")
            handcrafted = extract_handcrafted_features(cleaned, lemmatized, **self._feature_options)
            X_primary = self._build_primary_features(cleaned, lemmatized, handcrafted)
            expected_classes = sorted(self.config["primary_dataset"]["classes"])
            if list(self._primary_label_encoder.classes_) != expected_classes or list(self._primary_model.classes_) != list(range(len(expected_classes))):
                raise ValueError("Primary class order disagrees with label encoder contract")
            primary_proba = self._primary_model.predict_proba(X_primary)[0]
            # D-026: the guard covered NaN and negative values but not values
            # above 1. A corrupted or mis-scaled model could therefore return
            # 7.5 as a class probability and it would be published verbatim in
            # the response. A probability outside [0, 1] is not a small
            # inaccuracy, it is a broken model, so the track reports
            # unavailable instead of inventing a number.
            _assert_valid_probabilities(primary_proba, "primary")
            if len(primary_proba) != len(expected_classes):
                raise ValueError("Primary probability/class count mismatch")
            primary_pred_idx = int(np.argmax(primary_proba))
            primary_pred = self._primary_label_encoder.inverse_transform([primary_pred_idx])[0]
            primary_classes = self._primary_label_encoder.inverse_transform(
                np.arange(len(primary_proba))
            )
            primary_result = {
                "predicted_class": primary_pred,
                "class_probabilities": {c: float(p) for c, p in zip(primary_classes, primary_proba)},
                "status": primary_status,
            }
        except Exception as exc:
            logger.warning("primary_prediction_unavailable error_type=%s", type(exc).__name__)
            primary_result = {
                "predicted_class": None,
                "class_probabilities": {},
                "status": "unavailable",
                "error_type": type(exc).__name__,
            }

        # --- urgency_dataset (binary, tuned threshold) ---
        urgency_status = "complete"
        try:
            if lemmatized is None:
                raise RuntimeError("Preprocessing unavailable")
            X_urgency = self._urgency_vectorizer.transform([lemmatized])
            if list(self._urgency_model.classes_) != self.config["urgency_dataset"]["classes"] or self._urgency_classes != self.config["urgency_dataset"]["classes"]:
                raise ValueError("Urgency class order disagrees with configuration")
            urgency_proba_all = self._urgency_model.predict_proba(X_urgency)[0]
            # D-026: same guard, same reason. Observed before the fix:
            # suicide_probability=5.0, predicted_class="suicide", flagged=true,
            # status="complete" - an impossible number published as a fact.
            _assert_valid_probabilities(urgency_proba_all, "urgency")
            if len(urgency_proba_all) != len(self._urgency_classes):
                raise ValueError("Urgency probability/class count mismatch")
            suicide_proba = float(urgency_proba_all[self._suicide_idx])
            urgency_pred = "suicide" if suicide_proba >= self._urgency_threshold else "non-suicide"
            urgency_result = {
                "predicted_class": urgency_pred,
                "suicide_probability": suicide_proba,
                "decision_threshold_used": self._urgency_threshold,
                "flagged": urgency_pred == "suicide",
                "status": urgency_status,
            }
        except Exception as exc:
            logger.warning("urgency_prediction_unavailable error_type=%s", type(exc).__name__)
            urgency_result = {
                "predicted_class": None,
                "suicide_probability": None,
                "decision_threshold_used": self._urgency_threshold,
                "flagged": False,
                "status": "unavailable",
                "error_type": type(exc).__name__,
            }

        safety, components = fuse(safety, primary_result, urgency_result,
                                  preprocessing_available=cleaned is not None)

        return {
            "model_version": self.model_version,
            "components": components,
            "primary": primary_result,
            "safety": safety,
            "urgency": urgency_result,
            "cleaned_text": cleaned,
            "lemmatized_text": lemmatized,
            "provenance_caveat": self.config["provenance_caveat"],
        }
