from __future__ import annotations

from pathlib import Path


def validate_path_safety(file_path: Path | str, base_dir: Path | str) -> Path:
    """
    Ensure the file_path is safe, fully resolved, and within base_dir (prevents path traversal).
    Raises ValueError if unsafe.
    """
    resolved_base = Path(base_dir).resolve()
    
    p = Path(file_path)
    if not p.is_absolute():
        resolved_path = (resolved_base / p).resolve()
    else:
        resolved_path = p.resolve()
        
    try:
        resolved_path.relative_to(resolved_base)
    except ValueError:
        raise ValueError(
            f"Unsafe path traversal attempt blocked: Path {file_path} is outside of base directory {base_dir}"
        )
        
    return resolved_path
