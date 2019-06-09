import sys

import pytest

import futureproof

MAX_WORKERS = 4  # override for debugging


@pytest.fixture
def executor(request):
    kwargs = dict(max_workers=MAX_WORKERS)
    if sys.version_info >= (3, 6):
        kwargs["thread_name_prefix"] = request.function.__name__
    ex = futureproof.FutureProofExecutor(**kwargs)
    yield ex
