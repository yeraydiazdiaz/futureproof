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

The API is subject to change.

Currently only tested as a wrapper for ThreadPoolExecutor.

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

Just to reiterate, this is amazing, the fact that the barrier of entry for threads is this small is really an achievement on the work done by Brian Quinlan and the core Python developers.

However, I see two problems with this:

1. The boilerplate. I need to enter a context manager, call `submit` manually keeping track of the futures and its arguments, call `as_completed` which actually returns an iterator, call `result` on the future remembering to handle the exception.
2. It's surprising. Why do you need to get the result in order to raise? What if I don't expect it to raise? I probably want to know as soon as possible.

If you run this code you get the following output (at the time of this writing):

```
'http://some-made-up-domain-that-definitely-does-not-exist.com/' generated an exception: <urlopen error [Errno 8] nodename nor servname provided, or not known>
'http://www.foxnews.com/' page is 248838 bytes
'http://www.bbc.co.uk/' page is 338658 bytes
'http://www.cnn.com/' page is 991167 bytes
'http://europe.wsj.com/' page is 970346 bytes
```

Which is perfect, there was one worker per URL and the DNS failure is printed right at the top as expected.

How does futureproof compare?

```python
executor = futureproof.FutureProofExecutor(max_workers=5)
with futureproof.TaskManager(executor) as tm:
    for url in URLS:
        tm.submit(load_url, url, 60)
    for task in tm.as_completed():
        print("%r page is %d bytes" % (task.args[0], len(task.result)))
```

That looks quite similar, there's an executor *and* a task manager, `submit` and `as_completed` are methods on it and there's no try..except. If we run it we get:

```
'http://www.foxnews.com/' page is 248838 bytes
Traceback (most recent call last):
  File "/Users/yeray/.pyenv/versions/3.7.3/lib/python3.7/urllib/request.py", line 1317, in do_open
    encode_chunked=req.has_header('Transfer-encoding'))
  ... more traceback output ...
socket.gaierror: [Errno 8] nodename nor servname provided, or not known
```

Notice that `futureproof` raised the exception that ocurred immediately and stopped, as you would've expected, but it gives you the option to log, or ignore exceptions using error policies. Say we want to log the exceptions:

```python
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s %(thread)s] %(message)s",
    datefmt="%H:%M:%S",
)

executor = futureproof.FutureProofExecutor(max_workers=5)
with futureproof.TaskManager(
    executor, error_policy=futureproof.ErrorPolicyEnum.LOG
) as tm:
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

Note we only had to configure logging, everything else was taken care for us. You can also choose to ignore exceptions completely and manage them yourself accessing `result`, which is how `concurrent.futures` expects you to do.


Check out the [examples directory](https://github.com/yeraydiazdiaz/futureproof/tree/master/examples/) for a hands-on comparison between `futureproof` and `concurrent.futures`.
