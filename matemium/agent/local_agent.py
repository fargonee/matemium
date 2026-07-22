"""Offline Agent (v3) Lifecycle Integrations — Director, Engineer, and Critic."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from .local_runner import LocalInferenceRunner
from .models import DirectorOutput, DecoupledArtifacts, ProjectSession, ProcessingMode
from .script_parser import extract_div_markers
from .writer import write_decoupled_project

DIRECTOR_SYSTEM_PROMPT = """You are an elite mathematics educator, Disney-grade scriptwriter, and seasoned content creator.
Your goal is to write a highly engaging, pedagogically sound, and visually complete script for a mathematical animation.

You MUST structure the script into distinct visual and narrative sections using `# ---DIV: Section Title---` markers.
Within each section, you define the python-like function calls that declare the visual elements using the `b` (builder) object:
- `b.add_heading("...")` -> Add a clean screen title.
- `b.add_body("...")` -> Add educational voiceover or narrative text.
- `b.add_math(r"...")` -> Add beautifully rendered LaTeX formulas.
- `b.add_3d("...")` -> Add a 3D surface plot.
- `b.add_observation("...")` -> Add visual instructions/camera guidance.

Example Output format:
# ---DIV: Introducing Integrals---
def part_introduction(b):
    b.add_heading("Area Under a Curve")
    b.add_body("How do we measure the exact area bounded by a flowing curve?")
    b.add_math(r"\\int_a^b f(x) \\, dx")

# ---DIV: Refinement---
def part_refinement(b):
    b.add_body("We can approximate the area by slicing it into millions of tiny, infinite rectangles.")
    b.add_math(r"\\sum_{i=1}^n f(x_i) \\Delta x")

Keep your language clear, compelling, and professional. Always use double backslashes for LaTeX escape codes. Do not include markdown wraps around the code (no backticks), only the raw text with markers.
"""

ENGINEER_SYSTEM_PROMPT = """You are a highly disciplined Manim/Matemium compiler specialist.
Your goal is to refine and generate Python animation layouts using strict, decoupled structural syntax:
- `scenes.py`: Clean chronological timelines using CanvasBuilder.
- `helpers.py`: Heavy lifting, pure mathematics, LaTeX strings, coordinate generation matrices, and mesh definitions.

You will be given:
1. The educational script.
2. The absolute Timing Blueprint with durations.
3. Relevant math/Manim code snippets from our vector database.

Output your code modifications strictly using search/replace diff blocks:
<<<<<<< SEARCH
[old code]
=======
[new code]
>>>>>>> REPLACE
"""

CRITIC_SYSTEM_PROMPT = """You are a highly capable Manim debugging and compilation repair assistant.
You will be given:
1. The original python code that failed compilation.
2. The exact error message / traceback (`stderr`) from the compiler execution.

Your goal is to output an aider-style SEARCH/REPLACE diff patch block to fix the error in the code:
<<<<<<< SEARCH
[old code]
=======
[new code]
>>>>>>> REPLACE

Be extremely precise. Only make the minimal necessary changes to fix the compilation or syntax error. Do not output prose explanations, only the SEARCH/REPLACE block.
"""


def local_director_agent(user_prompt: str, mode: ProcessingMode) -> DirectorOutput:
    """Phase 1 — Run local/offline script-finalize LLM."""
    runner = LocalInferenceRunner()
    user_msg = f"User prompt: {user_prompt}\nProcessing mode: {mode.value}"

    script = runner.generate(DIRECTOR_SYSTEM_PROMPT, user_msg)
    div_markers = extract_div_markers(script)

    return DirectorOutput(
        script=script,
        mode=mode,
        div_markers=div_markers,
        tone="pedagogical",
    )


def local_engineer_agent(session: ProjectSession, retriever_fn: Any = None) -> DecoupledArtifacts:
    """Phase 3 — Run programmatic separation layout + GGUF custom refinement with local RAG context."""
    # Build robust, correct base files programmatically first
    base_result = write_decoupled_project(
        session.project_dir,
        session.director_output.script,
        session.blueprint,
        session=session,
    )

    if os.environ.get("MATEMIUM_USE_LOCAL_LLM") != "true":
        return base_result.artifacts

    try:
        runner = LocalInferenceRunner()

        scenes_file = session.project_dir / "scenes.py"
        assets_file = session.project_dir / "helpers.py"

        scenes_content = scenes_file.read_text(encoding="utf-8") if scenes_file.is_file() else ""
        assets_content = assets_file.read_text(encoding="utf-8") if assets_file.is_file() else ""

        # Query local vector DB (RAG) if retriever is present
        rag_context = ""
        if retriever_fn is not None:
            try:
                results = retriever_fn(session.director_output.script, 3)
                rag_context = "\n".join([f"Context Block:\n{r.get('chunk', '')}" for r in results])
            except Exception as e:
                print(f"[Local RAG Warning] RAG fetch failed: {e}")

        user_msg = f"""Educational script: {session.director_output.script}
