from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = ROOT / "evals" / "agent" / "phase0-benchmarks.json"
THRESHOLDS = ROOT / "evals" / "agent" / "phase0-thresholds.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_phase0_benchmark_suite_has_unique_complete_cases() -> None:
    suite = _load(BENCHMARKS)
    cases = suite["cases"]
    ids = [case["id"] for case in cases]

    assert suite["schema_version"] == 1
    assert len(cases) >= 10
    assert len(ids) == len(set(ids))
    for case in cases:
        assert case["category"]
        assert case["objective"]
        assert case["fixture"]
        assert case["required_evidence"]
        assert case["failure_tags"]


def test_phase0_thresholds_match_suite_and_cover_critical_failures() -> None:
    suite = _load(BENCHMARKS)
    config = _load(THRESHOLDS)
    thresholds = config["release_thresholds"]

    assert config["schema_version"] == 1
    assert config["suite_id"] == suite["suite_id"]
    assert thresholds["false_success_rate_max"] <= 0.01
    assert thresholds["destructive_edit_rate_max"] == 0.0
    assert thresholds["usage_reconciliation_rate_min"] >= 0.99
    assert thresholds["stall_detection_rate_min"] >= 0.95
