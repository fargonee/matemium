"""Tests for the Matemium multi-agent lifecycle coordinator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from matemium.agent import (
    CoordinatorConfig,
    CoordinatorHaltError,
    LifecycleCoordinator,
    ModelTier,
    Phase,
    ProcessingMode,
    TIER_MULTIPLIERS,
    build_audio_blueprint,
    build_mute_blueprint,
    instantiate_timing_blueprint,
    parse_whisper_timing_blueprint,
    run_lifecycle,
)
import subprocess

from matemium.agent.critic import (
    CriticHooks,
    MAX_CRITIC_RETRIES,
    VISUAL_QC_FAILURE,
    compile_project_via_sidecar,
    make_sidecar_compile_fn,
    run_critic_loop,
    run_sidecar_ipc,
    sidecar_binary_available,
)
from matemium.agent.sidecar_outcome import (
    SidecarIpcResult,
    compile_outcome_from_sidecar,
    contains_python_or_manim_error,
    format_compile_error,
    ipc_failure_result,
    merge_ipc_results,
)
from matemium.agent.verification_scratch import emit_scratch_artifacts
from matemium.agent.debug import DEBUG_FILENAME
from matemium.agent.models import ProjectSession
from matemium.agent.script_parser import parse_narrative_blocks
from matemium.agent.separation import build_decoupled_artifacts
from matemium.agent.stubs import (
    stub_director_agent,
    stub_tts,
    stub_whisper_json,
    whisper_transcript_from_payload,
)
from matemium.agent.writer import (
    PatchAmbiguousError,
    PatchBlock,
    PatchNotFoundError,
    SEARCH_MARKER,
    apply_patch,
    apply_patches_on_disk,
    format_patch_document,
    parse_patch_blocks,
    write_decoupled_project,
)
from matemium.workspace_project import load_scenes_module, workspace_context
from matemium.agent.timing import (
    INTER_BLOCK_GAP,
    MS_PRECISION,
    PADDING_TAIL,
    expected_audio_total_duration,
    expected_mute_total_duration,
    round_ms,
)

SAMPLE_SCRIPT = """# ---DIV: Scene parts---
def part_intro(b):
    b.add_heading("Quadratic roots")
    b.add_body("We factor step by step to find x.")
    b.add_math(r"x^2 - 5x + 6 = 0")

# ---DIV: Main scene---
def part_solution(b):
    b.add_math(r"x^2 - 5x + 6 = (x-2)(x-3)")
    b.add_3d("z = x^2 - y^2")
    b.add_text("Therefore x = 2 or x = 3.", after_3d=True)
