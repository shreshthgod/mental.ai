"""Shared local-worker admission counters; no real provider calls."""
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
import pytest
from api.limits import PredictLimiter, Limited


def attempt(path):
    try:
        PredictLimiter(path, maximum=3, window=60).check('synthetic-user-a', now=100)
        return True
    except Limited:
        return False


def test_processes_share_atomic_limit(tmp_path):
    path = str(tmp_path/'limits.sqlite3')
    with ProcessPoolExecutor(max_workers=4, mp_context=get_context('spawn')) as pool:
        results = list(pool.map(attempt, [path]*8))
    assert sum(results) == 3


def test_owner_key_isolation_and_retry_window(tmp_path):
    limiter = PredictLimiter(str(tmp_path/'limits.sqlite3'), maximum=1, window=60)
    limiter.check('a', now=100)
    with pytest.raises(Limited) as failure:
        limiter.check('a', now=110)
    assert failure.value.retry_after == 50
    limiter.check('b', now=110)
    limiter.check('a', now=160)
