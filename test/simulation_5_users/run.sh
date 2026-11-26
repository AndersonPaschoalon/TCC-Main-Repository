#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

uv sync
source .venv/bin/activate
python five_user_demo.py
