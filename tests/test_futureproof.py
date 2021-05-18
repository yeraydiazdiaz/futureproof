import os
import logging
import time
from functools import partial
from random import random

import pytest

import futureproof

import conftest


def _setup_logging():
    """Convenience function to use in combination with -s flag for debugging."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s %(thread)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    logger = logging.getLogger("futureproof")
    logger.setLevel(logging.DEBUG)


def custom_sum(a, b, delay=0):
    if delay:
        time.sleep(delay)
    else:
        time.sleep(random())
    return a + b


def flaky_sum(a, b, delay=0):
    if delay:
        time.sleep(delay)
    if a % 5 == 0:
        raise ValueError
    return a + b


def test_raise_immediate_exceptions():
    executor = conftest.get_executor_for_type()
    tm = futureproof.TaskManager(executor)

    tm.submit(custom_sum, 1)
    with pytest.raises(TypeError) as exc_info:
        tm.run()

    assert "custom_sum() missing 1 required positional argument: 'b'" == str(
        exc_info.value
    )


def test_log_immediate_exceptions(mocker):
    executor = conftest.get_executor_for_type()
    mock_logger = mocker.patch("futureproof.task_manager.logger")
    tm = futureproof.TaskManager(executor, error_policy=futureproof.ErrorPolicyEnum.LOG)

    tm.submit(custom_sum, 1)
    tm.run()

    assert mock_logger.exception.call_count == 1


def test_context_manager_raise_immediate_exceptions():
    executor = conftest.get_executor_for_type()
    with pytest.raises(TypeError) as exc_info:
        with futureproof.TaskManager(executor) as tm:
            tm.submit(custom_sum, 1)

    assert "custom_sum() missing 1 required positional argument: 'b'" == str(
        exc_info.value
    )


def test_context_manager_log_immediate_exceptions(mocker):
    executor = conftest.get_executor_for_type()
    mock_logger = mocker.patch("futureproof.task_manager.logger")

    with futureproof.TaskManager(
        executor, error_policy=futureproof.ErrorPolicyEnum.LOG
    ) as tm:
        tm.submit(custom_sum, 1)

    assert mock_logger.exception.call_count == 1


@pytest.mark.timeout(60)
@pytest.mark.slow
def test_submit_valid_functions():
    executor = conftest.get_executor_for_type()
    tm = futureproof.TaskManager(executor)

    for i in range(100):
        tm.submit(custom_sum, i, 1)
    tm.run()

    assert list(range(1, 101)) == sorted(tm.results)


def test_submit_flaky_functions():
    # Reduce the monitor interval to avoid having time outs on the test
    executor = conftest.get_executor_for_type(monitor_interval=0.1)
    tm = futureproof.TaskManager(executor)

    for i in range(1, 101):
        tm.submit(flaky_sum, i, 1, delay=0.1)

    with pytest.raises(ValueError):
        tm.run()

    assert len(tm.results) < 10
    failed_task = next(
        task for task in tm.completed_tasks if isinstance(task.result, Exception)
    )
    assert isinstance(failed_task.result, ValueError)


def test_submit_flaky_functions_context_manager():
    executor = conftest.get_executor_for_type()
    with pytest.raises(ValueError):
        with futureproof.TaskManager(executor) as tm:
            for i in range(1, 101):
                tm.submit(flaky_sum, i, 1)

    assert len(tm.results) < 10
    failed_task = next(
        task for task in tm.completed_tasks if isinstance(task.result, Exception)
    )
    assert isinstance(failed_task.result, ValueError)


@pytest.mark.timeout(60)
@pytest.mark.slow
def test_map_generator():
    executor = conftest.get_executor_for_type()
    fn = partial(custom_sum, b=1)
    with futureproof.TaskManager(executor) as tm:
        tm.map(fn, range(100))

    assert list(range(1, 101)) == sorted(tm.results)


@pytest.mark.timeout(60)
@pytest.mark.slow
def test_map_lazy_generator():
    executor = conftest.get_executor_for_type()

    def gen():
        for i in range(100):
            time.sleep(0.1)
            yield i

    fn = partial(custom_sum, b=1)
    tm = futureproof.TaskManager(executor)
    tm.map(fn, gen())
    tm.run()

    assert list(range(1, 101)) == sorted(tm.results)


@pytest.mark.timeout(10)
def test_submit_after_map():
    executor = conftest.get_executor_for_type()
    fn = partial(custom_sum, b=1)
    tm = futureproof.TaskManager(executor)
    tm.map(fn, range(9))
    tm.submit(fn, 9)
    tm.run()

    assert list(range(1, 11)) == sorted(tm.results)


@pytest.mark.timeout(10)
def test_map_after_submit():
    executor = conftest.get_executor_for_type()
    fn = partial(custom_sum, b=1)
    tm = futureproof.TaskManager(executor)
    tm.submit(fn, 0)
    tm.map(fn, range(1, 10))
    tm.run()

    assert list(range(1, 11)) == sorted(tm.results)


@pytest.mark.timeout(3)
def test_as_completed():
    executor = conftest.get_executor_for_type(monitor_interval=0.1)
    tm = futureproof.TaskManager(executor)

    for i in range(5):
        tm.submit(custom_sum, i, 1)

    gen = tm.as_completed()
    assert next(gen).complete
    assert len(tm.completed_tasks) == 1

    assert len(list(gen)) == 4
    assert list(range(1, 6)) == sorted(tm.results)


def test_task_manager_error_policy_as_string():
    executor = conftest.get_executor_for_type()
    tm = futureproof.TaskManager(executor, "log")

    assert tm._error_policy == futureproof.ErrorPolicyEnum.LOG


def test_process_pool_executor_3_7_only(mocker):
    mock_version = mocker.patch("futureproof.executors.sys")
    mock_version.version_info = (3, 6, 6)
    with pytest.raises(NotImplementedError):
        futureproof.ProcessPoolExecutor()

    mock_version.version_info = (3, 7, 0)
    assert futureproof.ProcessPoolExecutor()


def test_submit_returns_task():
    executor = conftest.get_executor_for_type()
    tm = futureproof.TaskManager(executor)

    task = tm.submit(custom_sum, 1, 1)
    assert task is not None
    tasks = {task: "foo"}
    assert tasks[task] == "foo"


@pytest.mark.skipif(
    os.getenv("EXECUTOR_TYPE") != "thread",
    reason="We cannot mock logging across processes",
)
@pytest.mark.timeout(5)
def test_monitor_logging(mocker):
    spy = mocker.spy(futureproof.executors.logger, "info")
    exception_spy = mocker.spy(futureproof.executors.logger, "exception")
    # the default monitoring interval is 2 seconds
    executor = conftest.get_executor_for_type()
    tm = futureproof.TaskManager(executor)

    tm.submit(custom_sum, 1, 1, delay=2)
    tm.run()

    assert exception_spy.call_count == 0
    assert spy.call_args_list[0][0] == ("Starting executor monitor",)
    assert (
        spy.call_args_list[1][0][0] == "%d task(s) completed in the last %.2f seconds"
    )


@pytest.mark.skipif(
    os.getenv("EXECUTOR_TYPE") != "thread",
    reason="We cannot mock logging across processes",
)
@pytest.mark.timeout(5)
def test_monitor_interval(mocker):
    spy = mocker.spy(futureproof.executors.logger, "info")
    exception_spy = mocker.spy(futureproof.executors.logger, "exception")
    executor = conftest.get_executor_for_type(monitor_interval=1)
    tm = futureproof.TaskManager(executor)

    tm.submit(custom_sum, 1, 1, delay=2)
    tm.run()

    assert exception_spy.call_count == 0
    assert spy.call_args_list[0][0] == ("Starting executor monitor",)
    assert (
        spy.call_args_list[1][0][0] == "%d task(s) completed in the last %.2f seconds"
    )
    assert (
        spy.call_args_list[2][0][0] == "%d task(s) completed in the last %.2f seconds"
    )


@pytest.mark.skipif(
    os.getenv("EXECUTOR_TYPE") != "thread",
    reason="We cannot mock logging across processes",
)
@pytest.mark.timeout(5)
def test_monitor_interval_disabled(mocker):
    spy = mocker.spy(futureproof.executors.logger, "info")
    exception_spy = mocker.spy(futureproof.executors.logger, "exception")
    executor = conftest.get_executor_for_type(monitor_interval=0)
    tm = futureproof.TaskManager(executor)

    tm.submit(custom_sum, 1, 1, delay=2)
    tm.run()

    assert exception_spy.call_count == 0
    assert spy.call_count == 0
    assert exception_spy.call_count == 0
    assert spy.call_count == 0
