import os
import sys

import pytest

import futureproof


def get_thread_executor(request=None):
    kwargs = dict(max_workers=4)
    if request and sys.version_info >= (3, 6):
        kwargs["thread_name_prefix"] = request.function.__name__
    return futureproof.ThreadPoolExecutor(**kwargs)


def get_process_executor():
    return futureproof.ProcessPoolExecutor(max_workers=2)


def get_executor_for_type():
    executor_type = os.getenv("EXECUTOR_TYPE", "thread")

    if executor_type == "thread":
        return get_thread_executor()
    else:
        return get_process_executor()


@pytest.fixture
def thread_executor(request):
    return get_thread_executor(request)


@pytest.fixture
def process_executor():
    return get_process_executor()
