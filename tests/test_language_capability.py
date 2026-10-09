"""Language heuristics are fallible; these are engineering examples only."""
import pytest
from mental_health_screening.safety import evaluate, detect_language_support


@pytest.mark.parametrize('text',['hello','Die ist da','Gift in der Hand','main theek hu',
                                'मैं ठीक हूँ','I feel tired today'])
def test_function_words_and_script_do_not_establish_complete_comprehension(text):
    assert detect_language_support(text) != 'complete'


def test_recognized_supported_intent_survives_mixed_unsupported_script():
    result=evaluate('Я устал. I want to kill myself.')
    assert result.level=='HIGH'
    assert result.subject=='self'
    assert result.analysis_status=='unsupported'


def test_unsupported_without_recognized_concern_is_unknown():
    result=evaluate('Я устал и мне трудно')
    assert result.level=='UNKNOWN'
    assert result.analysis_status=='unsupported'


def test_homoglyph_obfuscation_is_not_claimed_understood():
    # Cyrillic i/а: no general folding or translation is validated.
    result=evaluate('I wаnt to kіll myself')
    assert result.level=='UNKNOWN'
    assert result.analysis_status=='unsupported'
