"""Unit tests for single-worker background queue."""

# this file contains unit tests for the single-worker background queue in the Mnemo memory module.

import time

from mnemo.memory import worker


def test_worker_fifo_and_pending_count() -> None:
    order: list[int] = []

    def task(val: int) -> int:
        time.sleep(0.02)
        order.append(val)
        return val

    fut1 = worker.submit_extraction(task, 1)
    fut2 = worker.submit_extraction(task, 2)
    fut3 = worker.submit_extraction(task, 3)

    assert worker.pending_count() > 0

    assert worker.wait_for_idle(timeout=2.0) is True
    assert worker.pending_count() == 0
    assert order == [1, 2, 3]
    assert fut1.result() == 1
    assert fut2.result() == 2
    assert fut3.result() == 3


def test_worker_handles_job_exceptions_without_failing() -> None:
    def failing_task() -> None:
        raise ValueError("Job boom")

    def ok_task() -> str:
        return "ok"

    fut_fail = worker.submit_extraction(failing_task)
    fut_ok = worker.submit_extraction(ok_task)

    assert worker.wait_for_idle(timeout=2.0) is True
    assert fut_fail.result() is None
    assert fut_ok.result() == "ok"
