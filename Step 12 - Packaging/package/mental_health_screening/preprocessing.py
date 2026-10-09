"""
Cleaning + preprocessing for a single raw text string, reusing the exact
logic from Step 4 (clean_datasets.py) and Step 5 (preprocess_text.py) of the
pipeline -- copied here rather than imported so this package has no
dependency on the pipeline's sandbox folder layout.
"""
import re
import ftfy
import emoji
import contractions
from nltk import word_tokenize
from nltk.tag import pos_tag
from nltk.stem import WordNetLemmatizer

_LEM = WordNetLemmatizer()

# ---------- Step 4: cleaning (verbatim logic from clean_datasets.py) ----------
_URL_RE = re.compile(r"http\S+|www\.\S+")
_REDDIT_USER_RE = re.compile(r"/?u/[A-Za-z0-9_-]+")
_REDDIT_SUB_RE = re.compile(r"/?r/[A-Za-z0-9_-]+")
_TWITTER_MENTION_RE = re.compile(r"@\w+")
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"\b(\+?\d{1,2}[\s.-]?)?(\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}\b")
_JUNK_MARKER_RE = re.compile(r"^\s*\[(removed|deleted)\]\s*$", re.IGNORECASE)
_MULTI_WS_RE = re.compile(r"\s+")
_GLUED_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def clean_text(s: str) -> str:
    """Step 4's clean_text(), unchanged."""
    s = ftfy.fix_text(s)
    s = _GLUED_BOUNDARY_RE.sub(" ", s)
    s = _URL_RE.sub(" ", s)
    s = _REDDIT_USER_RE.sub(" ", s)
    s = _REDDIT_SUB_RE.sub(" ", s)
    s = _TWITTER_MENTION_RE.sub(" ", s)
    s = _EMAIL_RE.sub(" ", s)
    s = _PHONE_RE.sub(" ", s)
    s = emoji.demojize(s, delimiters=(" :", ": "))
    s = s.replace("_", " ")
    s = _MULTI_WS_RE.sub(" ", s).strip()
    return s


def is_junk_marker(s: str) -> bool:
    return bool(_JUNK_MARKER_RE.match(s))


# ---------- Step 5: contraction expansion + tokenize/POS/lemmatize ----------
def _wn_pos(tag):
    if tag.startswith("J"):
        return "a"
    if tag.startswith("V"):
        return "v"
    if tag.startswith("R"):
        return "r"
    return "n"


def _is_word(tok):
    return any(ch.isalnum() for ch in tok)


def safe_fix(s: str) -> str:
    """Expand contractions; failures reach the screener's availability boundary.

    Historical training retained a raw-string fallback. Serving now reports
    unavailable processing rather than silently changing the feature workflow.
    """
    return contractions.fix(s)


def lemmatize_text(cleaned_text: str) -> str:
    """Step 5's per-row logic (expand contractions -> lowercase -> tokenize ->
    POS-tag -> lemmatize -> drop punctuation-only tokens), for one string."""
    expanded = safe_fix(str(cleaned_text))
    tokens = word_tokenize(expanded.lower())
    tagged = pos_tag(tokens)
    lemmas = [_LEM.lemmatize(w, _wn_pos(t)) for w, t in tagged if _is_word(w)]
    return " ".join(lemmas)


def clean_and_lemmatize(raw_text: str):
    """Full Step 4 + Step 5 pipeline for one raw string. Returns
    (cleaned_text, lemmatized_text) -- both are needed by features.py,
    matching how Step 7 used both `text` and `text_lemmatized`."""
    cleaned = clean_text(str(raw_text))
    lemmatized = lemmatize_text(cleaned)
    return cleaned, lemmatized
