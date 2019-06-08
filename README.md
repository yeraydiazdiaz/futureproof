# Futureproof

> Bulletproof concurrent.futures

[`concurrent.futures`](https://docs.python.org/3/library/concurrent.futures.html) is amazing, but it's got some sharp edges that have bit me many times in the past.

Futureproof is a thin wrapper around it addressing some of these problems and adding some usability features.

## Features:

- **Monitoring**: a summary of completed tasks is logged by default.
- **Fail fast**: errors cause the main thread to raise an exception and stop by default.
- **Error policy**: the user can decide whether to raise, log or completely ignore errors on tasks.
- **Backpressure control**: large collections of tasks are consumed lazily as the executor completes tasks, drastically reducing memory consumption and improving responsiveness in these situations.

Check out the [examples directory](https://github.com/yeraydiazdiaz/futureproof/tree/master/examples/) for a hands-on comparison between `futureproof` and `concurrent.futures`.

## Current status: Alpha

The API is subject to change.

Currently only tested as a wrapper for ThreadPoolExecutor and Python 3.7.
