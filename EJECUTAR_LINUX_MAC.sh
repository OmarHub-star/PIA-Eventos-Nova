#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/init_env.py
python scripts/serve.py
