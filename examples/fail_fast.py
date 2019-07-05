"""
An example of how futureproof fails quickly on exceptions versus
concurrent.futures which blocks the interpreter with no traceback
until all tasks are completed.
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
    logger.info("Starting test")
    ex = futureproof.ThreadPoolExecutor(max_workers=2)
    with futureproof.TaskManager(
        ex, error_policy=futureproof.ErrorPolicyEnum.RAISE  # RAISE is the default
    ) as tm:
        for i in range(50):
            tm.submit(flaky_sum, i, 1)
    # an exception is raised as expected


def with_futures():
    logger.info("Starting test")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        fs = [ex.submit(flaky_sum, i, 1) for i in range(50)]
        for future in concurrent.futures.as_completed(fs):
            try:
                print(future.result())
            except ValueError:
                logger.info(
                    "Raised and exception which will stop the main thread, "
                    "however, since all 50 tasks were placed in the queue "
                    "the interpreter will now stop until all remaining tasks are "
                    "completed before exiting completly due to the exception."
                )
                logger.info(
                    "You can force quit with Ctrl+C but depending on the tasks "
                    "the interpreter might be blocked forcing you to sigkill "
                    "the process."
                )
                raise


if len(sys.argv) > 1 and sys.argv[1] == "futures":
    with_futures()
else:
    with_futureproof()
