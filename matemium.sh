#!/usr/bin/env bash
# Matemium — one command to render videos.
# Usage: ./matemium.sh demo | ./matemium.sh render my_project | ./matemium.sh list

set -e
cd "$(dirname "$0")"
if [ -z "$VIRTUAL_ENV" ] && [ -f venv/bin/activate ]; then
    source venv/bin/activate
fi
exec python -m matemium "$@"