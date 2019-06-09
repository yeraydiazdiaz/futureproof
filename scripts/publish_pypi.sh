#!/bin/bash

./scripts/package.sh
twine upload dist/*
