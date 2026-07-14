from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from matemium.paths import discover_root

from .base import BaseTool
from .safety import validate_path_safety


class ApplyDiffPatchArgs(BaseModel):
    file_path: str = Field(..., description="Path to the file to modify (relative to project root)")
    search: str = Field(..., description="The exact literal string block to find/replace")
    replace: str = Field(..., description="The exact literal string block to replace the search block with")
    project_dir: Optional[str] = Field(None, description="Base project directory path")


class FSApplyDiffPatchTool(BaseTool):
    name: str = "apply_diff_patch"
    description: str = (
        "Apply a surgical search/replace patch block to a file. "
        "The search block must match exactly one occurrence in the file."
    )
    args_schema = ApplyDiffPatchArgs

    def execute(self, **kwargs) -> str:
        try:
            args = self.args_schema(**kwargs)
        except Exception as e:
            return f"Error: Invalid arguments: {e}"

        base_dir = Path(args.project_dir) if args.project_dir else discover_root()
        try:
            safe_path = validate_path_safety(args.file_path, base_dir)
        except ValueError as e:
            return f"Error: {e}"

        if not safe_path.is_file():
            return f"Error: File {args.file_path} does not exist."

        try:
            content = safe_path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading file: {e}"

        # Import apply_patch programmatically
        try:
            from matemium.agent.writer import apply_patch
            updated = apply_patch(content, args.search, args.replace)
        except Exception as e:
            return f"Error applying patch: {e}"

        try:
            safe_path.write_text(updated, encoding="utf-8")
        except Exception as e:
            return f"Error writing updated file: {e}"

        return f"Successfully applied patch to {args.file_path}."


class RunCompilerArgs(BaseModel):
    project_dir: Optional[str] = Field(None, description="The workspace directory of the project to compile/check")


class FSRunCompilerTool(BaseTool):
    name: str = "run_compiler"
    description: str = (
        "Compile and validate the scenes.py file in the project directory. "
        "Returns success status and any compilation or syntax error tracebacks."
    )
    args_schema = RunCompilerArgs

    def execute(self, **kwargs) -> str:
        try:
            args = self.args_schema(**kwargs)
        except Exception as e:
            return f"Error: Invalid arguments: {e}"

        base_dir = Path(args.project_dir) if args.project_dir else discover_root()
        try:
            target_dir = validate_path_safety("", base_dir)
        except ValueError as e:
            return f"Error: {e}"

        try:
            from matemium.workspace_project import check_project
            res = check_project(target_dir)
            if res.get("ok", False):
                return "Compilation Successful: No errors found."
            else:
                errors = res.get("errors", [])
                err_msgs = []
                for err in errors:
                    msg = f"Line {err.get('line', 0)}: {err.get('message', 'Unknown error')}"
                    if err.get("source"):
                        msg += f" ({err.get('source')})"
                    err_msgs.append(msg)
                return "Compilation Failed:\n" + "\n".join(err_msgs)
        except Exception as e:
            return f"Compilation Failed with exception: {e}"