"""


def test_parse_narrative_blocks_finds_two_div_sections():
    blocks = parse_narrative_blocks(SAMPLE_SCRIPT)
    assert len(blocks) == 2
    assert blocks[0].title == "Scene parts"
    assert blocks[1].has_3d is True
    assert blocks[0].latex_fragments


def test_audio_blueprint_uses_whisper_timestamps():
    blueprint = build_audio_blueprint(SAMPLE_SCRIPT)
    assert blueprint.mode is ProcessingMode.AUDIO
    assert blueprint.total_duration > 0
    assert blueprint.segment_count == 2
    assert all(s.source == "whisper" for s in blueprint.segments)
    assert blueprint.segments[0].words


def test_audio_blueprint_total_duration_matches_transcript_end():
    tts = stub_tts(SAMPLE_SCRIPT)
    transcript = stub_whisper_json(tts, SAMPLE_SCRIPT)
    blueprint = build_audio_blueprint(SAMPLE_SCRIPT)
    assert blueprint.total_duration == expected_audio_total_duration(transcript)
    assert blueprint.total_duration == round(transcript.words[-1].end + PADDING_TAIL, 4)
    assert blueprint.total_duration > blueprint.segments[-1].end_time


def test_mute_blueprint_computes_wait_durations_from_complexity():
    blueprint = build_mute_blueprint(SAMPLE_SCRIPT)
    assert blueprint.mode is ProcessingMode.MUTE
    assert blueprint.segment_count == 2
    assert all(s.source == "beat_cadence" for s in blueprint.segments)
    assert all(s.wait_duration >= 0.5 for s in blueprint.segments)
    assert blueprint.segments[1].wait_duration > blueprint.segments[0].wait_duration


def test_mute_blueprint_total_duration_formula():
    blueprint = build_mute_blueprint(SAMPLE_SCRIPT)
    assert blueprint.total_duration == expected_mute_total_duration(blueprint.segments)
    waits = sum(s.wait_duration for s in blueprint.segments)
    gaps = INTER_BLOCK_GAP * (len(blueprint.segments) - 1)
    assert blueprint.total_duration == round(waits + gaps + PADDING_TAIL, 4)
    assert blueprint.segments[1].start_time == round(
        blueprint.segments[0].end_time + INTER_BLOCK_GAP, 4
    )


WHISPER_PAYLOAD = {
    "language": "en",
    "words": [
        {"word": "We", "start": 0.0, "end": 0.1234},
        {"word": "factor", "start": 0.1234, "end": 0.5678},
        {"word": "step", "start": 0.5678, "end": 0.9012},
        {"word": "by", "start": 0.9012, "end": 1.0456},
        {"word": "step", "start": 1.0456, "end": 1.489},
        {"word": "to", "start": 1.489, "end": 1.6123},
        {"word": "find", "start": 1.6123, "end": 2.0567},
        {"word": "roots", "start": 2.0567, "end": 2.5011},
    ],
}


def test_parse_whisper_timing_blueprint_from_openai_payload():
    blueprint = parse_whisper_timing_blueprint(SAMPLE_SCRIPT, WHISPER_PAYLOAD)
    blocks = parse_narrative_blocks(SAMPLE_SCRIPT)
    transcript = whisper_transcript_from_payload(WHISPER_PAYLOAD)

    assert blueprint.mode is ProcessingMode.AUDIO
    assert blueprint.segment_count == len(blocks)
    assert all(s.source == "whisper" for s in blueprint.segments)
    assert all(s.words for s in blueprint.segments)

    attached = [w["word"] for s in blueprint.segments for w in s.words]
    expected_words = [w.word for w in transcript.words]
    assert attached == expected_words

    assert blueprint.total_duration == expected_audio_total_duration(transcript)
    assert blueprint.total_duration == round_ms(transcript.words[-1].end + PADDING_TAIL)

    for segment in blueprint.segments:
        assert segment.start_time == round(segment.start_time, MS_PRECISION)
        assert segment.end_time == round(segment.end_time, MS_PRECISION)
        assert segment.wait_duration == segment.duration
        if segment.end_time > segment.start_time:
            assert segment.duration == round_ms(segment.end_time - segment.start_time)
        assert segment.start_time == round_ms(min(float(w["start"]) for w in segment.words))
        assert segment.end_time == round_ms(max(float(w["end"]) for w in segment.words))

    for prev, nxt in zip(blueprint.segments, blueprint.segments[1:]):
        assert nxt.start_time >= prev.end_time - 1e-4


def test_parse_whisper_blueprint_word_timestamps_drive_segment_bounds():
    blueprint = parse_whisper_timing_blueprint(SAMPLE_SCRIPT, WHISPER_PAYLOAD)
    for segment in blueprint.segments:
        first = round_ms(min(float(w["start"]) for w in segment.words))
        last = round_ms(max(float(w["end"]) for w in segment.words))
        assert segment.start_time == first
        assert segment.end_time == last
        assert segment.wait_duration == round_ms(last - first)
        for word in segment.words:
            assert first <= round_ms(float(word["start"])) <= last
            assert first <= round_ms(float(word["end"])) <= last


SPARSE_SCRIPT = """# ---DIV: Block A---
def part_a(b):
    b.add_body("First narrative block.")

# ---DIV: Block B---
def part_b(b):
    b.add_body("Second narrative block.")

# ---DIV: Block C---
def part_c(b):
    b.add_body("Third narrative block.")
"""

SPARSE_WHISPER_PAYLOAD = {
    "words": [{"word": "hello", "start": 0.0, "end": 0.05}],
}

EXACT_FIT_SCRIPT = """# ---DIV: A---
def part_a(b):
    b.add_body("one")
# ---DIV: B---
def part_b(b):
    b.add_body("two")
# ---DIV: C---
def part_c(b):
    b.add_body("three")
