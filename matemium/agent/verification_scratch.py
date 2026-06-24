"""Atomic scratch artifact emission for critic verification."""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from matemium.paths import discover_root

from .coordinator import CoordinatorConfig, run_lifecycle
from .critic import (
    CriticHooks,
    CoordinatorHaltError,
    MAX_CRITIC_RETRIES,
    compile_project_via_sidecar,
    make_sidecar_compile_fn,
    run_critic_loop,
    sidecar_binary_available,
)
from .debug import DEBUG_FILENAME
from .guard import (
    WATERMARK_MARKER,
    apply_guard_to_scenes_file,
    dsl_has_watermark,
    should_apply_watermark_for_session,
)
from .models import AccountTier, ModelTier, Phase, ProcessingMode, ProjectSession
from .writer import write_decoupled_project
from .separation import build_decoupled_artifacts
from .stubs import stub_director_agent
from .timing import build_mute_blueprint

DEFAULT_SCRATCH = Path("/tmp/grok-goal-8ed96c922e01/implementer")
DEMO_SCENES = discover_root() / "projects" / "demo" / "scenes.py"
CRITIC_SOURCE = discover_root() / "matemium" / "agent" / "critic.py"
GUARD_SOURCE = discover_root() / "matemium" / "agent" / "guard.py"


