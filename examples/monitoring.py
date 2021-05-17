"""
An example of how futureproof monitors the tasks and prints progress
versus concurrent.futures which shows no information.
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

logger = logging.getLogger(__name__)


def delayed_sum(a, b):
    time.sleep(random() + 3)
    return a + b


def with_futureproof():
    logger.info("Starting test")
    ex = futureproof.ThreadPoolExecutor(max_workers=2, monitor_interval=5)
    with futureproof.TaskManager(ex) as tm:
        for i in range(10):
            tm.submit(delayed_sum, i, 1)
        for task in tm.as_completed():
            print(task.result)


def with_futures():
    logger.info("Starting test")
    logger.info("The results come slowly without indication that things are working")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        fs = [ex.submit(delayed_sum, i, 1) for i in range(50)]
        for future in concurrent.futures.as_completed(fs):
            print(future.result(), flush=True)


if len(sys.argv) > 1 and sys.argv[1] == "futures":
    with_futures()
else:
    with_futureproof()
