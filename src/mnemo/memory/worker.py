"""Single-worker background queue for extraction pipeline jobs."""

# this file is responsible for managing a single-worker background queue
# for extraction pipeline jobs in the Mnemo memory module.

import logging
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_EXECUTOR: ThreadPoolExecutor | None = None
_PENDING_COUNT = 0


def _get_executor() -> ThreadPoolExecutor:
    global _EXECUTOR
    with _LOCK:
        if _EXECUTOR is None:
            _EXECUTOR = ThreadPoolExecutor(max_workers=1)
        return _EXECUTOR


# function to submit an extraction function to run asynchronously on the single worker thread
# it takes a callable function and its arguments, wraps it to handle exceptions
# and update the pending count, and submits it to the executor
def submit_extraction(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Future[Any]:
    """Submit an extraction function to run asynchronously on the single worker thread."""
    global _PENDING_COUNT

    with _LOCK:
        _PENDING_COUNT += 1

    def _wrapped() -> Any:
        global _PENDING_COUNT
        try:
            return fn(*args, **kwargs)
        except Exception:
            logger.exception("Background extraction job raised an exception")
            return None
        finally:
            with _LOCK:
                _PENDING_COUNT -= 1

    return _get_executor().submit(_wrapped)


def pending_count() -> int:
    """Return the number of background jobs queued or running."""
    with _LOCK:
        return _PENDING_COUNT


def wait_for_idle(timeout: float | None = None) -> bool:
    """Block until pending_count() reaches 0 or timeout is exceeded."""

    # Submit a dummy task to ensure all prior tasks finish
    def _sentinel() -> None:
        pass

    future = submit_extraction(_sentinel)
    try:
        future.result(timeout=timeout)
        return pending_count() == 0
    except Exception:  # noqa: BLE001
        return False


def shutdown(wait: bool = True) -> None:
    """Shutdown the background thread executor."""
    global _EXECUTOR
    with _LOCK:
        executor, _EXECUTOR = _EXECUTOR, None
    if executor is not None:
        executor.shutdown(wait=wait)
