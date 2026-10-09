"""
Handcrafted feature extraction for a single (cleaned_text, lemmatized_text)
pair -- reuses the exact logic from Step 7's feature_engineering.py, copied
here (not imported) so this package has no dependency on the pipeline's
sandbox folder layout. Returns features in the SAME order Step 9's models
were trained on (see artifacts/config.json's handcrafted_feature_order,
loaded by inference.py -- not hard-coded twice).
"""
import json
import re
import os
import pkgutil
import importlib.resources as ires
from functools import lru_cache

from nltk.sentiment.vader import SentimentIntensityAnalyzer
import textstat
from nrclex import NRCLex

_SIA = SentimentIntensityAnalyzer()
_NRC_LEXICON = NRCLex().__lexicon__
_NRC_CATEGORIES = ["fear", "anger", "anticipation", "trust", "surprise",
                   "positive", "negative", "sadness", "disgust", "joy"]

_ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")

@lru_cache(maxsize=8)
def _load_lexicons(urgency_path, emotion_path):
    with open(urgency_path, encoding="utf-8") as f:
        urgency = set(json.load(f)["curated_urgency_keywords"])
    with open(emotion_path, encoding="utf-8") as f:
        emotion = json.load(f)
    return urgency, emotion["classes"], emotion["lexicon"]

_PRONOUNS = {"i", "me", "my", "mine", "myself"}
_NEGATIONS = {"not", "no", "never", "none", "nobody", "nothing", "neither", "nor", "n't", "cannot"}
_ABSOLUTIST = {"always", "never", "completely", "entirely", "totally", "all", "none",
               "every", "everyone", "everybody", "everything", "nothing", "definitely",
               "must", "constantly", "forever", "whole", "full", "fully"}

_EXCLAIM_RE = re.compile(r"!")
_QUESTION_RE = re.compile(r"\?")
_ELLIPSIS_RE = re.compile(r"\.\.\.|…")
_REPEAT_PUNCT_RE = re.compile(r"([!?])\1{1,}")
_WORD_SPLIT_RE = re.compile(r"\S+")


def _stylistic_features(text):
    words = _WORD_SPLIT_RE.findall(text)
    n_words = len(words) or 1
    caps_words = sum(1 for w in words if len(w) >= 2 and w.isupper())
    return {
        "char_count": len(text),
        "word_count": len(words),
        "avg_word_len": sum(len(w) for w in words) / n_words,
        "exclam_count": len(_EXCLAIM_RE.findall(text)),
        "question_count": len(_QUESTION_RE.findall(text)),
        "ellipsis_count": len(_ELLIPSIS_RE.findall(text)),
        "all_caps_ratio": caps_words / n_words,
        "repeated_punct_count": len(_REPEAT_PUNCT_RE.findall(text)),
    }


def _vader_features(text):
    s = _SIA.polarity_scores(text)
    return {"vader_neg": s["neg"], "vader_neu": s["neu"], "vader_pos": s["pos"], "vader_compound": s["compound"]}


def _readability_features(text):
    return {
        "flesch_reading_ease": textstat.flesch_reading_ease(text),
        "flesch_kincaid_grade": textstat.flesch_kincaid_grade(text),
    }


def _token_features(tokens, urgency_keywords, emotion_classes, emotion_lexicon):
    n = len(tokens) or 1
    pronoun_n = sum(1 for t in tokens if t in _PRONOUNS)
    negation_n = sum(1 for t in tokens if t in _NEGATIONS)
    absolutist_n = sum(1 for t in tokens if t in _ABSOLUTIST)

    nrc_hits = []
    for t in tokens:
        if t in _NRC_LEXICON:
            nrc_hits.extend(_NRC_LEXICON[t])
    nrc_total = len(nrc_hits) or 1
    nrc_counts = {c: 0 for c in _NRC_CATEGORIES}
    for c in nrc_hits:
        nrc_counts[c] += 1
    nrc_feats = {f"nrc_{c}": nrc_counts[c] / nrc_total for c in _NRC_CATEGORIES}

    emo_sums = {c: 0.0 for c in emotion_classes}
    emo_matched = 0
    for t in tokens:
        if t in emotion_lexicon:
            emo_matched += 1
            for c in emotion_classes:
                emo_sums[c] += emotion_lexicon[t][c]
    emo_denom = emo_matched or 1
    emo_feats = {f"emo_lex_{c}": emo_sums[c] / emo_denom for c in emotion_classes}

    urgency_hits = sum(1 for t in tokens if t in urgency_keywords)

    out = {
        "pronoun_ratio": pronoun_n / n,
        "negation_count": negation_n,
        "absolutist_ratio": absolutist_n / n,
        "urgency_keyword_count": urgency_hits,
        "urgency_keyword_flag": int(urgency_hits > 0),
    }
    out.update(nrc_feats)
    out.update(emo_feats)
    return out


def extract_handcrafted_features(cleaned_text: str, lemmatized_text: str, *, urgency_lexicon=None, emotion_lexicon=None) -> dict:
    """Same feature dict Step 7's extract_all() produced -- one dict, keyed
    by feature name. Caller (inference.py) reorders via config.json's
    handcrafted_feature_order before handing to the model."""
    tokens = str(lemmatized_text).split()
    lexicons = _load_lexicons(
        urgency_lexicon or os.path.join(_ARTIFACTS_DIR, "curated_urgency_keywords.json"),
        emotion_lexicon or os.path.join(_ARTIFACTS_DIR, "emotion_lexicon.json"))
    row = {}
    row.update(_stylistic_features(str(cleaned_text)))
    row.update(_vader_features(str(cleaned_text)))
    row.update(_readability_features(str(cleaned_text)))
    row.update(_token_features(tokens, *lexicons))
    return row
