"""Failures must preserve raw-text safety; all inputs are synthetic."""
import subprocess
import sys
import pytest
from mental_health_screening import inference


@pytest.fixture(scope="module")
def screener():
    return inference.MentalHealthScreener()


@pytest.mark.parametrize("component", ["clean_and_lemmatize", "extract_handcrafted_features"])
def test_optional_processing_failure_preserves_high(screener, monkeypatch, component):
    def fail(*args):
        raise LookupError("synthetic missing resource")
    monkeypatch.setattr(inference, component, fail)
    result = screener.screen("i wanna jump from 10th floor")
    assert result["safety"]["level"] == "HIGH"
    assert result["safety"]["analysis_status"] == "degraded"
    assert result["safety"]["support_action"]
    assert result["primary"]["status"] == "unavailable"
    assert result["primary"]["predicted_class"] is None
    if component == "clean_and_lemmatize":
        assert result["urgency"]["suicide_probability"] is None
    else:
        assert result["urgency"]["status"] == "complete"


def test_safety_module_import_does_not_import_optional_packages():
    code = '''
import sys
class Block:
 def find_spec(self, fullname, path=None, target=None):
  if fullname.split('.')[0] in {'nltk','ftfy','numpy','scipy','sklearn'}:
   raise ImportError('synthetic unavailable dependency')
sys.meta_path.insert(0, Block())
from mental_health_screening.safety import evaluate
assert evaluate('i wanna jump from 10th floor').level == 'HIGH'
'''
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_feature_vector_failure_does_not_abort_safety_or_urgency(screener, monkeypatch):
    monkeypatch.setattr(screener, "_build_primary_features", lambda *args: (_ for _ in ()).throw(ValueError()))
    result = screener.screen("i wanna jump from 10th floor")
    assert result["safety"]["level"] == "HIGH"
    assert result["primary"]["status"] == "unavailable"
    assert result["urgency"]["status"] == "complete"


def test_processing_failure_without_reliable_evidence_is_unknown(screener, monkeypatch):
    def fail(*args):
        raise LookupError("synthetic missing resource")
    monkeypatch.setattr(inference, "clean_and_lemmatize", fail)
    result = screener.screen("An unfamiliar synthetic statement")
    assert result["safety"]["level"] == "UNKNOWN"
    assert result["safety"]["needs_clarification"] is True
    assert result["primary"]["predicted_class"] is None
    assert result["urgency"]["suicide_probability"] is None


@pytest.mark.parametrize("level", ["HIGH", "IMMEDIATE", "CONCERNING", "NEEDS_CLARIFICATION"])
def test_support_addresses_affected_person(level):
    from mental_health_screening.safety import support_action
    text = support_action(level, subject="another_person")
    assert "them" in text.lower() or "their" in text.lower()
    assert "harming yourself" not in text