def scratch_dir() -> Path:
    raw = os.environ.get("MATEMIUM_SCRATCH", str(DEFAULT_SCRATCH))
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _capture_guard_source_read() -> str:
    head = GUARD_SOURCE.read_text(encoding="utf-8").splitlines()[:100]
    out = ["=== guard.py head ===", *head, "", "=== grep key symbols ==="]
    proc = subprocess.run(
        [
            "grep",
            "-n",
            "-E",
            r"(should_apply_watermark|inject_watermark|WATERMARK|apply_guard|AccountTier)",
            str(GUARD_SOURCE),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    out.append(proc.stdout or proc.stderr or "(no grep output)")
    return "\n".join(out)


def _capture_source_read() -> str:
    head = CRITIC_SOURCE.read_text(encoding="utf-8").splitlines()[:100]
    out = ["=== critic.py head ===", *head, "", "=== grep key symbols ==="]
    proc = subprocess.run(
        [
            "grep",
            "-n",
            "-E",
            r"(sidecar|subprocess|stderr|compile|ipc_failure_result|merge_ipc_results|"
            r"compile_outcome_from_sidecar|TimeoutExpired|patch_fn|run_sidecar_ipc)",
            str(CRITIC_SOURCE),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    out.append(proc.stdout or proc.stderr or "(no grep output)")
    out.append("")
    outcome_source = discover_root() / "matemium" / "agent" / "sidecar_outcome.py"
    out.append("=== sidecar_outcome.py grep ===")
    proc2 = subprocess.run(
        ["grep", "-n", "-E", r"(richest|collect_error|compile_outcome|ipc_failure)", str(outcome_source)],
        capture_output=True,
        text=True,
        check=False,
    )
    out.append(proc2.stdout or proc2.stderr or "(no grep output)")
    return "\n".join(out)


def _run_consumer_scenarios(base: Path, log: io.StringIO) -> dict[str, str]:
    """Drive good/broken/exhaust paths; return content hashes."""
    if not sidecar_binary_available():
        log.write("SIDECAR_MISSING: dist/matemium-sidecar not built\n")
        return {}

    def writeln(msg: str = "") -> None:
        log.write(msg + "\n")

    writeln(f"=== consumer pid={os.getpid()} ===")

    good = base / "good"
    good.mkdir(parents=True, exist_ok=True)
    shutil.copy(DEMO_SCENES, good / "scenes.py")
    writeln(f"good listing: {sorted(p.name for p in good.iterdir())}")

    ok, stderr = compile_project_via_sidecar(good, scene="PortraitDemo")
    writeln(f"good compile ok: {ok}")
    writeln(f"good stderr repr: {repr(stderr)}")
    assert ok and stderr == ""

    session = ProjectSession(project_dir=good, user_prompt="demo", model_tier=ModelTier.STANDARD)
    session.record_transition(Phase.CRITIC, ("scenes_config",))
    critic = run_critic_loop(
        session,
        CriticHooks(
            compile_fn=make_sidecar_compile_fn(good, scene="PortraitDemo"),
            patch_fn=lambda _e: None,
        ),
    )
    writeln(f"good critic: {critic}")
    assert critic.passed and not (good / DEBUG_FILENAME).exists()

    broken_py = base / "broken_py"
    broken_py.mkdir(parents=True, exist_ok=True)
    (broken_py / "scenes.py").write_text("def broken(\n", encoding="utf-8")
    ok_py, err_py = compile_project_via_sidecar(broken_py)
    writeln(f"broken_py ok: {ok_py}")
    writeln(f"broken_py error excerpt: {err_py[:200]}...")
    assert not ok_py and "SyntaxError" in err_py

    patches: list[str] = []
    session_py = ProjectSession(project_dir=broken_py, user_prompt="broken", model_tier=ModelTier.STANDARD)
    session_py.director_output = stub_director_agent("broken", ProcessingMode.MUTE)
    session_py.blueprint = build_mute_blueprint(session_py.director_output.script)
    session_py.record_transition(Phase.CRITIC, ("scenes_config",))
    try:
        run_critic_loop(
            session_py,
            CriticHooks(compile_fn=make_sidecar_compile_fn(broken_py), patch_fn=patches.append),
        )
    except CoordinatorHaltError as exc:
        writeln(f"broken_py halt: {exc!r}")
    assert len(patches) == MAX_CRITIC_RETRIES - 1

    broken_manim = base / "broken_manim"
    broken_manim.mkdir(parents=True, exist_ok=True)
    (broken_manim / "scenes.py").write_text(
        "from canvas import CanvasScene\nfrom canvas.builder import CanvasBuilder\n\n"
        "class BadScene(CanvasScene):\n"
        "    def __init__(self, **kwargs):\n"
        "        builder = CanvasBuilder(title='Bad')\n"
        "        builder.wait(duration=1.0)\n"
        "        super().__init__(dsl=builder.build(), **kwargs)\n",
        encoding="utf-8",
    )
    ok_m, err_m = compile_project_via_sidecar(broken_manim)
    writeln(f"broken_manim ok: {ok_m}")
    writeln(f"broken_manim error: {err_m}")
    assert not ok_m

    exhaust = base / "exhaust"
    exhaust.mkdir(parents=True, exist_ok=True)
    (exhaust / "scenes.py").write_text("def broken(\n", encoding="utf-8")
    session_ex = ProjectSession(project_dir=exhaust, user_prompt="exhaust", model_tier=ModelTier.STANDARD)
    session_ex.director_output = stub_director_agent("exhaust", ProcessingMode.MUTE)
    session_ex.blueprint = build_mute_blueprint(session_ex.director_output.script)
    session_ex.record_transition(Phase.CRITIC, ("scenes_config",))
    exhaust_exc: CoordinatorHaltError | None = None
    try:
        run_critic_loop(
            session_ex,
            CriticHooks(compile_fn=make_sidecar_compile_fn(exhaust), patch_fn=lambda _e: None),
        )
    except CoordinatorHaltError as exc:
        exhaust_exc = exc
    assert exhaust_exc is not None
    debug = json.loads((exhaust / DEBUG_FILENAME).read_text(encoding="utf-8"))
    writeln(f"exhaust exception: {exhaust_exc!r}")
    writeln(f"exhaust debug json: {json.dumps(debug, indent=2)}")
    writeln("CONSUMER_PASS")
    return {
        "good_scenes": _sha(good / "scenes.py"),
        "broken_py": _sha(broken_py / "scenes.py"),
    }


def _sha(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_guard_consumer_scenarios(base: Path, log: io.StringIO) -> dict[str, str]:
    """Exercise guard tier decisions, writer emission, DSL inspection, and compile."""
    from matemium.workspace_project import instantiate_scene, workspace_context

    def writeln(msg: str = "") -> None:
        log.write(msg + "\n")

    writeln(f"=== guard consumer pid={os.getpid()} ===")

    blueprint = build_mute_blueprint(stub_director_agent("guard", ProcessingMode.MUTE).script)
    basic_script = stub_director_agent("guard", ProcessingMode.MUTE).script

    writer_dir = base / "writer_basic"
    writer_dir.mkdir(parents=True, exist_ok=True)
    writer_session = ProjectSession(
        project_dir=writer_dir,
        user_prompt="guard writer",
        model_tier=ModelTier.STANDARD,
        account_tier=AccountTier.BASIC,
    )
    write_decoupled_project(writer_dir, basic_script, blueprint, session=writer_session)
    writer_scenes = (writer_dir / "scenes.py").read_text(encoding="utf-8")
    writeln(f"writer basic has watermark: {WATERMARK_MARKER in writer_scenes}")
    assert WATERMARK_MARKER in writer_scenes

    basic_dir = base / "basic_unpaid"
    basic_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(DEMO_SCENES, basic_dir / "scenes.py")
    basic_session = ProjectSession(
        project_dir=basic_dir,
        user_prompt="guard basic",
        model_tier=ModelTier.STANDARD,
        account_tier=AccountTier.BASIC,
    )
    apply_guard_to_scenes_file(basic_dir / "scenes.py", basic_session)
    basic_scenes = (basic_dir / "scenes.py").read_text(encoding="utf-8")
    writeln(f"basic decision: {should_apply_watermark_for_session(basic_session)}")
    writeln(f"basic scenes has watermark: {WATERMARK_MARKER in basic_scenes}")
    assert should_apply_watermark_for_session(basic_session)
    assert WATERMARK_MARKER in basic_scenes

    premium_dir = base / "premium_clean"
    premium_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(DEMO_SCENES, premium_dir / "scenes.py")
    premium_session = ProjectSession(
        project_dir=premium_dir,
        user_prompt="guard premium",
        model_tier=ModelTier.STANDARD,
        account_tier=AccountTier.PREMIUM,
    )
    apply_guard_to_scenes_file(premium_dir / "scenes.py", premium_session)
    premium_scenes = (premium_dir / "scenes.py").read_text(encoding="utf-8")
    writeln(f"premium decision: {should_apply_watermark_for_session(premium_session)}")
    writeln(f"premium scenes has watermark: {WATERMARK_MARKER in premium_scenes}")
    assert not should_apply_watermark_for_session(premium_session)
    assert WATERMARK_MARKER not in premium_scenes

    paid_dir = base / "basic_paid_removal"
    paid_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(DEMO_SCENES, paid_dir / "scenes.py")
    paid_session = ProjectSession(
        project_dir=paid_dir,
        user_prompt="guard paid",
        model_tier=ModelTier.STANDARD,
        account_tier=AccountTier.BASIC,
        watermark_removal_paid=True,
    )
    apply_guard_to_scenes_file(paid_dir / "scenes.py", paid_session)
    paid_scenes = (paid_dir / "scenes.py").read_text(encoding="utf-8")
    writeln(f"paid removal decision: {should_apply_watermark_for_session(paid_session)}")
    assert not should_apply_watermark_for_session(paid_session)
    assert WATERMARK_MARKER not in paid_scenes

    with workspace_context(basic_dir):
        basic_instance = instantiate_scene(basic_dir, "PortraitDemo")
        writeln(f"basic dsl watermark: {dsl_has_watermark(basic_instance.dsl)}")
        assert dsl_has_watermark(basic_instance.dsl)

    with workspace_context(premium_dir):
        premium_instance = instantiate_scene(premium_dir, "PortraitDemo")
        writeln(f"premium dsl watermark: {dsl_has_watermark(premium_instance.dsl)}")
        assert not dsl_has_watermark(premium_instance.dsl)

    if sidecar_binary_available():
        ok_basic, err_basic = compile_project_via_sidecar(basic_dir, scene="PortraitDemo")
        ok_premium, err_premium = compile_project_via_sidecar(premium_dir, scene="PortraitDemo")
        writeln(f"basic compile ok: {ok_basic}")
        writeln(f"premium compile ok: {ok_premium}")
        writeln(f"basic compile err: {repr(err_basic)}")
        writeln(f"premium compile err: {repr(err_premium)}")
        assert ok_basic and ok_premium
    else:
        writeln("SIDECAR_MISSING: compile skipped")

    writeln("GUARD_CONSUMER_PASS")
    return {
        "basic_scenes": _sha(basic_dir / "scenes.py"),
        "premium_scenes": _sha(premium_dir / "scenes.py"),
        "paid_scenes": _sha(paid_dir / "scenes.py"),
        "writer_scenes": _sha(writer_dir / "scenes.py"),
    }


def _run_guard_launch_capture(scratch: Path, log: io.StringIO) -> None:
    project = scratch / "guard_launch_project"
    project.mkdir(parents=True, exist_ok=True)
    blueprint = build_mute_blueprint(stub_director_agent("launch", ProcessingMode.MUTE).script)
    script = stub_director_agent("launch", ProcessingMode.MUTE).script

    basic_session = ProjectSession(
        project_dir=project / "basic",
        user_prompt="launch basic",
        model_tier=ModelTier.STANDARD,
        account_tier=AccountTier.BASIC,
    )
    (project / "basic").mkdir(parents=True, exist_ok=True)
    write_decoupled_project(project / "basic", script, blueprint, session=basic_session)
    apply_guard_to_scenes_file(project / "basic" / "scenes.py", basic_session)
    basic_source = (project / "basic" / "scenes.py").read_text(encoding="utf-8")
    log.write(f"launch basic watermark: {WATERMARK_MARKER in basic_source}\n")

    premium_session = ProjectSession(
        project_dir=project / "premium",
        user_prompt="launch premium",
        model_tier=ModelTier.STANDARD,
        account_tier=AccountTier.PREMIUM,
    )
    (project / "premium").mkdir(parents=True, exist_ok=True)
    write_decoupled_project(project / "premium", script, blueprint, session=premium_session)
    apply_guard_to_scenes_file(project / "premium" / "scenes.py", premium_session)
    premium_source = (project / "premium" / "scenes.py").read_text(encoding="utf-8")
    log.write(f"launch premium watermark: {WATERMARK_MARKER in premium_source}\n")
    log.write("GUARD_LAUNCH_OK\n")


def _run_launch_capture(scratch: Path, log: io.StringIO) -> None:
    if not sidecar_binary_available():
        log.write("LAUNCH_SKIP: sidecar missing\n")
        return

    project = scratch / "launch_project"
    project.mkdir(parents=True, exist_ok=True)
    shutil.copy(DEMO_SCENES, project / "scenes.py")
    log.write(f"launch listing: {sorted(p.name for p in project.iterdir())}\n")

    def preserve_demo(session):
        assert session.director_output is not None
        assert session.blueprint is not None
        return build_decoupled_artifacts(session.director_output.script, session.blueprint)

    result = run_lifecycle(
        project,
        "Launch check",
        ProcessingMode.MUTE,
        config=CoordinatorConfig(use_sidecar_compile=True, engineer_fn=preserve_demo),
    )
    log.write(f"launch critic_result: {result.session.critic_result}\n")
    log.write(f"launch transitions: {[t.to_phase.value for t in result.session.transitions]}\n")
    log.write(f"launch debug absent: {not (project / DEBUG_FILENAME).exists()}\n")
    log.write("LAUNCH_OK\n")


def emit_scratch_artifacts(target: Path | None = None) -> Path:
    """Run verification scenarios and overwrite scratch log files atomically."""
    scratch = target or scratch_dir()
    scratch.mkdir(parents=True, exist_ok=True)

    consumer_log = io.StringIO()
    hashes = _run_consumer_scenarios(scratch / "bundle", consumer_log)
    (scratch / "critic_consumer.log").write_text(consumer_log.getvalue(), encoding="utf-8")

    launch_log = io.StringIO()
    _run_launch_capture(scratch, launch_log)
    (scratch / "critic_launch.log").write_text(launch_log.getvalue(), encoding="utf-8")

    exhaust_text = consumer_log.getvalue()
    exhaust_start = exhaust_text.find("exhaust exception:")
    (scratch / "critic_exhaust.log").write_text(
        exhaust_text[exhaust_start:] if exhaust_start >= 0 else exhaust_text,
        encoding="utf-8",
    )

    (scratch / "critic_source_read.log").write_text(_capture_source_read(), encoding="utf-8")

    if hashes:
        (scratch / "consumer_hashes.json").write_text(json.dumps(hashes, indent=2) + "\n", encoding="utf-8")

    return scratch


def emit_guard_scratch_artifacts(target: Path | None = None) -> Path:
    """Run guard verification scenarios and write scratch capture files."""
    scratch = target or scratch_dir()
    scratch.mkdir(parents=True, exist_ok=True)

    guard_consumer_log = io.StringIO()
    guard_hashes = _run_guard_consumer_scenarios(scratch / "guard_bundle", guard_consumer_log)
    (scratch / "guard_consumer.log").write_text(guard_consumer_log.getvalue(), encoding="utf-8")

    guard_launch_log = io.StringIO()
    _run_guard_launch_capture(scratch, guard_launch_log)
    (scratch / "guard_launch.log").write_text(guard_launch_log.getvalue(), encoding="utf-8")

    (scratch / "guard_source_read.log").write_text(_capture_guard_source_read(), encoding="utf-8")

    if guard_hashes:
        (scratch / "guard_consumer_hashes.json").write_text(
            json.dumps(guard_hashes, indent=2) + "\n",
            encoding="utf-8",
        )

    return scratch