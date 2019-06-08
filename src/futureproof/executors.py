import concurrent.futures as futures
import logging
import time
from threading import Lock

logger = logging.getLogger(__name__)


class FutureProofExecutor:
    """A wrapper around the base concurrent.futures Executor class."""

    _EXECUTOR_CLASS = futures.ThreadPoolExecutor
    TIMEOUT = 2

    def __init__(self, *args, **kwargs):  # TODO: use only 3.7 [kw]args?
        self._executor = self._EXECUTOR_CLASS(*args, **kwargs)
        self._current_futures: typing.Set = set()
        self._current_futures_lock: Lock = Lock()
        self._monitor_future: futures.Future = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._executor.__exit__(exc_type, exc_val, exc_tb)

    def set_queue(self, queue):
        self._executor._work_queue = queue

    @property
    def max_workers(self):
        return self._executor._max_workers

    def join(self):
        logger.debug("Shutting down executor")
        self._executor.shutdown()  # adds None to the work queue
        # not getting the above None prevents the thread from terminating
        assert self._executor._work_queue.get() is None

    def initialize_worker(self):
        """Called on a newly spawned worker to perform initialization"""
        pass

    def submit(self, fn, *args, **kwargs):
        """Create a future invoking fn with the specified args and kwargs"""
        if self._monitor_future is None:
            self._monitor_future = self._executor.submit(self.monitor)

        fut = self._executor.submit(fn, *args, **kwargs)
        with self._current_futures_lock:
            self._current_futures.add(fut)

        return fut

    def monitor(self):
        try:
            logger.info("Starting executor monitor")
            while True:
                if not self._current_futures:
                    if self._executor._shutdown:
                        return
                    else:
                        logger.debug("No current futures")
                        time.sleep(0.01)
                else:
                    start = time.time()
                    done, pending = futures.wait(
                        list(self._current_futures), self.TIMEOUT
                    )
                    logger.info(
                        "%d task completed in the last %.2f second(s)",
                        len(done),
                        time.time() - start,
                    )
                    if self._executor._shutdown:
                        logger.info("Shutting down monitor...")
                        return
                    with self._current_futures_lock:
                        for f in done:
                            self._current_futures.remove(f)
        except Exception:
            logger.exception("Error in monitor")
