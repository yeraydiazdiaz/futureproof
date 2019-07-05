import concurrent.futures as futures
import logging
import sys
import time
from threading import Lock

logger = logging.getLogger(__name__)


class _FutureProofExecutor:
    """A wrapper around a subclass of concurrent.futures.Executor.

    Requires the subclass to be passed as the first parameter to the constructor.
    Do not use this class directly, use either ThreadPoolExecutor or ProcessPoolExecutor.
    """

    TIMEOUT = 2  # TODO: allow parametrizing and disabling the monitor

    def __init__(self, executor_cls, *args, **kwargs):  # TODO: use only 3.7 [kw]args?
        self._executor = executor_cls(*args, **kwargs)  # type: futures.Executor
        self._current_futures = set()  # type: set
        self._current_futures_lock = Lock()  # type: Lock
        self._monitor_future = None  # type: futures.Future

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._executor.__exit__(exc_type, exc_val, exc_tb)

    @property
    def max_workers(self):
        return self._executor._max_workers

    def join(self):
        logger.debug("Shutting down executor")
        self._executor.shutdown()

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


class ThreadPoolExecutor(_FutureProofExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(futures.ThreadPoolExecutor, *args, **kwargs)


class ProcessPoolExecutor(_FutureProofExecutor):
    def __init__(self, *args, **kwargs):
        if sys.version_info < (3, 7):
            raise NotImplementedError(
                "ProcessPoolExecutor are only available for Python 3.7+"
            )
        super().__init__(futures.ProcessPoolExecutor, *args, **kwargs)
