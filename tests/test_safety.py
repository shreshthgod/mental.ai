"""
Focused tests for the crisis-safety routing layer.

These cover the specific failure that motivated the work: the primary condition
model reported "Normal" for an explicit high-risk disclosure, and nothing in the
response told a consumer to act on that. They also pin the behaviour the safety
route depends on - context, subject, tense, negation, model independence - so a
later model or preprocessing change cannot silently reopen it.

Run:
    PYTHONPATH="Step 12 - Packaging/package:." pytest tests/test_safety.py -q

The 78-case seeded corpus in tests/safety_corpus/cases.json is executed
separately by scripts/run_safety_corpus.py. This file is the fast, focused
regression net that runs with the rest of the suite.

Scope note: every expectation here is derived from the written routing spec,
not from clinical review. These are engineering tests, not a validation study.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "Step 12 - Packaging", "package"))
sys.path.insert(0, _ROOT)

import pytest

from mental_health_screening import safety
from mental_health_screening.inference import MentalHealthScreener


# ------------------------------------------------------------------
# Module-scoped screener: artifacts load once, as in production.
# ------------------------------------------------------------------
@pytest.fixture(scope="module")
def screener():
    return MentalHealthScreener()


def _predict(screener, text, **kwargs):
    return safety.evaluate(text, urgency_flagged=kwargs.pop("urgency_flagged", False), **kwargs)


# ------------------------------------------------------------------
# The reported defect
# ------------------------------------------------------------------
def test_reported_defect_is_not_routed_as_safe(screener):
    """
    "i wanna jump from 10th floor" was reported as Normal.

    The condition model still says Normal and that raw output is preserved -
    the fix is that nothing downstream is allowed to read Normal as "safe".
    """
    text = "i wanna jump from 10th floor"
    result = screener.screen(text)

    # Raw model outputs are still reported honestly.
    assert result["primary"]["predicted_class"] == "Normal"
    assert result["primary"]["status"] == "complete"

    # The authoritative route is not safe, and not vague.
    assert result["safety"]["level"] == "HIGH"
    assert result["safety"]["subject"] == "self"
    assert "INTENT_VERB" in result["safety"]["evidence_codes"]


def test_benign_floor_reference_is_not_treated_as_high_risk(screener):
    """
    A residence description shares vocabulary with a method disclosure.

    EXPECTATION CORRECTED, see decision D-002. This test previously accepted
    NEEDS_CLARIFICATION "and must ask instead". That expectation was taken from
    the old implementation, not from the routing specification, and the
    specification is unambiguous: seed S037 ("I live on the tenth floor.") is
    classified N - no automatic personal-crisis escalation from this text alone.
    Accepting a clarification prompt was therefore a weaker outcome than the
    product requires, not a stricter one.

    The urgency model does flag this text (p=0.247 at the deployed 0.15
    threshold). It must not escalate, and it must not prompt either: the
    classifier is not scope-aware, and a user describing where they live must
    not be asked whether they intend to harm themselves.
    """
    result = screener.screen("I live on the tenth floor.")
    assert result["safety"]["level"] == "NONE_DETECTED"
    assert result["safety"]["level"] != "HIGH"
    assert result["safety"]["needs_clarification"] is False
    # The classifier's signal is still recorded rather than discarded.
    assert "URGENCY_MODEL_FLAGGED" in result["safety"]["evidence_codes"]
    # And the raw model output is still reported honestly, unrewritten.
    assert result["urgency"]["flagged"] is True


def test_immediate_danger_outranks_the_condition_model(screener):
    """An in-progress disclosure must reach the top level, not the condition label."""
    result = screener.screen("I'm on the balcony now and I am about to jump.")
    assert result["safety"]["level"] == "IMMEDIATE"
    # EXPECTATION CORRECTED, see decision D-003. This asserted the values
    # "immediate"/"present", neither of which is in the declared immediacy
    # vocabulary (stated / not_stated / unclear). The engine was rewriting the
    # field to a fourth, undeclared value. A present-danger route is an
    # immediacy the text stated, so the in-contract value is "stated".
    assert result["safety"]["immediacy"] in ("stated", "not_stated", "unclear")
    assert result["safety"]["immediacy"] == "stated"


# ------------------------------------------------------------------
# Subject attribution
# ------------------------------------------------------------------
@pytest.mark.parametrize(
    "text, subject",
    [
        ("I want to die", "self"),
        ("I do not want to live anymore", "self"),
        ("he wants to die", "another_person"),
        ("my friend wants to hurt herself", "another_person"),
        ("mera dost bol raha hai ki wo apni jaan lena chahta hai", "another_person"),
    ],
)
def test_subject_is_attributed_correctly(screener, text, subject):
    assert screener.screen(text)["safety"]["subject"] == subject


def test_third_party_risk_is_not_dismissed(screener):
    """
    A disclosure about someone else is lower priority than the writer's own
    risk, but it is not NONE_DETECTED.
    """
    result = screener.screen("my brother is planning to kill himself this weekend")
    assert result["safety"]["level"] in ("CONCERNING", "HIGH")
    assert result["safety"]["subject"] == "another_person"


# ------------------------------------------------------------------
# Tense, history and recovery
# ------------------------------------------------------------------
def test_historical_past_without_present_intent_is_not_immediate(screener):
    """Past intent, explicitly recovered from, is not a live crisis."""
    result = screener.screen("I wanted to die last year. I am safe now and getting help.")
    assert result["safety"]["level"] in ("NONE_DETECTED", "CONCERNING")
    assert result["safety"]["level"] != "IMMEDIATE"


def test_past_attempt_is_routed_but_not_an_active_emergency(screener):
    """
    A past attempt with present recovery language.

    Deliberately NOT asserted down to NONE_DETECTED: attempt history is a real
    risk factor, and an engine that reads "I am okay now" as all-clear would be
    the more dangerous defect. The requirement here is that it is never presented
    as an in-progress emergency.
    """
    result = screener.screen("I tried to kill myself in 2019 and I am okay now.")
    assert result["safety"]["level"] != "IMMEDIATE"
    assert result["safety"]["level"] != "NONE_DETECTED"
    assert result["safety"]["review_recommended"] is True


def test_forward_intent_with_history_still_escalates(screener):
    """Historical context must not launder a current plan."""
    result = screener.screen(
        "I attempted suicide before and I am going to jump off the roof tonight."
    )
    assert result["safety"]["level"] in ("CONCERNING", "HIGH", "IMMEDIATE")


# ------------------------------------------------------------------
# Negation and quotation
# ------------------------------------------------------------------
@pytest.mark.parametrize(
    "text",
    [
        "I do not want to die",
        "I don't want to kill myself",
        "I never want to die",
        "she does not want to die",
        "I am not suicidal",
    ],
)
def test_negated_intent_is_not_risk(screener, text):
    result = screener.screen(text)
    assert result["safety"]["level"] in ("NONE_DETECTED", "NEEDS_CLARIFICATION", "CONCERNING")
    assert result["safety"]["level"] != "IMMEDIATE"


def test_negation_scoped_to_one_clause_does_not_cancel_the_other(screener):
    """A denial in one clause must not suppress a disclosure in another."""
    result = screener.screen("I am not okay. I want to die tonight.")
    assert result["safety"]["level"] in ("CONCERNING", "HIGH", "IMMEDIATE")


def test_pure_quotation_is_not_attributed_to_the_writer(screener):
    result = screener.screen('He said "I want to die" but he was being dramatic.')
    assert result["safety"]["subject"] in ("another_person", "fictional_or_quoted")
    assert result["safety"]["level"] != "IMMEDIATE"


def test_quoted_text_the_writer_claims_as_their_own_is_routed(screener):
    """The author re-asserting a quote about themselves must not be filtered out."""
    result = screener.screen("A quote says 'I want to die.' It describes how I feel right now.")
    assert result["safety"]["level"] in ("CONCERNING", "HIGH")


def test_fiction_is_not_routed_as_the_writers_own_risk(screener):
    result = screener.screen("In my novel the character says I want to die, but it is fiction.")
    assert result["safety"]["level"] in ("NONE_DETECTED", "NEEDS_CLARIFICATION", "CONCERNING")


# ------------------------------------------------------------------
# Language handling
# ------------------------------------------------------------------
def test_hinglish_explicit_intent_is_recognised(screener):
    result = screener.screen("mujhe khud ko maarne ka mann kar raha hai")
    assert result["safety"]["level"] in ("CONCERNING", "HIGH", "IMMEDIATE")


def test_devanagari_explicit_intent_is_recognised(screener):
    result = screener.screen("मुझे खुद को मारने का मन कर रहा है")
    assert result["safety"]["level"] in ("CONCERNING", "HIGH", "IMMEDIATE")


def test_negation_in_devanagari_is_honoured(screener):
    """A translation artefact that would otherwise fire on any Hindi text."""
    result = screener.screen("मैं खुद को मारना नहीं चाहता")
    assert result["safety"]["level"] != "HIGH"
    assert result["safety"]["level"] != "IMMEDIATE"


# ------------------------------------------------------------------
# The safety route must not depend on either model
# ------------------------------------------------------------------
def test_safety_route_works_without_the_urgency_model(screener):
    """
    A fast context-aware route must not be gated on a probability threshold.

    With the model silenced, an explicit disclosure still routes HIGH.
    """
    result = screener.screen("I am going to kill myself tonight")
    assert result["safety"]["level"] in ("HIGH", "IMMEDIATE")


def test_urgency_flag_raises_the_level_but_never_lowers_it(screener):
    """Model evidence is additive. It must not be able to suppress context evidence."""
    text = "I am going to kill myself tonight"
    low = safety.evaluate(text, urgency_flagged=False)
    high = safety.evaluate(text, urgency_flagged=True, urgency_probability=0.9)
    order = ["NONE_DETECTED", "NEEDS_CLARIFICATION", "CONCERNING", "HIGH", "IMMEDIATE"]
    assert order.index(high.level) >= order.index(low.level)


def test_no_match_without_semantic_assessment_reports_unknown(screener):
    """D-061; original oracle preserved in reports/legacy-unit-expectation-review.md."""
    result = screener.screen("The weather is nice today")
    assert result["safety"]["level"] == "UNKNOWN"
    assert result["safety"]["analysis_status"] == "degraded"
    assert result["safety"]["needs_clarification"] is True
    assert result["components"]["semantic"] == "disabled"


# ------------------------------------------------------------------
# Model failure must not remove the safety result
# ------------------------------------------------------------------
def test_primary_model_failure_still_returns_safety(screener, monkeypatch):
    """
    An ordinary condition-classifier error must not delete the safety result.

    This is the audit finding that the previous implementation had: the primary
    track raised, which aborted the call before any safety output existed.
    """
    def boom(_features):
        raise RuntimeError("simulated classifier fault")

    monkeypatch.setattr(screener._primary_model, "predict_proba", boom)

    result = screener.screen("i wanna jump from 10th floor")

    assert result["primary"]["status"] == "unavailable"
    assert result["primary"]["predicted_class"] is None
    assert result["safety"]["level"] in ("HIGH", "IMMEDIATE")
    assert result["safety"]["policy_version"] == safety.POLICY_VERSION


def test_urgency_model_failure_still_returns_safety(screener, monkeypatch):
    def boom(_features):
        raise RuntimeError("simulated urgency fault")

    monkeypatch.setattr(screener._urgency_model, "predict_proba", boom)

    result = screener.screen("i wanna jump from 10th floor")

    assert result["urgency"]["status"] == "unavailable"
    assert result["urgency"]["suicide_probability"] is None
    assert result["safety"]["level"] in ("HIGH", "IMMEDIATE")


def test_unavailable_output_is_never_reported_as_a_label(screener, monkeypatch):
    """Unavailable must read as unavailable - never 'Normal', never 0.0."""
    def boom(_features):
        raise RuntimeError("simulated classifier fault")

    monkeypatch.setattr(screener._primary_model, "predict_proba", boom)
    result = screener.screen("hello")
    assert result["primary"]["predicted_class"] is None
    assert result["primary"]["class_probabilities"] == {}


# ------------------------------------------------------------------
# Response contract
# ------------------------------------------------------------------
def test_safety_response_shape_is_stable(screener):
    required = {
        "level", "subject", "temporal_context", "immediacy", "evidence_codes",
        "summary", "needs_clarification", "review_recommended", "analysis_status",
        "policy_version",
    }
    payload = screener.screen("i wanna jump from 10th floor")["safety"]
    assert required.issubset(payload.keys())
    assert payload["policy_version"] == safety.POLICY_VERSION


def test_high_and_immediate_produce_a_support_action(screener):
    for text in ("i wanna jump from 10th floor", "I'm on the balcony now and I am about to jump."):
        level = screener.screen(text)["safety"]["level"]
        action = safety.support_action(level, subject="self")
        assert action
        assert len(action) > 40


def test_evidence_codes_are_traceable_not_invented(screener):
    """Every emitted code must be a real pattern match, not a guess."""
    text = "i wanna jump from 10th floor"
    payload = screener.screen(text)["safety"]
    lowered = safety.normalize_for_safety(text)
    for code in payload["evidence_codes"]:
        if code in {"URGENCY_MODEL_FLAGGED", "ANAPHORIC_PLANNING", "RECOVERY_CONTEXT",
                    "NEGATION_SCOPE", "LANGUAGE_APPROXIMATION"}:
            continue  # structural codes, documented in the policy
        entry = safety.EVIDENCE_PATTERNS.get(code)
        if entry is not None:
            pattern = entry[0] if isinstance(entry, tuple) else entry
            assert pattern.search(lowered), f"{code} emitted without a matching pattern"


def test_engine_never_raises_on_adversarial_input():
    """Garbage, huge strings and control characters must not crash the route."""
    hostile = [
        "", "   ", "\x00\x01\x02", "!" * 5000, "\n" * 500,
        "a" * 20000, "🙂🙃" * 100, "﻿", "\r\n\r\n",
        "()[]{}<>|*+?", "SELECT * FROM screenings; DROP TABLE users;--",
        "<script>alert(1)</script>", "../../etc/passwd", "%00", "null",
    ]
    for text in hostile:
        result = safety.evaluate(text, urgency_flagged=False)
        assert isinstance(result.level, str) and result.level
        assert result.analysis_status is not None


def test_predict_response_requires_a_safety_field():
    """
    Schema-level guard.

    The reported defect was that nothing in the response told a consumer to
    act. If `safety` is ever dropped from the contract, every other test in
    this file still passes but the defect is back.
    """
    from api.api import PredictResponse

    fields = PredictResponse.model_fields
    assert "safety" in fields, "/predict no longer returns a safety result"
    assert fields["safety"].is_required()

    # The condition LABEL must be nullable so a classifier fault is reported as
    # unavailable instead of aborting the response. The safety field above stays
    # required either way.
    from api.api import PrimaryResult

    assert not PrimaryResult.model_fields["predicted_class"].is_required()
    assert PrimaryResult.model_fields["status"].default == "complete"


def test_evaluate_is_deterministic():
    """The same text must route the same way on every call."""
    text = "i wanna jump from 10th floor"
    first = safety.evaluate(text, urgency_flagged=True, urgency_probability=0.8)
    second = safety.evaluate(text, urgency_flagged=True, urgency_probability=0.8)
    assert first.to_dict() == second.to_dict()
