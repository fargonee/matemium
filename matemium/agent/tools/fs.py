from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from matemium.paths import discover_root

from .base import BaseTool
from .safety import validate_path_safety


class ReadSliceArgs(BaseModel):
    file_path: str = Field(..., description="Path to the file to read (relative to project root or absolute within project)")
    start_line: int = Field(1, description="1-based starting line number (inclusive)")
    end_line: Optional[int] = Field(None, description="1-based ending line number (inclusive, optional)")
    project_dir: Optional[str] = Field(None, description="Base project directory path")


class FSReadSliceTool(BaseTool):
    name: str = "read_file_slice"
    description: str = (
        "Read a specific slice/range of lines from a file. "
        "Use this to inspect code surgically without bloating the context."
    )
    args_schema = ReadSliceArgs

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
            lines = safe_path.read_text(encoding="utf-8").splitlines()
        except Exception as e:
            return f"Error reading file: {e}"

        total_lines = len(lines)
        start = max(1, args.start_line)
        end = min(total_lines, args.end_line) if args.end_line is not None else total_lines

        if start > total_lines:
            return f"Error: start_line {start} is beyond total lines in file ({total_lines})."
        if start > end:
            return f"Error: start_line {start} is greater than end_line {end}."

        slice_lines = lines[start - 1 : end]
        output = [f"--- File: {args.file_path} (Lines {start}-{end} of {total_lines}) ---"]
        for idx, line in enumerate(slice_lines, start=start):
            output.append(f"{idx:4d} | {line}")
        return "\n".join(output)


class GrepSearchArgs(BaseModel):
    pattern: str = Field(..., description="Regex pattern to search for within file contents")
    include_pattern: Optional[str] = Field(None, description="Optional glob pattern to filter which files are searched, e.g. '*.py'")
    dir_path: Optional[str] = Field(None, description="Directory path to search in (relative to project root, defaults to project root)")
    project_dir: Optional[str] = Field(None, description="Base project directory path")


class FSGrepSearchTool(BaseTool):
    name: str = "grep_search"
    description: str = (
        "Search for a regular expression pattern within the contents of files "
        "matching an optional include pattern."
    )
    args_schema = GrepSearchArgs

    def execute(self, **kwargs) -> str:
        try:
            args = self.args_schema(**kwargs)
        except Exception as e:
            return f"Error: Invalid arguments: {e}"

        base_dir = Path(args.project_dir) if args.project_dir else discover_root()
        search_dir = base_dir
        if args.dir_path:
            try:
                search_dir = validate_path_safety(args.dir_path, base_dir)
            except ValueError as e:
                return f"Error: {e}"

        if not search_dir.is_dir():
            return f"Error: Directory {args.dir_path or ''} does not exist."

        try:
            regex = re.compile(args.pattern)
        except re.error as e:
            return f"Error: Invalid regex pattern '{args.pattern}': {e}"

        matches = []
        max_matches = 100
        matches_count = 0

        for p in search_dir.rglob("*"):
            if matches_count >= max_matches:
                break
            if not p.is_file():
                continue

            try:
                validate_path_safety(p, base_dir)
            except ValueError:
                continue

            parts = p.parts
            if any(part in parts for part in (".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache")):
                continue

            if args.include_pattern and not fnmatch.fnmatch(p.name, args.include_pattern):
                continue

            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            lines = content.splitlines()
            for idx, line in enumerate(lines, start=1):
                if regex.search(line):
                    rel_path = p.relative_to(base_dir)
                    matches.append(f"{rel_path}:{idx}: {line.strip()}")
                    matches_count += 1
                    if matches_count >= max_matches:
                        break

        if not matches:
            return f"No matches found for pattern '{args.pattern}'."

        res = [f"Found {len(matches)} match(es):"] + matches
        if matches_count >= max_matches:
            res.append("... (limit of 100 matches reached)")
        return "\n".join(res)


class ListDirectoryArgs(BaseModel):
    dir_path: Optional[str] = Field(None, description="Directory path to list (relative to project root, defaults to project root)")
    project_dir: Optional[str] = Field(None, description="Base project directory path")


class FSListDirectoryTool(BaseTool):
    name: str = "list_directory"
    description: str = (
        "List names of files and subdirectories within a specified directory path."
    )
    args_schema = ListDirectoryArgs

    def execute(self, **kwargs) -> str:
        try:
            args = self.args_schema(**kwargs)
        except Exception as e:
            return f"Error: Invalid arguments: {e}"

        base_dir = Path(args.project_dir) if args.project_dir else discover_root()
        target_dir = base_dir
        if args.dir_path:
            try:
                target_dir = validate_path_safety(args.dir_path, base_dir)
            except ValueError as e:
                return f"Error: {e}"

        if not target_dir.is_dir():
            return f"Error: Directory {args.dir_path or ''} does not exist."

        try:
            entries = sorted(target_dir.iterdir())
        except Exception as e:
            return f"Error listing directory: {e}"

        files = []
        dirs = []
        for entry in entries:
            name = entry.name
            if name in (".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache"):
                continue
            if entry.is_dir():
                dirs.append(f"{name}/")
            elif entry.is_file():
                files.append(name)

        if not dirs and not files:
            return f"Directory {args.dir_path or '.'} is empty."

        res = []
        if dirs:
            res.append("Directories:")
            res.extend([f"  {d}" for d in dirs])
        if files:
            res.append("Files:")
            res.extend([f"  {f}" for f in files])
        return "\n".join(res)
