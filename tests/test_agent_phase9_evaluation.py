from __future__ import annotations

import json
from pathlib import Path

from matemium.agent.evaluation import BenchmarkResult, evaluate_release
from matemium.agent.rollout import OperationalWindow, RolloutConfig, RolloutMode, rollback_required, select_runtime
from matemium.agent.runtime_version import LEGACY_REACT_RUNTIME, TARGET_STATE_MACHINE_RUNTIME

ROOT = Path(__file__).resolve().parents[1]


def result(case_id: str, profile: str = "cloud-test") -> BenchmarkResult:
    return BenchmarkResult(case_id, profile, True, True, False, True, True, 2, 2, 1.0, True, True, True, True, 2, 4, 100, 20, 0.01, 3.0)


def thresholds() -> dict[str, float]:
    return json.loads((ROOT / "evals/agent/phase0-thresholds.json").read_text())["release_thresholds"]


def test_release_report_rejects_missing_cases_and_false_success() -> None:
    rows = [result("a")]
    report = evaluate_release(rows, {"a", "b"}, thresholds())
    assert not report["approved"]
    assert report["profiles"]["cloud-test"]["missing_cases"] == ["b"]
    bad = result("b")
    bad = BenchmarkResult(**{**bad.__dict__, "succeeded": False, "claimed_success": True})
    assert not evaluate_release([rows[0], bad], {"a", "b"}, thresholds())["approved"]


def test_complete_passing_profile_is_approved() -> None:
    rows = [result("a"), result("b")]
    report = evaluate_release(rows, {"a", "b"}, thresholds())
    assert report["approved"]
    assert report["profiles"]["cloud-test"]["metrics"]["usage_reconciliation_rate"] == 1.0


def test_rollout_requires_approval_and_shadow_is_read_only() -> None:
    shadow = select_runtime(RolloutConfig(mode=RolloutMode.SHADOW), "user-1")
    assert shadow.execution_runtime == LEGACY_REACT_RUNTIME
    assert shadow.shadow_runtime == TARGET_STATE_MACHINE_RUNTIME
    assert not shadow.mutations_allowed
    blocked = select_runtime(RolloutConfig(mode=RolloutMode.TARGET, evaluation_approved=False), "user-1")
    assert blocked.execution_runtime == LEGACY_REACT_RUNTIME
    enabled = select_runtime(RolloutConfig(mode=RolloutMode.TARGET, evaluation_approved=True), "user-1")
    assert enabled.execution_runtime == TARGET_STATE_MACHINE_RUNTIME


def test_canary_is_stable_and_forced_rollback_wins() -> None:
    config = RolloutConfig(mode=RolloutMode.CANARY, canary_percent=50, evaluation_approved=True)
    assert select_runtime(config, "same-user") == select_runtime(config, "same-user")
    forced = select_runtime(RolloutConfig(mode=RolloutMode.TARGET, evaluation_approved=True, rollback_forced=True), "user")
    assert forced.execution_runtime == LEGACY_REACT_RUNTIME


def test_operational_threshold_breach_requests_rollback() -> None:
    healthy = OperationalWindow(0.0, 0, 0.01, 1.0, 1.0)
    assert not rollback_required(healthy)
    assert rollback_required(OperationalWindow(0.0, 1, 0.01, 1.0, 1.0))


def test_phase9_scenario_and_security_catalogs_cover_required_risks() -> None:
    scenarios = json.loads((ROOT / "evals/agent/phase9-scenarios.json").read_text())
    security = json.loads((ROOT / "evals/agent/phase9-security.json").read_text())
    assert {item["category"] for item in scenarios["scenarios"]} >= {"cancellation", "resume", "offline", "provider_failure", "concurrency"}
    assert {item["source"] for item in security["cases"]} >= {"workspace_file", "tool_output", "tool_arguments", "child_result"}
