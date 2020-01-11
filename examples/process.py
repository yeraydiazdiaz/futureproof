import concurrent.futures
import logging
import sys
import time

import futureproof

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s %(process)d %(processName)s %(thread)s] %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


def flaky_sum(a, b, delay=0):
    if delay:
        time.sleep(delay)
    if a % 5 == 0:
        raise ValueError
    return a + b


def with_futureproof():
    process_executor = futureproof.ProcessPoolExecutor(max_workers=2)
    tm = futureproof.TaskManager(process_executor, error_policy="log")
    for i in range(10):
        tm.submit(flaky_sum, i, 1, delay=1)
    tm.run()


def with_futures():
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as ex:
        futs = [ex.submit(flaky_sum, i, 1, delay=1) for i in range(10)]
        for fut in concurrent.futures.as_completed(futs):
            try:
                result = fut.result()
            except Exception as exc:
                print("An exception was raised:", exc)
            else:
                print(result)


if len(sys.argv) > 1 and sys.argv[1] == "futures":
    with_futures()
else:
    with_futureproof()
