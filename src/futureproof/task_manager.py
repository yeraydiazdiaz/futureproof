import concurrent.futures as futures
import logging
import queue
import time
import typing
from enum import IntEnum
from functools import partial
from threading import Lock

import attr

from futureproof import executors

logger = logging.getLogger(__name__)


class ErrorPolicyEnum(IntEnum):
    IGNORE = 1
    LOG = 2
    RAISE = 3


@attr.s(auto_attribs=True)
class Task:
    """Tasks describe an execution with parameters.

    Upon submitted a future is added to it encapsulating the result.
    """

    fn: typing.Callable
    args: typing.Tuple = attr.ib(default=())
    kwargs: typing.Dict = attr.ib(default={})
    result: typing.Any = attr.ib(default=None)
    complete: bool = attr.ib(default=False)


class TaskManager:
    """Manages how tasks are created and placed in the queue.

    Executors get Tasks from this manager.
    """

    def __init__(
        self,
        executor: executors.FutureProofExecutor,
        error_policy: ErrorPolicyEnum = ErrorPolicyEnum.RAISE,
    ):
        self._queue: queue.Queue = queue.Queue(executor.max_workers)
        self._error_policy = error_policy
        self._executor = executor
        self._executor.set_queue(self._queue)
        self._shutdown = False
        self._tasks: typing.Union[typing.List, typing.Generator] = []
        self._submitted_task_count: int = 0
        self.completed_tasks: typing.List = []
        self._completed_tasks_lock: Lock = Lock()
        self._results_queue: queue.Queue = queue.Queue()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.run()
        self.join()

    @property
    def results(self):
        with self._completed_tasks_lock:
            return [task.result for task in self.completed_tasks if task.complete]

    def submit(
        self, fn: typing.Callable, *args: typing.Any, **kwargs: typing.Any
    ) -> None:
        """Submit a task for execution."""
        task = Task(fn, args, kwargs)
        self._tasks.append(task)

    def map(self, fn: typing.Callable, iterable: typing.Iterable) -> None:
        """Submit a set of tasks from a callable and a iterable of arguments

        The iterable may be a iterable of primitives or an iterable of tuples.
        """
        self._tasks = (Task(fn, i if isinstance(i, tuple) else (i,)) for i in iterable)

    def run(self):
        for task in self._tasks:
            if self._shutdown:
                break

            if self._queue.full():
                self.wait_for_result()

            fut = self._executor.submit(task.fn, *task.args, **task.kwargs)
            cb = partial(self.on_complete, task=task)
            fut.add_done_callback(cb)
            self._submitted_task_count += 1

        self.join()

    def on_complete(self, future, task):
        """Called once per future to perform an operation over the result.

        Note this function is called by the executing threads.
        """
        complete_task = Task(task.fn, task.args, task.kwargs)
        complete_task.complete = True
        try:
            complete_task.result = future.result()
        except Exception as exc:
            complete_task.result = exc
        finally:
            self._results_queue.put(complete_task)

    def join(self):
        while len(self.completed_tasks) < self._submitted_task_count:
            self.wait_for_result()
        self._executor.join()

    def wait_for_result(self):
        """Gather result from a submitted tasks."""
        try:
            completed_task = self._results_queue.get(block=True)
            logger.debug("Completed task received: %s", completed_task)
            self.completed_tasks.append(completed_task)
        except queue.Empty:
            # This condition should not happen
            logger.debug("Queue empty")
        else:
            if isinstance(completed_task.result, Exception):
                if self._error_policy == ErrorPolicyEnum.RAISE:
                    self._raise(completed_task.result)
                elif self._error_policy == ErrorPolicyEnum.LOG:
                    logger.exception(
                        "Task %s raised an exception",
                        completed_task,
                        exc_info=completed_task.result,
                    )

    def _raise(self, exception):
        """Performs cleanup before raising an exception."""
        logger.info("Raising exception and shutting down")
        self._shutdown = True
        self._executor.join()
        raise exception
