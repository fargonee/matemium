#!/usr/bin/env python3
"""Deprecated — use: python -m matemium demo  or  ./matemium.sh demo"""

from __future__ import annotations

import sys

from matemium.cli import main

if __name__ == "__main__":
    print("Note: render.py is deprecated. Prefer: ./matemium.sh demo", file=sys.stderr)
    # Map old flags to new CLI where possible
    argv = sys.argv[1:]
    if "--demo" in argv:
        i = argv.index("--demo")
        variant = argv[i + 1] if i + 1 < len(argv) else "portrait"
        mapped = ["demo", variant]
        for flag in ("-q", "--quality", "-o", "--output", "-r", "--resolution"):
            if flag in argv:
                j = argv.index(flag)
                if j + 1 < len(argv):
                    mapped.extend([flag, argv[j + 1]])
        sys.exit(main(mapped))
    sys.exit(main(["demo", "portrait"]))