from __future__ import annotations

import pytest

from matemium.agent.runtime_version import (
    AIDER_RUNTIME,
    DEFAULT_AGENT_RUNTIME,
    LEGACY_REACT_RUNTIME,
    TARGET_STATE_MACHINE_RUNTIME,
    resolve_agent_runtime,
)


def test_default_runtime_is_aider() -> None:
    assert resolve_agent_runtime(None) == DEFAULT_AGENT_RUNTIME == AIDER_RUNTIME


def test_aider_runtime_can_be_requested() -> None:
    assert resolve_agent_runtime(AIDER_RUNTIME) == AIDER_RUNTIME


def test_legacy_react_runtime_can_be_requested() -> None:
    assert resolve_agent_runtime(LEGACY_REACT_RUNTIME) == LEGACY_REACT_RUNTIME


def test_target_runtime_cannot_be_requested_before_implementation() -> None:
    with pytest.raises(ValueError, match="unavailable"):
        resolve_agent_runtime(TARGET_STATE_MACHINE_RUNTIME)


def test_unknown_runtime_is_rejected() -> None:
    with pytest.raises(ValueError, match="made-up-v9"):
        resolve_agent_runtime("made-up-v9")
