"""
An example of using as_completed in futureproof and concurrent.futures

concurrent.futures will return the exception raised but the exit handler will
then block until all submitted tasks which delays the exit.

futureproof requires the user to define that she will handle the exceptions
and since it has only queued the minimum amount of tasks will exit much quicker.

"""

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
    logger.info("Starting as_completed test")
    ex = futureproof.FutureProofExecutor(max_workers=2)
    # the user must explictly state she wants to catch the exceptions manually
    with futureproof.TaskManager(
        ex, error_policy=futureproof.ErrorPolicyEnum.IGNORE
    ) as tm:
        for i in range(10):
            tm.submit(flaky_sum, i, 1)

        for task in tm.as_completed():
            logger.info("Got result from %s", task)
            if isinstance(task.result, Exception):
                # raising the exception will signal futureproof to cleanup
                # and not wait for any pending tasks exiting much quicker
                raise task.result


def with_futures():
    logger.info("Starting as_completed test")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        fs = [ex.submit(flaky_sum, i, 1) for i in range(50)]
        results = []
        try:
            for f in concurrent.futures.as_completed(fs):
                logger.info("Checking result...")
                results.append(f.result())
        except Exception as exc:
            logger.info("Exception raised in result")
            # even though we're re-raising the exception
            # concurrent.futures registers and exit handler which will block
            # until all the scheduled futures are resolved delaying the exit
            raise


if len(sys.argv) > 1 and sys.argv[1] == "futures":
    with_futures()
else:
    with_futureproof()
