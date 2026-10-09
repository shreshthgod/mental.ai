"""Each test uses isolated rate-limit storage, never operator state.

The production limiter implementation is retained. Provider stubs are supplied
explicitly by the individual API fixtures; this fixture does not supply auth.
"""
import pytest
import sys


@pytest.fixture(autouse=True)
def isolated_predict_limit_store(monkeypatch, tmp_path):
    if 'api.api' not in sys.modules:
        # Standalone engine tests do not import the service/models merely to
        # isolate a rate store they never use.
        return
    from api import api as service
    from api.limits import PredictLimiter
    monkeypatch.setattr(service, 'predict_limiter', PredictLimiter(str(tmp_path/'limits.sqlite3')))
