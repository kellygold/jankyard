#!/usr/bin/env bash
set -euo pipefail
# Run after installing the locked dependencies and configuring a local database.
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python ]]; then
    echo 'Create .venv and install requirements-test.txt first; see README.md.' >&2
    exit 1
fi
# Schema creation/migration is an explicit separate command; starting the web
# process must never silently initialize whichever database .env points at.
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "${PORT:-8000}"
