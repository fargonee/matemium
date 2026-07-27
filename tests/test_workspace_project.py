"""Desktop workspace loader tests (no Manim renders)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from matemium.workspace_project import (
    check_project,
    lint_scenes_file,
    list_scenes_in_workspace,
    load_scenes_module,
    load_scene_class,
    resolve_scene_name,
    scenes_file,
)

REPO = Path(__file__).resolve().parent.parent
DEMO_SCENES = REPO / "projects" / "demo" / "scenes.py"


@pytest.fixture
def demo_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    shutil.copy(DEMO_SCENES, ws / "scenes.py")
    return ws


def test_scenes_file_requires_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        scenes_file(tmp_path)


def test_list_scenes_from_demo_workspace(demo_workspace: Path):
    scenes = list_scenes_in_workspace(demo_workspace)
    assert "PortraitDemo" in scenes
    assert "LandscapeDemo" in scenes


def test_resolve_scene_name_defaults_to_portrait(demo_workspace: Path):
    assert resolve_scene_name(demo_workspace, None) == "PortraitDemo"


def test_load_scene_class(demo_workspace: Path):
    cls = load_scene_class(demo_workspace, "PortraitDemo")
    from canvas import CanvasScene

    assert issubclass(cls, CanvasScene)


@pytest.mark.parametrize(
    "legacy_import",
    [
        "from .assets import add_compare_row",
        "from . import assets as project_assets",
        "import assets as project_assets",
    ],
)
def test_helpers_support_legacy_assets_imports(tmp_path: Path, legacy_import: str):
    ws = tmp_path / "legacy-imports"
    ws.mkdir()
    (ws / "helpers.py").write_text(
        "def add_compare_row():\n    return 'loaded from helpers'\n",
        encoding="utf-8",
    )
    reference = (
        "add_compare_row"
        if "from .assets import" in legacy_import
        else "project_assets.add_compare_row"
    )
    (ws / "scenes.py").write_text(
        f"{legacy_import}\nRESULT = {reference}()\n",
        encoding="utf-8",
    )

    module = load_scenes_module(ws)

    assert module.RESULT == "loaded from helpers"


def test_lint_valid_workspace(demo_workspace: Path):
    diagnostics = lint_scenes_file(demo_workspace)
    errors = [d for d in diagnostics if d.severity == "error"]
    assert errors == []


def test_lint_syntax_error(tmp_path: Path):
    ws = tmp_path / "bad"
    ws.mkdir()
    (ws / "scenes.py").write_text("def broken(\n", encoding="utf-8")
    diagnostics = lint_scenes_file(ws)
    assert any(d.source == "syntax" and d.severity == "error" for d in diagnostics)


def test_check_project_ok(demo_workspace: Path):
    result = check_project(demo_workspace, scene="PortraitDemo")
    assert result["ok"] is True
    assert result["scene"] == "PortraitDemo"
    assert result["timeline_length"] > 0


def test_check_project_unknown_scene(demo_workspace: Path):
    result = check_project(demo_workspace, scene="NotAScene")
    assert result["ok"] is False
    assert result["errors"]


def test_check_project_reports_dsl_validation_errors(tmp_path: Path):
    workspace = tmp_path / "invalid_dsl"
    workspace.mkdir()
    (workspace / "scenes.py").write_text(
        "\n".join(
            [
                "from canvas import CanvasElement, CanvasScene, SheetDSL, StatePatch, StateTransition",
                "",
                "class InvalidScene(CanvasScene):",
                "    def __init__(self, **kwargs):",
                "        dsl = SheetDSL(timeline=[",
                "            CanvasElement(id='label', type='Text', content='hello'),",
                "            StateTransition(id='bad', patches=[",
                "                StatePatch(target_id='missing', changes={'opacity': 0.5})",
                "            ]),",
                "        ])",
                "        super().__init__(dsl=dsl, **kwargs)",
            ]
        ),
        encoding="utf-8",
    )
    result = check_project(workspace, scene="InvalidScene")
    assert result["ok"] is False
    assert result["errors"][0]["source"] == "dsl"
    assert result["errors"][0]["code"] == "unknown_target_element_id"
