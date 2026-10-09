"""
Context-aware safety routing for the MENTAL.AI screening service.

WHY THIS EXISTS
---------------
`MentalHealthScreener.screen()` returns two independent model outputs: a 7-class
condition label and a binary urgency probability. Neither is an authoritative
safety decision, and on the reported input they disagree in the way that matters:

    "i wanna jump from 10th floor"
        primary  -> Normal            (p = 0.950)
        urgency  -> suicide           (p = 0.785, threshold 0.15, flagged)

The condition model is trained on proxy subreddit labels, so an explicit method
statement with colloquial spelling reads as "Normal" to it. The urgency model is
trained on the same proxy labels and fires on method words, so it also fires on

    "I live on the tenth floor."   ->  urgency p = 0.247, flagged = true

Neither model can be promoted to the safety decision. This module supplies that
decision, separately from both, and states its own limits.

WHAT THIS MODULE IS NOT
-----------------------
- Not a diagnosis. It routes text to support intensity.
- Not a clinical risk model. No probability here is a probability of an attempt.
- Not language understanding. It is a documented, versioned rule set over
  surface features plus two model signals, and it abstains when it cannot read
  the text. RULE 8.7 of the session rules applies to every number produced here.

DESIGN CONSTRAINTS HONOURED
---------------------------
- Imports only the standard library, so routing is available even when NLTK or a
  model artifact is unavailable (the models are not imported here at all).
- Evaluates a minimally normalized copy of the text so negation, numerals,
  timing words, subject markers and quotation boundaries survive. The lossy ML
  preprocessing is untouched and still feeds the models.
- Never manufactures a model probability. Evidence and model scores stay in
  separate fields.
- Emits reason codes and short summaries, not chain-of-thought.
- Unknown / unavailable / out-of-language is never Normal.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable, Literal, Optional

POLICY_VERSION = "safety-policy-2026.10.09.6"

# ---------------------------------------------------------------------------
# Routing vocabulary
# ---------------------------------------------------------------------------
Level = Literal[
    "NONE_DETECTED",
    "NEEDS_CLARIFICATION",
    "CONCERNING",
    "HIGH",
    "IMMEDIATE",
    "UNKNOWN",
]

Subject = Literal["self", "another_person", "fictional_or_quoted", "unclear"]
Temporal = Literal["current", "recent", "historical", "hypothetical", "unclear"]
Immediacy = Literal["stated", "not_stated", "unclear"]
AnalysisStatus = Literal["complete", "degraded", "unavailable", "unsupported"]

LEVEL_ORDER: dict[str, int] = {
    "UNKNOWN": 0,
    "NONE_DETECTED": 1,
    "NEEDS_CLARIFICATION": 2,
    "CONCERNING": 3,
    "HIGH": 4,
    "IMMEDIATE": 5,
}

# ---------------------------------------------------------------------------
# Capability declaration - read by /health and by the runner, never guessed.
# ---------------------------------------------------------------------------
SUPPORTED_SCRIPTS = ("latin", "devanagari")
HINGLISH_SUPPORTED = True

# Unicode ranges we can reason about. Anything predominantly outside these
# yields UNKNOWN rather than a guess.
_RE_LATIN_HINT = re.compile(r"[A-Za-z]")
_RE_DEVA = re.compile(r"[ऀ-ॿ]")
_RE_CJK = re.compile(r"[一-鿿぀-ヿ가-힯]")
_RE_CYRILLIC = re.compile(r"[Ѐ-ӿ]")
_RE_ARABIC = re.compile(r"[؀-ۿ]")
_RE_DIGIT = re.compile(r"\d")
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)

# D-011 support. A closed list of closed-class English words. Function words
# rather than content words on purpose: "die" is an English word, so a
# content-word list would call German English. No English word list ships with
# this module, and adding one would be a dependency this rule layer does not have.
_ENGLISH_FUNCTION_WORDS = frozenset("""
    a an the all any some each every both either neither few many much more most
    other another same own such own several no none
    and or but nor so yet if then than that this these those there here
    i me my mine myself we us our ours ourselves you your yours yourself
    he him his himself she her hers herself it its itself they them their theirs
    themselves who whom whose which what when where why how
    am is are was were be been being do does did doing done doing
    have has had having will would shall should can could may might must
    not no never always often sometimes usually already still just even
    very too quite rather almost nearly really truly indeed also only even
    again once twice ever before after during while because about
    with without within into onto upon over under above below off out
    to of in on at by up down near between through across against toward
    as until till since per via
""".split())

# Below this many word tokens the language check abstains from guessing, so a
# short fragment in any language is not called unsupported.
_MIN_TOKENS_FOR_LANGUAGE_CHECK = 4
# A Latin-script text with a smaller share of English function words is treated
# as not-English. Conservative: it abstains rather than asserting a route it
# cannot read.
_MIN_ENGLISH_RATIO = 0.08


# ---------------------------------------------------------------------------
# Minimal normalization
# ---------------------------------------------------------------------------
# Deliberately NOT done here: destructive "not"-stripping, numeral removal,
# translation, base64 decoding, general Unicode stripping, or any lossy step that
# could move the meaning of a clause. Each of those is a way to turn a real
# disclosure into a benign one.
_ZERO_WIDTH = dict.fromkeys(
    [0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD], None
)


def normalize_for_safety(raw: str) -> str:
    """
    Build the safety view of the text.

    NFKC so that full-width and compatibility forms ("ｊｕｍｐ", "10ᵗʰ") match,
    zero-width joiners removed so "jum\u200bp" is readable, whitespace collapsed.
    Nothing that changes clause meaning is removed.
    """
    text = unicodedata.normalize("NFKC", raw)
    text = text.translate(_ZERO_WIDTH)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


# Bounded shorthand handling. Only two transformations, both reversible in
# meaning and both applied to a COPY used for routing only:
#   - leetspeak inside mixed alphanumeric tokens ("fl00r" -> "floor"),
#     deliberately NOT applied to tokens that begin with a digit, so ordinals
#     and floor numbers ("10th") survive untouched;
#   - a short, explicit abbreviation list ("jmp" -> "jump").
# No general transliteration, no homoglyph folding, no base64: each of those
# can change what a sentence means and none is needed for the observed cases.
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})
# D-020. Bounded typo tolerance for the risk vocabulary, applied to a COPY
# used for routing only. A short, closed list of misspellings of the words that
# matter, plus one transposition rule. Deliberately not general fuzzy matching:
# a spellchecker or an edit-distance pass over the whole vocabulary would also
# "correct" ordinary words into risk words. Every entry here is a misspelling
# that occurs in the seeded shorthand family.
_TYPO_MAP = {
    "myslef": "myself", "myselves": "myself", "myselv": "myself",
    "bulcony": "balcony", "balconey": "balcony", "barcony": "balcony",
    "florr": "floor",
    "lyfe": "life", "lief": "life", "liefe": "life",
    "suicid": "suicide", "sucid": "suicide",
    "wnat": "want", "wnna": "want", "wnt": "want", "wanna": "want",
    "flor": "floor", "florr": "floor", "flooor": "floor",
    "kudna": "jump", "jmp": "jump", "jmping": "jumping",
    "serius": "serious", "srsly": "seriously",
}
_TRANSPOSE = re.compile(r"(?<=(\w)(\w))\1(?=\w)")


def normalize_typos(text: str) -> str:
    """Expand a closed list of risk-word misspellings. Routing copy only."""
    out = []
    for token in text.split(" "):
        stripped = token.strip("\n\u0964.,!?;:'\"()")
        low = stripped.lower()
        if low in _TYPO_MAP:
            token = token.replace(stripped, _TYPO_MAP[low])
        else:
            # One adjacent transposition: "wnat" style slips inside a word.
            fixed = _TRANSPOSE.sub(r"\1\2", stripped.lower())
            if fixed != stripped.lower() and fixed in _TYPO_MAP:
                token = token.replace(stripped, _TYPO_MAP[fixed])
        out.append(token)
    return " ".join(out)


_ABBREV = {
    "jmp": "jump", "jumping": "jumping", "wnna": "want to", "wana": "want to",
    "gona": "going to", "wunna": "want to", "shuda": "should not",
    "wna": "want to", "fr": "from",
    "wnt": "want", "wanna": "want to", "wanna": "want to", "frm": "from",
    "flr": "floor", "fl00r": "floor", "fr0m": "from", "fl": "floor",
    "nthin": "nothing", "l8r": "later", "tmrw": "tomorrow", "tonite": "tonight",
    "pls": "please", "thx": "thanks", "u": "you", "ur": "your",
}
# Mixed alphanumeric tokens get leet expansion, EXCEPT tokens that begin with a
# digit. D-021: the leading-digit exclusion was documented in the comment below
# this pattern but was not actually implemented, so "10th" became "ioth" and
# the floor-number alternative of METHOD_OR_LOCATION stopped matching. Seed
# S052/S053 still routed HIGH only because a weaker alternative matched, so the
# corpus did not surface it until an expansion case combined leet risk with an
# ordinal. Ordinals and floor numbers are load-bearing, so they must survive.
_MIXED_TOKEN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)\S+$")
_DIGIT_LEADING_TOKEN = re.compile(r"^\d")


def normalize_shorthand(text: str) -> str:
    """Return a copy of the text with leetspeak and abbreviations expanded."""
    out_words = []
    for token in text.split(" "):
        stripped = token.strip("\n\u0964")
        if _MIXED_TOKEN.match(stripped) and not _DIGIT_LEADING_TOKEN.match(stripped):
            token = token.replace(stripped, stripped.translate(_LEET))
        core = re.sub(r"[^a-z]", "", token.lower())
        if core in _ABBREV:
            repl = _ABBREV[core]
            if len(core) <= 4 and core not in ("jumping",):
                token = re.sub(r"[A-Za-z]+$", repl, token)
        out_words.append(token)
    return " ".join(out_words)


def detect_language_support(text: str) -> AnalysisStatus:
    """
    Fallible script/lexicon heuristic, never proof of complete comprehension.

    Returns "unsupported" rather than guessing when the script is one this rule
    set was not written against. Honest abstention is a requirement here: a
    confident NONE_DETECTED in a language we cannot parse would be a fabricated
    all-clear.

    D-011: script alone is not enough. German, French, Spanish, Turkish and
    Indonesian all use Latin script, so a script check reported them as
    supported, no pattern matched, and the text came back NONE_DETECTED - a
    false all-clear on "Ich moechte heute sterben". Latin-script input is
    therefore also checked for English function words. The test is deliberately
    crude and bounded: it only abstains when a long enough Latin-script text
    contains essentially no English function word, so short and code-ish
    English still permits limited checks. Accepted heuristic cases return
    degraded, not complete. Unsupported material does not erase recognized
    supported danger elsewhere in the same input.
    """
    if _RE_CJK.search(text) or _RE_CYRILLIC.search(text) or _RE_ARABIC.search(text):
        return "unsupported"
    deva = len(_RE_DEVA.findall(text))
    latin = len(_RE_LATIN_HINT.findall(text))
    if deva >= 3 and latin < deva:
        return "degraded"  # Recognized script, limited unvalidated understanding.
    if latin >= 3:
        # Latin script. Is it English, or Hinglish - which this module does
        # support and which contains almost no English function words?
        tokens = _WORD.findall(text.lower())
        if _looks_hinglish(tokens):
            return "degraded"
        if len(tokens) >= _MIN_TOKENS_FOR_LANGUAGE_CHECK:
            english = sum(1 for tok in tokens if tok in _ENGLISH_FUNCTION_WORDS)
            if english / len(tokens) < _MIN_ENGLISH_RATIO:
                return "unsupported"
        return "degraded"
    return "unsupported" if text else "degraded"


# Hinglish markers: Roman-script Hindi/Urdu function and content words. A
# Hinglish sentence is mostly absent from the English function-word list, so
# without this carve-out the D-011 check abstained on text this module reads.
_HINGLISH_MARKERS = frozenset("""
    main mai mujhe mujko mera meri mere ham hum hamko humara apna apni apne
    hai haan hain hu hoon hota hoti hote tha thi the they
    nahi nahin nhi mat karna karna ki ke ka kiya kar kare karega karegi
    kudna koodna kudne kudunga chahiye chahta chahti chahta_hu chahta_hun
    dost dosti bhai bhaiya behen didi yaar pyaar dost
    ghar ka ki ke kaam dost khel khelna padhai
    jeena janna mar marna marna_marna maar maar_leta laana chhodh chod
    kyun kyon kaise kitna kitni bahut bohot thoda
