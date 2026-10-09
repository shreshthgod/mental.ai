# Preserved unit expectation and policy correction

Original `tests/test_safety.py::test_safety_never_returns_none_when_the_model_is_silent`:

```python
"""Silent model + no textual evidence is an honest UNKNOWN-free low route, not a crash."""
result = screener.screen("The weather is nice today")
assert result["safety"]["level"] in ("NONE_DETECTED", "NEEDS_CLARIFICATION")
assert result["safety"]["analysis_status"] in ("complete", "degraded", "insufficient_evidence")
```

Review: developer policy review, not clinical review. The real legacy model is present, not silent. Its negative result cannot establish sufficient safety assessment when semantic assessment is disabled and independent rules recognize no context. The user's required policy explicitly forbids this confident no-match negative. D-061 specifies UNKNOWN in that condition. Corrected test checks UNKNOWN, degraded, disabled semantic and clarification; raw classifier output is retained. Historical corpus labels are unchanged and continue to fail where their oracle requires unavailable certainty. This correction is to an obsolete expectation, not a claim that the corpus passes.

## D081 capability assertion correction

Original `tests/test_safety_contract.py::test_d01_model_flag_does_not_replace_a_text_derived_escalation` ended with `assert result.level == "NONE_DETECTED"` and `assert result.analysis_status == "complete"` for `I used to self-harm. I have no current urge and I have support.` with urgency_flagged=True and probability0.5057. The no-concern expectation is preserved; only completeness changes to degraded. A function-word heuristic, known recovery context and healthy raw signal do not establish validated full-language assessment. Nine new language examples reproduce the underlying capability/mixed-script behavior. Review status: developer engineering policy alignment, not clinical review. No corpus label changed.
