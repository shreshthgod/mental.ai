from mental_health_screening.inference import MentalHealthScreener
from mental_health_screening import preprocessing, features, inference


def test_contraction_failure_is_reported_not_silently_substituted(monkeypatch):
    def fail(*args): raise RuntimeError('synthetic contraction failure')
    monkeypatch.setattr(preprocessing.contractions, 'fix', fail)
    result=MentalHealthScreener().screen('i wanna jump from 10th floor')
    assert result['components']['preprocessing']=='unavailable'
    assert result['primary']['status']==result['urgency']['status']=='unavailable'
    assert result['safety']['level']=='HIGH'


def test_nonfinite_feature_is_not_published_as_complete_model_result(monkeypatch):
    original=inference.extract_handcrafted_features
    def broken(*args, **kwargs):
        values=original(*args, **kwargs)
        values['vader_neg']=float('nan')
        return values
    monkeypatch.setattr(inference,'extract_handcrafted_features',broken)
    result=MentalHealthScreener().screen('i wanna jump from 10th floor')
    assert result['primary']['status']=='unavailable'
    assert result['urgency']['status']=='complete'
    assert result['safety']['level']=='HIGH'
