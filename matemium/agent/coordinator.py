"""Core engine coordinator — Matemium Multi-Agent Lifecycle (Phases 1–5)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .critic import CriticHooks, CoordinatorHaltError, run_critic_loop
from .models import (
    AccountTier,
    DirectorOutput,
    LifecycleResult,
    ModelTier,
    Phase,
    PostProductionOutput,
    ProcessingMode,
    ProjectSession,
)
from .critic import make_sidecar_compile_fn, sidecar_binary_available
from .stubs import (
    CompileFn,
    PatchFn,
    TTSResult,
    WhisperTranscript,
    default_compile_success,
    default_visual_qc,
    sidecar_compile_for,
    stub_director_agent,
    stub_engineer_agent,
    stub_tts,
    stub_whisper_json,
)
from .timing import instantiate_timing_blueprint

DirectorFn = Callable[[str, ProcessingMode], DirectorOutput]
EngineerFn = Callable[[ProjectSession], object]
TTSFn = Callable[[str], TTSResult]
WhisperFn = Callable[[TTSResult, str], WhisperTranscript]

# Per-phase base token costs (before tier multiplier).
PHASE_TOKEN_BASE: dict[Phase, int] = {
    Phase.DIRECTOR: 120,
    Phase.TIMING_BLUEPRINT: 80,
    Phase.ENGINEER: 200,
    Phase.CRITIC: 150,
    Phase.POST_PRODUCTION: 60,
}


@dataclass
class CoordinatorConfig:
    """Injectable dependencies for testing and future real agent wiring."""

    director_fn: DirectorFn = stub_director_agent
    engineer_fn: EngineerFn = stub_engineer_agent
    tts_fn: TTSFn = stub_tts
    whisper_fn: WhisperFn = stub_whisper_json
    compile_fn: CompileFn | None = None
    patch_fn: PatchFn = lambda _stderr: None
    visual_qc_fn: Callable[[], bool] = default_visual_qc
    use_sidecar_compile: bool = False

    def resolve_compile_fn(self, project_dir: Path) -> CompileFn:
        """Resolve compile_fn — explicit override, optional sidecar, else stub success."""
        if self.compile_fn is not None:
            return self.compile_fn
        if self.use_sidecar_compile and sidecar_binary_available():
            return make_sidecar_compile_fn(project_dir)
        return default_compile_success


class LifecycleCoordinator:
    """Orchestrates the five-phase agent lifecycle for a single project run."""

    def __init__(
        self,
        project_dir: Path | str,
        *,
        model_tier: ModelTier = ModelTier.STANDARD,
        account_tier: AccountTier = AccountTier.BASIC,
        watermark_removal_paid: bool = False,
        extra_project_tokens_spent: bool = False,
        config: CoordinatorConfig | None = None,
    ):
        self.project_dir = Path(project_dir)
        self.model_tier = model_tier
        self.account_tier = account_tier
        self.watermark_removal_paid = watermark_removal_paid
        self.extra_project_tokens_spent = extra_project_tokens_spent
        self.config = config or CoordinatorConfig()

    def _charge_phase(self, session: ProjectSession, phase: Phase, label: str) -> None:
        base = PHASE_TOKEN_BASE[phase]
        session.token_ledger.record(phase, self.model_tier, base, label)

    def run_phase_director(
        self,
        session: ProjectSession,
        user_prompt: str,
        mode: ProcessingMode,
    ) -> DirectorOutput:
        """Phase 1 — lock script, tone, DIV boundaries, and mode config."""
        output = self.config.director_fn(user_prompt, mode)
        session.director_output = output
        self._charge_phase(session, Phase.DIRECTOR, "director_script_finalization")
        session.record_transition(Phase.TIMING_BLUEPRINT, ("script", "mode", "div_markers"))
        return output

    def run_phase_timing(self, session: ProjectSession) -> None:
        """Phase 2 — Audio-First or Beat-Cadence blueprint instantiation."""
        assert session.director_output is not None
        blueprint = instantiate_timing_blueprint(
            session.director_output.script,
            session.director_output.mode,
            tts_fn=self.config.tts_fn,
            whisper_fn=self.config.whisper_fn,
        )
        session.blueprint = blueprint
        label = (
            "audio_whisper_blueprint"
            if blueprint.mode is ProcessingMode.AUDIO
            else "mute_beat_cadence_blueprint"
        )
        self._charge_phase(session, Phase.TIMING_BLUEPRINT, label)
        session.record_transition(Phase.ENGINEER, ("blueprint",))

    def run_phase_engineer(self, session: ProjectSession) -> None:
        """Phase 3 — decoupled scenes.py / assets.py configuration."""
        artifacts = self.config.engineer_fn(session)
        session.artifacts = artifacts
        self._charge_phase(session, Phase.ENGINEER, "decoupled_code_generation")
        session.record_transition(Phase.CRITIC, ("scenes_config", "assets_config"))

    def run_phase_critic(self, session: ProjectSession) -> None:
        """Phase 4 — compile loop with capped self-correction."""
        self._charge_phase(session, Phase.CRITIC, "compile_visual_qc")
        hooks = CriticHooks(
            compile_fn=self.config.resolve_compile_fn(session.project_dir),
            patch_fn=self.config.patch_fn,
            visual_qc_fn=self.config.visual_qc_fn,
        )
        result = run_critic_loop(session, hooks)
        session.critic_result = result
        session.record_transition(Phase.POST_PRODUCTION, ("critic_passed",))

    def run_phase_post_production(self, session: ProjectSession) -> PostProductionOutput:
        """Phase 5 — sound/render mix metadata (no real ffmpeg in coordinator)."""
        assert session.director_output is not None
        assert session.blueprint is not None
        mode = session.director_output.mode
        output = PostProductionOutput(
            mode=mode,
            total_duration=session.blueprint.total_duration,
            audio_track_attached=mode is ProcessingMode.AUDIO,
            ambient_track_attached=mode is ProcessingMode.MUTE,
            reel_splits=("main",) if mode is ProcessingMode.AUDIO else ("silent_main",),
        )
        session.post_production = output
        self._charge_phase(session, Phase.POST_PRODUCTION, "final_assembly")
        return output

    def run(
        self,
        user_prompt: str,
        mode: ProcessingMode,
    ) -> LifecycleResult:
        """Execute the full lifecycle from Director through Post-Production."""
        session = ProjectSession(
            project_dir=self.project_dir,
            user_prompt=user_prompt,
            model_tier=self.model_tier,
            account_tier=self.account_tier,
            watermark_removal_paid=self.watermark_removal_paid,
            extra_project_tokens_spent=self.extra_project_tokens_spent,
        )
        try:
            self.run_phase_director(session, user_prompt, mode)
            self.run_phase_timing(session)
            self.run_phase_engineer(session)
            self.run_phase_critic(session)
            post = self.run_phase_post_production(session)
        except CoordinatorHaltError:
            raise

        assert session.blueprint is not None
        assert session.artifacts is not None
        return LifecycleResult(
            session=session,
            blueprint=session.blueprint,
            artifacts=session.artifacts,
            post_production=post,
            token_ledger=session.token_ledger,
        )


def run_lifecycle(
    project_dir: Path | str,
    user_prompt: str,
    mode: ProcessingMode,
    *,
    model_tier: ModelTier = ModelTier.STANDARD,
    account_tier: AccountTier = AccountTier.BASIC,
    watermark_removal_paid: bool = False,
    extra_project_tokens_spent: bool = False,
    config: CoordinatorConfig | None = None,
) -> LifecycleResult:
    """Module-level entry point for sidecar/server integration."""
    coordinator = LifecycleCoordinator(
        project_dir,
        model_tier=model_tier,
        account_tier=account_tier,
        watermark_removal_paid=watermark_removal_paid,
        extra_project_tokens_spent=extra_project_tokens_spent,
        config=config,
    )
    return coordinator.run(user_prompt, mode)