import logging
import time
from functools import partial
from random import random

import pytest

import futureproof

MAX_WORKERS = 4  # override for debugging


def _setup_logging():
    """Convenience function to use in combination with -s flag for debugging."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s %(thread)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    logger = logging.getLogger("futureproof")
    logger.setLevel(logging.DEBUG)


_setup_logging()


def custom_sum(a, b):
    time.sleep(random())
    return a + b


def flaky_sum(a, b):
    if a % 5 == 0:
        raise ValueError
    return a + b


def test_raise_immediate_exceptions():
    ex = futureproof.FutureProofExecutor(
        max_workers=MAX_WORKERS, thread_name_prefix="test_raise_immediate_exceptions"
    )
    tm = futureproof.TaskManager(ex)

    tm.submit(custom_sum, 1)
    with pytest.raises(TypeError) as exc_info:
        tm.run()

    assert "custom_sum() missing 1 required positional argument: 'b'" == str(
        exc_info.value
    )


def test_log_immediate_exceptions(mocker):
    mock_logger = mocker.patch("futureproof.task_manager.logger")
    ex = futureproof.FutureProofExecutor(
        max_workers=MAX_WORKERS, thread_name_prefix="test_log_immediate_exceptions"
    )
    tm = futureproof.TaskManager(ex, error_policy=futureproof.ErrorPolicyEnum.LOG)

    tm.submit(custom_sum, 1)
    tm.run()

    assert mock_logger.exception.call_count == 1


def test_context_manager_raise_immediate_exceptions():
    ex = futureproof.FutureProofExecutor(
        max_workers=MAX_WORKERS,
        thread_name_prefix="test_context_manager_raise_immediate_exceptions",
    )

    with pytest.raises(TypeError) as exc_info:
        with futureproof.TaskManager(ex) as tm:
            tm.submit(custom_sum, 1)

    assert "custom_sum() missing 1 required positional argument: 'b'" == str(
        exc_info.value
    )


def test_context_manager_log_immediate_exceptions(mocker):
    mock_logger = mocker.patch("futureproof.task_manager.logger")
    ex = futureproof.FutureProofExecutor(
        max_workers=MAX_WORKERS,
        thread_name_prefix="test_context_manager_log_immediate_exceptions",
    )

    with futureproof.TaskManager(
        ex, error_policy=futureproof.ErrorPolicyEnum.LOG
    ) as tm:
        tm.submit(custom_sum, 1)

    assert mock_logger.exception.call_count == 1


@pytest.mark.timeout(60)
@pytest.mark.slow
def test_submit_valid_functions():
    ex = futureproof.FutureProofExecutor(
        max_workers=MAX_WORKERS, thread_name_prefix="test_submit_valid_functions"
    )
    tm = futureproof.TaskManager(ex)

    for i in range(100):
        tm.submit(custom_sum, i, 1)
    tm.run()

    assert list(range(1, 101)) == sorted(tm.results)


def test_submit_flaky_functions():
    ex = futureproof.FutureProofExecutor(
        max_workers=MAX_WORKERS, thread_name_prefix="test_submit_flaky_functions"
    )
    tm = futureproof.TaskManager(ex)

    for i in range(1, 101):
        tm.submit(flaky_sum, i, 1)

    with pytest.raises(ValueError):
        tm.run()

    assert len(tm.results) == 5
    failed_task = next(
        task for task in tm.completed_tasks if isinstance(task.result, Exception)
    )
    assert isinstance(failed_task.result, ValueError)


def test_submit_flaky_functions_context_manager():
    ex = futureproof.FutureProofExecutor(
        max_workers=MAX_WORKERS,
        thread_name_prefix="test_submit_flaky_functions_context_manager",
    )
    with pytest.raises(ValueError):
        with futureproof.TaskManager(ex) as tm:
            for i in range(1, 101):
                tm.submit(flaky_sum, i, 1)

    assert len(tm.results) == 5
    failed_task = next(
        task for task in tm.completed_tasks if isinstance(task.result, Exception)
    )
    assert isinstance(failed_task.result, ValueError)


@pytest.mark.timeout(60)
@pytest.mark.slow
def test_map_generator():
    ex = futureproof.FutureProofExecutor(
        max_workers=MAX_WORKERS, thread_name_prefix="test_map_generator"
    )

    fn = partial(custom_sum, b=1)
    with futureproof.TaskManager(ex) as tm:
        tm.map(fn, range(100))

    assert list(range(1, 101)) == sorted(tm.results)


@pytest.mark.timeout(60)
@pytest.mark.slow
def test_map_lazy_generator():
    ex = futureproof.FutureProofExecutor(
        max_workers=MAX_WORKERS, thread_name_prefix="test_map_lazy_generator"
    )

    def gen():
        for i in range(100):
            time.sleep(0.1)
            yield i

    fn = partial(custom_sum, b=1)
    tm = futureproof.TaskManager(ex)
    tm.map(fn, gen())
    tm.run()

    assert list(range(1, 101)) == sorted(tm.results)
