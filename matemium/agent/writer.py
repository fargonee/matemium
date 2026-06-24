"""Patch engine — SEARCH/REPLACE writes for decoupled scenes.py and assets.py."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from matemium.paths import discover_root

from .models import DecoupledArtifacts, TimingBlueprint
from .script_parser import extract_div_markers, parse_narrative_blocks
from .separation import build_decoupled_artifacts
from .timing import round_ms

SEARCH_MARKER = "<<<<<<< SEARCH"
DIVIDER_MARKER = "======="
REPLACE_MARKER = ">>>>>>> REPLACE"
TEMPLATE_SEED_MARKER = "# <<<Matemium:TEMPLATE_SEED>>>\n"

ADD_MATH_RE = re.compile(r"b\.add_math\s*\(\s*r([\"'])(.*?)\1\s*\)", re.DOTALL)
ADD_3D_RE = re.compile(r'b\.add_3d\s*\(\s*["\']([^"\']+)["\']\s*\)')


class PatchError(Exception):
    """Base patch engine error."""


class PatchNotFoundError(PatchError):
    """SEARCH text absent from buffer."""


class PatchAmbiguousError(PatchError):
    """SEARCH text matched more than once."""


@dataclass(frozen=True)
class PatchBlock:
    """One Aider-style SEARCH/REPLACE unit."""

    search: str
    replace: str


@dataclass(frozen=True)
class WriterResult:
    """Outcome of a decoupled project write."""

    artifacts: DecoupledArtifacts
    scenes_path: Path
    assets_path: Path
    patches_applied: int
    patch_documents: dict[str, str]


def _templates_root() -> Path:
    return discover_root() / "shared" / "templates"


def load_template(name: str) -> str:
    path = _templates_root() / name
    return path.read_text(encoding="utf-8")


def parse_patch_blocks(document: str) -> list[PatchBlock]:
    """Parse one or more SEARCH/REPLACE blocks from a patch document."""
    blocks: list[PatchBlock] = []
    cursor = 0
    while True:
        search_idx = document.find(SEARCH_MARKER, cursor)
        if search_idx < 0:
            break
        divider_idx = document.find(DIVIDER_MARKER, search_idx)
        replace_idx = document.find(REPLACE_MARKER, divider_idx)
        if divider_idx < 0 or replace_idx < 0:
            raise PatchError("Malformed patch block: missing ======= or >>>>>>> REPLACE")
        search_text = document[search_idx + len(SEARCH_MARKER) : divider_idx]
        if search_text.startswith("\n"):
            search_text = search_text[1:]
        replace_text = document[divider_idx + len(DIVIDER_MARKER) : replace_idx]
        if replace_text.startswith("\n"):
            replace_text = replace_text[1:]
        blocks.append(PatchBlock(search=search_text, replace=replace_text))
        cursor = replace_idx + len(REPLACE_MARKER)
    return blocks


def apply_patch(content: str, search: str, replace: str) -> str:
    """Apply a single exact, unique SEARCH/REPLACE substitution."""
    count = content.count(search)
    if count == 0:
        raise PatchNotFoundError("SEARCH block did not match")
    if count > 1:
        raise PatchAmbiguousError("AMBIGUOUS_PATCH: SEARCH block matched multiple times")
    return content.replace(search, replace, 1)


def apply_patches(content: str, blocks: Sequence[PatchBlock]) -> str:
    """Apply patch blocks in order."""
    result = content
    for block in blocks:
        result = apply_patch(result, block.search, block.replace)
    return result


def format_patch_block(search: str, replace: str) -> str:
    """Serialize a patch block in Aider format."""
    return (
        f"{SEARCH_MARKER}\n"
        f"{search}"
        f"{DIVIDER_MARKER}\n"
        f"{replace}"
        f"{REPLACE_MARKER}\n"
    )


def format_patch_document(blocks: Sequence[PatchBlock]) -> str:
    """Serialize ordered patch blocks into one diff document."""
    return "".join(format_patch_block(block.search, block.replace) for block in blocks)


def apply_patch_to_disk(path: Path, block: PatchBlock) -> None:
    """Read a file, apply one exact unique SEARCH/REPLACE, write back."""
    content = path.read_text(encoding="utf-8")
    updated = apply_patch(content, block.search, block.replace)
    path.write_text(updated, encoding="utf-8")


def apply_patches_on_disk(path: Path, blocks: Sequence[PatchBlock]) -> int:
    """Apply patch blocks sequentially, one disk read/write per block."""
    for block in blocks:
        apply_patch_to_disk(path, block)
    return len(blocks)


def apply_patch_document_on_disk(path: Path, document: str) -> int:
    """Parse a diff document and apply each block to disk in order."""
    return apply_patches_on_disk(path, parse_patch_blocks(document))


def _indent_body(lines: list[str], indent: str = "    ") -> str:
    return "\n".join(indent + line if line.strip() else line for line in lines)


def _inject_wait_into_part(part_source: str, duration: float) -> str:
    """Append blueprint-sourced wait anchor inside a part_* function."""
    wait_line = f"    b.wait(duration={round_ms(duration)})"
    lines = part_source.rstrip().splitlines()
    if not lines:
        return f"def part_generated(b: CanvasBuilder) -> None:\n{wait_line}\n"
    insert_at = len(lines)
    for idx in range(len(lines) - 1, 0, -1):
        if lines[idx].strip() and not lines[idx].strip().startswith("#"):
            insert_at = idx + 1
            break
    lines.insert(insert_at, wait_line)
    return "\n".join(lines) + "\n"


def _decouple_part_body(body: str, block_index: int) -> str:
    """Rewrite inline LaTeX/3D literals to assets.* references."""
    latex_idx = 0

    def math_repl(match: re.Match[str]) -> str:
        nonlocal latex_idx
        ref = f"assets.latex_{block_index}_{latex_idx}()"
        latex_idx += 1
        return f"b.add_math({ref})"

    result = ADD_MATH_RE.sub(math_repl, body)
    if ADD_3D_RE.search(result):
        result = ADD_3D_RE.sub(f'b.add_3d(assets.surface_{block_index}())', result, count=1)
    return result


def _normalize_part_function(block_body: str, fn_name: str) -> str:
    """Ensure block body is a typed part_* function with the blueprint name."""
    stripped = block_body.strip()
    lines = stripped.splitlines()
    if not lines:
        return f"def {fn_name}(b: CanvasBuilder) -> None:\n    pass\n"
    if lines[0].strip().startswith("def part_"):
        body_lines = lines[1:]
        inner = "\n".join(body_lines).rstrip()
        if inner:
            return f"def {fn_name}(b: CanvasBuilder) -> None:\n{inner}\n"
        return f"def {fn_name}(b: CanvasBuilder) -> None:\n    pass\n"
    body_lines = [ln.strip() for ln in lines if ln.strip()]
    inner = _indent_body(body_lines)
    return f"def {fn_name}(b: CanvasBuilder) -> None:\n{inner}\n"


def emit_assets_replace(artifacts: DecoupledArtifacts) -> str:
    """Render assets.py REPLACE payload (pure data, no narrative)."""
    lines: list[str] = []

    latex_funcs: list[str] = []
    for comp_idx, latex in enumerate(artifacts.assets.latex_strings):
        block_id = (
            artifacts.assets.computations[comp_idx]["block_id"]
            if comp_idx < len(artifacts.assets.computations)
            else f"block_{comp_idx}"
        )
        block_num = block_id.split("_")[-1] if "_" in block_id else str(comp_idx)
        local_idx = sum(
            1
            for i in range(comp_idx)
            if i < len(artifacts.assets.computations)
            and artifacts.assets.computations[i].get("block_id") == block_id
        )
        fn = f"latex_{block_num}_{local_idx}"
        escaped = latex.replace("\\", "\\\\").replace('"', '\\"')
        latex_funcs.append(f'def {fn}() -> str:\n    return r"{escaped}"\n')

    surface_funcs: list[str] = []
    for mesh in artifacts.assets.mesh_definitions:
        block_id = mesh.get("block_id", "block_0")
        block_num = block_id.split("_")[-1] if "_" in block_id else "0"
        eq = mesh.get("equation", "z = x^2 - y^2")
        surface_funcs.append(
            f"def surface_{block_num}() -> str:\n    return \"{eq}\"\n"
        )

    lines.extend(latex_funcs)
    if latex_funcs and surface_funcs:
        lines.append("")
    lines.extend(surface_funcs)

    if artifacts.assets.coordinate_sets:
        lines.append("")
        lines.append("COORDINATE_SETS = " + repr(list(artifacts.assets.coordinate_sets)))
    if artifacts.assets.computations:
        lines.append("COMPUTATIONS = " + repr(list(artifacts.assets.computations)))
    if artifacts.assets.mesh_definitions:
        lines.append("MESH_DEFINITIONS = " + repr(list(artifacts.assets.mesh_definitions)))

    return "\n".join(lines).rstrip() + "\n"


def emit_scenes_parts_replace(script: str, blueprint: TimingBlueprint) -> str:
    """Render the scenes.py part_* section with waits from blueprint segments."""
    blocks = parse_narrative_blocks(script)
    segment_by_id = {s.block_id: s for s in blueprint.segments}
    div_markers = extract_div_markers(script)
    parts: list[str] = []

    for idx, block in enumerate(blocks):
        fn_name = f"part_{block.title.lower().replace(' ', '_')}"
        part_src = _normalize_part_function(block.body, fn_name)
        part_src = _decouple_part_body(part_src, idx)
        segment = segment_by_id.get(block.block_id)
        if segment:
            part_src = _inject_wait_into_part(part_src, segment.wait_duration)
        marker = div_markers[idx] if idx < len(div_markers) else block.title
        parts.append(f"# ---DIV: {marker}---")
        parts.append(part_src.rstrip())
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def emit_main_scene_replace(script: str, blueprint: TimingBlueprint) -> str:
    """Render CanvasScene class wiring all part_* builders."""
    artifacts = build_decoupled_artifacts(script, blueprint)
    part_calls = "\n        ".join(f"{fn}(builder)" for fn in artifacts.scenes.part_functions)
    class_name = "AgentScene"
    title = div_markers[0] if (div_markers := extract_div_markers(script)) else "Agent Scene"
    return f'''# ---DIV: Main scene---
class {class_name}(CanvasScene):
    """Decoupled agent-authored scene."""

    def __init__(self, **kwargs):
        builder = CanvasBuilder(
            title="{title}",
            canvas_settings=CanvasSettings.for_reels(title="{title}"),
        )
        {part_calls}
        super().__init__(dsl=builder.build(), **kwargs)
'''


def build_assets_patches(artifacts: DecoupledArtifacts) -> list[PatchBlock]:
    """Patches transforming template assets.py into decoupled engine room."""
    template = load_template("assets.py")
    search = (
        "def example_values() -> tuple[float, float]:\n"
        '    """Sample numeric helper for scenes.py."""\n'
        "    return 2.0, 3.0\n"
        "\n"
        "\n"
        "def example_latex() -> str:\n"
        '    """Sample LaTeX string for add_math()."""\n'
        '    return r"x^2 - 5x + 6 = 0"'
    )
    if search not in template:
        raise PatchError("assets.py template changed; bootstrap SEARCH anchor missing")
    return [PatchBlock(search=search, replace=emit_assets_replace(artifacts))]


def build_scenes_patches(script: str, blueprint: TimingBlueprint) -> list[PatchBlock]:
    """Patches transforming template scenes.py into decoupled narrative + waits."""
    template = load_template("scenes.py")
    patches: list[PatchBlock] = []

    import_search = (
        "from canvas import CanvasScene, CanvasSettings\n"
        "from canvas.builder import CanvasBuilder\n"
    )
    import_replace = (
        "import assets\n"
        "\n"
        "from canvas import CanvasScene, CanvasSettings\n"
        "from canvas.builder import CanvasBuilder\n"
    )
    if import_search in template:
        patches.append(PatchBlock(search=import_search, replace=import_replace))

    parts_search = (
        "# ---DIV: Scene parts---\n"
        "def part_intro(b: CanvasBuilder) -> None:\n"
        '    b.add_heading("Your title here")\n'
        '    b.add_body("Start your mathematical reasoning...")\n'
        '    b.add_math(r"x^2 - 5x + 6 = 0")\n'
        '    b.add_observation("We look for two numbers that multiply to 6 and add to -5.")\n'
        "\n"
        "\n"
        "def part_conclusion(b: CanvasBuilder) -> None:\n"
        '    b.add_math(r"x^2 - 5x + 6 = (x-2)(x-3)")\n'
        '    b.add_3d("z = x^2 - y^2")\n'
        '    b.add_text("Conclusion: x = 2 or x = 3", after_3d=True)\n'
    )
    if parts_search not in template:
        raise PatchError("scenes.py template changed; parts SEARCH anchor missing")
    patches.append(
        PatchBlock(search=parts_search, replace=emit_scenes_parts_replace(script, blueprint))
    )

    scene_search = (
        "# ---DIV: Main scene---\n"
        "class MyScene(CanvasScene):\n"
        '    """Main scene for this project."""\n'
        "\n"
        "    def __init__(self, **kwargs):\n"
        "        # Default: portrait 9:16 (Reels / Shorts). For YouTube 16:9 use:\n"
        "        # CanvasBuilder(title=\"My Scene\", canvas_settings=CanvasSettings.for_youtube())\n"
        "        builder = CanvasBuilder(\n"
        '            title="My Scene",\n'
        '            canvas_settings=CanvasSettings.for_reels(title="My Scene"),\n'
        "        )\n"
        "        part_intro(builder)\n"
        "        part_conclusion(builder)\n"
        "        super().__init__(dsl=builder.build(), **kwargs)"
    )
    if scene_search not in template:
        raise PatchError("scenes.py template changed; main scene SEARCH anchor missing")
    patches.append(
        PatchBlock(search=scene_search, replace=emit_main_scene_replace(script, blueprint))
    )
    return patches


def bootstrap_template_file(path: Path, template_name: str) -> None:
    """Place shared template content via a single SEARCH/REPLACE from seed marker."""
    template = load_template(template_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        existing = path.read_text(encoding="utf-8")
        if existing == template:
            return
    path.write_text(TEMPLATE_SEED_MARKER, encoding="utf-8")
    apply_patch_to_disk(
        path,
        PatchBlock(search=TEMPLATE_SEED_MARKER, replace=template),
    )


def write_decoupled_project(
    project_dir: Path | str,
    script: str,
    blueprint: TimingBlueprint,
) -> WriterResult:
    """Write decoupled scenes.py and assets.py via SEARCH/REPLACE patches only."""
    project_dir = Path(project_dir)
    artifacts = build_decoupled_artifacts(script, blueprint)
    scenes_path = project_dir / "scenes.py"
    assets_path = project_dir / "assets.py"

    bootstrap_template_file(scenes_path, "scenes.py")
    bootstrap_template_file(assets_path, "assets.py")

    assets_patches = build_assets_patches(artifacts)
    scenes_patches = build_scenes_patches(script, blueprint)
    assets_document = format_patch_document(assets_patches)
    scenes_document = format_patch_document(scenes_patches)

    assets_applied = apply_patches_on_disk(assets_path, assets_patches)
    scenes_applied = apply_patches_on_disk(scenes_path, scenes_patches)

    return WriterResult(
        artifacts=artifacts,
        scenes_path=scenes_path,
        assets_path=assets_path,
        patches_applied=assets_applied + scenes_applied,
        patch_documents={
            "assets.py": assets_document,
            "scenes.py": scenes_document,
        },
    )