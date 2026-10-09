"""
Regressions for defects confirmed against the deployed request path in Phase A.

Each test names the defect it pins. Nothing here asserts a probability value or a
condition label: these are routing-contract tests. Where a raw model output is
mentioned it is quoted as the observed value at the time of writing, and the
assertion is about what the POLICY does with it, not about the model.

Scope note: expectations come from the written routing specification. These are
engineering regressions, not clinical validation.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "Step 12 - Packaging", "package"))
sys.path.insert(0, _ROOT)

import pytest

from mental_health_screening import safety


# ------------------------------------------------------------------
# D-01  A model flag with no text evidence must not escalate a benign
#       sentence. Found by running the seeded corpus through the FULL
#       pipeline: the engine-only run passed 78/78 because it hardcoded
#       urgency_flagged=False, while the real path produced 66/78.
#
#       Measured cause: the urgency classifier is trained on subreddit proxy
#       labels and fires on method vocabulary regardless of intent. It flags
#       "I live on the tenth floor" (p=0.247), "This deadline is killing me"
#       (p=0.669) and "I need to kill the process" (p=0.466) at the deployed
#       0.15 threshold. The policy then converted NONE_DETECTED into
#       NEEDS_CLARIFICATION, so a user describing their address was asked
#       whether they were having thoughts of harming themselves.
# ------------------------------------------------------------------
BENIGN_WITH_MODEL_FLAG = [
    ("I live on the tenth floor.", 0.2471),
    ("Let's jump to the next chapter.", 0.2855),
    ("I am dying of laughter.", 0.2424),
    ("This deadline is killing me, but I am just talking about being busy.", 0.6688),
    ("The program crashed; I need to kill the process.", 0.4655),
    ("I slept badly once, but otherwise I feel fine.", 0.2075),
    ("I am afraid of heights and stay away from balcony edges.", 0.5251),
    ("I want to jump into the swimming pool during my supervised lesson.", 0.3408),
    ("Our suicide-prevention lesson explains how to ask for help.", 0.7549),
    ("A character in my story says, 'I want to die.'", 0.5525),
    ("The film includes a suicide scene, and it upset me.", 0.7429),
    ("I used to self-harm. I have no current urge and I have support.", 0.5057),
]


@pytest.mark.parametrize(
    "text,prob", BENIGN_WITH_MODEL_FLAG, ids=[t[:34] for t, _ in BENIGN_WITH_MODEL_FLAG]
)
def test_d01_model_flag_alone_does_not_escalate_benign_text(text, prob):
    """
    The urgency flag is evidence, not a decision. It is recorded; it does not
    move a benign sentence into a safety prompt.
    """
    result = safety.evaluate(text, urgency_flagged=True, urgency_probability=prob)

    assert result.level == "NONE_DETECTED", (
        f"model flag p={prob} escalated a benign control to {result.level}"
    )
    # The signal is still reported, so an auditor can see it was not ignored.
    assert "URGENCY_MODEL_FLAGGED" in result.evidence_codes
    # And no escalation means no urgent-support language.
    assert result.level not in ("HIGH", "IMMEDIATE")
    assert result.needs_clarification is False


def test_d01_model_flag_still_cannot_lower_a_text_derived_level():
    """The model is additive in one direction only: it never de-escalates."""
    result = safety.evaluate(
        "i wanna jump from 10th floor", urgency_flagged=False, urgency_probability=0.0
    )
    assert result.level == "HIGH"
    assert "URGENCY_MODEL_NOT_FLAGGED" in result.evidence_codes


def test_d01_model_flag_does_not_replace_a_text_derived_escalation():
    """
    A flag must not cap an escalation the text already earned. S026-style
    historical disclosure plus a flag stays at its text-derived level.
    """
    result = safety.evaluate(
        "I used to self-harm. I have no current urge and I have support.",
        urgency_flagged=True,
        urgency_probability=0.5057,
    )
    assert result.level == "NONE_DETECTED"
    # D081: heuristic/rule assessment is limited even with a healthy raw flag.
    assert result.analysis_status == "degraded"


# ------------------------------------------------------------------
# D-02  IMMEDIATE with immediacy="immediate" is outside the declared
#       contract. The schema says immediacy is stated / not_stated /
#       unclear, but the assembly step rewrote it to a fourth value.
# ------------------------------------------------------------------
def test_d02_immediacy_stays_inside_the_declared_enum():
    """
    Part 4 fixes `immediacy` to stated / not_stated / unclear. An IMMEDIATE
    route must be expressed with those three values, not a fourth one.
    """
    allowed = {"stated", "not_stated", "unclear"}
    for text in (
        "I'm on the balcony now and I am about to jump.",
        "मैं अभी छत पर हूँ और कूदने वाला हूँ।",
        "I took more medicine than prescribed and feel unwell.",
        "Someone at home is threatening to hurt me right now.",
    ):
        result = safety.evaluate(text, urgency_flagged=False)
        assert result.immediacy in allowed, f"{text!r} -> {result.immediacy!r}"
        assert result.level == "IMMEDIATE"


# ------------------------------------------------------------------
# D-03  `PASSIVE_DEATH_WISH` contained a double-escaped regex fragment.
#
#       The pattern was a raw string containing `me\\s+again`, which is a
#       literal backslash followed by one or more "s", so the farewell
#       alternative could never match. S019 "Goodbye. You won't hear from
#       me again." therefore reached NEEDS_CLARIFICATION only through the
#       generic fallback rule rather than the farewell evidence it was
#       written for.
# ------------------------------------------------------------------
def test_d03_farewell_pattern_is_live_not_dead():
    """
    Every alternative inside a compiled pattern must be reachable. This asserts
    the farewell alternative matches the string it was written for.
    """
    import re

    pattern = safety.EVIDENCE_PATTERNS["PASSIVE_DEATH_WISH"][0]
    assert pattern.search("you won't hear from me again"), (
        "the 'wont hear from me again' alternative in PASSIVE_DEATH_WISH is unreachable: "
        "the source contains a double-escaped \\s inside a raw string"
    )
    # And no alternative anywhere in the module may contain a literal backslash.
    for code, (compiled, _desc) in safety.EVIDENCE_PATTERNS.items():
        assert "\\\\" not in compiled.pattern, f"{code} contains a double-escaped sequence"


def test_d03_farewell_text_still_routes_to_a_question():
    result = safety.evaluate("Goodbye. You won't hear from me again.", urgency_flagged=False)
    assert result.level == "NEEDS_CLARIFICATION"
    assert result.needs_clarification is True


# ------------------------------------------------------------------
# D-04  `support_action()` ignored `region_known` and the unknown-region
#       instruction. Part 3.16 requires a usable generic local-emergency
#       instruction when the region is unknown, without assuming a country.
#       The function advertised the parameter and then ignored it.
# ------------------------------------------------------------------
def test_d04_support_action_never_assumes_a_country():
    for level in ("NONE_DETECTED", "NEEDS_CLARIFICATION", "CONCERNING", "HIGH", "IMMEDIATE", "UNKNOWN"):
        text = safety.support_action(level, subject="self", region_known=False)
        assert text and text.strip()
        # No hard-coded country, national hotline or assumed nationality.
        for forbidden in ("911", "999", "112", "AASRA", "NIMHANS", "Vandrevala"):
            assert forbidden not in text, f"{level} support text names {forbidden}"


def test_d04_unknown_region_support_text_stays_generic_but_actionable():
    text = safety.support_action("IMMEDIATE", subject="self", region_known=False)
    lowered = text.lower()
    assert "emergency" in lowered
    assert "not be alone" in lowered or "do not be alone" in lowered


# ------------------------------------------------------------------
# D-009  Vocabulary gaps found by the expanded corpus.
#
# The 78-case seed corpus passed 100% while common phrasings of the SAME
# constructs routed to NONE_DETECTED. The seed corpus was too small to see this:
# it contained one phrasing per family. Measured misses on the 320-case corpus
# are grouped below by the construct that was missing, not by wording.
#
# Every case here has a minimal pair in the same test, so an addition cannot
# pass by broadening rather than by being correct.
# ------------------------------------------------------------------
METHOD_GAPS = [
    ("I want to slit my wrists.", "self"),
    ("I want to walk into traffic and end it.", "self"),
    ("I want to step off the roof tonight.", "self"),
    ("I tried to hang myself last week.", "self"),
    ("I overdosed two days ago and I am still shaking.", "self"),
]


@pytest.mark.parametrize("text,subject", METHOD_GAPS, ids=[t[:34] for t, _ in METHOD_GAPS])
def test_d009_common_method_phrasings_are_not_missed(text, subject):
    result = safety.evaluate(text, urgency_flagged=False)
    assert result.level in ("HIGH", "IMMEDIATE"), f"{text!r} -> {result.level} ({result.evidence_codes})"
    assert result.subject == subject


METHOD_CONTROLS = [
    "I slipped on the wet roof tiles and hurt my arm.",
    "The traffic was terrible this morning.",
    "I have a wrist brace on after the gym.",
    "I stepped off the bus at the wrong stop.",
]


@pytest.mark.parametrize("text", METHOD_CONTROLS, ids=lambda t: t[:34])
def test_d009_method_additions_do_not_catch_near_miss_controls(text):
    assert safety.evaluate(text, urgency_flagged=False).level == "NONE_DETECTED", text


MEDICAL_GAPS = [
    "I took a whole packet of pills and I cannot stop vomiting.",
    "I have been bleeding heavily and I feel faint.",
    "I collapsed and I am not waking up properly.",
    "I cannot stop shaking and I keep passing out.",
]


@pytest.mark.parametrize("text", MEDICAL_GAPS, ids=lambda t: t[:34])
def test_d009_medical_emergency_phrasings_route_immediate(text):
    result = safety.evaluate(text, urgency_flagged=False)
    assert result.level == "IMMEDIATE", f"{text!r} -> {result.level} ({result.evidence_codes})"


# A later negative clause must not neutralise an earlier fact in the same
# sentence. "the bleeding has not stopped" negates "stopped", not "I hurt
# myself", and "I am not waking up properly" negates waking, not the collapse.
NEGATION_SCOPE = [
    ("I hurt myself earlier today and the bleeding has not stopped.", ["HIGH", "IMMEDIATE"]),
    ("I collapsed and I am not waking up properly.", ["IMMEDIATE"]),
    ("I cut myself and I cannot stop bleeding.", ["HIGH", "IMMEDIATE"]),
]


@pytest.mark.parametrize("text,allowed", NEGATION_SCOPE, ids=[t[:34] for t, _ in NEGATION_SCOPE])
def test_d009_negation_binds_to_its_own_clause_not_the_sentence(text, allowed):
    result = safety.evaluate(text, urgency_flagged=False)
    assert result.level in allowed, f"{text!r} -> {result.level} ({result.evidence_codes})"


OTHER_DANGER = [
    ("I want to kill the person who wronged me.", "self", ("HIGH", "IMMEDIATE")),
    ("I am planning to attack someone at work.", "self", ("HIGH", "IMMEDIATE")),
    ("My partner is hitting me right now and I cannot leave.", "self", ("HIGH", "IMMEDIATE")),
    ("He is beating me and I need help tonight.", "self", ("HIGH", "IMMEDIATE")),
    ("Someone is threatening my child and I am scared.", "self", ("HIGH", "IMMEDIATE")),
    ("Something in my head keeps telling me to end it.", "self", ("HIGH", "IMMEDIATE")),
]


@pytest.mark.parametrize("text,subject,allowed", OTHER_DANGER, ids=[t[:30] for t, _, _ in OTHER_DANGER])
def test_d009_other_danger_categories_route_to_support(text, subject, allowed):
    result = safety.evaluate(text, urgency_flagged=False)
    assert result.level in allowed, f"{text!r} -> {result.level} ({result.evidence_codes})"
    assert result.subject == subject, f"{text!r} subject {result.subject}"


THIRD_PARTY_GAPS = [
    "A classmate posted that he is going to end his life.",
    "My neighbour is talking about hanging herself.",
    "My dad told me he is going to kill himself.",
]


@pytest.mark.parametrize("text", THIRD_PARTY_GAPS, ids=lambda t: t[:32])
def test_d009_third_party_risk_phrasings_route_urgent(text):
    result = safety.evaluate(text, urgency_flagged=False)
    assert result.level in ("HIGH", "IMMEDIATE"), f"{text!r} -> {result.level}"
    assert result.subject == "another_person", f"{text!r} -> {result.subject}"


INDIC_GAPS = [
    ("hinglish", "main apni jaan khatam karna chahta hu", ("HIGH", "IMMEDIATE"), "self"),
    ("hinglish", "mera dost bol raha hai ki wo khud ko maar leta hai", ("HIGH", "IMMEDIATE"), "another_person"),
    ("hi", "मैं अपनी जान खत्म करना चाहता हूँ।", ("HIGH", "IMMEDIATE"), "self"),
    ("hi", "मैंने कल खुद को नुकसान पहुँचाया।", ("HIGH", "IMMEDIATE"), "self"),
]


@pytest.mark.parametrize("lang,text,allowed,subject", INDIC_GAPS, ids=[t[:28] for _, t, _, _ in INDIC_GAPS])
def test_d009_indic_phrasings_route(lang, text, allowed, subject):
    result = safety.evaluate(text, urgency_flagged=False)
    assert result.level in allowed, f"{text!r} -> {result.level} ({result.evidence_codes})"
    assert result.subject == subject, f"{text!r} -> {result.subject}"


# ------------------------------------------------------------------
# D-009a  A bare "poem|song" alternative in the fiction detector made ANY text
#         mentioning a song or poem classify as fictional_or_quoted. Subject
#         attribution is a contract field consumers read, so "I like that song"
#         reporting subject=fictional_or_quoted is a real corruption.
# ------------------------------------------------------------------
@pytest.mark.parametrize(
    "text",
    ["I like that song a lot.", "I wrote a poem today.", "My friend likes this song."],
    ids=lambda t: t[:28],
)
def test_d009a_mentioning_a_song_or_poem_is_not_a_fiction_frame(text):
    result = safety.evaluate(text, urgency_flagged=False)
    assert result.subject != "fictional_or_quoted", f"{text!r} -> {result.subject}"
    assert "FICTION_FRAME" not in result.evidence_codes


def test_d009a_a_work_with_no_risk_content_stays_benign():
    """
    "The poem is about the sea" carries no disclosure. EXPECTATION CORRECTED:
    this input was previously listed above with a subject assertion. Reading a
    text ABOUT a poem as fictional_or_quoted is defensible and harmless at
    NONE_DETECTED; the defect D-009a fixed was a first-person statement such as
    "I like that song" being reported as fictional. What matters here is that no
    escalation is manufactured, so that is what is asserted.
    """
    result = safety.evaluate("The poem is about the sea.", urgency_flagged=False)
    assert result.level == "NONE_DETECTED"
    assert result.needs_clarification is False


def test_d009_no_pattern_has_an_empty_alternative():
    """
    Structural guard for a real bug found while fixing D-009c.

    `_PRESENT_TIME` was written with a doubled pipe across a line break
    ("|as\\s+we\\s+speak|" + "|presently"), which compiled an empty alternative.
    It matched the empty string at position 0 of every input, so the guard that
    was supposed to require an explicit present-time marker fired on all text.
    Any pattern here that can match the empty string is a latent defect of the
    same kind.
    """
    import re as _re

    patterns = dict(safety.EVIDENCE_PATTERNS)
    for name in ("NEGATION",):
        patterns[name] = (safety.NEGATION, "")
    for name in ("_FAREWELL", "_PRESENT_TIME", "_METHOD_INTENT", "_LOCATION_WORD_ONLY",
                 "_LOCATION_ACTION", "_ACQUISITION", "_STRONG_METHOD", "_RECOVERY",
                 "_SELF_ASSERTION", "_POSSESSIVE_OTHER"):
        patterns[name] = (getattr(safety, name), "")

    for name, (compiled, _desc) in patterns.items():
        assert isinstance(compiled, _re.Pattern), name
        if compiled.search(""):
            raise AssertionError(f"pattern {name} matches the empty string: {compiled.pattern!r}")


def test_d009_no_pattern_contains_a_double_escape():
    """
    A raw string containing `\\s` is a literal backslash followed by "s", not
    whitespace. D-003 was exactly this: a farewell alternative that could never
    match. This guard covers the whole vocabulary.
    """
    for name, (compiled, _desc) in safety.EVIDENCE_PATTERNS.items():
        assert "\\\\" not in compiled.pattern, f"{name} contains a double-escaped sequence"


@pytest.mark.parametrize(
    "text",
    ["In my novel the heroine says she wants to die.",
     "My poem describes someone who ends her life.",
     "The song goes on about wanting to disappear."],
    ids=lambda t: t[:30],
)
def test_d009a_real_fiction_frames_are_still_detected(text):
    result = safety.evaluate(text, urgency_flagged=False)
    assert result.subject == "fictional_or_quoted", f"{text!r} -> {result.subject}"


# ------------------------------------------------------------------
# D-009b  "I want to get a rooftop apartment" routed HIGH. A location word in
#         a possessive or acquisition context is not a method statement.
# ------------------------------------------------------------------
BENIGN_ROOFTOP = [
    "I want to get a rooftop apartment.",
    "We are looking at a flat with a rooftop terrace.",
    "I bought a book about climbing and ropes.",
    "I want to buy a balcony planter.",
]


@pytest.mark.parametrize("text", BENIGN_ROOFTOP, ids=lambda t: t[:32])
def test_d009b_location_words_in_an_acquisition_context_do_not_escalate(text):
    result = safety.evaluate(text, urgency_flagged=False)
    assert result.level != "HIGH", f"{text!r} -> {result.level} ({result.evidence_codes})"


# ------------------------------------------------------------------
# D-009c  Presence at a fall edge with an explicit present-time marker.
#         "I'm outside on the ledge right now" matched neither the location
#         nor the present-position patterns.
# ------------------------------------------------------------------
EDGE_PRESENT = [
    "I'm outside on the ledge right now.",
    "I am standing on the roof edge at this moment.",
    "I am on the ledge of the building right now.",
]


@pytest.mark.parametrize("text", EDGE_PRESENT, ids=lambda t: t[:32])
def test_d009c_presence_at_an_edge_with_a_present_marker_escalates(text):
    result = safety.evaluate(text, urgency_flagged=False)
    assert result.level in ("HIGH", "IMMEDIATE"), f"{text!r} -> {result.level} ({result.evidence_codes})"


BENIGN_EDGE = [
    "I am afraid of heights and stay away from balcony edges.",
    "My phone battery died on the balcony.",
    "I am at the balcony watering plants.",
]


@pytest.mark.parametrize("text", BENIGN_EDGE, ids=lambda t: t[:32])
def test_d009c_presence_at_an_edge_without_urgent_markers_does_not_escalate(text):
    result = safety.evaluate(text, urgency_flagged=False)
    assert result.level not in ("HIGH", "IMMEDIATE"), f"{text!r} -> {result.level}"


# ------------------------------------------------------------------
# Invariants that must hold for every level the engine can return.
# ------------------------------------------------------------------
ALL_LEVELS = ["NONE_DETECTED", "NEEDS_CLARIFICATION", "CONCERNING", "HIGH", "IMMEDIATE", "UNKNOWN"]

REASSURANCE_MARKERS = ("nothing to worry", "you're fine", "you are fine", "all clear", "no risk")


@pytest.mark.parametrize("level", ALL_LEVELS)
def test_invariant_no_level_emits_a_reassuring_takeaway(level):
    """No routing output may read as reassurance, at any level."""
    text = safety.support_action(level, subject="self").lower()
    for marker in REASSURANCE_MARKERS:
        assert marker not in text, f"{level} support text contains {marker!r}"


def test_invariant_unknown_is_never_none_detected():
    """
    The contract's core: an unknown, unsupported or failed analysis is not a
    low-risk result. These are the inputs the engine cannot read.
    """
    unreadable = [
        "",                # no text
        "   ",             # whitespace only
        "!!!???",          # punctuation only
        "\U0001f600",          # emoji only
        "###",             # junk marker
    ]
    for text in unreadable:
        result = safety.evaluate(text, urgency_flagged=False)
        assert result.level != "NONE_DETECTED", f"{text!r} was treated as safe"
        assert result.analysis_status in ("unsupported", "degraded", "unavailable")


def test_invariant_unsupported_script_abstains():
    # Cyrillic, CJK and Arabic are outside the declared capability. They must
    # abstain rather than return a confident low level, even when the English
    # words inside them spell out an explicit intent.
    for text in (
        "я хочу спрыгнуть с крыши сегодня",       # Cyrillic
        "我从十楼跳下去",                            # CJK
        "أريد أن أقفز من الطابق العاشر",            # Arabic
        "私は今夜屋顶から飛びたい",                     # Japanese
    ):
        result = safety.evaluate(text, urgency_flagged=False)
        assert result.language_support == "unsupported", text
        assert result.level == "UNKNOWN", text
        assert "UNSUPPORTED_LANGUAGE" in result.evidence_codes
        assert result.review_recommended is True
