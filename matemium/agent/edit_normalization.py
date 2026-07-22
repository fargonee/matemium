"""Generic validation and minimization for model-proposed source edits."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re


SEARCH_MARKER = "<<<<<<< SEARCH"
DIVIDER_MARKER = "======="
REPLACE_MARKER = ">>>>>>> REPLACE"
MAX_PATCH_BYTES = 32 * 1024
MAX_CHANGED_LINES = 200
MAX_EXISTING_FILE_CHANGE_RATIO = 0.35


@dataclass(frozen=True)
class NormalizedEdit:
    description: str
    search: str | None = None
    replace: str | None = None
    full_file: str | None = None


def has_edit_proposal(content: str) -> bool:
    """Whether the response appears to contain a machine-applicable proposal."""
    return SEARCH_MARKER in content or _extract_python_file(content) is not None


def normalize_model_edit(content: str, current_source: str | None) -> NormalizedEdit | None:
    """Extract one applicable edit without understanding the user's edit category.

    Explicit search/replace proposals are accepted only when their search text is
    unique in the current source. Full-file proposals are reduced to the smallest
    enclosing changed range and rejected when that range is disproportionately
    large. New files may still use a full-file proposal.
    """
    explicit = _extract_search_replace(content)
    if explicit:
        return _validate_explicit(explicit, current_source)

    candidate = _extract_python_file(content)
    if candidate is None:
        return None
    if not current_source:
        return NormalizedEdit("Create the proposed scene file", full_file=candidate)
    return _minimize_full_file(current_source, candidate)


def _extract_search_replace(content: str) -> tuple[str, str] | None:
    search_idx = content.find(SEARCH_MARKER)
    if search_idx < 0:
        return None
    divider_idx = content.find(DIVIDER_MARKER, search_idx + len(SEARCH_MARKER))
    replace_idx = content.find(REPLACE_MARKER, divider_idx + len(DIVIDER_MARKER))
    if divider_idx < 0 or replace_idx < 0:
        return None
    search = content[search_idx + len(SEARCH_MARKER):divider_idx].strip("\n")
    replace = content[divider_idx + len(DIVIDER_MARKER):replace_idx].strip("\n")
    return search, replace


def _extract_python_file(content: str) -> str | None:
    blocks = re.findall(r"```(?:python)?\s*\n(.*?)\n\s*```", content, re.DOTALL)
    for block in blocks:
        if "class " in block and ("CanvasScene" in block or "CanvasBuilder" in block):
            return block.strip()
    return None


def _validate_explicit(proposal: tuple[str, str], current_source: str | None) -> NormalizedEdit | None:
    search, replace = proposal
    if not search or search == replace or len(search) + len(replace) > MAX_PATCH_BYTES:
        return None
    if current_source is None or current_source.count(search) != 1:
        return None
    changed_lines = max(len(search.splitlines()), len(replace.splitlines()))
    if changed_lines > MAX_CHANGED_LINES:
        return None
    return NormalizedEdit("Apply the validated targeted edit", search=search, replace=replace)


def _minimize_full_file(current: str, proposed: str) -> NormalizedEdit | None:
    if current == proposed:
        return None
    current_lines = current.splitlines(keepends=True)
    proposed_lines = proposed.splitlines(keepends=True)
    opcodes = SequenceMatcher(None, current_lines, proposed_lines, autojunk=False).get_opcodes()
    changed = [opcode for opcode in opcodes if opcode[0] != "equal"]
    if not changed:
        return None
    first, last = changed[0], changed[-1]
    old_start, old_end = first[1], last[2]
    new_start, new_end = first[3], last[4]

    # Include one unchanged line of context where available. This makes the
    # precondition easier to review while retaining a unique exact match.
    old_start = max(0, old_start - 1)
    new_start = max(0, new_start - 1)
    old_end = min(len(current_lines), old_end + 1)
    new_end = min(len(proposed_lines), new_end + 1)
    search = "".join(current_lines[old_start:old_end]).rstrip("\n")
    replace = "".join(proposed_lines[new_start:new_end]).rstrip("\n")
    span_lines = max(old_end - old_start, new_end - new_start)
    changed_lines = sum(max(old_to - old_from, new_to - new_from) for _, old_from, old_to, new_from, new_to in changed)
    ratio = changed_lines / max(1, len(current_lines))
    if (
        not search
        or search == replace
        or current.count(search) != 1
        or span_lines > MAX_CHANGED_LINES
        or ratio > MAX_EXISTING_FILE_CHANGE_RATIO
        or len(search) + len(replace) > MAX_PATCH_BYTES
    ):
        return None
    return NormalizedEdit(
        "Apply the minimal validated diff extracted from the proposal",
        search=search,
        replace=replace,
    )
