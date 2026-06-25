"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from matemium.paths import ensure_on_path


@pytest.fixture(autouse=True)
def _matemium_path():
    ensure_on_path()