Timing blueprint segments: {session.blueprint.segments}
RAG context: {rag_context}

Here is the current base scenes.py:
{scenes_content}

Here is the current base helpers.py:
{assets_content}

Please generate an aider-style SEARCH/REPLACE diff patch block to enhance helpers.py with more detailed math matrices, grids, or latex styling if relevant."""

        from .grammars import AIDER_DIFF_GBNF
        patches = runner.generate(ENGINEER_SYSTEM_PROMPT, user_msg, grammar=AIDER_DIFF_GBNF)

        from .writer import parse_patch_blocks, apply_patches
        blocks = parse_patch_blocks(patches)
        if blocks:
            # Check where the block belongs and apply
            search_block = blocks[0].search
            if assets_content.count(search_block) == 1:
                updated_assets = apply_patches(assets_content, blocks)
                assets_file.write_text(updated_assets, encoding="utf-8")
                print("[Local Engineer] Applied GGUF code refinements to helpers.py successfully.")
            elif scenes_content.count(search_block) == 1:
                updated_scenes = apply_patches(scenes_content, blocks)
                scenes_file.write_text(updated_scenes, encoding="utf-8")
                print("[Local Engineer] Applied GGUF code refinements to scenes.py successfully.")

    except Exception as e:
        # Gracefully proceed with the robust programmatically-generated files
        print(f"[Local LLM Warning] Custom engineering refinement skipped or failed: {e}")

    return base_result.artifacts


def make_local_critic_patch_fn(project_dir: Path) -> Callable[[str], None]:
    """Phase 4 — Return critic closure bound to local GGUF self-correction."""

    def local_critic_patch_fn(stderr: str) -> None:
        if os.environ.get("MATEMIUM_USE_LOCAL_LLM") != "true":
            return

        scenes_file = project_dir / "scenes.py"
        assets_file = project_dir / "helpers.py"

        scenes_content = scenes_file.read_text(encoding="utf-8") if scenes_file.is_file() else ""
        assets_content = assets_file.read_text(encoding="utf-8") if assets_file.is_file() else ""

        runner = LocalInferenceRunner()

        user_msg = f"""Failing scenes.py code:
{scenes_content}

Failing helpers.py code:
{assets_content}

Compiler stderr output:
{stderr}

Please generate a precise SEARCH/REPLACE patch block to repair the failing file."""

        try:
            from .grammars import AIDER_DIFF_GBNF
            patches = runner.generate(CRITIC_SYSTEM_PROMPT, user_msg, grammar=AIDER_DIFF_GBNF)

            from .writer import parse_patch_blocks, apply_patches
            blocks = parse_patch_blocks(patches)

            if blocks:
                search_block = blocks[0].search
                if scenes_content.count(search_block) == 1:
                    updated_scenes = apply_patches(scenes_content, blocks)
                    scenes_file.write_text(updated_scenes, encoding="utf-8")
                    err_summary = stderr.splitlines()[-1] if stderr else ""
                    print(f"[Local Critic] Patched scenes.py successfully to resolve: {err_summary}")
                elif assets_content.count(search_block) == 1:
                    updated_assets = apply_patches(assets_content, blocks)
                    assets_file.write_text(updated_assets, encoding="utf-8")
                    err_summary = stderr.splitlines()[-1] if stderr else ""
                    print(f"[Local Critic] Patched helpers.py successfully to resolve: {err_summary}")
                else:
                    print("[Local Critic Warning] SEARCH block matched multiple times or was absent.")
        except Exception as e:
            print(f"[Local Critic Warning] Self-correction patching failed: {e}")

    return local_critic_patch_fn
