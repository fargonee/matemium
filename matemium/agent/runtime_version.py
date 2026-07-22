"""Stable identifiers for agent runtimes exposed at API and event boundaries."""

from __future__ import annotations

LEGACY_REACT_RUNTIME = "legacy-react-v1"
TARGET_STATE_MACHINE_RUNTIME = "state-machine-v2"
AIDER_RUNTIME = "aider-v1"

AVAILABLE_AGENT_RUNTIMES = frozenset({AIDER_RUNTIME, LEGACY_REACT_RUNTIME})
DEFAULT_AGENT_RUNTIME = AIDER_RUNTIME


def resolve_agent_runtime(requested: str | None) -> str:
    """Resolve an API runtime selector or reject an unavailable runtime."""
    runtime = requested or DEFAULT_AGENT_RUNTIME
    if runtime not in AVAILABLE_AGENT_RUNTIMES:
        available = ", ".join(sorted(AVAILABLE_AGENT_RUNTIMES))
        raise ValueError(
            f"Agent runtime '{runtime}' is unavailable. Available runtimes: {available}."
        )
    return runtime
