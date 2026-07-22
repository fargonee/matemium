"""Phase 9 benchmark aggregation and release-gate evaluation.

The harness consumes recorded run results. It never substitutes mocks for real
cloud/local execution and never marks a profile as approved when cases are absent.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import ceil
from statistics import mean
from typing import Any, Iterable


@dataclass(frozen=True)
class BenchmarkResult:
    case_id: str
    profile: str
    succeeded: bool
    claimed_success: bool
    destructive_edit: bool
    recovery_required: bool
    recovered: bool
    provider_calls: int
    reconciled_calls: int
    cancellation_seconds: float | None
    resume_required: bool
    resumed: bool
    stall_expected: bool
    stall_detected: bool
    model_calls: int
    tool_calls: int
    input_tokens: int
    output_tokens: int
    cost: float
    wall_seconds: float
    failure_tags: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "BenchmarkResult":
        fields = dict(value)
        fields["failure_tags"] = tuple(fields.get("failure_tags", ()))
        return cls(**fields)


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 1.0


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, ceil(len(ordered) * 0.95) - 1)]


def summarize_profile(results: Iterable[BenchmarkResult]) -> dict[str, Any]:
    rows = list(results)
    if not rows:
        raise ValueError("cannot summarize an empty benchmark profile")
    recoveries = [row for row in rows if row.recovery_required]
    resumes = [row for row in rows if row.resume_required]
    stalls = [row for row in rows if row.stall_expected]
    provider_calls = sum(row.provider_calls for row in rows)
    cancellation = [row.cancellation_seconds for row in rows if row.cancellation_seconds is not None]
    false_success = sum(row.claimed_success and not row.succeeded for row in rows)
    return {
        "case_count": len(rows),
        "task_success_rate": _rate(sum(row.succeeded for row in rows), len(rows)),
        "false_success_rate": _rate(false_success, len(rows)),
        "destructive_edit_rate": _rate(sum(row.destructive_edit for row in rows), len(rows)),
        "recovery_success_rate": _rate(sum(row.recovered for row in recoveries), len(recoveries)),
        "usage_reconciliation_rate": _rate(sum(row.reconciled_calls for row in rows), provider_calls),
        "cancellation_p95_seconds": _p95(cancellation),
        "resume_success_rate": _rate(sum(row.resumed for row in resumes), len(resumes)),
        "stall_detection_rate": _rate(sum(row.stall_detected for row in stalls), len(stalls)),
        "model_calls_mean": mean(row.model_calls for row in rows),
        "tool_calls_mean": mean(row.tool_calls for row in rows),
        "input_tokens_mean": mean(row.input_tokens for row in rows),
        "output_tokens_mean": mean(row.output_tokens for row in rows),
        "cost_mean": mean(row.cost for row in rows),
        "wall_seconds_p50": sorted(row.wall_seconds for row in rows)[(len(rows) - 1) // 2],
        "wall_seconds_p95": _p95([row.wall_seconds for row in rows]),
    }


def evaluate_release(
    results: Iterable[BenchmarkResult],
    required_case_ids: set[str],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    grouped: dict[str, list[BenchmarkResult]] = {}
    for result in results:
        grouped.setdefault(result.profile, []).append(result)
    if not grouped:
        return {"approved": False, "profiles": {}, "reasons": ["no recorded benchmark results"]}

    profiles: dict[str, Any] = {}
    reasons: list[str] = []
    for profile, rows in sorted(grouped.items()):
        observed = {row.case_id for row in rows}
        missing = sorted(required_case_ids - observed)
        duplicate = len(rows) != len(observed)
        metrics = summarize_profile(rows)
        checks = {
            "task_success_rate_min": metrics["task_success_rate"] >= thresholds["task_success_rate_min"],
            "false_success_rate_max": metrics["false_success_rate"] <= thresholds["false_success_rate_max"],
            "destructive_edit_rate_max": metrics["destructive_edit_rate"] <= thresholds["destructive_edit_rate_max"],
            "recovery_success_rate_min": metrics["recovery_success_rate"] >= thresholds["recovery_success_rate_min"],
            "usage_reconciliation_rate_min": metrics["usage_reconciliation_rate"] >= thresholds["usage_reconciliation_rate_min"],
            "cancellation_p95_seconds_max": metrics["cancellation_p95_seconds"] is not None and metrics["cancellation_p95_seconds"] <= thresholds["cancellation_p95_seconds_max"],
            "resume_success_rate_min": metrics["resume_success_rate"] >= thresholds["resume_success_rate_min"],
            "stall_detection_rate_min": metrics["stall_detection_rate"] >= thresholds["stall_detection_rate_min"],
        }
        approved = not missing and not duplicate and all(checks.values())
        profiles[profile] = {"approved": approved, "missing_cases": missing, "duplicate_cases": duplicate, "metrics": metrics, "checks": checks}
        if not approved:
            reasons.append(f"profile {profile} did not pass all release gates")
    return {"approved": not reasons, "profiles": profiles, "reasons": reasons}


def result_dict(result: BenchmarkResult) -> dict[str, Any]:
    return asdict(result)
