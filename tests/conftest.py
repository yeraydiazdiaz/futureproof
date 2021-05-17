import os
import sys

import pytest

import futureproof


def get_executor_for_type(*args, **kwargs):
    executor_type = os.getenv("EXECUTOR_TYPE", "thread")

    if executor_type == "thread":
        return get_thread_executor(*args, **kwargs)
    else:
        return get_process_executor(*args, **kwargs)


def get_thread_executor(*args, request=None, **kwargs):
    kwargs.setdefault("max_workers", 3)
    if request and sys.version_info >= (3, 6):
        kwargs["thread_name_prefix"] = request.function.__name__
    return futureproof.ThreadPoolExecutor(*args, **kwargs)


def get_process_executor(*args, **kwargs):
    kwargs.setdefault("max_workers", 3)
    return futureproof.ProcessPoolExecutor(*args, **kwargs)


@pytest.fixture
def thread_executor(request):
    return get_thread_executor(request)


@pytest.fixture
def process_executor():
    return get_process_executor()
