from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

import pytest

from matemium.agent import aider_runner
from matemium.agent.aider_runner import AiderAgentRunner


def test_target_files_enforce_lifecycle_phase(tmp_path: Path) -> None:
    (tmp_path / "brief" / "tapes").mkdir(parents=True)
    for relative in (
        "scenes.py",
        "helpers.py",
        "brief/description.md",
        "brief/passport.json",
        "brief/tapes/main.md",
        "brief/orchestration.md",
    ):
        path = tmp_path / relative
        path.write_text("placeholder\n", encoding="utf-8")
    (tmp_path / "brief" / "roadmap.json").write_text(
        '{"current_phase":"tape_content"}\n', encoding="utf-8"
    )

    targets = AiderAgentRunner(env={})._target_files(tmp_path)

    assert targets == ["brief/roadmap.json", "brief/tapes/main.md"]
    assert "scenes.py" not in targets
    assert "helpers.py" not in targets


def test_target_files_allow_code_during_authoring(tmp_path: Path) -> None:
    (tmp_path / "brief").mkdir(parents=True)
    (tmp_path / "scenes.py").write_text("class Demo:\n    pass\n", encoding="utf-8")
    (tmp_path / "helpers.py").write_text("ASSETS = {}\n", encoding="utf-8")
    (tmp_path / "brief" / "roadmap.json").write_text(
        '{"current_phase":"authoring"}\n', encoding="utf-8"
    )

    targets = AiderAgentRunner(env={})._target_files(tmp_path)

    assert targets == ["scenes.py", "helpers.py", "brief/roadmap.json"]


def test_authoring_reads_approved_briefs_without_making_them_writable(tmp_path: Path) -> None:
    (tmp_path / "brief" / "tapes").mkdir(parents=True)
    for relative in (
        "scenes.py",
        "helpers.py",
        "brief/description.md",
        "brief/orchestration.md",
        "brief/tapes/main.md",
        "brief/tts-narration.md",
        "brief/tts-narration-style.md",
        "brief/timestamps.json",
    ):
        (tmp_path / relative).write_text("placeholder\n", encoding="utf-8")
    (tmp_path / "brief" / "passport.json").write_text(
        '{"production_path":"tts"}\n', encoding="utf-8"
    )
    (tmp_path / "brief" / "roadmap.json").write_text(
        '{"current_phase":"authoring"}\n', encoding="utf-8"
    )
    runner = AiderAgentRunner(env={})

    writable = runner._target_files(tmp_path)
    read_only = runner._read_only_files(tmp_path, writable)

    assert writable == ["scenes.py", "helpers.py", "brief/roadmap.json"]
    assert "brief/passport.json" in read_only
    assert "brief/tapes/main.md" in read_only
    assert "brief/orchestration.md" in read_only
    assert "brief/tts-narration.md" in read_only
    assert not set(writable).intersection(read_only)


def test_aider_runner_uses_workspace_files_and_local_model(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "scenes.py").write_text("class Demo:\n    pass\n", encoding="utf-8")
    (tmp_path / "helpers.py").write_text("ASSETS = {}\n", encoding="utf-8")
    captured: dict[str, Any] = {}

    monkeypatch.setattr("shutil.which", lambda executable: f"/usr/bin/{executable}")
    monkeypatch.setattr(
        AiderAgentRunner,
        "_ensure_local_model_server_available",
        lambda self, env: "http://127.0.0.1:8765",
    )

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["cwd"] = kwargs["cwd"]
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout=(
                "Warning: Input is not a terminal (fd=0).\n"
                "Added helpers.py to the chat.\n"
                "Added scenes.py to the chat.\n"
                "Tokens: 3.1k sent, 964 received.\n"
                "Applied edit to scenes.py\n"
                "Summarization failed for model openai/matemium-local: cannot schedule new futures after shutdown\n"
            ),
            stderr="",
        )

    monkeypatch.setattr("subprocess.run", fake_run)

    result = AiderAgentRunner(env={}, timeout_seconds=1).run(
        workspace=tmp_path,
        prompt="add a title",
        model="qwen2.5-coder:7b-instruct",
        use_local_model=True,
    )

    assert result.output == "Done. Aider updated scenes.py."
    assert result.model == "openai/matemium-local"
    assert result.files == ("scenes.py", "helpers.py")
    assert captured["cwd"] == tmp_path.resolve()
    assert "--no-auto-commits" in captured["cmd"]
    assert "--no-git" in captured["cmd"]
    assert "scenes.py" in captured["cmd"]
    assert "helpers.py" in captured["cmd"]
    assert captured["env"]["AIDER_ANALYTICS"] == "false"
    assert captured["env"]["OPENAI_API_BASE"] == "http://127.0.0.1:8765/v1"
    assert captured["env"]["OPENAI_BASE_URL"] == "http://127.0.0.1:8765/v1"
    assert captured["env"]["OPENAI_API_KEY"] == "matemium-local"
    assert "--no-show-model-warnings" in captured["cmd"]
    assert any(event["type"] == "action_completed" for event in result.trace)
    assert any(event["type"] == "agent_warning" for event in result.trace)


def test_aider_runner_uses_matemium_provider_for_local_assets(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "scenes.py").write_text("class Demo:\n    pass\n", encoding="utf-8")
    captured: dict[str, Any] = {}

    monkeypatch.setattr("shutil.which", lambda executable: f"/usr/bin/{executable}")
    monkeypatch.setattr(
        AiderAgentRunner,
        "_ensure_local_model_server_available",
        lambda self, env: "http://127.0.0.1:8766",
    )

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="edited", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = AiderAgentRunner(env={}, timeout_seconds=1).run(
        workspace=tmp_path,
        prompt="rename a class",
        model="llm-qwen-coder-3b-q4",
        use_local_model=True,
    )

    model_index = captured["cmd"].index("--model") + 1
    assert result.model == "openai/matemium-local"
    assert captured["cmd"][model_index] == "openai/matemium-local"