""".split())


def _looks_hinglish(tokens: list[str]) -> bool:
    """
    Is this Roman-script text Hinglish rather than an unreadable language?

    A count, not a classifier: if a meaningful share of the tokens are Hinglish
    markers, the text is inside the declared capability. Deliberately
    permissive in the "complete" direction only for genuinely Hinglish text;
    anything else still has to pass the English check.
    """
    if not tokens:
        return False
    hits = sum(1 for tok in tokens if tok in _HINGLISH_MARKERS)
    return hits >= 2 or (hits >= 1 and len(tokens) <= 4)


# ---------------------------------------------------------------------------
# Clause segmentation
# ---------------------------------------------------------------------------
_SENT_SPLIT = re.compile(r"(?<=[.!?।])[\"\'\u2019\u201d)\]]*\s+|[\n]+")


@dataclass(frozen=True)
class Clause:
    text: str
    lowered: str
    index: int


def split_clauses(text: str) -> list[Clause]:
    """
    Split into sentence-like clauses.

    Splitting matters because negation and temporality bind to a clause: "I do
    not want to live, but I might hurt myself tonight" is two different
    statements and only the second one is HIGH.
    """
    out: list[Clause] = []
    for chunk in _SENT_SPLIT.split(text):
        chunk = chunk.strip()
        if not chunk:
            continue
        # Commas that join two self-reporting clauses also split, but only when
        # a contrast conjunction follows, so lists and parentheticals survive.
        pieces = re.split(r",\s+(?=(?:but|and|though|although|however)\b)", chunk)
        for piece in pieces:
            piece = piece.strip()
            if piece:
                out.append(Clause(piece, piece.lower(), len(out)))
    return out


# ---------------------------------------------------------------------------
# Evidence vocabulary
# ---------------------------------------------------------------------------
# Each entry: code -> (regex, human-readable description). Regexes are matched
# per clause, so they never leak across a contrast boundary.

EVIDENCE_PATTERNS: dict[str, tuple[re.Pattern[str], str]] = {
    # --- self-harm / suicidal act + intent ---------------------------
    "SELF_HARM_ACT": (
        re.compile(
            r"\b(kill(?:s|ed|ing)?\s+(?:my ?self|myself)|harm(?:s|ed|ing)?\s+(?:my ?self|myself)"
            r"|hurt(?:s|ed|ing)?\s+(?:my ?self|myself)|cut(?:s|ed|ting)?\s+(?:my ?self|myself)"
            r"|cutting\s+my\s+skin|end(?:ing)?\s+(?:my|it)\s+(?:own\s+)?life"
            r"|take\s+my\s+own\s+life|suicid\w*|end\s+my\s+(?:own\s+)?life"
            # D-009: common phrasings absent from the seed corpus, each with a
            # minimal-pair control in tests/test_safety_contract.py so an
            # addition cannot pass by over-broadening.
            #   "slit my wrists" / "cut my arm" family
            r"|(?:slit|cuts?|sliced|slicing)\s+(?:my|his|her|their)\s+wrists?"
            # Instruments of self-harm, stated as the act.
            r"|(?:took|taking|taken|used|using)\s+(?:a|an|the|my)\s+"
            r"(?:blade|knife|razor|scissors|glass|shard|cut)\b"
            r"|(?:cut|hurt)\s+(?:my\s?self|myself)\s+with"
            r"|(?:drank|swallowed|took)\s+(?:something|anything)\s+i\s+should\s+not"
            r"|(?:scratch|scraping|burn|burning|hit|hitting|punch)\s+(?:my\s?self|myself)"
            r"|(?:harm|hurt)\s+(?:my\s?self|myself)\s+(?:to\s+cope|when|whenever|again)"
            r"|(?:open|cut)\s+(?:up\s+)?my\s+arm"
            #   "walk into traffic and end it" / "just end it"
            r"|(?:walk|step|throw)\s+(?:my ?self\s+)?into\s+traffic"
            r"|end\s+(?:it|everything|this)\b"
            r"|be\s+(?:done|finished)\s+with\s+(?:it|everything|life)"
            #   hanging, first and third person
            r"|(?:hang|hanged)\s+(?:my ?self|myself|himself|herself|themselves)"
            #   medication excess, as an act rather than a wish
            r"|(?:took|taking|taken|swallowed|ingested)\s+(?:far\s+|way\s+|a\s+whole\s+|the\s+whole\s+)?"
            r"(?:too\s+(?:much|many)|a\s+whole\s+(?:packet|bottle|box|strip)|an\s+overdose)"
            r"|overdos\w*"
            r"|(?:end|ended|ending)\s+(?:my\s+)?life\b"
            r""
            r"|kaat|maaru\s+jana)\b"
        ),
        "Explicit reference to self-harm, ending one's life, or not wanting to live.",
    ),
    "NEGATIVE_WISH": (
        re.compile(
            # D-025: this pattern was Devanagari-only. The English form is the
            # commonest statement of intent NOT to die and it appears in seed
            # S023 and in the self_harm_no_intent family.
            r"(?:do\s+not|don'?t|dont|never)\s+want\s+to\s+(?:die|be\s+dead)"
            r"|not\s+wanting\s+to\s+die|would\s+not\s+die"
            r"|jeena\s+nahi\s+hai|जीने\s+नहीं\s+है"
            r"|मरना\s+नहीं\s+चाहता|मरने\s+का\s+इरादा\s+नहीं"
            r"|आत्महत्या\s+नहीं\s+कर"
        ),
        "Explicit 'I do not want to live / do not want to die'. The negation is "
        "part of the phrase and is not reassurance.",
    ),
    "PASSIVE_WISH_ACT": (
        re.compile(
            r"\b(?:want(?:s|ed)?\s+to\s+disappear\s+forever"
            r"|wish(?:es)?\s+i\s+(?:would\s+not|wouldn'?t|could\s+not|couldn'?t)\s+wake"
            r"|wish(?:es)?\s+i\s+(?:wasn'?t|was\s+not|were\s+not)\s+(?:born|here)"
            r"|no\s+reason\s+(?:for\s+me\s+)?to\s+(?:keep\s+living|go\s+on|live|be\s+alive)"
            r"|better\s+off\s+without\s+me"
            r"|(?:don'?t|do\s+not|never|no\s+longer|not)\s+want\s+to\s+(?:be\s+alive|be\s+here|live\s+anymore|live|exist|be\s+here\s+anymore)"
            r"|want\s+to\s+(?:disappear|be\s+gone|not\s+exist)\b)\b"
        ),
        "Passive death wish: not wanting to be alive, wishing not to wake, wanting to disappear.",
    ),
    # --- Devanagari / Hinglish: explicit risk ----------------------------
    # A bounded, documented capability. Terms were chosen for unambiguous
    # first-person self-harm intent in these scripts. Anything outside this list
    # is routed by the fallback rules or abstained on - never guessed.
    "DEVANAGARI_SELF_HARM": (
        re.compile(
            r"(?:कूदना|कूदने|कूदूँगा|कूदना\s+चाहता|छत\s+से|दसवीं|दसवी|मंज़िल\s+से|मंजिल\s+से"
            r"|मरना|मरने|मरूँगा|मरूंगा|आत्महत्या|पानी\s+देना|फांसी|जान\s+खत्म|अपनी\s+जान|खुद\s+को\s+नुकसान"
            r"|खुद\s+को\s+मार(?:ना|ने)|इस\s+दुनिया\s+से|दुनिया\s+से\s+छुट|छुट\s+जाना|मारने|मारूँगा|मारूंगा|मन\s+कर|आत्महत्या\s+कर)"
        ),
        "Devanagari expression of self-harm, method, or intent to die.",
    ),
    "DEVANAGARI_PRESENT_DANGER": (
        re.compile(
            r"(?:अभी|इस\s+समय)\s+.{0,20}(?:छत|किनारे|बालकनी)"
            r"|कूदने\s+वाला|कूदूँगा"
        ),
        "Devanagari present-position or immediate-action expression.",
    ),
    "DEVANAGARI_NEGATION": (
        re.compile(
            r"(?:नहीं|नहीं\s+चाहता|मुखे\s+नहीं|मुझे\s+नहीं"
            r"|(?:^|\s)ना\s+(?:चाहता|चाहती|करूँगा|करूंगा))"
        ),
        "Devanagari negation marker as a standalone token.",
    ),
    "DEVANAGARI_HELP": (
        re.compile(r"(?:मदद\s+चाहिए|मदद\s+चाहता|सहायता)"),
        "Devanagari help-seeking.",
    ),
    "HINGLISH_SELF_HARM": (
        re.compile(
            # D-009: "apni jaan khatam karna", "khud ko maar leta hai" are the
            # commonest Hinglish forms of ending one's life and a report that
            # someone else is doing it. Both were missing.
            r"(?:kudna|koodna|kudne|kudunga|karna\s+hai|maarna\s+hai|maaru\s+ja"
            r"|jeena\s+nahi\s+hai|jaan\s+lena|jaan\s+khatam|apni\s+jaan"
            r"|khud\s+ko\s+(?:marna|maarna|maarne|maar\s+leta)"
            r"|(?:mujhe|mujko)\s+khud\s+ko|maarna|maarne|maarte|marna\b|mar\s+ja"
            r"|maar\s+leta\s+hai|khud\s+ko\s+maar|khud\s+ko\s+khatam"
            r"|khatam\s+kar(?:\s+dunga|\s+denge|\s+dungi|\s+na)"
            r"|chhoot\s+ja(?:na|unga|ungi)|chhoot\s+jayega"
            r"|mann\s+kar|dusri\s+mansi|dasvi\s+mansi|chhat\s+se|chhat\s+par)"
        ),
        "Hinglish expression of self-harm, method, or not wanting to live.",
    ),
    # --- method / high-risk location ------------------------------------
    "METHOD_OR_LOCATION": (
        re.compile(
            r"\b(?:jump(?:ing|s)?\s+(?:off|from|off\s+of|from\s+off|from\s+out\s+of)"
            r"|kud(?:na|ne|naa)\w*|chad\w*\s+par|kood\w*"
            r"|hang(?:ing)?\s+(?:my ?self|myself|himself|herself|themselves|it)\b"
            r"|jump(?:ing|s)?\s+(?:off|from)\s+(?:the\s+)?"
            r"(?:\d+(?:st|nd|rd|th)|ten|twelve|fifteen|roof|balcony|bridge|building|tower|window)"
            r"|(?:ten|10th|10|twelfth|20th)\s*(?:st|nd|rd|th)?\s*floor"
            # D-009: "step off the roof", "off the ledge" - the same construct
            # as "jump off" with a different verb.
            r"|(?:step|steps|stepped|go|going|went|come|coming|climb|climbed|climbing)\s+"
            r"(?:off|down|out|up)\s+(?:the\s+|a\s+|an\s+)?"
            r"(?:\d+(?:st|nd|rd|th)\s+)?(?:roof|ledge|edge|balcony|building|tower|bridge|window|cliff"
            r"|fire\s+escape|chimney|gantry)"
            r"|(?:slit|cuts?|sliced|slicing)\s+(?:my|his|her|their)\s+wrists?"
            # Instruments of self-harm, stated as the act.
            r"|(?:took|taking|taken|used|using)\s+(?:a|an|the|my)\s+"
            r"(?:blade|knife|razor|scissors|glass|shard|cut)\b"
            r"|(?:cut|hurt)\s+(?:my\s?self|myself)\s+with"
            r"|(?:drank|swallowed|took)\s+(?:something|anything)\s+i\s+should\s+not"
            r"|(?:scratch|scraping|burn|burning|hit|hitting|punch)\s+(?:my\s?self|myself)"
            r"|(?:harm|hurt)\s+(?:my\s?self|myself)\s+(?:to\s+cope|when|whenever|again)"
            r"|(?:into|under)\s+(?:a\s+|the\s+)?(?:train|lorry|truck|bus|car|water)"
            # Bare location nouns. D-009b: these are the false-positive source
            # for "I want to get a rooftop apartment", so they are reported as
            # LOCATION_WORD and the escalation guard below requires either an
            # action verb, a present-position claim, or a self-harm term
            # alongside them. See `_location_is_actionable`.
            r"|balcon(?:y|ies)|rooftop|roof-top|bridge|cliff\s+edge|ledge|fire\s+escape"
            r"|(?:roof|building|tower|balcony|cliff|bridge)\s+edge)\b"
        ),
        "Method or high-risk location named (jumping from a height, a balcony, a bridge, a rooftop, hanging, cutting wrists, stepping off an edge, overdose).",
    ),
    # --- intent ---------------------------------------------------------
    "INTENT_VERB": (
        re.compile(
            r"\b(want|wanna|wan\w*|going\s+to|gonna|plan(?:ning)?\s+to|intend(?:ing)?\s+to"
            r"|will|would|about\s+to|decided\s+to|planning\s+to|trying\s+to|aim\w*\s+to"
            r"|chahta|chahti|chahta\s+hu|kar\s+unga|karna\s+hai|karna\s+chahta|decided\s+to|feel\s+like\s+(?:ending|killing|hurting|doing|dying)|going\s+to\s+die|plan\s+to\s+die|want\s+to\s+die|mein\s+marna)\b"
        ),
        "First-person intent verb attached to a self-harm expression.",
    ),
    "PLANNED_ACTION": (
        re.compile(
            r"\b(?:i(?:'m| am)\s+(?:going\s+to|gonna|about\s+to)|tonight|today\s+tonight"
            r"|right\s+now|at\s+night|midnight|after\s+dark)\b"
        ),
        "Stated near-term timing or an action underway.",
    ),
    # --- present location / access ---------------------------------------
    "PRESENT_ACCESS": (
        re.compile(
            r"\b(?:i(?:'m| am)\s+(?:outside\s+|out\s+)?(?:on|at|standing\s+on|out\s+on|sitting\s+on|sat\s+on|standing\s+at|stood\s+on)\s+"
            r"(?:the\s+|a\s+|an\s+)?(?:top\s+of\s+the\s+|edge\s+of\s+the\s+|"
            r"balcony|roof|rooftop|ledge|bridge|tower|building|edge|cliff|fire\s+escape)"
            r"|i(?:'m| am)\s+alone|by\s+myself\s+now|on\s+the\s+edge"
            r"|(?:he|she|they|my\s+\w+)\s+(?:is|are|'s|'re)\s+(?:on|at)\s+(?:the\s+|a\s+)?"
            r"(?:balcony|roof|rooftop|ledge|bridge|tower|fire\s+escape)"
            # "I climbed up here and nobody knows where I am": position plus
            # isolation, with no location noun to key off.
            r"|climbed\s+up\s+(?:here|there|on\s+the\s+roof)"
            r"|nobody\s+knows\s+where\s+i\s+am)\b"
        ),
        "Present physical location or stated absence of another person.",
    ),
    # --- recent act ------------------------------------------------------
    "RECENT_ACT": (
        re.compile(
            r"\b(?:already\s+harmed\s+myself"
            r"|(?:tried|attempted)\s+to\s+(?:kill|harm|hurt|cut)\s+(?:my\s?self|myself)"
            r"|(?:hurt|harmed|cut|injured)\s+(?:my\s?self|myself)\s+(?:yesterday|last\s+night|earlier)"
            r"|(?:yesterday|last\s+night|earlier\s+today)\s+i\s+(?:cut|hurt|harmed|injured|overdosed|tried|attempted)"
            r"|i\s+took\s+(?:far\s+|way\s+)?too\s+(?:much|many)"
            r"|(?:took|swallowed|taken)\s+(?:a\s+whole|the\s+whole|a\s+whole\s+pack)\w*"
            # D-032: a past-tense self-harm verb is itself the report of a
            # completed act. "I killed myself" was CONCERNING because no
            # timing word, intent verb or method was present.
            r"|(?:killed|hung|overdosed|hurt|cut|slit|sliced|shot)\s+(?:my\s?self|myself)\b"
            r"|(?:took|swallowed)\s+(?:the\s+whole\s+)?packet"
            r"|(?:cut|hurt|harmed|injured)\s+(?:my\s?self|myself)\s+(?:again\s+)?"
            r"(?:yesterday|last\s+night|earlier|this\s+morning|again))\b"
        ),
        "Reported self-harm that has already occurred.",
    ),
    "MEDICAL_EMERGENCY": (
        re.compile(
            r"\b(?:chest\s+pain|cannot\s+breathe|can'?t\s+breathe|difficulty\s+breathing"
            r"|shortness\s+of\s+breath|passed\s+out|unconscious|took\s+(?:far\s+)?too\s+much"
            r"|overdose|overdos\w+|bleeding\s+a\s+lot|feel\s+unwell"
            # D-009: phrasings the seed corpus did not contain. Each has a
            # non-emergency near neighbour in the regression file.
            r"|(?:cannot|can'?t|unable\s+to)\s+stop\s+(?:vomiting|bleeding|coughing)"
            r"|(?:keep|keeps)\s+vomiting|throwing\s+up"
            r"|bleed(?:ing)?\s+(?:heavily|a\s+lot|badly)"
            r"|feel\s+(?:faint|dizzy|woozy)|going\s+(?:faint|grey)"
            r"|collaps\w+|(?:nearly|about\s+to)\s+(?:faint|black\s+out|pass\s+out)"
            r""
            r"|blood\s+(?:is\s+)?(?:in\s+my\s+)?urine|blood\s+in\s+my\s+vomit"
            r"|seizure|fitting\s+episode|convulsion"
            r"|pass(?:ing|ed)?\s+out|black(?:ing|s)?\s+out"
            r"|(?:cannot|can'?t)\s+stop\s+(?:shaking|trembling|vomiting|bleeding)"
            r"|(?:have\s+been|been)\s+bleeding|cannot\s+get\s+up|can'?t\s+get\s+up"
            r"|chest\s+tightness|vision\s+is\s+going|going\s+grey"
            # D-035: bare "not waking up" also matched the passive death wish
            # "I would not mind not waking up" and routed it IMMEDIATE. The
            # medical reading needs a clinical anchor.
            r"|(?:i\s+am|i'?m)\s+not\s+waking\s+up|still\s+not\s+waking"
            r"|cannot\s+wake(?:\s+up)?|can'?t\s+wake(?:\s+up)?|won'?t\s+wake(?:\s+up)?"
            r"|feel\s+strange\s+and\s+i\s+drank|drank\s+something)\b"
        ),
        "Possible medical emergency.",
    ),
    # --- distress / burden / farewell -----------------------------------
    "PASSIVE_DEATH_WISH": (
        re.compile(
            r"\b(?:wish\s+i\s+(?:would\s+not|wouldn'?t|could\s+not|couldn'?t)\s+wake"
            r"|better\s+off\s+without\s+me"
            r"|tired\s+of\s+(?:life|living|everything)|"
            r"(?:no|the)\s+point\s+(?:in\s+)?(?:living|going\s+on|continuing)"
            r"|burden|giving\s+away\s+my\s+(?:things|stuff|possessions)"
            r"|goodbye.{0,24}(?:won'?t|not)\s+(?:hear|see)\s+(?:from\s+)?me"
            r"|won'?t\s+(?:ever\s+)?(?:see|hear)\s+(?:from\s+)?me\s+again|disappear(?:\s+forever)?"
            r"|better\s+off\s+(?:gone|without\s+me|if\s+i\s+(?:was|were)\s+gone)"
            r"|end(?:ing)?\s+it|ending\s+(?:my\s+)?life"
            # D-022: passive wishes phrased without a wish verb. Measured against
            # the passive_wish corpus family, where the seed corpus had one
            # phrasing and the engine recognised none of these.
            r"|wish\s+i\s+could\s+(?:just\s+)?not\s+exist"
            r"|hope\s+i\s+(?:do\s+not|don'?t|never)\s+wake"
            r"|(?:happier|better)\s+(?:off\s+)?if\s+i\s+(?:was|were)\s+never\s+born"
            r"|wish\s+i\s+could\s+fall\s+asleep\s+and\s+stay\s+asleep"
            r"|wish\s+i\s+(?:would|could)\s+just\s+sleep\s+forever"
            r"|(?:nobody|no\s+one)\s+would\s+(?:miss|care|notice)\s+me"
            r"|nobody\s+would\s+miss\s+me\s+if\s+i\s+was\s+gone"
            r"|feel\s+like\s+nobody\s+(?:would\s+)?(?:care|would\s+miss)"
            r"|(?:cannot|can'?t)\s+see\s+(?:a\s+way\s+(?:forward|out)|the\s+point)"
            r"|see\s+no\s+point"
            r"|feel\s+unsafe|still\s+feel\s+unsafe)\b"
        ),
        "Passive death wish, burden statement, or farewell.",
    ),
    "AMBIGUOUS_DISTRESS": (
        re.compile(
            r"\b(?:can(?:not|'?t)\s+do\s+this\s+anymore|do(?:es)?\s+not\s+know\s+what\s+i\s+want"
            r"|give\s+up|can't\s+go\s+on|no\s+one\s+would\s+miss\s+me)\b"
        ),
        "Ambiguous exhaustion without stated intent; needs a direct question.",
    ),
    "DISTRESS": (
        re.compile(
            r"\b(?:hopeless|helpless|worthless|empty|numb|can(?:not|'?t)\s+cope"
            r"|falling\s+apart|no\s+hope|disconnected|scared\s+of\s+myself|drowning"
            r"|cannot\s+enjoy\s+anything|lost\s+interest\s+in"
            r"|heart\s+is\s+racing|panic(?:ked|king)?|panicking"
            r"|unusually\s+energ|not\s+slept\s+for|several\s+nights\s+without"
            r"|scared|frightened|afraid\s+of\s+what\s+i\s+am|burden"
            # D-013: anhedonia, low mood, irritability, altered energy, and
            # distressing perceptual experience. All are ordinary first-person
            # distress with no disorder implied.
            r"|have\s+been\s+(?:low|down|feeling\s+low)"
            r"|do\s+not\s+enjoy\s+things|don'?t\s+enjoy\s+things|enjoy\s+nothing"
            r"|feel\s+sad\s+most\s+days|low\s+mood|anhedonia"
            r"|no\s+energy|no\s+motivation|lost\s+all\s+my\s+appetite"
            r"|feeling\s+irritable|so\s+irritable|irritable\s+all\s+the\s+time"
            r"|feel\s+(?:utterly\s+|completely\s+|totally\s+)?(?:drained|exhausted|spent|empty)"
            r"|feel\s+wired|wired\s+and\s+i|full\s+of\s+energy|lots\s+of\s+energy"
            r"|(?:hardly|not)\s+slept|not\s+slept\s+in\s+\w+\s+days|three\s+hours\s+of\s+sleep"
            r"|(?:people|someone|they)\s+(?:are\s+|is\s+)?watching\s+me"
            r"|do\s+not\s+recognise\s+myself|don'?t\s+recognise\s+myself"
            r"|hear(?:ing|d|s)?\s+(?:someone|somebody|a\s+voice|voices)\s+(?:talking|saying)|hears?\s+voices?"
            r"|would\s+not\s+say\s+i\s+am\s+fine|not\s+that\s+i\s+am\s+fine"
            r"|feel\s+awful|feel\s+terrible|something\s+is\s+wrong"
            r"|utterly\s+drained|completely\s+numb"
            # D-023: forms the earlier additions missed by one token.
            r"|feel\s+irritable|feeling\s+irritable|irritable"
            # Persistence is required. Seed S058 ("I slept badly once, but
            # otherwise I feel fine") is classified N, so a single bad night
            # must not route. The qualifying forms below all imply a pattern
            # rather than one off event.
            r"|(?:sleeping|slept)\s+badly\s+(?:for|most|every|again\s+and)"
            r"|bad\s+sleep\s+for|poor\s+sleep\s+for|bad\s+sleep\s+again"
            r"|nobody\s+(?:would\s+)?(?:would\s+)?care"
            r"|should\s+i\s+be\s+worried|worried\s+about\s+how\s+i\s+feel"
            r"|not\s+sure\s+(?:whether|if)|do\s+not\s+know\s+if\s+i\s+should"
            r"|cannot\s+name\s+it|no\s+idea\s+what\s+is\s+wrong)\b"
        ),
        "General distress or concerning change in state language.",
    ),
    # --- other-person risk ------------------------------------------------
    "THIRD_PARTY_SUBJECT": (
        re.compile(
            r"\b(?:my\s+(?:friend|brother|sister|mother|father|son|daughter|wife|husband"
            r"|partner|boyfriend|girlfriend|neighbour|neighbor|cousin|pal)|"
            r"someone|somebody|a\s+person|he|she|they|someone|somebody|a\s+person|he|she|they|dost|dost\w*|bhai|bhaiya|behen|behen\w*|didi|mama|mummy|papa|abba|maa|yaar)\b"
        ),
        "The affected person is not necessarily the author.",
    ),
    "THIRD_PARTY_RISK": (
        re.compile(
            r"\b(?:(?:kill|harm|hurt|end|hang)\s+(?:him|her|himself|herself|itself|themselves|them)"
            r"|about\s+to\s+(?:jump|kud\w*|chad\w*)"
            r"|(?:going|gonna)\s+(?:to\s+)?(?:jump|kud\w*|chad\w*|kill|harm)"
            r"|(?:kill|harm|hurt|end|hang|slit|cut)\s+(?:him|her|himself|herself|itself|themselves|them)"
            r"|hang(?:ing)?\s+(?:himself|herself|themselves)"
            r"|end\s+(?:his|her|their|its)\s+(?:own\s+)?life"
            r"|(?:kill|hang|slit)\s+(?:his|her|their)\s+(?:himself|herself|themselves)"
            r"|(?:about\s+to|talking\s+about|going\s+to|posted\s+about|said\s+(?:she|he)\s+is)"
            r"|stopping\s+(?:her|his|their)\s+tablets|stopped?\s+taking\s+(?:her\s+|his\s+)?(?:tablets|medication)"
            r"|not\s+taking\s+(?:her|his)\s+medication"
            r"|ending\s+(?:their|his|her)\s+life"
            r"|apni\s+jaan\s+lena\s+chahta\s+hai"
            r"|jaan\s+lena\s+chahta\s+hai"
            r"|khud\s+ko\s+marna|khud\s+ko\s+maar(?:\s+leta)?|apni\s+jaan\s+khatam)\b"
        ),
        "Another person described as at risk. Only evidence when the clause also names a third person.",
    ),
    # --- quotation / fiction ---------------------------------------------
    "QUOTATION_WRAPPER": (
        re.compile(
            r"(?:\"|\u201c|\u2018|'|\u2019)[^\"'\u201c\u201d]{0,120}(?:want\s+to\s+die|end\s+my\s+life)[^\"'\u201c\u201d]{0,20}"
            r"(?:\"|\u201c|\u201d|\u2019)"
            r"|(?:a\s+quote\s+says|character\s+in\s+my\s+story|the\s+film"
            r"|article\s+says|song\s+says)"
            # D-009e: `lesson\s+explains` used to live here, which made an
            # educational text report subject=fictional_or_quoted (seed S032
            # expects unclear). It is an EDUCATIONAL_FRAME, not a quotation.
        ),
        "The statement is quoted or described rather than asserted.",
    ),
    "EDUCATIONAL_FRAME": (
        re.compile(
            r"(?:suicide|self[- ]harm|self[- ]injury|mental\s+health)\s*[- ]?(?:prevention|awareness|first\s+aid|lesson|training|support)"
            r"|\b(?:how\s+to\s+ask\s+for\s+help|warning\s+signs|research\s+(?:paper|article)\s+on\s+suicide)\b"
        ),
        "Educational or informational framing.",
    ),
    # --- temporal --------------------------------------------------------
    "HISTORICAL": (
        re.compile(
            r"\b(?:years?\s+ago|last\s+year|in\s+the\s+past|used\s+to|previously|formerly"
            r"|i\s+(?:am|'m)\s+safe\s+now|got\s+no\s+current\s+urge|no\s+current\s+urge"
            r"|i\s+(?:am|'m)\s+getting\s+help|receiving\s+help|in\s+recovery|sober)\b"
        ),
        "Historical or recovery context.",
    ),
    "HYPOTHETICAL": (
        re.compile(r"\b(?:if\s+i\s+(?:ever|were\s+to)|what\s+if|hypothetically|in\s+theory)\b"),
        "Conditional or hypothetical framing.",
    ),
    # --- negation ---------------------------------------------------------
    "NEGATION": (
        re.compile(
            r"\b(?:not|never|no\s+longer|don'?t|doesn'?t|didn'?t|won'?t|wouldn'?t"
            r"|n[aä]hi|nahi|नहीं|ना"
            r"|no\s+(?:plans?|intention|intentions|thoughts?|urges?|urge|desire|desires|"
            r"intentions|reason)\s+to|not\s+going\s+to|never\s+going\s+to|"
            r"don'?t\s+plan\s+to|do\s+not\s+plan\s+to)\b"
        ),
        "A negation marker present in this clause.",
    ),
    # --- intrusive thought -------------------------------------------------
    "EXPLICIT_DIE_INTENT": (
        re.compile(
            r"\b(?:decided|deciding|planning|planned|intend(?:ing)?|want(?:s|ed)?|going|gonna|will)\s+"
            r"(?:to\s+)?(?:die|kill\s+my ?self|end\s+(?:it|my\s+(?:own\s+)?life)|kudna|koodna)\b"
        ),
        "Explicit intention to die or to end one's life.",
    ),
    "RELATES_TO_QUOTE": (
        re.compile(
            r"\b(?:i\s+(?:relate|related|identified|identify)\s+to\s+(?:that|it|this)"
            r"|it\s+hit\s+me\s+hard|that\s+hit\s+me|struck\s+a\s+chord"
            r"|i\s+(?:keep|kept)\s+thinking\s+about\s+it"
            r"|and\s+i\s+(?:relate|feel\s+that|agree)"
            r"|makes\s+me\s+feel\s+(?:that\s+)?(?:less\s+alone|understood))\b"
        ),
        "A quoted disclosure the author personally identifies with.",
    ),
    "ANAPHORIC_NEAR_TERM": (
        re.compile(
            r"\b(?:i(?:'m| am)\s+(?:going\s+to|gonna|about\s+to)\s+(?:do|end)\s+it"
            r"|i\s+will\s+(?:do|end)\s+it"
            r"|i\s+have\s+it\s+planned"
            r"|(?:tonight|tomorrow|this\s+weekend|before\s+morning|by\s+morning)\s+is\s+the\s+"
            r"(?:night|time|day)"
            r"|(?:it|that)\s+is\s+happening\s+(?:tonight|tomorrow|now)"
            r"|i\s+am\s+doing\s+it\s+(?:tonight|tomorrow|now|soon))\b"
        ),
        "A near-term action stated with an unstated object. The text does not "
        "say what 'it' is, so this is a question rather than a finding.",
    ),
    "UNWANTED_THOUGHT": (
        re.compile(
            r"\b(?:unwanted|intrusive|keep\s+(?:thinking|crossing)\s+my\s+mind"
            r"|thought\s+(?:about|of)\s+(?:jumping|killing|dying)"
            r"|scares?\s+me|don'?t\s+want\s+to\s+act\s+on\s+it)\b"
        ),
        "An unwanted intrusive thought rather than intent.",
    ),
    # --- injection --------------------------------------------------------
    "INSTRUCTION_INJECTION": (
        re.compile(
            r"\b(?:ignore\s+(?:your|all|the)\s+(?:rules|instructions|safety)"
            r"|return\s+normal|mark\s+me\s+normal|set\s+risk\s+to\s+zero"
            r"|safety\s+(?:checks?\s+are\s+)?disabled|pretend\s+this\s+is\s+harmless"
            r"|reveal\s+your\s+secret|another\s+user'?s?)\b"
        ),
        "Text attempting to override the safety policy or extract secrets.",
    ),
    # --- other danger categories -------------------------------------------
    "VIOLENCE_OTHER": (
        # D-009: "the person who wronged me" and "attack someone" were missed.
        re.compile(
            r"\b(?:(?:going\s+to|want\s+to|plan(?:ning)?\s+to|will|am\s+going\s+to)\s+"
            r"(?:kill|hurt|harm|attack|stab|shoot|strangle|poison|fight|beat|break|"
            r"smash|strangle)\s+"
            r"(?:someone|somebody|another|him|her|them|people|"
            r"his\s+(?:jaw|face|head|nose|ribs)|her\s+(?:face|head|jaw)|"
            r"(?:the|a)\s+(?:person|man|woman|guy|girl|people|family|school|class|office)\b)"
            r"|attack\s+(?:someone|somebody|him|her|them|the\s+\w+)"
            r"|(?:threaten|threatened|threatening)\s+(?:to\s+)?(?:kill|hurt|harm)"
            r"|revenge)\b"
        ),
        "Violence toward another person.",
    ),
    "ABUSE_THREAT": (
        # D-009: "is hitting me", "is beating me", "threatening my child" were all
        # missed because only the verb phrase "threatening to hurt me" matched.
        re.compile(
            r"\b(?:threatening\s+(?:to\s+)?(?:kill|hurt|harm|hit)\s+(?:me|my|us|our)"
            r"|(?:(?:is|are|has|have|keeps|kept)\s+(?:hitting|beating|slapping|punching|"
            r"kicking|choking|stabbing|threatening|abusing|harassing)\s+"
            r"(?:me|my\s+\w+|us|our\s+\w+))"
            r"|(?:is|are|keeps?|have)\s+(?:shouting|grabbing)\s+(?:me|at\s+me)"
            r"|(?:is|are|keeps?|have)\s+pushing\s+me(?!\s+(?:toward|towards|aside|away))"
            r"|(?:shouting|pushing|grabbing|threatening)\s+at\s+me"
            r"|(?:shouting|arguing|ranting|screaming)\s+and\s+(?:pushing|hitting|grabbing|throwing)"
            r"\s+me"
            # D-035: "Nobody is pushing me toward anything" matched
            # `is pushing me` and routed IMMEDIATE. A negated or hypothetical
            # subject, and the "pushing me aside/away/toward" sense, are not
            # abuse. Regression introduced by the D-030 addition.
            r"|(?:is|are)\s+pushing\s+me(?!\s+(?:toward|towards|aside|away))"
            r"|(?:pushed|hit|grabbed|shoved)\s+me\s+and\s+i"
            r"|(?:is|are|has|have|keeps|kept)\s+(?:hitting|beating|hitting|slapping|punching|"
            r"kicking|choking|stabbing|threatening|abusing|harassing)\s+"
            r"(?:me|my\s+\w+|us|our\s+\w+)"
            r"|(?:hit|beat|hurt|abuse|abused|attack)\s+me\s+(?:right\s+now|again|tonight|every\s+\w+)"
            r"|locked\s+me\s+in)\b"
        ),
        "Abuse-related danger.",
    ),
    "PSYCHOSIS_VOICE": (
        # D-009: "keeps telling me to end it" was missed because the pattern
        # required the word "voice".
        re.compile(
            r"\b(?:voice\s+(?:is\s+)?(?:telling|saying)\s+me|hear\s+voices?"
            r"|(?:something|something\s+in\s+my\s+head|it|someone)\s*"
            r"(?:keeps?|keep|won'?t\s+stop\s+\w+ing)\s+(?:telling|saying|whispering|urging)\s+me"
            r"|told\s+me\s+to\s+(?:hurt|kill|end|cut|hang|jump))\b"
        ),
        "Command hallucinations or voices instructing self-harm.",
    ),
    # --- support seeking ---------------------------------------------------
    "SUPPORT_SEEKING": (
        re.compile(r"\b(?:i\s+need\s+help|help\s+me|please\s+help|want\s+help|need\s+support|talking\s+to\s+(?:someone|a\s+(?:doctor|therapist|friend)))\b"),
        "Explicit help-seeking.",
    ),
    # D-012  Preparation and farewell. Measured against the out-of-vocabulary
    # corpus family, which exists precisely to measure what the model flag used
    # to catch and no longer can: "I have made arrangements", "I have written
    # the note", "I have said my goodbyes", "I will not be here", "there is
    # only one way out". Each is a fact about ending, not a statement of intent,
    # and each has a benign near neighbour in the regression file
    # ("I have made arrangements for the party", "I finished everything I
    # needed to do"). These route HIGH, not IMMEDIATE: nothing here claims the
    # act is underway.
    "FINAL_ARRANGEMENTS": (
        re.compile(
            r"\b(?:made\s+(?:my\s+|all\s+the\s+|the\s+)?arrangements\s+"
            r"(?:for\s+)?(?:afterwards|after|to\s+go|to\s+leave|to\s+disappear|for\s+my\s+death|to\s+die)"
            r"|arranged\s+(?:my\s+)?(?:affairs|accounts|possessions)"
            r"|writt?en\s+(?:the|a|my)\s+(?:note|letter|goodbye|goodbyes)"
            r"|(?:said|say|said\s+my)\s+good\s?byes"
                        r"|(?:be|being|am|will\s+be|going\s+to\s+be)\s+gone\s+(?:by|before|after)"
            r"|(?:not|won'?t|will\s+not)\s+miss\s+(?:this|me|us|the\s+world)"
            r"|(?:one|only)\s+way\s+out\s+of\s+this"
            r"|(?:done|finished)\s+(?:talking|being)\s+about\s+(?:living|life|it)"
            r"|finished\s+everything\s+i\s+needed\s+to\s+say"
            r"|(?:tired|ready)\s+to\s+(?:go\s+to\s+sleep\s+forever|be\s+done)\b"
            r"|no\s+(?:longer\s+)?(?:want|wanting)\s+to\s+(?:be\s+here|exist|stay)"
            r"|(?:want|wanted)\s+to\s+(?:just\s+)?(?:not\s+exist|disappear|be\s+gone)\b)"
        ),
        "Preparation for, or farewell from, life. A fact about ending rather "
        "than a statement of intent.",
    ),
}

# Method/location + intent, with no self-harm word: still actionable, because
# "I'm on the balcony and I am about to jump" names no self-harm term.
_METHOD_INTENT = re.compile(
    r"\b(?:about\s+to|going\s+to|gonna|will)\s+(?:jump|kud\w*|chad\w*)\b"
    r"|\b(?:jump|jumping)\s+(?:off|from)\b",
    re.IGNORECASE,
)

# D-009c: an explicit present-time marker. "now"/"at this moment" qualify;
# "tonight" and "today" deliberately do not, because they are compatible with
# being elsewhere right now.
_PRESENT_TIME = re.compile(
    r"\b(?:right\s+now|at\s+this\s+(?:moment|second|very\s+moment|point\s+in\s+time)"
    r"|at\s+the\s+moment|this\s+(?:moment|second)|just\s+now|as\s+we\s+speak"
    r"|presently|already\s+(?:there|on\s+the))\b"
)

# D-009b. A location noun alone ("rooftop", "balcony", "bridge", "ledge") is
# evidence of a place, not of an act. It escalates only when the clause also
# carries an action verb, a present-position claim, or a self-harm term.
# "I want to get a rooftop apartment" has an intent verb and a location and is
# still benign, because the intent is for the property, not for a fall.
_LOCATION_WORD_ONLY = re.compile(
    r"\b(?:balcon(?:y|ies)|rooftop|roof-top|bridge|cliff\s+edge|ledge)\b", re.IGNORECASE
)
_STRONG_METHOD = re.compile(
    r"\b(?:jump|kud|chad|kood|hang|hanged|slit|wrist|wrists|traffic|lorry|truck)\w*",
    re.IGNORECASE,
)
# Verbs that mean the person is about to move off the place, rather than
# looking at it or wanting to own it.
_LOCATION_ACTION = re.compile(
    r"\b(?:jump|step|stepped|go|going|went|come|coming|climb|climbing|lean|leaning"
    r"|hang|hanged|drop|fall|threw|throw)\w*\s+(?:off|from|down|out\s+of|over)\b"
    r"|\b(?:off|down|over)\s+the\s+(?:roof|ledge|edge|balcony|building|tower|bridge|cliff)\b",
    re.IGNORECASE,
)
# Acquisition / property / decorative contexts for a location noun.
_ACQUISITION = re.compile(
    r"\b(?:get|getting|got|buy|buying|bought|rent|renting|rented|move|moving|moved\s+into"
    r"|look(?:ing)?\s+at|view|viewing|tour|touring|apartment|flat|terrace|house|home"
    r"|office|listing|paint(?:ing)?|decorat\w*|plant(?:s|er)?|furnitur\w*|chair\w*"
    r"|book|books|film|movie|photo\w*)\b",
    re.IGNORECASE,
)


def _location_is_actionable(clause: str, *, method: bool, intent: bool,
                            present_access: bool, act: bool) -> bool:
    """
    May a location noun raise the level?

    Only when the clause shows an act rather than a place. Three ways to
    qualify, in order of directness:
      1. a strong method verb (jump, hang, slit, traffic) - unambiguous;
      2. a present-position claim at that location - someone is there now;
      3. a self-harm term in the same clause.
    An acquisition or decorative context disqualifies the route, so
    "I want to get a rooftop apartment" and "I am buying a balcony planter"
    stay where they belong.
    """
    if not method:
        return True
    if _STRONG_METHOD.search(clause):
        return True
    # D-014: the acquisition check must come BEFORE the present-access
    # shortcut. "I am at the balcony watering plants" is present access plus a
    # location word, and reading the shortcut first escalated it to a question
    # about self-harm.
    if _LOCATION_WORD_ONLY.search(clause) and _ACQUISITION.search(clause) \
            and not _LOCATION_ACTION.search(clause):
        return False
    if act or present_access:
        return True
    if _LOCATION_WORD_ONLY.search(clause) and not _LOCATION_ACTION.search(clause):
        # A bare location noun with only a generic intent verb is a place, not
        # an act. "I want to get a rooftop apartment", "I want to buy a
        # balcony planter".
        if intent:
            return False
    return True


# ---------------------------------------------------------------------------
# Support text
# ---------------------------------------------------------------------------
# Region is never inferred from language or IP (explicit constraint). These are
# generic, and the caller is expected to ask for the user's location rather than
# assume one. Numbers are given as placeholders to verify before release.
def support_action(level: str, *, subject: str, region_known: bool = False) -> str:
    """
    Support text for a level.

    `region_known` is false everywhere in this release. Region is never inferred
    from language, script or IP, so no national hotline is named here: the
    routing specification requires usable generic local-emergency guidance.
    This single-text API cannot promise a later location-resolving conversation.
    The parameter exists so a
    verified-region implementation has an honest seam to fill later; it is read
    rather than ignored.
    """
    if subject == "another_person" and level != "NONE_DETECTED":
        if level in ("HIGH", "IMMEDIATE"):
            return (
                "The person you described may need urgent support. If they are in immediate "
                "danger, contact their local emergency service now. If it is safe for you, "
                "stay connected with them and help them reach a trusted person. Do not put "
                "yourself in danger. Are they safe right now?"
            )
        return (
            "Check in with the person you described and help them reach someone they trust "
            "or a qualified professional. Are they having thoughts of harming themselves now?"
        )
    if level == "IMMEDIATE":
        return (
            "Please seek urgent help. Contact your local emergency service or go to "
            "the nearest emergency department. If there is an immediate hazard, move "
            "away from it if you can do so safely. If it is safe to have someone "
            "with you, do not be alone. Stay connected with someone you trust "
            "and tell them what is happening."
        )
    if level == "HIGH":
        return (
            "This disclosure suggests a serious concern that warrants support now. "
            "Please reach out to someone you "
            "trust today, and consider contacting a crisis line or your local "
            "emergency service. If you or someone else is in immediate danger, "
            "move away from hazards if you can do so safely."
            + ("" if region_known else " If you are unsure which local service to use, "
                "someone you trust or a healthcare professional may help you find it.")
        )
    if level == "CONCERNING":
        return (
            "Thank you for saying this. Some of what you have described sounds heavy "
            "to be carrying. Talking to someone you trust, or a doctor or "
            "counsellor, would be worth doing soon. If that feels hard, one message "
            "to one person is enough to start."
        )
    if level == "NEEDS_CLARIFICATION":
        return (
            "I want to understand you properly before I say anything else. Are you "
            "having thoughts of harming yourself, and is that happening now? Either "
            "answer is fine, and both are worth getting support for."
        )
    if level == "UNKNOWN":
        return (
            "I could not reliably interpret this text, so I am not going to guess "
            "at what it means. If you are struggling, please talk to someone you "
            "trust or to a local crisis service."
        )
    return (
        "No relevant concern was detected by the supported checks. This does not "
        "confirm anyone's safety. If the result does not reflect what is happening, "
        "please reach out to someone you trust or a qualified professional."
    )


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------
@dataclass
class SafetyResult:
    level: Level = "UNKNOWN"
    subject: Subject = "unclear"
    temporal_context: Temporal = "unclear"
    immediacy: Immediacy = "unclear"
    evidence_codes: list[str] = field(default_factory=list)
    summary: str = ""
    needs_clarification: bool = False
    review_recommended: bool = False
    analysis_status: AnalysisStatus = "complete"
    policy_version: str = POLICY_VERSION
    language_support: AnalysisStatus = "complete"

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "subject": self.subject,
            "temporal_context": self.temporal_context,
            "immediacy": self.immediacy,
            "evidence_codes": sorted(set(self.evidence_codes)),
            "summary": self.summary,
            "needs_clarification": self.needs_clarification,
            "review_recommended": self.review_recommended,
            "analysis_status": self.analysis_status,
            "policy_version": self.policy_version,
            "language_support": self.language_support,
        }


def _escalate(current: str, candidate: str) -> str:
    return candidate if LEVEL_ORDER[candidate] > LEVEL_ORDER[current] else current


# ---------------------------------------------------------------------------
# The policy
# ---------------------------------------------------------------------------
def evaluate(
    raw_text: str,
    *,
    urgency_flagged: Optional[bool] = None,
    urgency_probability: Optional[float] = None,
    urgency_threshold: Optional[float] = None,
) -> SafetyResult:
    """
    Route text to a support level.

    `urgency_*` are the classifier's own outputs, passed in so this function can
    weigh them. They are evidence, not the decision, and they are never rewritten
    or rescaled here. When they are None (model unavailable) the decision rests
    on the text evidence alone and `analysis_status` becomes "degraded".
    """
    result = SafetyResult()

    if raw_text is None or not isinstance(raw_text, str) or not raw_text.strip():
        result.level = "UNKNOWN"
        result.analysis_status = "unsupported"
        result.summary = "No readable text was supplied."
        result.needs_clarification = True
        return result

    text = normalize_shorthand(normalize_typos(normalize_for_safety(raw_text)))
    result.language_support = detect_language_support(text)

    if result.language_support == "unsupported":
        # Honest abstention. Not Normal: we do not know.
        result.analysis_status = "unsupported"
        # Continue the independent check: a supported explicit disclosure can
        # coexist with unsupported material. No broad comprehension is claimed.
    else:
        result.analysis_status = "degraded"

    clauses = split_clauses(text)
    if not clauses:
        result.level = "UNKNOWN"
        result.analysis_status = "unsupported"
        result.summary = "No interpretable sentence was found."
        result.needs_clarification = True
        return result

    codes: set[str] = {"UNSUPPORTED_LANGUAGE"} if result.language_support == "unsupported" else set()
    self_evidence_seen = False
    explicit_evidence_seen = False
    level = "NONE_DETECTED"
    subject_votes: list[str] = []
    contexts: list[tuple[str, str, str]] = []
    historical_event_seen = False
    fictional_character_seen = False
    immediacy_votes: list[str] = []
    summary_bits: list[str] = []

    for clause in clauses:
        subject_start = len(subject_votes)
        c = clause.lowered

        # ---- injection: never lets text choose its own level -------------
        if EVIDENCE_PATTERNS["INSTRUCTION_INJECTION"][0].search(c):
            codes.add("INSTRUCTION_INJECTION")
            # The attempt is noted, then ignored. Routing continues on the rest
            # of the clause exactly as if the instruction were not there.
            c = EVIDENCE_PATTERNS["INSTRUCTION_INJECTION"][0].sub(" ", c)

        # ---- collect evidence present in this clause ----------------------
        present = [
            code
            for code, (pattern, _desc) in EVIDENCE_PATTERNS.items()
            if pattern.search(c)
        ]
        codes.update(present)

        act = "SELF_HARM_ACT" in present or "EXPLICIT_DIE_INTENT" in present
        passive_act = "PASSIVE_WISH_ACT" in present
        method = "METHOD_OR_LOCATION" in present
        intent = "INTENT_VERB" in present
        negated = "NEGATION" in present
        quoted = "QUOTATION_WRAPPER" in present
        educational = "EDUCATIONAL_FRAME" in present
        historical = "HISTORICAL" in present
        hypothetical = "HYPOTHETICAL" in present
        third_party = "THIRD_PARTY_SUBJECT" in present
        # Third-party risk only counts when the clause actually names another
        # person. Otherwise "I want to jump" reads as other-directed, which is
        # both wrong and a false-positive generator.
        third_risk = "THIRD_PARTY_RISK" in present and third_party
        recent_act = "RECENT_ACT" in present
        medical = "MEDICAL_EMERGENCY" in present
        passive = "PASSIVE_DEATH_WISH" in present
        farewell = bool(_FAREWELL.search(c))
        planned = "PLANNED_ACTION" in present
        present_access = "PRESENT_ACCESS" in present
        intrusion = "UNWANTED_THOUGHT" in present
        relates_to_quote = "RELATES_TO_QUOTE" in present
        anaphoric_near_term = "ANAPHORIC_NEAR_TERM" in present
        farewell_prep = "FINAL_ARRANGEMENTS" in present
        violence = "VIOLENCE_OTHER" in present
        deva_harm = "DEVANAGARI_SELF_HARM" in present
        deva_danger = "DEVANAGARI_PRESENT_DANGER" in present
        deva_neg = "DEVANAGARI_NEGATION" in present
        deva_help = "DEVANAGARI_HELP" in present
        hinglish = "HINGLISH_SELF_HARM" in present
        # Devanagari negation scopes this clause exactly like "not" does.
        negated = negated or deva_neg
        abuse = "ABUSE_THREAT" in present
        psychosis = "PSYCHOSIS_VOICE" in present

        # First-person authorship of the risky act, computed once per clause.
        self_ref = self_reference(c)
        other_match = EVIDENCE_PATTERNS["THIRD_PARTY_SUBJECT"][0].search(c)
        author_match = re.search(r"\b(?:i|i'?m|main|mai)\b|(?:मैं|मै)", c)
        event_matches = [EVIDENCE_PATTERNS[code][0].search(c) for code in (
            "SELF_HARM_ACT", "EXPLICIT_DIE_INTENT", "METHOD_OR_LOCATION", "PASSIVE_WISH_ACT")]
        event_positions = [match.start() for match in event_matches if match]
        author_owned_evidence = self_ref and not _QUOTED_SPAN.search(c) and (
            (act and bool(re.search(r"\bmyself\b", c))) or
            (author_match is not None and other_match is not None and event_positions and
             author_match.start() <= min(event_positions) < other_match.start()))
        if author_owned_evidence:
            third_risk = False
        acting_on_self = self_ref and not (third_party and third_risk)

        # D-009d: negation scope. A clause may contain several conjuncts, and a
        # negation binds to what it governs, not to everything after it. "I
        # hurt myself earlier today and the bleeding has not stopped" negates
        # "stopped", not "hurt myself"; reading it as a denial downgraded a
        # reported act plus ongoing bleeding to CONCERNING.
        #
        # Rule: the clause counts as negated for THIS clause's evidence only
        # when a negation marker appears BEFORE the evidence it would cancel.
        # A negation after the evidence is a later conjunct and is not a denial
        # of it.
        negation_span = next(NEGATION.finditer(c), None)
        first_negation_at = negation_span.start() if negation_span else None

        def negated_for(*patterns: re.Pattern) -> bool:
            """Is this clause negated with respect to any of `patterns`?"""
            if first_negation_at is None:
                return False
            for pattern in patterns:
                match = pattern.search(c)
                if match is not None and first_negation_at < match.start():
                    return True
            return False

        # ---- subject -------------------------------------------------------
        # A quotation only makes the subject fictional_or_quoted when the text
        # does NOT also assert it about the author. "A quote says 'I want to
        # die.' It describes how I feel right now" is the author talking.
        asserts_self = self_ref
        clarified_other = bool(
            re.search(r"\b(?:not\s+me|it'?s\s+not\s+me|i\s+mean\s+my|i\s+mean\s+mera)\b", c)
        )
        if clarified_other:
            subject_votes.append("another_person")

        # D-009a: this alternation used to end in a bare `|poem|song`, so ANY
        # clause mentioning a song or a poem matched and the text was reported
        # as fictional_or_quoted. "I like that song a lot" is a first-person
        # statement about a preference. Every alternative now requires an
        # explicit creative frame or a named work.
        fiction = bool(
            re.search(r"\b(?:a\s+quote\s+says|character\s+in\s+my\s+(?:story|novel|book|script)"
                      r"|in\s+my\s+(?:story|novel|book|script|play|game|poem|song)"
                      r"|(?:it|this|that)\s+is\s+(?:just\s+)?(?:a\s+)?(?:fiction|fictional)"
                      r"|(?:purely\s+|only\s+)?fictional"
                      r"|the\s+(?:film|movie|book|show|series|novel|play)\s+(?:includes|features|ends|stars)"
                      r"|my\s+(?:character|hero|heroine|villain)"
                      r"|a\s+character\s+in\s+my\s+story"
                      r"|(?:the|this|my|that|a)\s+(?:poem|song|lyric|script|dialogue)\s+(?:says|says\s+that|goes\s+on|reads|describes|is\s+about)"
                      r"|fictional\s+character)\b", c)
        )
        # An explicit fiction frame is the container: a first-person pronoun
        # inside it belongs to the character, not to the author. A SEPARATE
        # clause that re-asserts the statement ("it describes how I feel") still
        # votes self, which is what decides S034.
        # D-010: an explicit fiction container outranks a bare third-person pronoun.
        # "My novel's main character says she wants to die" was routed HIGH and
        # attributed to another person, because "she" looked like a third-party
        # disclosure and the creative frame was only checked afterwards. The
        # container is the more specific fact: it tells us the death statement
        # belongs to a character, not to the author or to a real person.
        fiction_container = bool(
            re.search(r"\b(?:my\s+(?:character|hero|heroine|villain|"
                      r"(?:story|novel|book|script|play|game)\s*'?s?"
                      r"(?:\s+\w+){0,3}\s+character)|"
                      r"(?:main|primary|central)\s+character\s+(?:says|said|thinks|thought|feels|felt|does|did|goes|went|wants|wanted)\b|"
                      r"character\s+in\s+my\s+(?:story|novel|book|script)"
                      r"|(?:in|of)\s+my\s+(?:story|novel|book|script|play|game)"
                      r"|(?:the|a|this)\s+(?:film|movie|book|novel|play|game)\b"
                      r"|\bthe\s+npc\b|\bin\s+the\s+game\b"
                      r"|(?:it|this|that)\s+is\s+(?:just\s+)?(?:a\s+)?(?:fiction|fictional)"
                      r"|(?:purely\s+|only\s+)?fictional|fictional\s+character)\b", c)
        )
        if fiction_container and re.search(r"\bcharacter\b", c):
            fictional_character_seen = True
        if fiction_container or fiction:
            subject_votes.append("fictional_or_quoted")
        elif third_party and (third_risk or act or passive_act or method) \
                and not author_owned_evidence and not _SELF_ASSERTION.search(c):
            # D-009: "My dad told me he is going to kill himself" was attributed
            # to the author, because the reporting frame ("my dad told me")
            # contains a first-person word and tripped asserts_self. A third
            # party named as at risk wins over an incidental pronoun in the
            # reporting clause; only an explicit self-assertion
            # ("it describes how I feel") outranks it.
            subject_votes.append("another_person")
        elif asserts_self:
            subject_votes.append("self")
        else:
            subject_votes.append("unclear")

        # ---- clause-local level ------------------------------------------
        # Negation is scoped to THIS clause and never clears a self-harm clause
        # on its own: "I do not want to live" is a death wish, not reassurance.
        clause_level = "NONE_DETECTED"

        # Passive death wish: real concern, but never HIGH on its own. Escalating
        # "I want to disappear forever" to HIGH would make HIGH meaningless and
        # train people to ignore it.
        if passive_act and clause_level == "NONE_DETECTED":
            clause_level = "CONCERNING"
            codes.add("PASSIVE_WISH_ACT")
        if "NEGATIVE_WISH" in present and clause_level in ("NONE_DETECTED", "NEEDS_CLARIFICATION"):
            clause_level = "CONCERNING"
            codes.add("NEGATIVE_WISH")

        # An unwanted intrusive thought is worth a direct question, and is not
        # itself intent.
        if intrusion and clause_level == "NONE_DETECTED":
            clause_level = "NEEDS_CLARIFICATION"

        # D-016: a quoted statement the author personally identifies with is
        # not a quotation to be set aside. "A quote said life is not worth
        # living, and I relate to it" is a self-disclosure by way of a quote.
        if relates_to_quote and clause_level in ("NONE_DETECTED", "NEEDS_CLARIFICATION"):
            clause_level = "CONCERNING"
            codes.add("RELATES_TO_QUOTE")

        # D-017: "I am going to do it in an hour" names an action and a time
        # but not its object. The text does not tell us what "it" is, so this
        # is a direct question, not an inference of intent.
        if anaphoric_near_term and clause_level in ("NONE_DETECTED", "NEEDS_CLARIFICATION") \
                and self_ref and not negated_for(EVIDENCE_PATTERNS["ANAPHORIC_NEAR_TERM"][0]):
            clause_level = "NEEDS_CLARIFICATION"
            codes.add("ANAPHORIC_NEAR_TERM")

        # D-012: preparation and farewell evidence. HIGH, never IMMEDIATE -
        # nothing in this pattern claims an act is underway. A negated or quoted
        # instance (someone else's arrangements, a story about them) is not the
        # author's own.
        if farewell_prep and clause_level == "NONE_DETECTED" \
                and (acting_on_self or third_risk) \
                and not negated_for(EVIDENCE_PATTERNS["FINAL_ARRANGEMENTS"][0]):
            clause_level = "HIGH"
            codes.add("FINAL_ARRANGEMENTS")
        elif farewell_prep and clause_level == "NONE_DETECTED":
            clause_level = "CONCERNING"
            codes.add("FINAL_ARRANGEMENTS")

        # Another person described at risk routes to support for THEM. It is
        # never downgraded because the author is not the one at risk.
        if third_risk and clause_level == "NONE_DETECTED":
            clause_level = "HIGH"

        # Non-Latin scripts: same routing, own vocabulary.
        if (deva_harm or hinglish) and (acting_on_self or third_risk) and not negated:
            clause_level = "HIGH"
        if deva_danger:
            clause_level = _escalate(clause_level, "IMMEDIATE")
        if deva_help and clause_level == "NONE_DETECTED":
            clause_level = "CONCERNING"

        if act:
            # Both patterns that can make `act` true must be checked: keying
            # negation on SELF_HARM_ACT alone let "I do not want to die" route
            # HIGH, because that sentence is matched by EXPLICIT_DIE_INTENT.
            if negated_for(
                EVIDENCE_PATTERNS["SELF_HARM_ACT"][0],
                EVIDENCE_PATTERNS["EXPLICIT_DIE_INTENT"][0],
            ):
                # "I do not want to kill myself today, but ..." - the negation
                # is real for this clause, but the statement still concerns
                # self-harm and must not read as reassurance.
                #
                # D-018: a CLEAN denial ("I don't want to kill myself", "I have
                # no plans to harm myself") with no other distress signal is
                # best answered by a direct question, not by support copy that
                # presumes the person is at risk. The moment the clause also
                # carries distress or a passive wish, it becomes CONCERNING.
                # Seed S022 ("I do not want to live anymore") is matched by
                # PASSIVE_WISH_ACT, not by this branch, so it is unaffected.
                if passive or passive_act or "DISTRESS" in present \
                        or "AMBIGUOUS_DISTRESS" in present \
                        or "NEGATIVE_WISH" in present:
                    clause_level = "CONCERNING"
                else:
                    clause_level = "NEEDS_CLARIFICATION"
                codes.add("NEGATED_SELF_HARM_CLAUSE")
            elif intrusion:
                clause_level = "NEEDS_CLARIFICATION"
            elif planned or present_access or recent_act:
                clause_level = "HIGH"
            elif intent or method:
                clause_level = "HIGH"
            else:
                clause_level = "CONCERNING"

        # Method/location with intent but no self-harm vocabulary at all.
        # Scope: the intent must belong to the person, and a negation in this
        # clause cancels it. "I do not want to jump from the tenth floor" is a
        # real statement about NOT wanting to; routing it HIGH would be the
        # same category of error as routing a disclosure to Normal.
        # D-010c: computed before the escalation branches so it also guards the
        # present-position branch. "I am at the balcony watering plants" is a
        # person on a balcony, which is not itself a risk statement.
        location_actionable = _location_is_actionable(
            c, method=method, intent=intent, present_access=present_access, act=act
        )
        if clause_level == "NONE_DETECTED" and method and intent and acting_on_self \
                and not negated and location_actionable:
            clause_level = "HIGH"
        if clause_level == "NONE_DETECTED" and _METHOD_INTENT.search(c) and not negated:
            clause_level = "HIGH"

        # Immediate danger needs three things together, not a location alone:
        # a method/location, a present position, AND an action or stated intent.
        # "I am on the balcony" is a Q question, not a present emergency.
        action_signal = bool(planned or _METHOD_INTENT.search(c) or intent)
        if method and present_access and action_signal and not negated:
            clause_level = "IMMEDIATE"
        elif present_access and not negated and clause_level == "NONE_DETECTED" and self_ref \
                and location_actionable:
            # Standing somewhere risky with no stated action: ask, do not assume.
            clause_level = "NEEDS_CLARIFICATION"

        # D-009c. A present-position claim at a named fall edge, with an
        # explicit present-time marker, is supportable now even though no action
        # is stated. "I'm outside on the ledge right now" and "I am standing on
        # the roof edge at this moment" both qualify; "I am at the balcony
        # watering plants" does not, because it names no edge and no present
        # marker. The text does not say the person intends to jump, and this does
        # not claim that it does - it routes them to a person rather than away
        # from one.
        if method and present_access and not negated and clause_level in (
            "NONE_DETECTED", "NEEDS_CLARIFICATION"
        ) and self_ref and _PRESENT_TIME.search(c):
            clause_level = _escalate(clause_level, "HIGH")
            codes.add("PRESENT_POSITION_AT_EDGE")
        if recent_act and not negated:
            # A reported past act is concerning support, not a present emergency
            # unless the text also puts the person somewhere now.
            clause_level = _escalate(clause_level, "HIGH")

        if farewell and clause_level in ("NONE_DETECTED", "NEEDS_CLARIFICATION"):
            clause_level = "NEEDS_CLARIFICATION"
            codes.add("FAREWELL")
        if "AMBIGUOUS_DISTRESS" in present and clause_level == "NONE_DETECTED":
            clause_level = "NEEDS_CLARIFICATION"
        # A farewell is a question, not a finding. It is exempt from the generic
        # passive-wish promotion below because "you won't hear from me again"
        # states a goodbye, not a wish to die: routing it CONCERNING would claim
        # more than the text says, and would drop the direct clarification the
        # specification requires. Elevated instead, by combination, elsewhere.
        if passive and not farewell and clause_level in ("NONE_DETECTED", "NEEDS_CLARIFICATION"):
            clause_level = "CONCERNING"
        if "DISTRESS" in present and clause_level == "NONE_DETECTED":
            clause_level = "CONCERNING"

        if medical:
            clause_level = _escalate(clause_level, "IMMEDIATE")
            codes.add("MEDICAL_EMERGENCY")
        if violence:
            clause_level = _escalate(clause_level, "HIGH")
        if abuse:
            clause_level = _escalate(clause_level, "IMMEDIATE")
        if psychosis:
            clause_level = _escalate(clause_level, "HIGH")

        if third_risk and clause_level != "NONE_DETECTED":
            subject_votes.append("another_person")

        # ---- context gates -------------------------------------------------
        if historical and _temporal_for_concern(c, present) == "historical" and clause_level in ("HIGH", "IMMEDIATE"):
            # Past-tense risk with an explicit recovery marker stays supportable
            # but is not presented as a present emergency.
            clause_level = "CONCERNING"
            codes.add("HISTORICAL_CONTEXT")
        # Educational framing suppresses the word, not just the escalation: a
        # suicide-prevention lesson necessarily contains the word "suicide".
        # It only stays suppressed while nothing asserts first-person intent.
        if educational and not (acting_on_self and intent):
            clause_level = "NONE_DETECTED"
            codes.add("EDUCATIONAL_FRAME")
        if quoted and not self_reference(c) and not negated:
            # Quoted or fictional and not re-asserted as personal.
            if clause_level in ("HIGH", "IMMEDIATE"):
                clause_level = "NEEDS_CLARIFICATION"
                codes.add("QUOTED_STATEMENT")

        # A disclaimer does not cancel a personal disclosure.
        if (fiction or fiction_container) and not _SELF_ASSERTION.search(c):
            clause_level = "NONE_DETECTED"
            codes.add("FICTION_FRAME")
        if clause_level in ("HIGH", "IMMEDIATE") and re.search(r"\b(?:just\s+(?:saying|kidding)|lol|😂|\u2028)\b", c):
            codes.add("DISMISSAL_PRESENT")

        if act or passive_act or deva_harm or hinglish:
            self_evidence_seen = True
        if act or deva_harm or hinglish or third_risk:
            # Only an explicit act licenses carrying a later planning clause up
            # to HIGH. A passive wish plus "tomorrow" is still a passive wish.
            explicit_evidence_seen = True

        if _temporal_for_concern(c, present) == "historical":
            historical_event_seen = True
        if clause_level != "NONE_DETECTED":
            clause_subject = _majority(subject_votes[subject_start:], "unclear")
            clause_temporal = _temporal_for_concern(c, present)
            contexts.append((clause_level, clause_subject, clause_temporal))
            summary_bits.append(clause.text[:80])
            level = _escalate(level, clause_level)
            if clause_level in ("HIGH", "IMMEDIATE") and not negated:
                immediacy_votes.append("stated" if (planned or present_access) else "not_stated")

    # ---- anaphoric carry-over -------------------------------------------
    # "I don't want to kill myself today, but I have a plan for tomorrow."
    # The second clause names no self-harm term at all; it only makes sense
    # against the first. Without this, the contrast clause silently downgrades
    # the text. The same rule keeps M003 ("never mind, forget it") from
    # resetting unresolved concern.
    # D-019. A recovery or safety marker ANYWHERE in the text caps a HIGH that
    # carries no present-tense marker. "I tried to kill myself as a teenager. I
    # am safe now" was routed IMMEDIATE because the recovery sentence was in a
    # different clause than the disclosure. The cap applies only when the HIGH
    # clause itself contains no current timing or present position, so adding a
    # real present-tense statement still raises the level.
    if level in ("HIGH", "IMMEDIATE") and _RECOVERY.search(text) \
            and contexts and all(time == "historical" for _, _, time in contexts):
        level = "CONCERNING"
        codes.add("HISTORICAL_CONTEXT")

    if explicit_evidence_seen and level in ("NONE_DETECTED", "NEEDS_CLARIFICATION", "CONCERNING"):
        for clause in clauses:
            low = clause.lowered
            # A recovery clause closes the question rather than opening it.
            # "I am safe now and getting help" must not be read as an
            # anaphoric reference to an earlier disclosure.
            if _RECOVERY.search(low):
                codes.add("RECOVERY_CONTEXT")
                continue
            # D-015: a clause already resolved as fiction, quotation or
            # education is not an anaphoric reference back to a disclosure.
            # Without this, "In the game, the NPC says he will end his life"
            # was cleared by the fiction gate and then immediately re-escalated
            # by the carry-over, because it contains the word "will".
            if _CONTEXT_RESOLVED.search(low):
                codes.add("CONTEXT_RESOLVED_NO_CARRY")
                continue
            planning = re.search(r"\b(?:plan(?:ned|ning)?|intend(?:ing)?|going\s+to|gonna"
                                r"|tonight|tomorrow|later|soon|afterwards|will)\b", low)
            # A present-time word only carries anaphora when the clause also
            # re-asserts the statement about the author. "I am safe now" is
            # caught by the recovery guard above; "it describes how I feel right
            # now" is the author claiming the quoted disclosure.
            reasserting = bool(
                _SELF_ASSERTION.search(low)
                and re.search(r"\b(?:right\s+now|now|today|still|present)\b", low)
            )
            if planning or reasserting:
                level = _escalate(level, "HIGH")
                codes.add("ANAPHORIC_PLANNING")
                carried_subject = "self" if reasserting or self_reference(low) else (
                    contexts[-1][1] if contexts else _majority(subject_votes, "unclear"))
                contexts.append(("HIGH", carried_subject, "current"))
                break

    # ---- model evidence, recorded but never substituted -------------------
    # The urgency classifier is trained on the same subreddit proxy labels as the
    # condition model, so it fires on method vocabulary regardless of who is
    # talking or what they intend. Measured on the seeded corpus at the deployed
    # 0.15 threshold: it flags 67 of 78 cases, including "I live on the tenth
    # floor" (p=0.247), "This deadline is killing me" (p=0.669) and "I need to
    # kill the process" (p=0.466).
    #
    # When this flag was allowed to lift NONE_DETECTED to NEEDS_CLARIFICATION, a
    # user describing their address was asked whether they were having thoughts
    # of harming themselves. That is a false positive in the one channel the
    # product cannot afford to have noisy, so the flag is now evidence only.
    #
    # It remains strictly additive: it can never lower a text-derived level, and
    # a HIGH text that the classifier does not flag stays HIGH. Silence from the
    # model is not treated as reassurance.
    #
    # Residual risk, stated rather than hidden: a disclosure phrased entirely
    # outside this pattern set that the engine also reads as NONE_DETECTED now
    # returns NONE_DETECTED rather than a clarification question. That risk is
    # measured by the out-of-vocabulary paraphrase families in the corpus, not
    # assumed away.
    if urgency_flagged is None:
        if result.analysis_status != "unsupported":
            result.analysis_status = "degraded"
        codes.add("URGENCY_MODEL_UNAVAILABLE")
    elif urgency_flagged:
        codes.add("URGENCY_MODEL_FLAGGED")
    else:
        codes.add("URGENCY_MODEL_NOT_FLAGGED")

    # ---- assemble --------------------------------------------------------
    if result.language_support == "unsupported" and level == "NONE_DETECTED":
        level = "UNKNOWN"
    result.level = level  # type: ignore[assignment]
    if contexts:
        priority = max(LEVEL_ORDER[entry[0]] for entry in contexts)
        relevant = [entry for entry in contexts if LEVEL_ORDER[entry[0]] == priority]
        result.subject = _majority((entry[1] for entry in relevant), "unclear")
        times = [entry[2] for entry in relevant]
        # Unresolved current concern outranks older concern. This is event
        # attribution within one input, not persisted conversation memory.
        result.temporal_context = "current" if "current" in times else _majority(times, "unclear")
    else:
        result.subject = _majority(subject_votes, "unclear")
        result.temporal_context = (
            "historical" if historical_event_seen else
            "hypothetical" if "FICTION_FRAME" in codes and (fictional_character_seen or any(code in codes for code in (
                "SELF_HARM_ACT", "EXPLICIT_DIE_INTENT", "PASSIVE_DEATH_WISH", "THIRD_PARTY_RISK", "METHOD_OR_LOCATION"
            ))) else "unclear")
    result.immediacy = _majority(immediacy_votes, "unclear")
    # Support priority cannot manufacture stated timing. Missing timing remains
    # unclear even when urgent support is warranted.
    result.evidence_codes = sorted(codes)
    result.needs_clarification = result.level in ("NEEDS_CLARIFICATION", "UNKNOWN") or (
        result.subject == "unclear" and result.level in ("CONCERNING",)
    )
    result.review_recommended = result.level in (
        "CONCERNING",
        "HIGH",
        "IMMEDIATE",
        "UNKNOWN",
    ) or "DISMISSAL_PRESENT" in codes
    result.summary = _summary(result.level, summary_bits)
    if result.level == "UNKNOWN" and result.language_support == "unsupported":
        result.summary = "Unsupported language/script and no reliably recognized concern; assessment is insufficient."

    if result.level in ("HIGH", "IMMEDIATE", "CONCERNING"):
        # Invariants the contract depends on. Asserted rather than assumed.
        assert "NORMAL_TAKEAWAY" not in result.summary
    return result


# The negation marker list, reused for the scope analysis in `negated_for`.
# Derived from the evidence entry rather than restated, so the two cannot drift.
NEGATION = EVIDENCE_PATTERNS["NEGATION"][0]

# D-015: clauses in which context already settled the matter. The anaphoric
# carry-over must not reach into them.
_CONTEXT_RESOLVED = re.compile(
    r"\b(?:fictional(?:ly)?|it\s+is\s+(?:just\s+)?(?:a\s+)?(?:fiction|fictional)"
    r"|a\s+quote\s+says|the\s+film|the\s+(?:documentary|article|paper|lesson|teacher)"
    r"|(?:suicide|self[- ]harm|mental\s+health)\s*(?:prevention|awareness)"
    r"|warning\s+signs|a\s+character\s+in\s+my|\bthe\s+npc\b"
    r"|in\s+the\s+game|in\s+my\s+(?:story|novel|book|script|play))\b"
)

# A farewell: a goodbye with no stated intent. Kept separate from the passive
# death wish because the two need different handling - one is a statement about
# dying, the other is a question to ask.
_FAREWELL = re.compile(
    r"\b(?:won'?t|will\s+not)\s+(?:ever\s+)?(?:see|hear|speak\s+to|be\s+in\s+touch)"
    r"\s+(?:from\s+)?me\b"
    r"|goodbye\b[^.?!]{0,24}(?:again|anymore|any\s+more)\b"
)

# Possessives that point at somebody or something else rather than the author's
# own state: "my friend wants to die" is not the author talking.
_POSSESSIVE_OTHER = re.compile(
    r"\b(?:my|mera|meri|mere|apne|apki)\s+(?:friend|brother|sister|mother|father|son|daughter|wife|husband|partner"
    r"|boyfriend|girlfriend|neighbour|neighbor|cousin|pal|story|novel|book|film|movie"
    r"|character|class|teacher|therapist|doctor|dost|dost\w*|bhai|behen|bhai\w*|behen\w*|didi|bhaiya)\b"
)

# Explicit first-person self-assertion that survives a quotation wrapper.
# Explicit recovery / safety markers. Present tense "now" alone is NOT one of
# these: "I am safe now" is recovery, "I am going to jump now" is not.
_RECOVERY = re.compile(
    r"\b(?:safe\s+now|i(?:'m| am)\s+safe|getting\s+help|receiving\s+help|in\s+recovery"
    r"|no\s+current\s+urge|not\s+going\s+to|away\s+from\s+danger|with\s+(?:a\s+)?trusted"
    r"|with\s+someone|with\s+my\s+(?:partner|friend|family)|i\s+have\s+support|supported)\b"
)

_SELF_ASSERTION = re.compile(
    r"\b(?:how\s+i\s+feel|describes\s+(?:me|how\s+i)|that'?s\s+me|speaks\s+to\s+me"
    r"|it\s+is\s+(?:me|i)|this\s+is\s+(?:me|my))\b"
)


_QUOTED_SPAN = re.compile(
    "[\\\"\\u201c][^\\\"\\u201c\\u201d]{1,160}[\\\"\\u201d]"
)


def self_reference(clause: str) -> bool:
    """
    Does this clause talk about the author's own state?

    Hinglish first person (main / mujhe / mera / mujko) counts, because the
    supported capability includes Hinglish and treating "main ... kudna chahta
    hu" as third-person would silently drop a disclosure.

    A possessive naming another person or a story is NOT self-reference: "my
    friend says he is about to jump" is a third-party disclosure and must not be
    relabelled as the author's own risk.
    """
    stripped = _POSSESSIVE_OTHER.sub(" ", _QUOTED_SPAN.sub(" ", clause))
    if _SELF_ASSERTION.search(clause):
        return True
    return bool(
        re.search(r"\b(?:i|i'?m|i'?ve|my|mine|myself|me)\b", stripped)
        or re.search(r"(?:^|[\s।])(?:main|mai|mujhe|mujko|mera|meri|मैं|मुझे|मेरा|मेरी|मै)", stripped)
    )


# Time cues are grammatical/event anchors, not new danger vocabulary. A
# recovery statement is not itself evidence that a preceding event is old.
_HISTORICAL_TIME = re.compile(r"\b(?:years?\s+ago|last\s+year|as\s+a\s+teenager|in\s+20\d{2}|used\s+to)\b")
_RECENT_TIME = re.compile(r"\b(?:last\s+(?:night|week)|earlier(?:\s+today)?|yesterday|\w+\s+days?\s+ago)\b")
_PRESENT_GRAMMAR = re.compile(
    r"\b(?:am|is|are|do|does|cannot|have|has|need|needs|keep|keeps|think|thinks|hope|hopes|feel(?:s)?|wish(?:es)?|want(?:s)?|plan(?:s)?|intend(?:s)?|"
    r"have\s+(?:been|decided|made|written)|will|going\s+to|now|today|tonight|tomorrow)\b"
    r"|\b(?:hu|hoon|hai|hain|chahta|chahti|wala)\b|(?:हूँ|है|हैं|चाहता|चाहती)"
)


def _temporal_for_concern(clause: str, present: list[str]) -> str:
    """Time of relevant concern; urgency, recovery and benign filler are separate."""
    historical_self_harm = bool(re.search(r"\bused\s+to\s+self[- ]harm\b", clause))
    event = historical_self_harm or any(code in present for code in (
        "SELF_HARM_ACT", "EXPLICIT_DIE_INTENT", "RECENT_ACT", "PASSIVE_WISH_ACT",
        "PASSIVE_DEATH_WISH", "HINGLISH_SELF_HARM", "DEVANAGARI_SELF_HARM"))
    if event and _HISTORICAL_TIME.search(clause):
        return "historical"
    if event and (_RECENT_TIME.search(clause) or
                  ("कल" in clause and any(marker in clause for marker in ("मैंने", "था", "किया", "पहुँचाया")))):
        return "recent"
    if "HYPOTHETICAL" in present:
        return "hypothetical"
    if _PRESENT_GRAMMAR.search(clause) or (
        "PASSIVE_DEATH_WISH" in present and "HISTORICAL" not in present
    ):
        return "current"
    return "unclear"


def _majority(votes: Iterable[str], default: str) -> str:
    votes = list(votes)
    if not votes:
        return default
    counts: dict[str, int] = {}
    for v in votes:
        counts[v] = counts.get(v, 0) + 1
    # "self" wins ties: when the author is unclear the safer read is that they
    # are talking about themselves, which routes to support rather than away.
    best = max(counts.items(), key=lambda kv: (kv[1], kv[0] == "self"))
    return best[0]


def _summary(level: str, bits: list[str]) -> str:
    if not bits:
        return "No self-harm evidence found in the text."
    head = "; ".join(bits[:2])
    return f"Routed {level} on: {head}"


__all__ = [
    "POLICY_VERSION",
    "SafetyResult",
    "evaluate",
    "normalize_for_safety",
    "detect_language_support",
    "split_clauses",
    "support_action",
    "LEVEL_ORDER",
]
