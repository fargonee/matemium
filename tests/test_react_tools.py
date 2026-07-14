from __future__ import annotations

import pytest
from pathlib import Path

from matemium.agent.tools.safety import validate_path_safety
from matemium.agent.tools.fs import FSReadSliceTool, FSGrepSearchTool, FSListDirectoryTool
from matemium.agent.tools.mod import FSApplyDiffPatchTool, FSRunCompilerTool


def test_validate_path_safety(tmp_path: Path):
    base_dir = tmp_path / "project"
    base_dir.mkdir()
    
    # Create valid files
    safe_file = base_dir / "scenes.py"
    safe_file.write_text("print('hello')", encoding="utf-8")
    
    # Safe checks
    assert validate_path_safety("scenes.py", base_dir) == safe_file.resolve()
    assert validate_path_safety(str(safe_file), base_dir) == safe_file.resolve()
    
    # Unsafe checks (path traversal)
    with pytest.raises(ValueError, match="Unsafe path traversal attempt blocked"):
        validate_path_safety("../outside.txt", base_dir)
        
    with pytest.raises(ValueError, match="Unsafe path traversal attempt blocked"):
        validate_path_safety("/etc/passwd", base_dir)


def test_read_file_slice_tool(tmp_path: Path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    
    test_file = project_dir / "test.txt"
    lines = [f"Line {i}" for i in range(1, 11)]
    test_file.write_text("\n".join(lines), encoding="utf-8")
    
    tool = FSReadSliceTool()
    
    # Success read
    res = tool.execute(file_path="test.txt", start_line=3, end_line=5, project_dir=str(project_dir))
    assert "Line 3" in res
    assert "Line 4" in res
    assert "Line 5" in res
    assert "Line 2" not in res
    assert "Line 6" not in res
    
    # Invalid line bounds
    res_err = tool.execute(file_path="test.txt", start_line=15, end_line=20, project_dir=str(project_dir))
    assert "Error:" in res_err
    
    # Path traversal block
    res_unsafe = tool.execute(file_path="../outside.txt", start_line=1, project_dir=str(project_dir))
    assert "Error: Unsafe path traversal" in res_unsafe


def test_grep_search_tool(tmp_path: Path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    
    file_a = project_dir / "a.py"
    file_a.write_text("class MyScene(CanvasScene):\n    pass", encoding="utf-8")
    
    file_b = project_dir / "b.txt"
    file_b.write_text("Some regular text here", encoding="utf-8")
    
    tool = FSGrepSearchTool()
    
    # Find match
    res = tool.execute(pattern="MyScene", project_dir=str(project_dir))
    assert "a.py:1: class MyScene(CanvasScene):" in res
    
    # Find match with include pattern
    res_glob = tool.execute(pattern="MyScene", include_pattern="*.py", project_dir=str(project_dir))
    assert "a.py" in res_glob
    
    # No match
    res_none = tool.execute(pattern="MissingPattern", project_dir=str(project_dir))
    assert "No matches found" in res_none


def test_list_directory_tool(tmp_path: Path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    
    (project_dir / "subdir").mkdir()
    (project_dir / "file.py").write_text("", encoding="utf-8")
    (project_dir / ".git").mkdir() # Should be ignored
    
    tool = FSListDirectoryTool()
    
    res = tool.execute(project_dir=str(project_dir))
    assert "subdir/" in res
    assert "file.py" in res
    assert ".git" not in res


def test_apply_diff_patch_tool(tmp_path: Path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    
    scenes_file = project_dir / "scenes.py"
    scenes_file.write_text(
        "def part_intro(b):\n    b.add_heading('Hello')\n",
        encoding="utf-8"
    )
    
    tool = FSApplyDiffPatchTool()
    
    # Success apply
    res = tool.execute(
        file_path="scenes.py",
        search="b.add_heading('Hello')",
        replace="b.add_heading('Hello World')",
        project_dir=str(project_dir)
    )
    assert "Successfully applied patch" in res
    assert "Hello World" in scenes_file.read_text(encoding="utf-8")
    
    # Ambiguous search patch error
    scenes_file.write_text("x = 5\nx = 5\n", encoding="utf-8")
    res_err = tool.execute(
        file_path="scenes.py",
        search="x = 5",
        replace="x = 10",
        project_dir=str(project_dir)
    )
    assert "Error applying patch" in res_err


def test_run_compiler_tool(tmp_path: Path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    
    scenes_file = project_dir / "scenes.py"
    scenes_file.write_text("import invalid_import_name_abc_123", encoding="utf-8")
    
    tool = FSRunCompilerTool()
    
    res = tool.execute(project_dir=str(project_dir))
    # It should report compilation failure
    assert "Compilation Failed" in res
