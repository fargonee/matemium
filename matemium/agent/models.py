"""Core data models for the Matemium multi-agent lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Phase(str, Enum):
    """Ordered lifecycle phases from agentic_ai_goal.md."""

    DIRECTOR = "director"
    TIMING_BLUEPRINT = "timing_blueprint"
    ENGINEER = "engineer"
    CRITIC = "critic"
    POST_PRODUCTION = "post_production"


class ProcessingMode(str, Enum):
    """User-selected authoring path (Audio-First vs Beat-Cadence)."""

    AUDIO = "audio"
    MUTE = "mute"


class ModelTier(str, Enum):
    """Token economy tiers from the monetization matrix."""

    STANDARD = "standard"  # 1x
    ELITE = "elite"  # 5x
    DEEP = "deep"  # 12x


class AccountTier(str, Enum):
    """Commercial subscription plan — distinct from AI model_tier."""

    BASIC = "basic"
    PREMIUM = "premium"


TIER_MULTIPLIERS: dict[ModelTier, int] = {
    ModelTier.STANDARD: 1,
    ModelTier.ELITE: 5,
    ModelTier.DEEP: 12,
}


@dataclass(frozen=True)
class NarrativeBlock:
    """A script segment bounded by # ---DIV: markers or implicit paragraphs."""

    block_id: str
    title: str
    body: str
    latex_fragments: tuple[str, ...] = ()
    has_3d: bool = False
    word_count: int = 0
    complexity_score: float = 0.0


@dataclass(frozen=True)
class TimingSegment:
    """One timed unit in the blueprint — audio-anchored or beat-cadence wait."""

    block_id: str
    start_time: float
    end_time: float
    duration: float
    wait_duration: float
    source: str  # "whisper" | "beat_cadence"
    words: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class TimingBlueprint:
    """Phase 2 output — absolute timeline map for scenes.py wait anchors."""

    mode: ProcessingMode
    segments: tuple[TimingSegment, ...]
    total_duration: float
    script_fingerprint: str

    @property
    def segment_count(self) -> int:
        return len(self.segments)


@dataclass(frozen=True)
class WaitAnchor:
    """Explicit builder.wait(duration) marker sourced from the blueprint."""

    block_id: str
    duration: float
    after_call: str


@dataclass(frozen=True)
class ScenesConfig:
    """Decoupled timeline narrative — no heavy math (Guardrail 1)."""

    div_markers: tuple[str, ...]
    part_functions: tuple[str, ...]
    builder_calls: tuple[dict[str, Any], ...]
    wait_anchors: tuple[WaitAnchor, ...]
    orientation: str = "portrait"


@dataclass(frozen=True)
class AssetsConfig:
    """Engine room — LaTeX, coordinates, pure computations (Guardrail 1)."""

    latex_strings: tuple[str, ...]
    coordinate_sets: tuple[dict[str, Any], ...]
    computations: tuple[dict[str, Any], ...]
    mesh_definitions: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class DecoupledArtifacts:
    """Phase 3 engineer output ready for scenes.py / assets.py emission."""

    scenes: ScenesConfig
    assets: AssetsConfig


@dataclass
class TokenEntry:
    """Single charge event within a lifecycle run."""

    phase: Phase
    tier: ModelTier
    base_tokens: int
    multiplier: int
    charged_tokens: int
    label: str


@dataclass
class TokenLedger:
    """Cumulative token accounting across all phases."""

    entries: list[TokenEntry] = field(default_factory=list)

    @property
    def total_charged(self) -> int:
        return sum(e.charged_tokens for e in self.entries)

    def record(self, phase: Phase, tier: ModelTier, base_tokens: int, label: str) -> TokenEntry:
        multiplier = TIER_MULTIPLIERS[tier]
        entry = TokenEntry(
            phase=phase,
            tier=tier,
            base_tokens=base_tokens,
            multiplier=multiplier,
            charged_tokens=base_tokens * multiplier,
            label=label,
        )
        self.entries.append(entry)
        return entry


@dataclass(frozen=True)
class DirectorOutput:
    """Phase 1 — finalized script and locked mode configuration."""

    script: str
    mode: ProcessingMode
    div_markers: tuple[str, ...]
    tone: str = "pedagogical"


@dataclass(frozen=True)
class CriticResult:
    """Phase 4 outcome."""

    passed: bool
    attempts: int
    stderr: str = ""
    visual_qc_passed: bool = False


@dataclass(frozen=True)
class PostProductionOutput:
    """Phase 5 — final assembly metadata."""

    mode: ProcessingMode
    total_duration: float
    audio_track_attached: bool
    ambient_track_attached: bool
    reel_splits: tuple[str, ...] = ()


@dataclass(frozen=True)
class PhaseTransition:
    """Observable hand-off between lifecycle phases."""

    from_phase: Phase | None
    to_phase: Phase
    payload_keys: tuple[str, ...]


@dataclass
class ProjectSession:
    """Mutable orchestration context carried through the lifecycle."""

    project_dir: Path
    user_prompt: str
    model_tier: ModelTier
    account_tier: AccountTier = AccountTier.BASIC
    watermark_removal_paid: bool = False
    extra_project_tokens_spent: bool = False
    current_phase: Phase = Phase.DIRECTOR
    director_output: DirectorOutput | None = None
    blueprint: TimingBlueprint | None = None
    artifacts: DecoupledArtifacts | None = None
    critic_result: CriticResult | None = None
    post_production: PostProductionOutput | None = None
    token_ledger: TokenLedger = field(default_factory=TokenLedger)
    transitions: list[PhaseTransition] = field(default_factory=list)
    halted: bool = False
    halt_reason: str = ""

    def record_transition(self, to_phase: Phase, payload_keys: tuple[str, ...]) -> None:
        self.transitions.append(
            PhaseTransition(
                from_phase=self.current_phase,
                to_phase=to_phase,
                payload_keys=payload_keys,
            )
        )
        self.current_phase = to_phase


@dataclass(frozen=True)
class LifecycleResult:
    """Terminal success payload from a full coordinator run."""

    session: ProjectSession
    blueprint: TimingBlueprint
    artifacts: DecoupledArtifacts
    post_production: PostProductionOutput
    token_ledger: TokenLedger