# API reference

`futureproof` consists in two main objects: executors and task managers.

If you're used to `concurrent.futures` you'll note this is a departure
from the single `Executor` entrypoint. This is intentional as we separate
the *scheduling* of the tasks from the *execution* of the tasks.

## Executors

`futureproof`'s executors are a thin wrapper around the ones exposed by
`concurrent.futures`.

```{eval-rst}
.. autoclass:: futureproof.executors.ThreadPoolExecutor
    :members:
    :noindex:
```

```{eval-rst}
.. autoclass:: futureproof.executors.ProcessPoolExecutor
    :members:
    :noindex:
```

In the executors is where `futureproof` adds the monitoring functionality by
regularly checking for completed tasks and logging as required.

An important difference with `concurrent.futures` is that you don't call them
directly, they need to be passed as parameters to task managers.

## Task managers

Task managers are the main point of interaction with `futureproof`. They
encapsulate a queue of jobs to be executed by an executor, exposing methods
to add jobs and retrieve results easily.

```{eval-rst}
.. autoclass:: futureproof.task_manager.TaskManager
    :members:
    :noindex:
```

```{eval-rst}
.. autoclass:: futureproof.task_manager.Task
    :members:
    :noindex:
```

```{eval-rst}
.. autoclass:: futureproof.task_manager.ErrorPolicyEnum
    :members:
    :noindex:
```
