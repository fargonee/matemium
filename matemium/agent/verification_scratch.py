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
    apply_guard_to_project,
    apply_guard_to_scenes_file,
    dsl_has_watermark,
    should_apply_watermark,
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


def _dir_listing(path: Path) -> list[str]:
    if not path.is_dir():
        return []
    return sorted(p.name for p in path.iterdir())


def _excerpt_builder_config(source: str, *, lines: int = 6) -> str:
    """Return scenes.py lines around the main-scene builder / watermark block."""
    split = source.splitlines()
    anchor_idx = -1
    for idx, line in enumerate(split):
        if WATERMARK_MARKER in line or "super().__init__(dsl=builder.build()" in line:
            anchor_idx = idx
            break
    if anchor_idx < 0:
        return "(builder config excerpt not found)"
    start = max(0, anchor_idx - lines)
    end = min(len(split), anchor_idx + lines + 1)
    return "\n".join(split[start:end])


def _append_scratch_transcript(
    path: Path,
    text: str,
    *,
    append: bool = True,
    separator: str = "\n---\n",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if append and path.is_file() and path.stat().st_size > 0:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(separator)
            handle.write(text)
    else:
        path.write_text(text, encoding="utf-8")


def _run_guard_consumer_scenarios(base: Path, log: io.StringIO) -> dict[str, str]:
    """Exercise guard tier decisions, writer emission, DSL inspection, and compile."""
    from matemium.workspace_project import instantiate_scene, workspace_context

    def writeln(msg: str = "") -> None:
        log.write(msg + "\n")

    writeln(f"=== guard consumer pid={os.getpid()} ===")

    if base.exists():
        shutil.rmtree(base)

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
    writeln(f"writer listing: {_dir_listing(writer_dir)}")
    writeln(f"writer basic has watermark: {WATERMARK_MARKER in writer_scenes}")
    writeln("writer scenes excerpt:")
    writeln(_excerpt_builder_config(writer_scenes))
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
    writeln(f"basic listing: {_dir_listing(basic_dir)}")
    writeln(f"basic decision: {should_apply_watermark_for_session(basic_session)}")
    writeln(f"basic scenes has watermark: {WATERMARK_MARKER in basic_scenes}")
    writeln("basic scenes excerpt:")
    writeln(_excerpt_builder_config(basic_scenes))
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
    writeln(f"premium listing: {_dir_listing(premium_dir)}")
    writeln(f"premium decision: {should_apply_watermark_for_session(premium_session)}")
    writeln(f"premium scenes has watermark: {WATERMARK_MARKER in premium_scenes}")
    writeln("premium scenes excerpt:")
    writeln(_excerpt_builder_config(premium_scenes))
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

    hashes = {
        "basic_scenes": _sha(basic_dir / "scenes.py"),
        "premium_scenes": _sha(premium_dir / "scenes.py"),
        "paid_scenes": _sha(paid_dir / "scenes.py"),
        "writer_scenes": _sha(writer_dir / "scenes.py"),
    }
    writeln(f"hashes: {json.dumps(hashes, indent=2)}")
    writeln("GUARD_CONSUMER_PASS")
    return hashes


def _run_guard_direct_launch(log: io.StringIO) -> None:
    """Plan step 3 — guard + writer + apply_guard_to_project + make_sidecar_compile_fn."""
    import tempfile

    def writeln(msg: str = "") -> None:
        log.write(msg + "\n")

    writeln(f"=== guard direct launch pid={os.getpid()} ===")

    script = stub_director_agent("launch", ProcessingMode.MUTE).script
    blueprint = build_mute_blueprint(script)

    writer_basic = Path(tempfile.mkdtemp(prefix="guard_launch_writer_basic_"))
    writer_premium = Path(tempfile.mkdtemp(prefix="guard_launch_writer_premium_"))
    compile_basic = Path(tempfile.mkdtemp(prefix="guard_launch_compile_basic_"))
    compile_premium = Path(tempfile.mkdtemp(prefix="guard_launch_compile_premium_"))

    basic_session = ProjectSession(
        project_dir=writer_basic,
        user_prompt="launch basic",
        model_tier=ModelTier.STANDARD,
        account_tier=AccountTier.BASIC,
    )
    premium_session = ProjectSession(
        project_dir=writer_premium,
        user_prompt="launch premium",
        model_tier=ModelTier.STANDARD,
        account_tier=AccountTier.PREMIUM,
    )

    writeln(f"should_apply_watermark basic: {should_apply_watermark(AccountTier.BASIC)}")
    writeln(f"should_apply_watermark premium: {should_apply_watermark(AccountTier.PREMIUM)}")

    write_decoupled_project(writer_basic, script, blueprint, session=basic_session)
    write_decoupled_project(writer_premium, script, blueprint, session=premium_session)
    basic_writer_source = (writer_basic / "scenes.py").read_text(encoding="utf-8")
    premium_writer_source = (writer_premium / "scenes.py").read_text(encoding="utf-8")
    writeln(f"writer basic listing: {_dir_listing(writer_basic)}")
    writeln(f"writer premium listing: {_dir_listing(writer_premium)}")
    writeln(f"writer basic watermark: {WATERMARK_MARKER in basic_writer_source}")
    writeln(f"writer premium watermark: {WATERMARK_MARKER in premium_writer_source}")
    writeln("writer basic excerpt:")
    writeln(_excerpt_builder_config(basic_writer_source))
    writeln("writer premium excerpt:")
    writeln(_excerpt_builder_config(premium_writer_source))

    shutil.copy(DEMO_SCENES, compile_basic / "scenes.py")
    shutil.copy(DEMO_SCENES, compile_premium / "scenes.py")
    compile_basic_session = ProjectSession(
        project_dir=compile_basic,
        user_prompt="compile basic",
        model_tier=ModelTier.STANDARD,
        account_tier=AccountTier.BASIC,
    )
    compile_premium_session = ProjectSession(
        project_dir=compile_premium,
        user_prompt="compile premium",
        model_tier=ModelTier.STANDARD,
        account_tier=AccountTier.PREMIUM,
    )
    apply_guard_to_project(compile_basic_session)
    apply_guard_to_project(compile_premium_session)
    compile_basic_source = (compile_basic / "scenes.py").read_text(encoding="utf-8")
    compile_premium_source = (compile_premium / "scenes.py").read_text(encoding="utf-8")
    writeln(f"compile basic listing: {_dir_listing(compile_basic)}")
    writeln(f"compile premium listing: {_dir_listing(compile_premium)}")
    writeln(f"compile basic watermark: {WATERMARK_MARKER in compile_basic_source}")
    writeln(f"compile premium watermark: {WATERMARK_MARKER in compile_premium_source}")
    writeln("compile basic excerpt:")
    writeln(_excerpt_builder_config(compile_basic_source))
    writeln("compile premium excerpt:")
    writeln(_excerpt_builder_config(compile_premium_source))

    if sidecar_binary_available():
        basic_compile_fn = make_sidecar_compile_fn(compile_basic, scene="PortraitDemo")
        premium_compile_fn = make_sidecar_compile_fn(compile_premium, scene="PortraitDemo")
        ok_basic, err_basic = basic_compile_fn()
        ok_premium, err_premium = premium_compile_fn()
        writeln(f"make_sidecar_compile_fn basic ok: {ok_basic}")
        writeln(f"make_sidecar_compile_fn premium ok: {ok_premium}")
        writeln(f"make_sidecar_compile_fn basic err: {repr(err_basic)}")
        writeln(f"make_sidecar_compile_fn premium err: {repr(err_premium)}")
        assert ok_basic and ok_premium
    else:
        writeln("SIDECAR_MISSING: make_sidecar_compile_fn compile skipped")

    assert WATERMARK_MARKER in basic_writer_source
    assert WATERMARK_MARKER not in premium_writer_source
    assert WATERMARK_MARKER in compile_basic_source
    assert WATERMARK_MARKER not in compile_premium_source
    writeln("GUARD_LAUNCH_OK")


def run_standalone_guard_consumer(*, append: bool = True) -> dict[str, str]:
    """Standalone consumer entry point — full scenario transcript to guard_consumer.log."""
    scratch = scratch_dir()
    log = io.StringIO()
    bundle = scratch / f"guard_bundle_{os.getpid()}"
    hashes = _run_guard_consumer_scenarios(bundle, log)
    transcript = log.getvalue()
    _append_scratch_transcript(scratch / "guard_consumer.log", transcript, append=append)
    hash_path = scratch / "guard_consumer_hashes.json"
    existing: dict[str, str] = {}
    if append and hash_path.is_file():
        existing = json.loads(hash_path.read_text(encoding="utf-8"))
    existing[f"run_{os.getpid()}"] = hashes
    hash_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    return hashes


def run_standalone_guard_launch(*, append: bool = True) -> None:
    """Standalone direct launch entry point — full transcript to guard_launch.log."""
    scratch = scratch_dir()
    log = io.StringIO()
    _run_guard_direct_launch(log)
    _append_scratch_transcript(scratch / "guard_launch.log", log.getvalue(), append=append)


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
    prev = os.environ.get("MATEMIUM_SCRATCH")
    os.environ["MATEMIUM_SCRATCH"] = str(scratch)
    try:
        run_standalone_guard_consumer(append=False)
        run_standalone_guard_launch(append=False)
        (scratch / "guard_source_read.log").write_text(_capture_guard_source_read(), encoding="utf-8")
    finally:
        if prev is None:
            os.environ.pop("MATEMIUM_SCRATCH", None)
        else:
            os.environ["MATEMIUM_SCRATCH"] = prev
    return scratch


def main(argv: list[str] | None = None) -> int:
    """CLI entry: guard-consumer | guard-launch | guard-all."""
    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        print("usage: python -m matemium.agent.verification_scratch guard-consumer|guard-launch|guard-all")
        return 2
    command = args[0]
    if command == "guard-consumer":
        run_standalone_guard_consumer(append=True)
        return 0
    if command == "guard-launch":
        run_standalone_guard_launch(append=True)
        return 0
    if command == "guard-all":
        emit_guard_scratch_artifacts()
        return 0
    print(f"unknown command: {command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())