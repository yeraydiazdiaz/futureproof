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


def custom_sum(a, b):
    time.sleep(0.1)
    return a + b


def with_futureproof():
    logger.info("Starting backpressure test")
    ex = futureproof.FutureProofExecutor(max_workers=2)
    with futureproof.TaskManager(
        ex, error_policy=futureproof.ErrorPolicyEnum.RAISE
    ) as tm:
        fn = partial(custom_sum, b=1)
        tm.map(fn, range(1_000_000_000))

    logging.info("Done: %s", len(tm.results))


def with_futures():
    logger.info("Starting backpressure test")
    response = input(
        "This example will take a fair bit of memory and might "
        "block and not respond to KeyboardInterrupts, a SIGINT will "
        "be required to stop it, are you sure you want to continue? [Y/n] "
    )
    if response == "n":
        print("Aborting as requested")
        return

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        fn = partial(custom_sum, b=1)
        ex.map(fn, range(1_000_000_000))


if len(sys.argv) > 1 and sys.argv[1] == "futures":
    with_futures()
else:
    with_futureproof()
