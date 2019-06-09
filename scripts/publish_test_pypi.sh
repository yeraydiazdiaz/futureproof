#!/bin/bash

./scripts/package.sh
twine upload --repository-url https://test.pypi.org/legacy/ dist/*
