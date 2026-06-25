#!/bin/bash
# Generate the portrait test demo. Prefer: ./matemium.sh demo

set -e
cd "$(dirname "$0")"
exec ./matemium.sh demo "$@"