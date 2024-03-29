---
hide-toc: true
---

# Futureproof - Bulletproof concurrent.futures

[![Documentation Status](https://readthedocs.org/projects/futureproof/badge/?version=latest)](https://futureproof.readthedocs.io/en/latest/?badge=latest)
[![Build Status](https://github.com/yeraydiazdiaz/futureproof/workflows/CI/badge.svg?branch=master)](https://github.com/yeraydiazdiaz/futureproof/actions?workflow=CI)
[![Supported Python Versions](https://img.shields.io/pypi/pyversions/futureproof.svg)](https://pypi.org/project/futureproof/)
[![PyPI](https://img.shields.io/pypi/v/futureproof.svg)](https://pypi.org/project/futureproof/)
[![codecov](https://codecov.io/gh/yeraydiazdiaz/futureproof/branch/master/graph/badge.svg)](https://codecov.io/gh/yeraydiazdiaz/futureproof)
[![shoutouts.dev](https://shoutouts.dev/projects/yeraydiazdiaz/futureproof/badge)](https://shoutouts.dev/projects/yeraydiazdiaz/futureproof)

[`concurrent.futures`](https://docs.python.org/3/library/concurrent.futures.html) is amazing, but it's got some sharp edges that have bit me many times in the past.

Futureproof is a thin wrapper around it addressing some of these problems and adding some usability features.

## Features:

- **Monitoring**: a summary of recent completed tasks is logged by default.
- **Fail fast**: errors cause the main thread to raise an exception and stop by default.
- **Error policy**: the user can decide whether to raise, log or completely ignore errors on tasks.
- **Backpressure control**: large collections of tasks are consumed lazily as the executor completes tasks, drastically reducing memory consumption and improving responsiveness in these situations.

## Current status: Alpha

The API is subject to change, any changes will be documented in the changelog.

Futureproof was designed to wrap ThreadPoolExecutor, however version 0.2+ includes limited support ProcessPoolExecutor but only for Python3.7+.


```{toctree}
:hidden:
motivation
api
alternatives
changelog
GitHub Repository <https://github.com/yeraydiazdiaz/futureproof>
```
