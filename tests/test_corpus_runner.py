"""Mutation checks for the engineering oracle, not model validation."""
import copy
import pytest
from scripts import run_safety_corpus as runner


@pytest.fixture
def case():
    return {
        "case_id": "mutation", "family": "explicit_intent", "input": "synthetic",
        "expected_allowed_routes": ["HIGH"], "expected_subject": "self",
        "expected_temporal_context": "current", "expected_support_action": "urgent",
        "prohibited_behavior": "normal_takeaway",
        "paraphrase_group": "mutation", "review_status": "synthetic",
    }


@pytest.mark.parametrize("change", [
    {"level": "NONE_DETECTED"}, {"subject": "unclear"},
    {"temporal_context": "historical"}, {"action": ""},
    {"action": "You're fine, all clear"},
    {"status": "unavailable", "level": "NONE_DETECTED"},
])
def test_oracle_rejects_wrong_behavior(case, change):
    actual = dict(level="HIGH", subject="self", codes=set(),
                  action="Contact local emergency support.",
                  temporal_context="current", status="complete")
    actual.update(change)
    assert runner.check_case(case, **actual)


def test_pipeline_checks_returned_action_and_temporal_context(case):
    class BrokenPipeline:
        def screen(self, text):
            return {
                "safety": {"level": "HIGH", "subject": "self", "evidence_codes": [],
                           "temporal_context": "historical", "analysis_status": "complete",
                           "support_action": "You're fine"},
                "primary": {"predicted_class": "Normal", "status": "complete"},
                "urgency": {"predicted_class": "suicide", "status": "complete",
                            "suicide_probability": .7},
            }
    rows, failures = runner.run_layer([case], "pipeline", BrokenPipeline())
    assert failures == ["mutation"]
    assert rows[0]["actual_temporal_context"] == "historical"
    assert any("reassurance" in p for p in rows[0]["problems"])


def test_required_failure_exits_nonzero(case, monkeypatch, tmp_path):
    bad = copy.deepcopy(case)
    bad["expected_allowed_routes"] = ["IMMEDIATE"]
    monkeypatch.setattr(runner, "load_corpus", lambda **kw: ([bad], {
        "corpus_versions": ["mutation"], "review_status": {"synthetic"},
        "includes_holdout": False}))
    monkeypatch.setattr(runner, "ROOT", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["runner", "--layer", "engine"])
    assert runner.main() == 1


def test_subject_denominator_excludes_documented_opt_outs(case):
    skipped=copy.deepcopy(case)
    skipped.update(case_id='opt-out', subject_check='not_required_benign_control', paraphrase_group='opt-out')
    rows, _=runner.run_layer([case,skipped], 'engine', None)
    report=runner.build_report([case,skipped], {'corpus_versions':['mutation'],
        'review_status':['synthetic'], 'includes_holdout':False}, {'engine':rows})
    assert report['metrics']['engine']['total']==2
    assert report['metrics']['engine']['subject_not_required_count']==1
    assert report['metrics']['engine']['subject_asserted_cases']==1
