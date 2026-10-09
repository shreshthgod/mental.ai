"""Actual synchronous work stays bounded after async timeout/cancellation."""
import asyncio
import threading
import pytest
from api.execution import BoundedExecutor, CapacityExceeded, WorkTimedOut


def test_timeout_does_not_release_running_work_capacity():
    async def scenario():
        executor = BoundedExecutor(workers=1, outstanding=1)
        started, release = threading.Event(), threading.Event()
        def work():
            started.set()
            release.wait(2)
            return 'done'
        try:
            with pytest.raises(WorkTimedOut):
                await executor.run(work, timeout=.02)
            assert started.is_set()
            with pytest.raises(CapacityExceeded):
                await executor.run(lambda: 'new', timeout=.02)
            release.set()
        finally:
            release.set()
            executor.close()
    asyncio.run(scenario())


def test_cancellation_does_not_admit_more_running_work():
    async def scenario():
        executor = BoundedExecutor(workers=1, outstanding=1)
        started, release = threading.Event(), threading.Event()
        def work():
            started.set()
            release.wait(2)
        try:
            task = asyncio.create_task(executor.run(work, timeout=1))
            while not started.is_set():
                await asyncio.sleep(.001)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            with pytest.raises(CapacityExceeded):
                await executor.run(lambda: None, timeout=.02)
        finally:
            release.set()
            executor.close()
    asyncio.run(scenario())


def test_serial_worker_isolates_non_thread_safe_models():
    async def scenario():
        executor = BoundedExecutor(workers=1, outstanding=2)
        active = 0
        lock = threading.Lock()
        def work(value):
            nonlocal active
            with lock:
                active += 1
                assert active == 1
                active -= 1
            return value
        try:
            assert await asyncio.gather(executor.run(work, 'a', timeout=1),
                                        executor.run(work, 'b', timeout=1)) == ['a','b']
        finally:
            executor.close()
    asyncio.run(scenario())
