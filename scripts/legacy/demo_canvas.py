#!/usr/bin/env python3
"""Deprecated — scenes moved to projects/demo/scenes.py

Render with:
    ./matemium.sh demo
    python -m matemium demo
"""

from projects.demo.scenes import BuilderDemo, LandscapeDemo, PortraitDemo

# Backward-compatible aliases for manim CLI users
CanvasDemo = PortraitDemo
LandscapeCanvasDemo = LandscapeDemo
PythonCanvasDemo = BuilderDemo

__all__ = [
    "PortraitDemo",
    "LandscapeDemo",
    "BuilderDemo",
    "CanvasDemo",
    "LandscapeCanvasDemo",
    "PythonCanvasDemo",
]