"""

EXACT_FIT_PAYLOAD = {
    "words": [
        {"word": "one", "start": 0.0, "end": 0.3},
        {"word": "two", "start": 0.3, "end": 0.6},
        {"word": "three", "start": 0.6, "end": 1.0},
    ],
}

WHISPER_SEGMENT_TABLE = [
    pytest.param(
        SAMPLE_SCRIPT,
        WHISPER_PAYLOAD,
        (
            {"start": 0.0, "end": 1.0456, "words": ["We", "factor", "step", "by"]},
            {"start": 1.0456, "end": 2.5011, "words": ["step", "to", "find", "roots"]},
        ),
        id="dense_8w_2b",
    ),
    pytest.param(
        SPARSE_SCRIPT,
        SPARSE_WHISPER_PAYLOAD,
        (
            {"start": 0.0, "end": 0.05, "words": ["hello"]},
            {"start": 0.05, "end": 0.05, "words": []},
            {"start": 0.05, "end": 0.05, "words": []},
        ),
        id="sparse_1w_3b",
    ),
    pytest.param(
        EXACT_FIT_SCRIPT,
        EXACT_FIT_PAYLOAD,
        (
            {"start": 0.0, "end": 0.3, "words": ["one"]},
            {"start": 0.3, "end": 0.6, "words": ["two"]},
            {"start": 0.6, "end": 1.0, "words": ["three"]},
        ),
        id="exact_fit_3w_3b",
    ),
]


@pytest.mark.parametrize("script,payload,expected", WHISPER_SEGMENT_TABLE)
def test_whisper_timing_blueprint_segment_table(script, payload, expected):
    """Table-driven frozen segment expectations — run twice for determinism."""
    for _ in range(2):
        blueprint = parse_whisper_timing_blueprint(script, payload)
        assert len(blueprint.segments) == len(expected)
        for segment, exp in zip(blueprint.segments, expected):
            assert segment.start_time == exp["start"]
            assert segment.end_time == exp["end"]
            assert [w["word"] for w in segment.words] == exp["words"]
            if segment.words:
                assert segment.start_time == round_ms(
                    min(float(w["start"]) for w in segment.words)
                )
                assert segment.end_time == round_ms(
                    max(float(w["end"]) for w in segment.words)
                )


def test_parse_whisper_timing_blueprint_sorts_out_of_order_payload():
    script = """# ---DIV: A---
def part_a(b):
    b.add_body("first")
# ---DIV: B---
def part_b(b):
    b.add_body("second")
"""
    payload = {
        "words": [
            {"word": "second", "start": 1.0, "end": 1.5},
            {"word": "first", "start": 0.0, "end": 0.5},
        ],
    }
    blueprint = parse_whisper_timing_blueprint(script, payload)
    transcript = whisper_transcript_from_payload(payload)
    assert blueprint.segments[0].start_time == 0.0
    assert blueprint.segments[0].end_time == 0.5
    assert blueprint.segments[1].start_time == 1.0
    assert blueprint.segments[1].end_time == 1.5
    assert [w["word"] for w in blueprint.segments[0].words] == ["first"]
    assert blueprint.total_duration == expected_audio_total_duration(transcript)
    assert blueprint.total_duration == round_ms(1.5 + PADDING_TAIL)
    assert blueprint.total_duration >= blueprint.segments[-1].end_time


def test_parse_whisper_timing_blueprint_non_monotonic_word_ends_use_max_in_slice():
    """Slice bounds use min(start)/max(end), not list-order first/last."""
    script = """# ---DIV: Only---
def part_only(b):
    b.add_body("mixed timing words")
