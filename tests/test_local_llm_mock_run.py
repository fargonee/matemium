"""Unit tests and mock run simulations for the local GGUF offline agentic loop."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from matemium.agent.coordinator import LifecycleCoordinator, CoordinatorConfig
from matemium.agent.local_agent import local_director_agent, local_engineer_agent
from matemium.agent.models import ProjectSession, ProcessingMode, Phase, ModelTier, TimingBlueprint, TimingSegment, DirectorOutput


@pytest.fixture
def clean_env() -> None:
    """Ensure environment variables are clean before and after tests."""
    vars_to_clean = ["MATEMIUM_USE_LOCAL_LLM", "MATEMIUM_LOCAL_LLM_MODEL_PATH"]
    for v in vars_to_clean:
        if v in os.environ:
            del os.environ[v]
    yield
    for v in vars_to_clean:
        if v in os.environ:
            del os.environ[v]


@patch("matemium.agent.local_runner.LocalInferenceRunner.generate")
def test_local_director_mock(mock_generate: MagicMock, clean_env: None) -> None:
    """Verify that local_director_agent calls LocalInferenceRunner with proper system prompts."""
    # Setup mock return script containing DIV boundaries
    mock_script = """# ---DIV: Setup---
def part_setup(b):
    b.add_heading("Pythagorean Theorem")
    b.add_body("Right triangles conceal a gorgeous geometric area equivalence.")
    b.add_math(r"a^2 + b^2 = c^2")
"""
    mock_generate.return_value = mock_script

    output = local_director_agent("pythagorean theorem", ProcessingMode.AUDIO)

    assert output.script == mock_script
    assert len(output.div_markers) == 1
    assert output.div_markers[0] == "Setup"
    assert output.mode == ProcessingMode.AUDIO

    # Verify that the model was called
    mock_generate.assert_called_once()
    args, _ = mock_generate.call_args
    # Check that our custom system prompt was injected
    assert "elite mathematics educator" in args[0]


@patch("matemium.agent.local_runner.LocalInferenceRunner.generate")
def test_local_engineer_mock_refinement(mock_generate: MagicMock, tmp_path: Path, clean_env: None) -> None:
    """Verify that local_engineer_agent programmatically writes the base project and applies GGUF refinements."""
    # Setup session with director output
    session = ProjectSession(
        project_dir=tmp_path,
        user_prompt="pythagorean theorem",
        model_tier=ModelTier.STANDARD,
    )
    
    script = """# ---DIV: Area---
def part_area(b):
    b.add_heading("Area")
    b.add_math(r"\\int x^2 \\, dx")
"""
    session.director_output = DirectorOutput(
        script=script,
        mode=ProcessingMode.AUDIO,
        div_markers=("Area",),
        tone="pedagogical",
    )
    
    # Timing blueprint
    session.blueprint = TimingBlueprint(
        mode=ProcessingMode.AUDIO,
        segments=(
            TimingSegment(
                block_id="part_area",
                start_time=0.0,
                end_time=5.0,
                duration=5.0,
                wait_duration=3.0,
                source="beat_cadence",
            ),
        ),
        total_duration=5.0,
        script_fingerprint="dummy",
    )

    # Mock GGUF patch refinement output
    patch_document = """
Some LLM conversational preamble...
<<<<<<< SEARCH
def part_area(b: CanvasBuilder) -> None:
    b.add_heading("Area")
=======
def part_area(b: CanvasBuilder) -> None:
    b.add_heading("Your custom math title")
    # Added visual grid matrices
>>>>>>> REPLACE
"""
    mock_generate.return_value = patch_document
    os.environ["MATEMIUM_USE_LOCAL_LLM"] = "true"

    # Run engineer
    artifacts = local_engineer_agent(session)

    # 1. Assert base files were generated
    scenes_file = tmp_path / "scenes.py"
    assets_file = tmp_path / "assets.py"
    assert scenes_file.is_file()
    assert assets_file.is_file()

    # 2. Assert that the search/replace block from GGUF was applied cleanly
    scenes_content = scenes_file.read_text(encoding="utf-8")
    assert "Your custom math title" in scenes_content
    assert "Added visual grid matrices" in scenes_content


def test_coordinator_dynamic_injection(clean_env: None) -> None:
    """Verify that LifecycleCoordinator dynamically overrides handlers when local LLM is enabled."""
    # 1. Default config uses stubs
    coord_default = LifecycleCoordinator("/tmp/dummy")
    assert coord_default.config.director_fn.__name__ == "stub_director_agent"
    assert coord_default.config.engineer_fn.__name__ == "stub_engineer_agent"

    # 2. Local LLM enabled config uses local_agent overrides
    os.environ["MATEMIUM_USE_LOCAL_LLM"] = "true"
    coord_local = LifecycleCoordinator("/tmp/dummy")
    assert coord_local.config.director_fn.__name__ == "local_director_agent"
    assert coord_local.config.engineer_fn.__name__ == "<lambda>"  # Wrapped in lambda closure for retriever injection
