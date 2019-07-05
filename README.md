# Futureproof - Bulletproof concurrent.futures

[![Build Status](https://dev.azure.com/yeraydiazdiaz/futureproof/_apis/build/status/yeraydiazdiaz.futureproof?branchName=master)](https://dev.azure.com/yeraydiazdiaz/futureproof/_build/latest?definitionId=1&branchName=master)
[![Supported Python Versions](https://img.shields.io/pypi/pyversions/futureproof.svg)](https://pypi.org/project/futureproof/)
[![PyPI](https://img.shields.io/pypi/v/futureproof.svg)](https://pypi.org/project/futureproof/)

[`concurrent.futures`](https://docs.python.org/3/library/concurrent.futures.html) is amazing, but it's got some sharp edges that have bit me many times in the past.

Futureproof is a thin wrapper around it addressing some of these problems and adding some usability features.

## Features:

- **Monitoring**: a summary of completed tasks is logged by default.
- **Fail fast**: errors cause the main thread to raise an exception and stop by default.
- **Error policy**: the user can decide whether to raise, log or completely ignore errors on tasks.
- **Backpressure control**: large collections of tasks are consumed lazily as the executor completes tasks, drastically reducing memory consumption and improving responsiveness in these situations.

## Current status: Alpha

The API is subject to change, any changes will be documented in the changelog.

Futureproof was designed to wrap ThreadPoolExecutor, however version 0.2+ includes limited support ProcessPoolExecutor but only for Python3.7+.

When using ProcessPoolExecutor a "OSError: handle is closed" error is known to be printed from the interpreter exit handler, seemingly caused by worker processed being shut down prematurely. This is not affect the execution of the tasks.

## concurrent.futures has problems? What problems?

Let's have a look at the canonical example for ThreadPoolExecutor:

```python
import concurrent.futures
import urllib.request

URLS = ['http://www.foxnews.com/',
        'http://www.cnn.com/',
        'http://europe.wsj.com/',
        'http://www.bbc.co.uk/',
        'http://some-made-up-domain-that-definitely-does-not-exist.com/']

# Retrieve a single page and report the URL and contents
def load_url(url, timeout):
    with urllib.request.urlopen(url, timeout=timeout) as conn:
        return conn.read()

# We can use a with statement to ensure threads are cleaned up promptly
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    # Start the load operations and mark each future with its URL
    future_to_url = {executor.submit(load_url, url, 60): url for url in URLS}
    for future in concurrent.futures.as_completed(future_to_url):
        url = future_to_url[future]
        try:
            data = future.result()
        except Exception as exc:
            print('%r generated an exception: %s' % (url, exc))
        else:
            print('%r page is %d bytes' % (url, len(data)))
```

Just to reiterate, this is amazing, the fact that the barrier of entry for multithreading is this small is really a testament to the great work done by Brian Quinlan and the core Python developers.

However, I see two problems with this:

1. The boilerplate. We need to enter a context manager, call `submit` manually keeping track of the futures and its arguments, call `as_completed` which actually returns an iterator, call `result` on the future remembering to handle the exception.
2. It's surprising. Why do we need to get the result in order to raise? What if we don't expect it to raise? We probably want to know as soon as possible.

If you run this code you get the following output (at the time of this writing):

```
'http://some-made-up-domain-that-definitely-does-not-exist.com/' generated an exception: <urlopen error [Errno 8] nodename nor servname provided, or not known>
'http://www.foxnews.com/' page is 248838 bytes
'http://www.bbc.co.uk/' page is 338658 bytes
'http://www.cnn.com/' page is 991167 bytes
'http://europe.wsj.com/' page is 970346 bytes
```

Which is perfect. How does futureproof compare?

```python
executor = futureproof.FutureProofExecutor(max_workers=5)
with futureproof.TaskManager(executor) as tm:
    for url in URLS:
        tm.submit(load_url, url, 60)
    for task in tm.as_completed():
        print("%r page is %d bytes" % (task.args[0], len(task.result)))
```

That looks quite similar, there's an executor and a *task manager*. `submit` and `as_completed` are methods on it and there's no `try..except`. If we run it we get:

```
'http://www.foxnews.com/' page is 248838 bytes
Traceback (most recent call last):
  File "/Users/yeray/.pyenv/versions/3.7.3/lib/python3.7/urllib/request.py", line 1317, in do_open
    encode_chunked=req.has_header('Transfer-encoding'))
  ... omitted traceback output ...
socket.gaierror: [Errno 8] nodename nor servname provided, or not known
```

Notice that `futureproof` raised the exception that ocurred immediately and everything stopped, as you would've expected in normal non-threaded Python, no surprises.

If we prefer `futureproof` gives you the option to log or even ignore exceptions using error policies. Say we want to log the exceptions:

```python
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s %(thread)s] %(message)s",
    datefmt="%H:%M:%S",
)

executor = futureproof.FutureProofExecutor(max_workers=5)
with futureproof.TaskManager(executor, error_policy="log") as tm:
    for url in URLS:
        tm.submit(load_url, url, 60)
        for task in tm.as_completed():
            if not isinstance(task.result, Exception):
                print("%r page is %d bytes" % (task.args[0], len(task.result)))
```

Note we've added a check to only print the result in case it's not an exception, this outputs:

```
'http://www.foxnews.com/' page is 251088 bytes
[12:09:15 4350641600] Task Task(fn=<function load_url at 0x1029ef1e0>, args=('http://some-made-up-domain-that-definitely-does-not-exist.com/', 60), kwargs={}, result=URLError(gaierror(8, 'nodename nor servname provided, or not known')),
 complete=True) raised an exception
Traceback (most recent call last):
  File "/Users/yeray/.pyenv/versions/3.7.3/lib/python3.7/urllib/request.py", line 1317, in do_open
    encode_chunked=req.has_header('Transfer-encoding'))
    ... omitted long traceback ...
  File "/Users/yeray/.pyenv/versions/3.7.3/lib/python3.7/urllib/request.py", line 1319, in do_open
    raise URLError(err)
urllib.error.URLError: <urlopen error [Errno 8] nodename nor servname provided, or not known>
'http://some-made-up-domain-that-definitely-does-not-exist.com/' generated an exception: <urlopen error [Errno 8] nodename nor servname provided, or not known>
'http://www.bbc.co.uk/' page is 339087 bytes
'http://www.cnn.com/' page is 991167 bytes
[12:09:16 123145404444672] 5 task completed in the last 1.18 second(s)
'http://europe.wsj.com/' page is 970880 bytes
```

Note we only had to configure logging and pass the appropriate error policy, everything else was taken care for us. You can also choose to ignore exceptions completely and manage them yourself accessing `result`, which is the workflow when using `concurrent.futures`.

### `as_completed`?

If you think about it, why do we need `as_completed`?

The answer is for monitoring and error handling.

If we had loads of URLs, you don't want to wait until all URLs are back to show output, it could take ages. But really it just adds complexity to the code. What does the example look like if you don't use `as_completed`?

```python
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    future_to_url = {executor.submit(load_url, url, 60): url for url in URLS}

for future, url in future_to_url.items():
    try:
        data = future.result()
    except Exception as exc:
        print("%r generated an exception: %s" % (url, exc))
    else:
        print("%r page is %d bytes" % (url, len(data)))
```

Which is arguably more readable, however, it has a subtle difference: there's no output until all the futures are complete. If you imagine tasks taking longer you're left wondering if things are even working at all.

Let's compare to the `futureproof` version:

```python
executor = futureproof.FutureProofExecutor(max_workers=5)
with futureproof.TaskManager(executor, error_policy="ignore") as tm:
    for url in URLS:
        tm.submit(load_url, url, 60)

for task in tm.completed_tasks:
    if isinstance(task.result, Exception):
        print("%r generated an exception: %s" % (task.args[0], task.result))
    else:
        print("%r page is %d bytes" % (task.args[0], len(task.result)))
```

```
[12:40:28 123145393414144] Starting executor monitor
[12:40:29 123145393414144] 5 task completed in the last 1.01 second(s)
[12:40:29 123145393414144] Shutting down monitor...
'http://www.foxnews.com/' page is 252016 bytes
'http://some-made-up-domain-that-definitely-does-not-exist.com/' generated an exception: <urlopen error [Errno 8] nodename nor servname provided, or not known>
'http://www.cnn.com/' page is 992648 bytes
'http://www.bbc.co.uk/' page is 338987 bytes
'http://europe.wsj.com/' page is 969285 bytes
```

`futureproof` defaults to logging monitoring information on the tasks so you always know if things are working. Note how the task manager exposes `completed_tasks` allowing easy access to the results without having to manually keep track of futures. Finally, as mentioned previously, you're also in total control over exception handling so you don't need to add code for that either.

These are fairly minor problems that we can work around manually using `concurrent.futures` but when starting to deal higher number of tasks other problems arise, check out the [examples directory](https://github.com/yeraydiazdiaz/futureproof/tree/master/examples/) for a hands-on comparison between `futureproof` and `concurrent.futures` in other more serious scenarios.

## Alternatives

I am by no means the first person to address these problems. Here a few similar, more stable and feature full, albeit restrictively licensed alternatives:

- [Pebble](https://pebble.readthedocs.io/en/latest/), LGPL 3.0
- [more-executors](https://github.com/rohanpm/more-executors), GPL 3.0

`futureproof` is licensed MIT.
