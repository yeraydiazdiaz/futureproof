#!/bin/bash

rm -fr dist/
python setup.py sdist
python setup.py bdist_wheel --universal
