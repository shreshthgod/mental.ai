import inspect

import pytest

from evaluation.evaluate_contextual_intelligence import predict_text


class Screener:
    def screen(self, text):
        assert isinstance(text, str)
        return {"primary": {"predicted_class": "Normal"}, "urgency": {"flagged": False},
                "safety": {"level": "NONE_DETECTED"}, "model_version": "test"}


def test_prediction_accepts_text_only():
    assert list(inspect.signature(predict_text).parameters) == ["text", "screener", "recognizer"]
    with pytest.raises(TypeError):
        predict_text({"text": "hello", "expected_safety": "HIGH"}, Screener())


def test_changing_labels_cannot_change_predictions():
    a = {"text": "I plan to jump from the bridge tonight.", "expected_safety": "HIGH"}
    b = {**a, "expected_safety": "NONE_DETECTED"}
    first = predict_text(a["text"], Screener())
    second = predict_text(b["text"], Screener())
    assert first == second
    assert first["safety_raw"] in {"HIGH", "IMMEDIATE"}
    assert first["contextual"]["status"] == "unavailable"
    assert first["fusion"]["status"] == "unavailable"


def test_legacy_normal_cannot_override_safety():
    result = predict_text("I want to kill myself tonight.", Screener())
    assert result["condition"] == "Normal"
    assert result["safety_raw"] in {"HIGH", "IMMEDIATE"}
