"""Versioned agent rollout, shadowing, cohort selection, and rollback policy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256

from .runtime_version import LEGACY_REACT_RUNTIME, TARGET_STATE_MACHINE_RUNTIME


class RolloutMode(str, Enum):
    LEGACY = "legacy"
    SHADOW = "shadow"
    CANARY = "canary"
    TARGET = "target"


@dataclass(frozen=True)
class RolloutConfig:
    mode: RolloutMode = RolloutMode.LEGACY
    canary_percent: int = 0
    evaluation_approved: bool = False
    rollback_forced: bool = False


@dataclass(frozen=True)
class RuntimeDecision:
    execution_runtime: str
    shadow_runtime: str | None
    mutations_allowed: bool
    reason: str


@dataclass(frozen=True)
class OperationalWindow:
    false_success_rate: float
    destructive_edits: int
    provider_failure_rate: float
    cancellation_p95_seconds: float
    accounting_reconciliation_rate: float


def rollback_required(window: OperationalWindow) -> bool:
    return (
        window.false_success_rate > 0.01
        or window.destructive_edits > 0
        or window.provider_failure_rate > 0.10
        or window.cancellation_p95_seconds > 3.0
        or window.accounting_reconciliation_rate < 0.99
    )


def select_runtime(config: RolloutConfig, cohort_key: str) -> RuntimeDecision:
    if config.rollback_forced:
        return RuntimeDecision(LEGACY_REACT_RUNTIME, None, True, "operator rollback is active")
    if config.mode == RolloutMode.LEGACY:
        return RuntimeDecision(LEGACY_REACT_RUNTIME, None, True, "legacy mode")
    if config.mode == RolloutMode.SHADOW:
        return RuntimeDecision(LEGACY_REACT_RUNTIME, TARGET_STATE_MACHINE_RUNTIME, False, "v2 shadow is observation-only")
    if not config.evaluation_approved:
        return RuntimeDecision(LEGACY_REACT_RUNTIME, None, True, "v2 evaluation is not approved")
    if config.mode == RolloutMode.TARGET:
        return RuntimeDecision(TARGET_STATE_MACHINE_RUNTIME, None, True, "approved target rollout")
    percent = max(0, min(config.canary_percent, 100))
    bucket = int.from_bytes(sha256(cohort_key.encode()).digest()[:4], "big") % 100
    runtime = TARGET_STATE_MACHINE_RUNTIME if bucket < percent else LEGACY_REACT_RUNTIME
    return RuntimeDecision(runtime, None, True, f"stable canary bucket {bucket}")
