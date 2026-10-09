"""Missing optional raw artifacts do not disable the independent safety path."""
import json
from pathlib import Path
import shutil
import pytest
from mental_health_screening.inference import MentalHealthScreener

ARTIFACTS = Path(__file__).resolve().parents[1]/'Step 12 - Packaging/package/mental_health_screening/artifacts'


@pytest.mark.parametrize('missing,status', [('primary_xgboost.pkl','primary'), ('urgency_logreg.pkl','urgency')])
def test_missing_raw_model_preserves_supported_high(tmp_path, missing, status):
    for path in ARTIFACTS.iterdir():
        if path.is_file() and path.name != missing:
            try:
                (tmp_path/path.name).symlink_to(path)
            except OSError:
                shutil.copy2(path, tmp_path/path.name)
    result = MentalHealthScreener(artifacts_dir=str(tmp_path)).screen('i wanna jump from 10th floor')
    assert result['safety']['level'] == 'HIGH'
    assert result[status]['status'] == 'unavailable'
    assert result['safety']['analysis_status'] == 'degraded'


def test_wrong_feature_order_is_not_published_as_real_prediction():
    screener = MentalHealthScreener()
    screener._feature_order = list(reversed(screener._feature_order))
    result = screener.screen('i wanna jump from 10th floor')
    assert result['primary']['status'] == 'unavailable'
    assert result['safety']['level'] == 'HIGH'


def test_wrong_class_order_is_not_published_as_real_prediction():
    screener = MentalHealthScreener()
    screener._primary_label_encoder.classes_ = screener._primary_label_encoder.classes_[::-1]
    result = screener.screen('i wanna jump from 10th floor')
    assert result['primary']['status'] == 'unavailable'
    assert result['safety']['level'] == 'HIGH'
