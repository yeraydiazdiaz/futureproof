"""
An example of using error policies in futureproof, the user can define
a policy when creating the TaskManager configuring it to simply return them
as the result of the task.

In contrast concurrent.futures will not raise the exception until we call
`result` on the future.
"""

import concurrent.futures
import sys
import logging
import time
from random import random

import futureproof

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s %(thread)s] %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


def flaky_sum(a, b):
    time.sleep(random() * 2)
    if a % 5 == 0:
        raise ValueError
    return a + b


def with_futureproof():
    logger.info("Starting as_completed test")
    ex = futureproof.ThreadPoolExecutor(max_workers=2)
    results = []
    # the user must explictly state she wants to catch the exceptions manually
    with futureproof.TaskManager(
        ex, error_policy=futureproof.ErrorPolicyEnum.IGNORE
    ) as tm:
        for i in range(10):
            tm.submit(flaky_sum, i, 1)

        for task in tm.as_completed():
            if isinstance(task.result, Exception):
                logger.exception("Exception raised in result", exc_info=task.result)
            else:
                results.append(task.result)

    print(results)


def with_futures():
    logger.info("Starting as_completed test")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        fs = [ex.submit(flaky_sum, i, 1) for i in range(10)]
        results = []
        for f in concurrent.futures.as_completed(fs):
            logger.info("Checking result...")
            try:
                results.append(f.result())
            except Exception:
                logger.exception("Exception raised in result")

    print(results)


if len(sys.argv) > 1 and sys.argv[1] == "futures":
    with_futures()
else:
    with_futureproof()
