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

    def __init__(self, executor_cls, *args, monitor_interval=2, **kwargs):
        self._executor = executor_cls(*args, **kwargs)  # type: futures.Executor
        self._monitor_interval = monitor_interval  # type: int
        self._log = logger.info if self._monitor_interval != 0 else logger.debug
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
            self._log("Starting executor monitor")
            while True:
                if not self._current_futures:
                    if self._executor._shutdown:
                        return
                    else:
                        self._log("No current futures")
                        time.sleep(0.01)
                else:
                    start = time.time()
                    # TODO: if all current futures complete under the interval
                    # we log with a lower time which sounds incorrect
                    done, pending = futures.wait(
                        list(self._current_futures), self._monitor_interval
                    )
                    self._log(
                        "%d task completed in the last %.2f second(s)",
                        len(done),
                        time.time() - start,
                    )
                    if self._executor._shutdown:
                        self._log("Shutting down monitor...")
                        return
                    with self._current_futures_lock:
                        for f in done:
                            self._current_futures.remove(f)
        except Exception:
            logger.exception("Error in monitor")


class ThreadPoolExecutor(_FutureProofExecutor):
    """Wrapper around concurrent.futures ThreadPoolExecutor.

    Arguments not specified below will be forwarded to the underlying executor.

    :param monitor_interval: Frequency in seconds for monitor logging, defaults
        to 2 seconds, set to 0 to disable.
    """

    def __init__(self, *args, monitor_interval=2, **kwargs):
        super().__init__(futures.ThreadPoolExecutor, *args, **kwargs)


class ProcessPoolExecutor(_FutureProofExecutor):
    """Wrapper around concurrent.futures ProcessPoolExecutor.

    Available only in Python 3.7 and above.

    Arguments not specified below will be forwarded to the underlying executor.

    :param monitor_interval: Frequency in seconds for monitor logging, defaults
        to 2 seconds, set to 0 to disable.
    """

    def __init__(self, *args, monitor_interval=2, **kwargs):
        if sys.version_info < (3, 7):
            raise NotImplementedError(
                "ProcessPoolExecutor are only available for Python 3.7+"
            )
        super().__init__(futures.ProcessPoolExecutor, *args, **kwargs)

    def join(self):
        logger.debug("Shutting down executor")
        # Do not shutdown the executor manually as it logs an error
        # in the concurrent.futures.process registered exit handler
