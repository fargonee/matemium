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
from .models import ModelTier, Phase, ProcessingMode, ProjectSession
from .separation import build_decoupled_artifacts
from .stubs import stub_director_agent
from .timing import build_mute_blueprint

DEFAULT_SCRATCH = Path("/tmp/grok-goal-14c0d5b9ab35/implementer")
DEMO_SCENES = discover_root() / "projects" / "demo" / "scenes.py"
CRITIC_SOURCE = discover_root() / "matemium" / "agent" / "critic.py"


def scratch_dir() -> Path:
    raw = os.environ.get("MATEMIUM_SCRATCH", str(DEFAULT_SCRATCH))
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


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