def test_aider_runner_rejects_unavailable_local_provider_before_spawn(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "scenes.py").write_text("class Demo:\n    pass\n", encoding="utf-8")
    calls: list[list[str]] = []

    monkeypatch.setattr("shutil.which", lambda executable: f"/usr/bin/{executable}")

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="should not run", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr(
        AiderAgentRunner,
        "_ensure_local_model_server_available",
        lambda self, env: (_ for _ in ()).throw(aider_runner.AiderUnavailableError("local down")),
    )

    with pytest.raises(aider_runner.AiderUnavailableError, match="local down"):
        AiderAgentRunner(env={}, timeout_seconds=1).run(
            workspace=tmp_path,
            prompt="rename a class",
            model="llm-qwen-coder-3b-q4",
            use_local_model=True,
        )

    assert calls == []


def test_aider_runner_allows_explicit_model_override(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "scenes.py").write_text("class Demo:\n    pass\n", encoding="utf-8")
    captured: dict[str, Any] = {}

    monkeypatch.setattr("shutil.which", lambda executable: f"/usr/bin/{executable}")

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = AiderAgentRunner(env={"MATEMIUM_AIDER_MODEL": "openrouter/anthropic/claude-sonnet-4"}).run(
        workspace=tmp_path,
        prompt="fix the scene",
        model="gpt-4o-mini",
        provider="openai",
    )

    model_index = captured["cmd"].index("--model") + 1
    assert captured["cmd"][model_index] == "openrouter/anthropic/claude-sonnet-4"
    assert result.model == "openrouter/anthropic/claude-sonnet-4"


def test_aider_runner_discovers_uv_managed_runtime(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "scenes.py").write_text("class Demo:\n    pass\n", encoding="utf-8")
    runtime_dir = tmp_path / "aider-runtime"
    aider_bin = runtime_dir / "bin" / "aider"
    aider_bin.parent.mkdir(parents=True)
    aider_bin.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    captured: dict[str, Any] = {}

    monkeypatch.setattr("shutil.which", lambda executable: None)

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="managed aider", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = AiderAgentRunner(env={"MATEMIUM_AIDER_RUNTIME_DIR": str(runtime_dir)}).run(
        workspace=tmp_path,
        prompt="add a title",
    )

    assert result.output == "Aider finished. Checked scenes.py."
    assert captured["cmd"][0] == str(aider_bin.resolve())


def test_aider_runner_provisions_uv_managed_runtime(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "scenes.py").write_text("class Demo:\n    pass\n", encoding="utf-8")
    runtime_dir = tmp_path / "aider-runtime"
    uv_bin = tmp_path / "uv"
    uv_bin.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    captured_cmds: list[list[str]] = []

    monkeypatch.setattr("shutil.which", lambda executable: None)

    def fake_run(cmd, **kwargs):
        captured_cmds.append(cmd)
        if cmd[1] == "venv":
            (runtime_dir / "bin").mkdir(parents=True)
            (runtime_dir / "bin" / "python").write_text("", encoding="utf-8")
        elif cmd[1] == "pip":
            (runtime_dir / "bin" / "aider").write_text("", encoding="utf-8")
        else:
            return subprocess.CompletedProcess(cmd, 0, stdout="provisioned aider", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = AiderAgentRunner(
        env={
            "MATEMIUM_AIDER_RUNTIME_DIR": str(runtime_dir),
            "MATEMIUM_UV_BIN": str(uv_bin),
        },
        timeout_seconds=1,
    ).run(workspace=workspace, prompt="add a title")

    assert result.output == "Aider finished. Checked scenes.py."
    assert captured_cmds[0][:4] == [str(uv_bin), "venv", "--python", "3.12"]
    assert captured_cmds[1][:4] == [str(uv_bin), "pip", "install", "--python"]
    assert captured_cmds[2][0] == str((runtime_dir / "bin" / "aider").resolve())


def test_missing_aider_mentions_launcher_configuration(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "scenes.py").write_text("class Demo:\n    pass\n", encoding="utf-8")
    monkeypatch.setattr("shutil.which", lambda executable: None)
    monkeypatch.setattr(
        AiderAgentRunner,
        "_candidate_runtime_dirs",
        lambda self: [tmp_path / "missing-runtime"],
    )

    with pytest.raises(aider_runner.AiderUnavailableError, match="MATEMIUM_UV_BIN"):
        AiderAgentRunner(
            env={"MATEMIUM_ROOT": str(tmp_path / "empty-root")},
        ).run(workspace=workspace, prompt="add a title")


def test_aider_runner_preserves_project_questions_for_the_ui(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "scenes.py").write_text("class Demo:\n    pass\n", encoding="utf-8")
    monkeypatch.setattr("shutil.which", lambda executable: f"/usr/bin/{executable}")
    response = """<matemium_response>
The production path changes what I make next. Choose one route.

```project_questions
{"questions":[{"id":"production_path","passport_field":"production_path","question":"Which route should we use?","type":"single","required":true,"allow_custom":false,"options":[{"id":"mute_video","label":"Mute video","description":"You add audio later.","recommended":true},{"id":"tts","label":"TTS","description":"Matemium generates narration.","recommended":false}]}]}
```
</matemium_response>"""
    monkeypatch.setattr(
        "subprocess.run",
        lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, stdout=response, stderr=""),
    )

    result = AiderAgentRunner(env={}, timeout_seconds=1).run(
        workspace=tmp_path,
        prompt="help me choose",
    )

    assert result.output.startswith("The production path changes")
    assert "```project_questions" in result.output
    assert "<matemium_response>" not in result.output
