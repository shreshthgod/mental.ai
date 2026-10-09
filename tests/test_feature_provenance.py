import json
from pathlib import Path
import pytest
from mental_health_screening import features
from mental_health_screening.inference import MentalHealthScreener


def test_configured_lexicon_is_used_instead_of_packaged_defaults(tmp_path):
    (tmp_path/'urgency.json').write_text(json.dumps({'curated_urgency_keywords':['synthetickeyword']}))
    (tmp_path/'emotion.json').write_text(json.dumps({'classes':['Normal'], 'lexicon':{'synthetickeyword':{'Normal':1.0}}}))
    row = features.extract_handcrafted_features('synthetickeyword', 'synthetickeyword',
        urgency_lexicon=str(tmp_path/'urgency.json'), emotion_lexicon=str(tmp_path/'emotion.json'))
    assert row['urgency_keyword_count'] == 1
    assert row['emo_lex_Normal'] == 1


def test_readability_failure_does_not_fabricate_zero_features(monkeypatch):
    def fail(*args): raise RuntimeError('synthetic readability failure')
    monkeypatch.setattr(features.textstat, 'flesch_reading_ease', fail)
    result = MentalHealthScreener().screen('i wanna jump from 10th floor')
    assert result['primary']['status'] == 'unavailable'
    assert result['safety']['level'] == 'HIGH'
