#!/bin/bash

mkdir -p .dev
cd .dev
python -m venv .venv
source .venv/bin/activate

pip install futureproof

python -c "import futureproof"
