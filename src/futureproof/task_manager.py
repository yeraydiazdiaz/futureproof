import logging
import queue
from typing import Any, Callable, List, Union, Iterable, Iterator
from enum import Enum
from functools import partial
from threading import Lock
from itertools import chain

import attr

from futureproof import executors

logger = logging.getLogger(__name__)


class ErrorPolicyEnum(Enum):
    IGNORE = "ignore"
    LOG = "log"
    RAISE = "raise"


@attr.s
class Task:
    """Tasks describe an execution with parameters.

    Upon submitted a future is added to it encapsulating the result.
    """

    fn = attr.ib()  # type: Callable
    args = attr.ib(default=())  # type: tuple
    kwargs = attr.ib(default={})  # type: dict
    result = attr.ib(default=None)  # type: Any
    complete = attr.ib(default=False)  # type: bool


class TaskManager:
    """Manages how tasks are created and placed in the queue.

    Executors get Tasks from this manager.
    """

    def __init__(
        self,
        executor: executors._FutureProofExecutor,
        error_policy: Union[ErrorPolicyEnum, str] = ErrorPolicyEnum.RAISE,
    ):
        self._tasks_in_queue = 0
        self._error_policy = (
            error_policy
            if isinstance(error_policy, ErrorPolicyEnum)
            else ErrorPolicyEnum(error_policy.lower())
        )
        self._executor = executor
        self._shutdown = False
        self._tasks = []  # type: Iterable
        self._submitted_task_count = 0  # type: int
        self.completed_tasks = []  # type: List
        self._completed_tasks_lock = Lock()  # type: Lock
        self._results_queue = queue.Queue()  # type: queue.Queue

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.run()
        self.join()

    @property
    def results(self) -> List:
        with self._completed_tasks_lock:
            return [task.result for task in self.completed_tasks if task.complete]

    def submit(self, fn: Callable, *args: Any, **kwargs: Any) -> None:
        """Submit a task for execution."""
        task = Task(fn, args, kwargs)
        self._tasks = chain(self._tasks, [task])

    def map(self, fn: Callable, iterable: Iterable) -> None:
        """Submit a set of tasks from a callable and a iterable of arguments

        The iterable may be a iterable of primitives or an iterable of tuples.
        """

        def gen():
            for i in iterable:
                args = i if isinstance(i, tuple) else (i,)
                yield Task(fn, args)

        self._tasks = chain(self._tasks, gen())

    def run(self) -> None:
        """Start the manager and wait until all tasks are completed before shutting down."""
        for _ in self.as_completed():
            pass

    def as_completed(self) -> Iterator[Task]:
        """Start the manager and return an interator of completed tasks."""
        for task in self._tasks:
            if self._shutdown:
                break

            if self._tasks_in_queue == self._executor.max_workers:
                logger.debug("Queue full, waiting for result")
                yield self.wait_for_result()

            self._submit_task(task)

        while len(self.completed_tasks) < self._submitted_task_count:
            yield self.wait_for_result()

        self._executor.join()

    def _submit_task(self, task: Task) -> None:
        """Submits a task to the executor, note this will block if the queue is full."""
        logger.debug(
            "Tasks in queue: %d, submitting task %r", self._tasks_in_queue, task
        )
        self._tasks_in_queue += 1
        fut = self._executor.submit(task.fn, *task.args, **task.kwargs)
        cb = partial(self._on_complete, task=task)
        fut.add_done_callback(cb)
        self._submitted_task_count += 1

    def _on_complete(self, future, task):
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
            logger.debug("Completed task %r", complete_task)
            self._results_queue.put(complete_task)

    def join(self) -> None:
        while len(self.completed_tasks) < self._submitted_task_count:
            self.wait_for_result()
        self._executor.join()

    def wait_for_result(self) -> Task:
        """Gather result from a submitted tasks."""
        completed_task = self._results_queue.get(block=True)
        logger.debug("Gathering result for completed task %r", completed_task)
        self._tasks_in_queue -= 1
        self.completed_tasks.append(completed_task)
        if isinstance(completed_task.result, Exception):
            if self._error_policy == ErrorPolicyEnum.RAISE:
                self._raise(completed_task.result)
            elif self._error_policy == ErrorPolicyEnum.LOG:
                logger.exception(
                    "Task %s raised an exception",
                    completed_task,
                    exc_info=completed_task.result,
                )

        return completed_task

    def _raise(self, exception) -> None:
        """Performs cleanup before raising an exception."""
        logger.info("Raising exception and shutting down")
        self._shutdown = True
        self._executor.join()
        raise exception
