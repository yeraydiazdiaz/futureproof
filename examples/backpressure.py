"""
An example of how futureproof handles backpressure of tasks
versus concurrent.futures which can hog resources and even cause the
system to be unresponsive in extreme cases.
"""

import concurrent.futures
import sys
import logging
import time
from functools import partial

import futureproof

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s %(thread)s] %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


def custom_sum(a, b):
    time.sleep(0.1)
    return a + b


def with_futureproof():
    logger.info("Starting backpressure test with 1,000,000 tasks")
    logger.info(
        "You may KeyboardInterrupt at any point "
        "and the executor will stop almost immediately"
    )
    ex = futureproof.ThreadPoolExecutor(max_workers=2)
    with futureproof.TaskManager(
        ex, error_policy=futureproof.ErrorPolicyEnum.RAISE
    ) as tm:
        fn = partial(custom_sum, b=1)
        tm.map(fn, range(1_000_000_000))

    logging.info("Done: %s", len(tm.results))


def with_futures():
    response = input(
        "Leaving this example running too will take a fair bit of memory and "
        "might block and not respond to KeyboardInterrupts, a SIGINT will "
        "be required to stop it, are you sure you want to continue? [Y/n] "
    )
    if response == "n":
        print("Aborting as requested")
        return

    logger.info("Starting backpressure test with 1,000,000 tasks")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        fn = partial(custom_sum, b=1)
        ex.map(fn, range(1_000_000_000))


if len(sys.argv) > 1 and sys.argv[1] == "futures":
    with_futures()
else:
    with_futureproof()
