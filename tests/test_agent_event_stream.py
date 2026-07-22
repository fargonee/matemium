from __future__ import annotations

from matemium.agent.event_stream import AgentEventEmitter


def test_events_are_versioned_ordered_redacted_and_bounded() -> None:
    emitter = AgentEventEmitter("run-1")
    first = emitter.event("action_started", {"api_key": "secret", "summary": "safe"})
    second = emitter.event("action_completed", {"output": "x" * 50_000})
    assert first["schema_version"] == 1
    assert first["sequence"] == 1 and second["sequence"] == 2
    assert first["payload"]["api_key"] == "[REDACTED]"
    assert second["payload"]["output"].endswith("…[truncated]")


def test_legacy_thought_is_replaced_with_concise_progress_summary() -> None:
    event = AgentEventEmitter("run-1").legacy_callback_event(
        {"type": "thought", "content": "private detailed reasoning"}
    )
    assert event["event_type"] == "progress_updated"
    assert "private detailed reasoning" not in str(event)