"""
    payload = {
        "words": [
            {"word": "alpha", "start": 0.0, "end": 1.0},
            {"word": "beta", "start": 0.5, "end": 0.8},
        ],
    }
    blueprint = parse_whisper_timing_blueprint(script, payload)
    segment = blueprint.segments[0]
    assert segment.start_time == 0.0
    assert segment.end_time == 1.0
    assert segment.wait_duration == 1.0
    for word in segment.words:
        assert segment.start_time <= round_ms(float(word["start"]))
        assert round_ms(float(word["end"])) <= segment.end_time


def test_parse_whisper_blueprint_sparse_words_no_duplication_monotonic():
    """Fewer whisper words than DIV blocks must not duplicate tokens or overlap."""
    blueprint = parse_whisper_timing_blueprint(SPARSE_SCRIPT, SPARSE_WHISPER_PAYLOAD)
    transcript = whisper_transcript_from_payload(SPARSE_WHISPER_PAYLOAD)

    assert blueprint.segment_count == 3
    attached = [w["word"] for s in blueprint.segments for w in s.words]
    assert attached == [w.word for w in transcript.words]
    assert sum(1 for s in blueprint.segments if s.words) == 1
    assert blueprint.segments[0].words
    assert not blueprint.segments[1].words
    assert not blueprint.segments[2].words

    assert blueprint.segments[0].start_time == round_ms(0.0)
    assert blueprint.segments[0].end_time == round_ms(0.05)
    assert blueprint.segments[0].wait_duration == round_ms(0.05)
    assert blueprint.segments[1].wait_duration == 0.0
    assert blueprint.segments[2].wait_duration == 0.0
    for segment in blueprint.segments:
        if segment.words:
            assert segment.start_time < segment.end_time
            for word in segment.words:
                assert segment.start_time <= round_ms(float(word["start"]))
                assert round_ms(float(word["end"])) <= segment.end_time
    for prev, nxt in zip(blueprint.segments, blueprint.segments[1:]):
        assert nxt.start_time >= prev.end_time - 1e-4

    assert blueprint.total_duration == expected_audio_total_duration(transcript)


def test_parse_whisper_blueprint_wait_anchors_match_segments():
    blueprint = parse_whisper_timing_blueprint(SAMPLE_SCRIPT, WHISPER_PAYLOAD)
    artifacts = build_decoupled_artifacts(SAMPLE_SCRIPT, blueprint)
    anchor_by_block = {a.block_id: a.duration for a in artifacts.scenes.wait_anchors}
    for segment in blueprint.segments:
        assert anchor_by_block[segment.block_id] == segment.wait_duration


def test_instantiate_timing_blueprint_dispatches_by_mode():
    audio = instantiate_timing_blueprint(SAMPLE_SCRIPT, ProcessingMode.AUDIO)
    mute = instantiate_timing_blueprint(SAMPLE_SCRIPT, ProcessingMode.MUTE)
    assert audio.mode is ProcessingMode.AUDIO
    assert mute.mode is ProcessingMode.MUTE
    assert audio.script_fingerprint == mute.script_fingerprint


def test_director_stub_varies_content_by_topic():
    quadratic = stub_director_agent("Explain quadratic roots and factoring", ProcessingMode.MUTE)
    integral = stub_director_agent("Compute the integral area under the curve", ProcessingMode.MUTE)
    assert quadratic.script != integral.script
    assert quadratic.div_markers != integral.div_markers
    assert "integral" in integral.script.lower() or "\\int" in integral.script
    assert "x^2 - 5x" in quadratic.script or "parabola" in quadratic.script.lower()


def test_lifecycle_audio_mode_completes_all_phases(tmp_path: Path):
    result = run_lifecycle(
        tmp_path / "audio_project",
        "Explain quadratic formula",
        ProcessingMode.AUDIO,
        model_tier=ModelTier.ELITE,
    )
    session = result.session
    assert session.current_phase is Phase.POST_PRODUCTION
    tts = stub_tts(result.session.director_output.script)  # type: ignore[union-attr]
    transcript = stub_whisper_json(tts, result.session.director_output.script)  # type: ignore[union-attr]
    assert result.blueprint.total_duration == expected_audio_total_duration(transcript)
    assert result.blueprint.segment_count == len(result.session.director_output.div_markers)  # type: ignore[union-attr]
    assert result.artifacts.scenes.wait_anchors
    assert result.artifacts.assets.latex_strings
    math_calls = [c for c in result.artifacts.scenes.builder_calls if c.get("method") == "add_math"]
    assert math_calls
    assert all("content_ref" in c or "latex_ref" in c for c in math_calls)
    assert result.post_production.audio_track_attached is True


def test_lifecycle_mute_mode_completes_with_beat_cadence(tmp_path: Path):
    result = run_lifecycle(
        tmp_path / "mute_project",
        "Explain quadratic formula",
        ProcessingMode.MUTE,
        model_tier=ModelTier.STANDARD,
    )
    assert result.blueprint.mode is ProcessingMode.MUTE
    assert result.blueprint.total_duration == expected_mute_total_duration(result.blueprint.segments)
    waits = [a.duration for a in result.artifacts.scenes.wait_anchors]
    assert len(waits) == result.blueprint.segment_count
    assert result.post_production.ambient_track_attached is True
    assert result.post_production.audio_track_attached is False


def test_writer_patch_apply_exact_unique_match():
    content = "alpha\nbeta\ngamma\n"
    result = apply_patch(content, "beta\n", "BETA\n")
    assert result == "alpha\nBETA\ngamma\n"


def test_writer_patch_not_found_raises():
    with pytest.raises(PatchNotFoundError, match="SEARCH block did not match"):
        apply_patch("hello", "missing", "x")


def test_writer_patch_ambiguous_raises():
    with pytest.raises(PatchAmbiguousError, match="AMBIGUOUS_PATCH"):
        apply_patch("dup\ndup\n", "dup\n", "x\n")


def test_writer_parse_patch_blocks_roundtrip():
    doc = (
        "<<<<<<< SEARCH\n"
        "old line\n"
        "=======\n"
        "new line\n"
        ">>>>>>> REPLACE\n"
    )
    blocks = parse_patch_blocks(doc)
    assert len(blocks) == 1
    assert blocks[0].search == "old line\n"
    assert blocks[0].replace == "new line\n"


def test_writer_emits_search_replace_patch_documents(tmp_path: Path):
    blueprint = build_mute_blueprint(SAMPLE_SCRIPT)
    result = write_decoupled_project(tmp_path, SAMPLE_SCRIPT, blueprint)
    assert SEARCH_MARKER in result.patch_documents["scenes.py"]
    assert SEARCH_MARKER in result.patch_documents["assets.py"]
    assert result.patch_documents["scenes.py"].count(SEARCH_MARKER) == 3
    assert result.patch_documents["assets.py"].count(SEARCH_MARKER) == 1


def test_writer_applies_patches_incrementally_on_disk(tmp_path: Path, monkeypatch):
    blueprint = build_mute_blueprint(SAMPLE_SCRIPT)
    calls: list[str] = []
    original = apply_patches_on_disk

    def track(path, blocks):
        calls.append(path.name)
        return original(path, blocks)

    monkeypatch.setattr(
        "matemium.agent.writer.apply_patches_on_disk",
        track,
    )
    write_decoupled_project(tmp_path, SAMPLE_SCRIPT, blueprint)
    assert calls == ["assets.py", "scenes.py"]


def test_writer_decoupled_project_writes_files_with_waits(tmp_path: Path):
    blueprint = parse_whisper_timing_blueprint(SAMPLE_SCRIPT, WHISPER_PAYLOAD)
    result = write_decoupled_project(tmp_path, SAMPLE_SCRIPT, blueprint)

    scenes_path = tmp_path / "scenes.py"
    assets_path = tmp_path / "assets.py"
    assert scenes_path.is_file()
    assert assets_path.is_file()
    assert result.patches_applied == 4
    assert format_patch_document([]) == ""

    scenes = scenes_path.read_text(encoding="utf-8")
    assets = assets_path.read_text(encoding="utf-8")

    for segment in blueprint.segments:
        assert f"b.wait(duration={segment.wait_duration})" in scenes

    assert "import assets" in scenes
    assert "class AgentScene" in scenes
    assert "assets.latex_" in scenes
    assert "add_heading" not in assets
    assert "def latex_" in assets
    assert "def surface_" in assets

    compile(scenes, "scenes.py", "exec")
    compile(assets, "assets.py", "exec")
    with workspace_context(tmp_path):
        module = load_scenes_module(tmp_path)
        assert hasattr(module, "AgentScene")


def test_writer_decoupled_output_is_deterministic(tmp_path: Path):
    blueprint = build_mute_blueprint(SAMPLE_SCRIPT)
    project_a = tmp_path / "a"
    project_b = tmp_path / "b"
    write_decoupled_project(project_a, SAMPLE_SCRIPT, blueprint)
    write_decoupled_project(project_b, SAMPLE_SCRIPT, blueprint)
    assert (project_a / "scenes.py").read_text() == (project_b / "scenes.py").read_text()
    assert (project_a / "assets.py").read_text() == (project_b / "assets.py").read_text()


def test_lifecycle_engineer_writes_scenes_and_assets_on_disk(tmp_path: Path):
    result = run_lifecycle(tmp_path / "disk_project", "Factor quadratics", ProcessingMode.MUTE)
    assert (tmp_path / "disk_project" / "scenes.py").is_file()
    assert (tmp_path / "disk_project" / "assets.py").is_file()
    scenes = (tmp_path / "disk_project" / "scenes.py").read_text(encoding="utf-8")
    for segment in result.blueprint.segments:
        assert f"b.wait(duration={segment.wait_duration})" in scenes


def test_decoupled_artifacts_separate_math_from_narrative(tmp_path: Path):
    result = run_lifecycle(tmp_path / "decouple", "Factor quadratics", ProcessingMode.MUTE)
    scenes = result.artifacts.scenes
    assets = result.artifacts.assets
    assert scenes.div_markers
    assert scenes.part_functions
    assert assets.latex_strings
    assert assets.computations
    assert assets.mesh_definitions
    for call in scenes.builder_calls:
        if call.get("method") == "add_math":
            assert "content_ref" in call or "latex_ref" in call


def test_token_ledger_applies_tier_multipliers(tmp_path: Path):
    result = run_lifecycle(
        tmp_path / "tokens",
        "Quadratic roots",
        ProcessingMode.AUDIO,
        model_tier=ModelTier.DEEP,
    )
    ledger = result.token_ledger
    assert ledger.total_charged > 0
    for entry in ledger.entries:
        assert entry.charged_tokens == entry.base_tokens * TIER_MULTIPLIERS[entry.tier]
    assert all(e.multiplier == 12 for e in ledger.entries)
    phases_charged = {e.phase for e in ledger.entries}
    assert Phase.CRITIC in phases_charged
    assert Phase.POST_PRODUCTION in phases_charged


REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_SCENES = REPO_ROOT / "projects" / "demo" / "scenes.py"
SIDECAR_AVAILABLE = sidecar_binary_available()
requires_sidecar = pytest.mark.skipif(
    not SIDECAR_AVAILABLE,
    reason="dist/matemium-sidecar not built",
)


def test_compile_outcome_ensures_non_empty_error_on_failure():
    result = SidecarIpcResult(responses=({"ok": False, "error": {}},), stderr="", returncode=1)
    ok, err = compile_outcome_from_sidecar(result)
    assert ok is False
    assert err.strip()
    assert err == "sidecar exited with code 1"


def test_run_sidecar_ipc_timeout_returns_failure(monkeypatch):
    def raise_timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="matemium-sidecar", timeout=1)

    monkeypatch.setattr("matemium.agent.critic.subprocess.run", raise_timeout)
    monkeypatch.setattr("matemium.agent.critic.sidecar_binary_path", lambda: Path("/fake/sidecar"))
    result = run_sidecar_ipc([("ping", "ping", {})], timeout=1)
    ok, err = compile_outcome_from_sidecar(result)
    assert ok is False
    assert "timed out" in err


def test_compile_project_when_sidecar_binary_absent(tmp_path: Path, monkeypatch):
    """Uses real sidecar_binary_path resolution against a root with no dist/ binary."""
    fake_root = tmp_path / "no_sidecar_root"
    fake_root.mkdir()
    ws = fake_root / "ws"
    ws.mkdir()
    (ws / "scenes.py").write_text("pass\n", encoding="utf-8")
    monkeypatch.setattr("matemium.agent.critic.discover_root", lambda: fake_root)
    assert sidecar_binary_available() is False

    ok, err = compile_project_via_sidecar(ws)
    assert ok is False
    assert "PyInstaller sidecar not found" in err
    assert str(fake_root / "dist" / "matemium-sidecar") in err

    ok_fn, err_fn = make_sidecar_compile_fn(ws)()
    assert ok_fn is False
    assert "PyInstaller sidecar not found" in err_fn


LIST_SYNTAX_TRACEBACK = (
    '  File "/tmp/ws/scenes.py", line 1\n'
    "    def broken(\n"
    "              ^\n"
    "SyntaxError: '(' was never closed\n"
)

OUTCOME_TABLE = [
    pytest.param(
        ipc_failure_result("PyInstaller sidecar not found at /missing/matemium-sidecar"),
        False,
        ("PyInstaller sidecar not found",),
        id="missing_binary",
    ),
    pytest.param(
        ipc_failure_result("sidecar subprocess timed out after 30s"),
        False,
        ("timed out",),
        id="timeout",
    ),
    pytest.param(
        SidecarIpcResult(responses=(), stderr="", returncode=0),
        False,
        ("sidecar produced no responses",),
        id="empty_responses",
    ),
    pytest.param(
        SidecarIpcResult(
            responses=(
                {
                    "ok": False,
                    "error": {
                        "message": "'(' was never closed",
                        "traceback": LIST_SYNTAX_TRACEBACK,
                    },
                },
            ),
            stderr="",
            returncode=0,
        ),
        False,
        ("SyntaxError", "^"),
        id="list_syntax_fail",
    ),
    pytest.param(
        SidecarIpcResult(
            responses=(
                {
                    "ok": True,
                    "result": {
                        "ok": False,
                        "errors": [
                            {
                                "message": "'CanvasBuilder' object has no attribute 'wait'",
                            }
                        ],
                    },
                },
            ),
            stderr="",
            returncode=0,
        ),
        False,
        ("has no attribute",),
        id="check_attr_fail",
    ),
    pytest.param(
        merge_ipc_results(
            SidecarIpcResult(
                responses=(
                    {
                        "ok": False,
                        "error": {"message": "short", "traceback": LIST_SYNTAX_TRACEBACK},
                    },
                ),
                stderr="",
                returncode=0,
            ),
            SidecarIpcResult(
                responses=(
                    {
                        "ok": True,
                        "result": {
                            "ok": False,
                            "errors": [{"message": LIST_SYNTAX_TRACEBACK}],
                        },
                    },
                ),
                stderr="",
                returncode=0,
            ),
        ),
        False,
        ("SyntaxError", "^"),
        id="merged_list_check",
    ),
    pytest.param(
        SidecarIpcResult(
            responses=({"ok": True, "result": {"ok": True, "scene": "PortraitDemo"}},),
            stderr="",
            returncode=0,
        ),
        True,
        (),
        id="success",
    ),
]


@pytest.mark.parametrize("result,expected_ok,must_contain", OUTCOME_TABLE)
def test_compile_outcome_table(result, expected_ok, must_contain):
    ok, err = compile_outcome_from_sidecar(result)
    assert ok is expected_ok
    if expected_ok:
        assert err == ""
    else:
        assert err.strip()
        for token in must_contain:
            assert token in err


def test_format_compile_error_extracts_syntax_message():
    responses = (
        {
            "ok": True,
            "result": {
                "ok": False,
                "errors": [{"message": "SyntaxError: invalid syntax"}],
            },
        },
    )
    text = format_compile_error(responses, "")
    assert "SyntaxError" in text
    assert contains_python_or_manim_error(text)


@requires_sidecar
def test_sidecar_compile_good_demo_workspace(tmp_path: Path):
    import shutil

    ws = tmp_path / "good"
    ws.mkdir()
    shutil.copy(DEMO_SCENES, ws / "scenes.py")
    ok, stderr = compile_project_via_sidecar(ws, scene="PortraitDemo")
    assert ok is True
    assert stderr == ""
    assert not contains_python_or_manim_error(stderr)


@requires_sidecar
def test_sidecar_compile_syntax_error_workspace(tmp_path: Path):
    ws = tmp_path / "broken_py"
    ws.mkdir()
    (ws / "scenes.py").write_text("def broken(\n", encoding="utf-8")
    ok, stderr = compile_project_via_sidecar(ws)
    assert ok is False
    assert "SyntaxError" in stderr
    assert "File" in stderr
    assert "^" in stderr
    assert contains_python_or_manim_error(stderr)


@requires_sidecar
def test_critic_loop_feeds_patch_fn_from_sidecar_errors(tmp_path: Path):
    ws = tmp_path / "patch_feed"
    ws.mkdir()
    (ws / "scenes.py").write_text("def broken(\n", encoding="utf-8")
    session = ProjectSession(project_dir=ws, user_prompt="broken", model_tier=ModelTier.STANDARD)
    session.director_output = stub_director_agent("broken", ProcessingMode.MUTE)
    session.blueprint = build_mute_blueprint(session.director_output.script)
    session.record_transition(Phase.CRITIC, ("scenes_config",))

    patches: list[str] = []

    def track_patch(stderr: str) -> None:
        patches.append(stderr)

    hooks = CriticHooks(
        compile_fn=make_sidecar_compile_fn(ws),
        patch_fn=track_patch,
    )
    with pytest.raises(CoordinatorHaltError):
        run_critic_loop(session, hooks)

    assert len(patches) == MAX_CRITIC_RETRIES - 1
    assert all(contains_python_or_manim_error(p) for p in patches)
    debug = json.loads((ws / DEBUG_FILENAME).read_text(encoding="utf-8"))
    assert debug["retry_count"] == MAX_CRITIC_RETRIES
    assert contains_python_or_manim_error(debug["error"])


@requires_sidecar
def test_sidecar_ipc_spawns_binary():
    result = run_sidecar_ipc([("ping", "ping", {})], timeout=30)
    assert result.returncode == 0
    assert result.responses
    assert result.responses[-1]["ok"] is True


@requires_sidecar
def test_critic_verification_bundle(tmp_path: Path, monkeypatch):
    """Atomic verification: scenarios + scratch artifact emission in one pytest run."""
    scratch = tmp_path / "scratch_bundle"
    monkeypatch.setenv("MATEMIUM_SCRATCH", str(scratch))
    out = emit_scratch_artifacts(scratch)
    assert (out / "critic_consumer.log").is_file()
    assert (out / "critic_source_read.log").is_file()
    assert (out / "critic_launch.log").is_file()
    assert (out / "critic_exhaust.log").is_file()
    consumer = (out / "critic_consumer.log").read_text(encoding="utf-8")
    assert "CONSUMER_PASS" in consumer
    assert "good stderr repr: ''" in consumer
    source = (out / "critic_source_read.log").read_text(encoding="utf-8")
    assert "merge_ipc_results" in source
    assert "richest_error_text" in source or "compile_outcome_from_sidecar" in source
    launch = (out / "critic_launch.log").read_text(encoding="utf-8")
    assert "LAUNCH_OK" in launch
    assert "launch listing:" in launch


def test_critic_failure_writes_debug_and_halts(tmp_path: Path):
    project_dir = tmp_path / "fail_project"
    attempts = {"count": 0}

    def always_fail() -> tuple[bool, str]:
        attempts["count"] += 1
        return False, "SyntaxError: invalid syntax in scenes.py line 42"

    config = CoordinatorConfig(compile_fn=always_fail)
    coordinator = LifecycleCoordinator(project_dir, config=config)

    with pytest.raises(CoordinatorHaltError) as exc_info:
        coordinator.run("Broken compile scenario", ProcessingMode.MUTE)

    assert attempts["count"] == MAX_CRITIC_RETRIES
    assert exc_info.value.debug_path is not None
    debug_path = project_dir / DEBUG_FILENAME
    assert debug_path.is_file()
    payload = json.loads(debug_path.read_text(encoding="utf-8"))
    assert payload["phase"] == Phase.CRITIC.value
    assert payload["retry_count"] == MAX_CRITIC_RETRIES
    assert "SyntaxError" in payload["error"]
    assert payload["error_trace"]
    assert payload["script_excerpt"]
    assert payload["blueprint_snapshot"]
    assert payload["halted"] is True
    critic_entries = [e for e in payload["token_ledger"]["entries"] if e["phase"] == "critic"]
    assert critic_entries
    assert critic_entries[0]["charged_tokens"] > 0


def test_critic_halt_skips_post_production(tmp_path: Path):
    config = CoordinatorConfig(compile_fn=lambda: (False, "compile error"))
    coordinator = LifecycleCoordinator(tmp_path / "halt", config=config)
    with pytest.raises(CoordinatorHaltError):
        coordinator.run("Halt test", ProcessingMode.AUDIO)
    debug = json.loads((tmp_path / "halt" / DEBUG_FILENAME).read_text(encoding="utf-8"))
    assert debug["phase"] == "critic"
    transition_targets = [t["to_phase"] for t in debug["transitions"]]
    assert Phase.POST_PRODUCTION.value not in transition_targets


def test_visual_qc_failure_retries_and_halts(tmp_path: Path):
    project_dir = tmp_path / "visual_fail"
    attempts = {"compile": 0, "visual": 0, "patch": 0}

    def compile_ok() -> tuple[bool, str]:
        attempts["compile"] += 1
        return True, ""

    def visual_fail() -> bool:
        attempts["visual"] += 1
        return False

    def track_patch(_stderr: str) -> None:
        attempts["patch"] += 1

    config = CoordinatorConfig(
        compile_fn=compile_ok,
        visual_qc_fn=visual_fail,
        patch_fn=track_patch,
    )
    coordinator = LifecycleCoordinator(project_dir, config=config)
    with pytest.raises(CoordinatorHaltError):
        coordinator.run("Visual QC stress", ProcessingMode.MUTE)

    assert attempts["compile"] == MAX_CRITIC_RETRIES
    assert attempts["visual"] == MAX_CRITIC_RETRIES
    assert attempts["patch"] == MAX_CRITIC_RETRIES - 1
    payload = json.loads((project_dir / DEBUG_FILENAME).read_text(encoding="utf-8"))
    assert VISUAL_QC_FAILURE in payload["error"]


def test_coordinator_phase_transitions_are_clean_sequence(tmp_path: Path):
    coordinator = LifecycleCoordinator(tmp_path / "transitions")
    session = coordinator.run("Phase trace", ProcessingMode.MUTE).session
    ordered = [t.to_phase for t in session.transitions]
    assert ordered == [
        Phase.TIMING_BLUEPRINT,
        Phase.ENGINEER,
        Phase.CRITIC,
        Phase.POST_PRODUCTION,
    ]
    assert session.current_phase is Phase.POST_PRODUCTION