"""assets.py for Phase 10 test project.

This file is imported by scenes.py. Use it for shared data, equations,
coordinates, meshes, or helper values that the builder scenes need.

For pure 3D testing you don't need heavy assets, but this shows the pattern.
"""

from __future__ import annotations


def get_test_positions() -> dict[str, tuple[float, float, float]]:
    """Useful world positions for the 3D test scenes."""
    return {
        "cube": (4.2, 1.2, 2.8),
        "sphere": (5.5, 3.0, 1.5),
        "axes": (-1.5, 0.3, -5.0),
        "marker": (-2.8, 0.6, -3.5),
    }


def get_demo_equations() -> list[str]:
    """A few equations to use in add_math / add_3d."""
    return [
        r"\vec{r} = (x, y, z)",
        r"z = \sin(x) \cos(y)",
        r"\int_{-\infty}^{\infty} e^{-x^2} \, dx = \sqrt{\pi}",
    ]


def get_solid_spec(shape: str = "cube", size: float = 1.0) -> dict:
    """Helper to build solid content dicts."""
    return {
        "shape": shape,
        "size": size,
        "color": "#5eb3ff" if shape == "cube" else "#ffcc66",
        "opacity": 0.82,
    }
