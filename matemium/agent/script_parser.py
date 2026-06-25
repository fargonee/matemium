"""Script parsing and mathematical complexity scoring for beat-cadence timing."""

from __future__ import annotations

import re
from hashlib import sha256

from .models import NarrativeBlock

DIV_MARKER_RE = re.compile(r"^#\s*---DIV:\s*(.+?)---\s*$", re.MULTILINE)
LATEX_RAW_RE = re.compile(r'r"([^"]+)"|r\'([^\']+)\'')
LATEX_INLINE_RE = re.compile(r"\\(?:frac|sqrt|int|sum|nabla|vec|partial|cdot|times)\b")
ADD_MATH_RE = re.compile(r"add_math\s*\(\s*r?[\"']([^\"']+)[\"']")
ADD_3D_RE = re.compile(r"add_3d\s*\(")


def script_fingerprint(script: str) -> str:
    return sha256(script.encode("utf-8")).hexdigest()[:16]


def extract_div_markers(script: str) -> tuple[str, ...]:
    return tuple(m.group(1).strip() for m in DIV_MARKER_RE.finditer(script))


def _extract_latex_fragments(text: str) -> tuple[str, ...]:
    fragments: list[str] = []
    for match in ADD_MATH_RE.finditer(text):
        fragments.append(match.group(1))
    for match in LATEX_RAW_RE.finditer(text):
        frag = match.group(1) or match.group(2) or ""
        if any(c in frag for c in "=^\\"):
            fragments.append(frag)
    return tuple(dict.fromkeys(fragments))


def _word_count(text: str) -> int:
    tokens = re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?", text)
    return max(len(tokens), 1)


def complexity_score(text: str, latex_fragments: tuple[str, ...], has_3d: bool) -> float:
    """Weighted reading-cadence multiplier for mathematical content."""
    score = 1.0
    score += len(latex_fragments) * 0.8
    for frag in latex_fragments:
        score += len(LATEX_INLINE_RE.findall(frag)) * 0.35
        score += frag.count("^") * 0.15
        score += frag.count("_") * 0.1
    if has_3d:
        score += 2.0
    equation_lines = sum(1 for line in text.splitlines() if "=" in line and "\\" in line)
    score += equation_lines * 1.2
    return round(score, 4)


def parse_narrative_blocks(script: str) -> tuple[NarrativeBlock, ...]:
    """Split script into DIV-bounded narrative blocks with complexity metadata."""
    markers = list(DIV_MARKER_RE.finditer(script))
    if not markers:
        body = script.strip()
        latex = _extract_latex_fragments(body)
        has_3d = bool(ADD_3D_RE.search(body))
        return (
            NarrativeBlock(
                block_id="block_0",
                title="Main",
                body=body,
                latex_fragments=latex,
                has_3d=has_3d,
                word_count=_word_count(body),
                complexity_score=complexity_score(body, latex, has_3d),
            ),
        )

    blocks: list[NarrativeBlock] = []
    for idx, match in enumerate(markers):
        title = match.group(1).strip()
        start = match.end()
        end = markers[idx + 1].start() if idx + 1 < len(markers) else len(script)
        body = script[start:end].strip()
        latex = _extract_latex_fragments(body)
        has_3d = bool(ADD_3D_RE.search(body))
        blocks.append(
            NarrativeBlock(
                block_id=f"block_{idx}",
                title=title,
                body=body,
                latex_fragments=latex,
                has_3d=has_3d,
                word_count=_word_count(body),
                complexity_score=complexity_score(body, latex, has_3d),
            )
        )
    return tuple(blocks)