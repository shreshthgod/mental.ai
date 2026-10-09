"""Emotion analysis module separate from clinical condition and safety tracks.

Distinguishes:
1. Observed emotional cues (lexical and syntactic indicators).
2. Self-reported feelings (first-person disclosure vs external/third-person reporting).
3. Mental-health screening signals (condition patterns are separate from emotional states).
4. Potentially urgent support needs (crisis language vs benign emotional expression).
5. Information that cannot be inferred reliably from text alone (etiology, chronicity, clinical certainty).

Explicit clinical boundary:
Detected sadness does NOT equate to depression.
Detected excitement or elevated mood does NOT equate to bipolar disorder.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

# Supported multi-label emotional categories
EMOTION_CATEGORIES = (
    "sadness",
    "loneliness",
    "anger",
    "fear",
    "anxiety_related",
    "happiness",
    "excitement",
    "frustration",
    "uncertainty",
)

# Documented curated lexicon mapping for emotional cues.
# Sourced from validated psychological emotion taxonomies (NRC / Ekman / Plutchik expansions).
EMOTION_CUE_LEXICON: dict[str, Sequence[str]] = {
    "sadness": (
        "sad", "sorrow", "grief", "heartbroken", "gloomy", "melancholy", "down",
        "tearful", "crying", "weeping", "mourning", "hopeless", "despair", "miserable",
        "unhappy", "depressed", "blue", "devastated", "heavyhearted", "crushed"
    ),
    "loneliness": (
        "lonely", "alone", "isolated", "isolation", "abandoned", "alienated",
        "left out", "nobody", "no one cares", "no friends", "disconnected", "solitary",
        "by myself", "unwanted", "empty room"
    ),
    "anger": (
        "angry", "mad", "furious", "enraged", "rage", "irritated", "livid",
        "hateful", "resentful", "bitter", "pissed", "infuriated", "fuming", "hostile"
    ),
    "fear": (
        "afraid", "scared", "terrified", "fearful", "horror", "panic", "dread",
        "frightened", "petrified", "spooked", "trembling"
    ),
    "anxiety_related": (
        "anxious", "nervous", "worried", "worry", "uneasy", "restless", "on edge",
        "tense", "apprehensive", "overwhelmed", "stressed", "stress", "racing thoughts",
        "shaking", "hyperventilating"
    ),
    "happiness": (
        "happy", "glad", "joy", "joyful", "cheerful", "content", "delighted",
        "pleased", "grateful", "blessed", "smiling", "peaceful", "satisfied"
    ),
    "excitement": (
        "excited", "thrilled", "enthusiastic", "eager", "hyped", "pumped",
        "electrified", "ecstatic", "exhilarated", "energetic", "hyper"
    ),
    "frustration": (
        "frustrated", "annoyed", "exasperated", "fed up", "stuck", "defeated",
        "aggravated", "bothered", "impatient", "discontented"
    ),
    "uncertainty": (
        "uncertain", "confused", "unsure", "hesitant", "ambivalent", "lost",
        "doubtful", "torn", "perplexed", "second guessing", "unclear", "puzzled"
    ),
}

FIRST_PERSON_PATTERNS = (
    re.compile(r"\b(i feel|i am feeling|i'm feeling|i felt|makes me feel|i am so|i'm so|inside me|to me)\b", re.IGNORECASE),
    re.compile(r"\b(i am|i'm|myself|my heart|my mind|my life)\b", re.IGNORECASE),
)

THIRD_PERSON_PATTERNS = (
    re.compile(r"\b(he is|he was|he seemed|he feels|she is|she was|she seemed|she feels|they are|they were|they seemed|they feel|my friend|my brother|my sister|my mom|my dad|people are|everyone is|someone)\b", re.IGNORECASE),
)

NEGATION_PATTERNS = (
    re.compile(r"\b(not|never|hardly|scarcely|barely|no longer|without)\s+(?:really\s+|very\s+|feeling\s+)?(\w+)", re.IGNORECASE),
)


@dataclass(frozen=True)
class EmotionCue:
    emotion: str
    intensity: str  # mild, moderate, pronounced
    evidence_terms: tuple[str, ...]
    score: float


@dataclass(frozen=True)
class EmotionAnalysis:
    cues_detected: tuple[EmotionCue, ...]
    primary_emotions: tuple[str, ...]
    is_self_reported: bool
    is_third_person_or_external: bool
    ambiguity_or_uncertainty_present: bool
    distinction_advisory: str
    uninferrable_limitations: tuple[str, ...]
    raw_scores: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cues_detected": [
                {
                    "emotion": c.emotion,
                    "intensity": c.intensity,
                    "evidence_terms": list(c.evidence_terms),
                    "score": round(c.score, 4),
                }
                for c in self.cues_detected
            ],
            "primary_emotions": list(self.primary_emotions),
            "is_self_reported": self.is_self_reported,
            "is_third_person_or_external": self.is_third_person_or_external,
            "ambiguity_or_uncertainty_present": self.ambiguity_or_uncertainty_present,
            "distinction_advisory": self.distinction_advisory,
            "uninferrable_limitations": list(self.uninferrable_limitations),
            "raw_scores": {k: round(v, 4) for k, v in self.raw_scores.items()},
        }


class EmotionRecognizer:
    """Analyzes multi-label emotional signals with self-report and clinical boundaries."""

    def __init__(self, custom_lexicon_path: str | None = None):
        self._lexicon = dict(EMOTION_CUE_LEXICON)
        if custom_lexicon_path and os.path.isfile(custom_lexicon_path):
            try:
                with open(custom_lexicon_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "lexicon" in data:
                        # Incorporate statistical emotion lexicon distributions where available
                        for word, dist in data["lexicon"].items():
                            if isinstance(dist, dict):
                                for em_name, p in dist.items():
                                    em_key = em_name.lower()
                                    if em_key in self._lexicon and p > 0.25 and word not in self._lexicon[em_key]:
                                        self._lexicon[em_key] = tuple(self._lexicon[em_key]) + (word,)
            except Exception:
                pass

    def analyze(self, text: str) -> EmotionAnalysis:
        if not text or not text.strip():
            return EmotionAnalysis(
                cues_detected=(),
                primary_emotions=(),
                is_self_reported=False,
                is_third_person_or_external=False,
                ambiguity_or_uncertainty_present=False,
                distinction_advisory="No emotional cues detected in empty text.",
                uninferrable_limitations=(
                    "Text is empty; psychological states cannot be inferred.",
                ),
                raw_scores={e: 0.0 for e in EMOTION_CATEGORIES},
            )

        lower = text.lower()
        words = set(re.findall(r"[a-z']+", lower))

        # Check negation context
        negated_targets: set[str] = set()
        for match in re.finditer(r"\b(not|never|don't|no|hardly)\s+(\w+)", lower):
            negated_targets.add(match.group(2))

        # Self-reported vs third-person detection
        is_self_reported = any(bool(p.search(lower)) for p in FIRST_PERSON_PATTERNS)
        is_third_person = any(bool(p.search(lower)) for p in THIRD_PERSON_PATTERNS)

        cues: list[EmotionCue] = []
        scores: dict[str, float] = {}

        for emotion, term_list in self._lexicon.items():
            matched_terms: list[str] = []
            for term in term_list:
                if " " in term:
                    if term in lower:
                        matched_terms.append(term)
                else:
                    if term in words and term not in negated_targets:
                        matched_terms.append(term)

            count = len(matched_terms)
            score = min(1.0, count * 0.35)
            scores[emotion] = score

            if count > 0:
                intensity = "pronounced" if count >= 3 else "moderate" if count >= 2 else "mild"
                cues.append(
                    EmotionCue(
                        emotion=emotion,
                        intensity=intensity,
                        evidence_terms=tuple(sorted(set(matched_terms))),
                        score=score,
                    )
                )

        # Sort cues by score descending
        cues.sort(key=lambda c: c.score, reverse=True)
        primary_emotions = tuple(c.emotion for c in cues if c.score >= 0.3)

        has_uncertainty = (
            "uncertainty" in primary_emotions
            or bool(re.search(r"\b(i don't know|not sure|maybe|perhaps|confused)\b", lower))
        )

        # Build clinical distinction advisory
        distinctions: list[str] = []
        if "sadness" in primary_emotions:
            distinctions.append("Observed sadness is an emotional cue, not clinical depression.")
        if "excitement" in primary_emotions:
            distinctions.append("Observed excitement is an affective state, not a bipolar manic symptom.")
        if "anxiety_related" in primary_emotions:
            distinctions.append("Expressed tension or nervousness represents an anxiety cue, not an anxiety disorder diagnosis.")
        if not distinctions:
            distinctions.append("Observed emotional cues represent momentary textual expression, not clinical psychiatric conditions.")

        distinction_advisory = " ".join(distinctions)

        limitations = (
            "Textual emotion cues do not measure chronicity or functional impairment.",
            "Linguistic expression may reflect conversational style rather than felt emotion.",
            "No clinical diagnosis or psychiatric validity is implied by detected emotion labels.",
        )

        return EmotionAnalysis(
            cues_detected=tuple(cues),
            primary_emotions=primary_emotions,
            is_self_reported=is_self_reported,
            is_third_person_or_external=is_third_person,
            ambiguity_or_uncertainty_present=has_uncertainty,
            distinction_advisory=distinction_advisory,
            uninferrable_limitations=limitations,
            raw_scores=scores,
        )
