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
        self._monitor_count = 0  # type: int
        self._monitor_future = None  # type: futures.Future
        self._monitor_lock = Lock()  # type: Lock

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
            # TODO: we're taking up a worker for monitoring without alerting the user
            # This is especially bad in the case of a ProcessExecutor
            self._monitor_future = self._executor.submit(self.monitor)

        fut = self._executor.submit(fn, *args, **kwargs)
        with self._current_futures_lock:
            self._current_futures.add(fut)
        # NOTE: done callbacks will be executed immediately if the future is complete
        fut.add_done_callback(self._cb)
        return fut

    def _cb(self, future):
        with self._current_futures_lock:
            self._current_futures.remove(future)
        with self._monitor_lock:
            self._monitor_count += 1

    def monitor(self):
        """Monitor task checking on the status of the futures and logging the progress."""
        try:
            self._log("Starting executor monitor")
            while True:
                # If there are no futures being processed we check if we're
                # shutting down or eagerly wait for more futures
                if not self._current_futures:
                    if self._executor._shutdown:
                        return
                    else:
                        logger.debug("No current futures")
                        time.sleep(0.01)
                else:
                    start = time.time()
                    previous_count = self._monitor_count

                    time.sleep(self._monitor_interval)

                    with self._monitor_lock:
                        self._log(
                            "%d task(s) completed in the last %.2f seconds",
                            self._monitor_count - previous_count,
                            time.time() - start,
                        )

                    if self._executor._shutdown:
                        self._log("Shutting down monitor...")
                        return
        except Exception:
            logger.exception("Error in monitor")


class ThreadPoolExecutor(_FutureProofExecutor):
    """Wrapper around concurrent.futures ThreadPoolExecutor.

    Arguments not specified below will be forwarded to the underlying executor.

    :param monitor_interval: Frequency in seconds for monitor logging, defaults
        to 2 seconds, set to 0 to disable.
    """

    def __init__(self, *args, monitor_interval=2, **kwargs):
        super().__init__(
            futures.ThreadPoolExecutor,
            *args,
            monitor_interval=monitor_interval,
            **kwargs
        )


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
        super().__init__(
            futures.ProcessPoolExecutor,
            *args,
            monitor_interval=monitor_interval,
            **kwargs
        )

    def join(self):
        logger.debug("Shutting down executor")
        # Do not shutdown the executor manually as it logs an error
        # in the concurrent.futures.process registered exit handler
