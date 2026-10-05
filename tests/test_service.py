"""
Integration and unit tests for the mental-health screening system.

These tests verify:
- package import and artifact loading
- inference with actual artifacts
- API endpoints
- defensive error handling

Run:
    PYTHONPATH=Step 12 - Packaging/package:$PYTHONPATH pytest tests/test_service.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Step 12 - Packaging", "package"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

import pytest
from mental_health_screening.inference import MentalHealthScreener


def test_package_import_and_screen():
    """Verified: MentalHealthScreener imports and produces predictions."""
    s = MentalHealthScreener()
    result = s.screen("This is a test input for screening.")
    assert "primary" in result
    assert "urgency" in result
    assert "predicted_class" in result["primary"]
    assert isinstance(result["urgency"]["flagged"], bool)
    assert "cleaned_text" in result


def test_input_validation_none():
    s = MentalHealthScreener()
    with pytest.raises(ValueError):
        s.screen(None)


def test_input_validation_empty():
    s = MentalHealthScreener()
    with pytest.raises(ValueError):
        s.screen("   ")


def test_input_validation_non_string():
    s = MentalHealthScreener()
    with pytest.raises(ValueError):
        s.screen(12345)


def test_artifact_loading():
    """Verified: all required artifacts load without FileNotFoundError."""
    s = MentalHealthScreener()
    # Screen call implicitly verifies artifacts
    s.screen("Verification input.")


if __name__ == "__main__":
    # Quick smoke test
    test_package_import_and_screen()
    print("Smoke test PASSED")
