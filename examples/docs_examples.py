"""
The reference example of concurrent.futures from the Python docs
and how it compares to futureproof.
"""

import concurrent.futures
import logging
import sys
import urllib.request

import futureproof

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s %(thread)s] %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)

URLS = [
    "http://www.foxnews.com/",
    "http://www.cnn.com/",
    "http://europe.wsj.com/",
    "http://www.bbc.co.uk/",
    "http://some-made-up-domain-that-definitely-does-not-exist.com/",
]


# Retrieve a single page and report the URL and contents
def load_url(url, timeout):
    with urllib.request.urlopen(url, timeout=timeout) as conn:
        return conn.read()


def with_futures():
    # We can use a with statement to ensure threads are cleaned up promptly
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Start the load operations and mark each future with its URL
        future_to_url = {executor.submit(load_url, url, 60): url for url in URLS}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data = future.result()
            except Exception as exc:
                print("%r generated an exception: %s" % (url, exc))
            else:
                print("%r page is %d bytes" % (url, len(data)))


def with_futureproof():
    executor = futureproof.ThreadPoolExecutor(max_workers=5)
    with futureproof.TaskManager(executor) as tm:
        for url in URLS:
            tm.submit(load_url, url, 60)
        for task in tm.as_completed():
            print("%r page is %d bytes" % (task.args[0], len(task.result)))


if len(sys.argv) > 1 and sys.argv[1] == "futures":
    with_futures()
else:
    with_futureproof()
