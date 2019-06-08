import concurrent.futures
import sys
import logging
import threading
import time
from functools import partial
from random import random

import futureproof

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s %(thread)s] %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger("futureproof")


def flaky_sum(a, b):
    time.sleep(random() * 2)
    if a % 5 == 0:
        raise ValueError
    return a + b


def with_futureproof():
    logger.info("Starting test")
    ex = futureproof.FutureProofExecutor(max_workers=2)
    with futureproof.TaskManager(
        ex, error_policy=futureproof.ErrorPolicyEnum.RAISE
    ) as tm:
        for i in range(50):
            tm.submit(flaky_sum, i, 1)
    # an exception is raised


def with_futures():
    logger.info("Starting test")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        fs = [ex.submit(flaky_sum, i, 1) for i in range(50)]

    logger.info(
        "Got all results but no exception has been raised, "
        "we need to gather results for it to be raised, "
        "gathering now..."
    )
    results = [f.result() for f in fs]


if len(sys.argv) > 1 and sys.argv[1] == "futures":
    with_futures()
else:
    with_futureproof()
