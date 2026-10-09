"""Bound admitted synchronous jobs, including work surviving caller timeout."""
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor


class CapacityExceeded(RuntimeError):
    pass


class WorkTimedOut(RuntimeError):
    pass


class BoundedExecutor:
    def __init__(self, *, workers=1, outstanding=2):
        self._slots = threading.BoundedSemaphore(outstanding)
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix='screening-work')

    async def run(self, function, *args, timeout):
        if not self._slots.acquire(blocking=False):
            raise CapacityExceeded()

        def work():
            try:
                return function(*args)
            finally:
                self._slots.release()
        try:
            future = self._pool.submit(work)
        except BaseException:
            self._slots.release()
            raise
        try:
            # A deadline/cancelled caller cannot release a still-running job's
            # admission slot. Synchronous work finishes under its own bound.
            wrapped = asyncio.wrap_future(future)
            # Observe late exceptions even if the caller stopped waiting;
            # otherwise asyncio may log their raw message as unhandled.
            wrapped.add_done_callback(lambda result: result.exception() if not result.cancelled() else None)
            return await asyncio.wait_for(asyncio.shield(wrapped), timeout)
        except asyncio.TimeoutError as exc:
            raise WorkTimedOut() from exc

    def close(self):
        self._pool.shutdown(wait=True)
