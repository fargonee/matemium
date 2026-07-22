"""Injectable stubs for TTS, Whisper, and sub-agent surfaces."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Callable

from .models import (
    DecoupledArtifacts,
    DirectorOutput,
    ProcessingMode,
    ProjectSession,
)
from .script_parser import extract_div_markers

WORD_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?")

_TOPIC_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(integral|area under|antiderivative)\b", re.I), "integral"),
    (re.compile(r"\b(derivative|slope|rate of change|differentiat)\b", re.I), "derivative"),
    (re.compile(r"\b(pythagor|triangle|hypotenuse)\b", re.I), "pythagorean"),
    (re.compile(r"\b(quadratic|factor|roots?|parabola)\b", re.I), "quadratic"),
    (re.compile(r"\b(vector|matrix|linear algebra)\b", re.I), "linear_algebra"),
]


@dataclass(frozen=True)
class TTSResult:
    """Deterministic pseudo-audio artifact from script content."""

    script_hash: str
    duration_hint: float
    voice_id: str = "matemium-director-v1"


@dataclass(frozen=True)
class WhisperWord:
    word: str
    start: float
    end: float

    def as_dict(self) -> dict[str, Any]:
        return {"word": self.word, "start": self.start, "end": self.end}


@dataclass(frozen=True)
class WhisperTranscript:
    words: tuple[WhisperWord, ...]
    language: str = "en"

    def as_json(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "words": [w.as_dict() for w in self.words],
        }


def _coerce_whisper_word(entry: dict[str, Any]) -> WhisperWord | None:
    """Normalize a single OpenAI verbose_json word entry."""
    if "start" not in entry or "end" not in entry:
        return None
    word = str(entry.get("word", entry.get("text", ""))).strip()
    if not word:
        return None
    return WhisperWord(
        word=word,
        start=round(float(entry["start"]), 4),
        end=round(float(entry["end"]), 4),
    )


def extract_whisper_words_from_payload(payload: dict[str, Any]) -> tuple[WhisperWord, ...]:
    """Extract word-level timestamps from an OpenAI Whisper verbose_json payload."""
    raw_words: list[dict[str, Any]] = list(payload.get("words") or [])
    if not raw_words:
        for segment in payload.get("segments") or []:
            if isinstance(segment, dict):
                raw_words.extend(segment.get("words") or [])

    words: list[WhisperWord] = []
    for entry in raw_words:
        if not isinstance(entry, dict):
            continue
        parsed = _coerce_whisper_word(entry)
        if parsed is not None:
            words.append(parsed)
    return tuple(words)


def whisper_transcript_from_payload(payload: dict[str, Any]) -> WhisperTranscript:
    """Build a WhisperTranscript from an in-memory OpenAI Whisper JSON dict."""
    language = str(payload.get("language", "en"))
    return WhisperTranscript(words=extract_whisper_words_from_payload(payload), language=language)


def stub_tts(script: str) -> TTSResult:
    """Mock TTS generation — deterministic hash and duration hint, no network I/O."""
    digest = hashlib.sha256(script.encode("utf-8")).hexdigest()
    word_count = len(WORD_TOKEN_RE.findall(script))
    duration_hint = max(word_count * 0.38, 1.5)
    return TTSResult(script_hash=digest, duration_hint=duration_hint)


def stub_whisper_json(tts_result: TTSResult, script: str) -> WhisperTranscript:
    """Mock Whisper word-level timestamp extraction from script tokens."""
    tokens = WORD_TOKEN_RE.findall(script)
    if not tokens:
        tokens = ["silence"]

    base_pace = tts_result.duration_hint / len(tokens)
    words: list[WhisperWord] = []
    cursor = 0.0
    for token in tokens:
        duration = base_pace * (1.0 + (len(token) % 3) * 0.05)
        words.append(WhisperWord(word=token, start=round(cursor, 4), end=round(cursor + duration, 4)))
        cursor += duration
    return WhisperTranscript(words=tuple(words))


def _detect_topic(user_prompt: str) -> str:
    for pattern, topic in _TOPIC_PATTERNS:
        if pattern.search(user_prompt):
            return topic
    digest = hashlib.sha256(user_prompt.encode("utf-8")).hexdigest()
    return ("quadratic", "integral", "derivative", "pythagorean", "linear_algebra")[
        int(digest[:2], 16) % 5
    ]


def _topic_script(topic: str, heading: str, mode: ProcessingMode) -> str:
    """Build pedagogically distinct scripts per detected topic."""
    pacing = (
        "Audio-first pacing: kinetic subtitles align to whisper anchors."
        if mode is ProcessingMode.AUDIO
        else "Beat-cadence pacing: waits derive from reading complexity."
    )

    if topic == "integral":
        return f"""# ---DIV: Geometric intuition---
def part_area(b):
    b.add_heading("{heading}")
    b.add_body("Picture area as stacked rectangles hugging a curve.")
    b.add_body("{pacing}")
    b.add_math(r"\\int_0^1 x^2 \\, dx")

# ---DIV: Riemann refinement---
def part_riemann(b):
    b.add_body("Finer partitions tighten the underestimate.")
    b.add_math(r"\\sum_{{i=1}}^n f(x_i)\\,\\Delta x")
    b.add_observation("The limit of sums becomes the integral.")

# ---DIV: Evaluation---
def part_eval(b):
    b.add_math(r"\\int_0^1 x^2 \\, dx = \\frac{{1}}{{3}}")
    b.add_text("Area under x² from 0 to 1 is exactly one third.", after_3d=False)
"""

    if topic == "derivative":
        return f"""# ---DIV: Secant to tangent---
def part_secant(b):
    b.add_heading("{heading}")
    b.add_body("Zoom in: average rate of change becomes instantaneous slope.")
    b.add_math(r"f'(x) = \\lim_{{h\\to 0}} \\frac{{f(x+h)-f(x)}}{{h}}")

# ---DIV: Power rule---
def part_power(b):
    b.add_body("{pacing}")
    b.add_math(r"\\frac{{d}}{{dx}} x^n = n x^{{n-1}}")
    b.add_3d("z = x^2 - y^2")
    b.add_text("Slope field intuition for x².", after_3d=True)
"""

    if topic == "pythagorean":
        return f"""# ---DIV: Triangle setup---
def part_triangle(b):
    b.add_heading("{heading}")
    b.add_body("A right triangle hides a surprising area identity.")
    b.add_math(r"a^2 + b^2 = c^2")

# ---DIV: Visual proof---
def part_proof(b):
    b.add_body("{pacing}")
    b.add_math(r"c^2 = a^2 + b^2")
    b.add_observation("Rearrange four congruent triangles inside a square.")
"""

    if topic == "linear_algebra":
        return f"""# ---DIV: Vector basis---
def part_basis(b):
    b.add_heading("{heading}")
    b.add_body("Every point in the plane is a weighted sum of basis vectors.")
    b.add_math(r"\\vec{{v}} = a\\vec{{i}} + b\\vec{{j}}")

# ---DIV: Transformation---
def part_transform(b):
    b.add_body("{pacing}")
    b.add_math(r"\\begin{{bmatrix}} x' \\\\ y' \\end{{bmatrix}} = A \\begin{{bmatrix}} x \\\\ y \\end{{bmatrix}}")
    b.add_3d("z = x + y")
    b.add_text("Linear maps stretch and rotate space.", after_3d=True)
"""

    return f"""# ---DIV: Hook---
def part_hook(b):
    b.add_heading("{heading}")
    b.add_body("A parabola encodes two roots hiding in plain sight.")
    b.add_body("{pacing}")

# ---DIV: Factoring---
def part_factor(b):
    b.add_math(r"x^2 - 5x + 6 = 0")
    b.add_observation("Seek factors of 6 that sum to -5.")

# ---DIV: Solution---
def part_solution(b):
    b.add_math(r"x^2 - 5x + 6 = (x-2)(x-3)")
    b.add_3d("z = x^2 - y^2")
    b.add_text("Therefore x = 2 or x = 3.", after_3d=True)
"""


def stub_director_agent(user_prompt: str, mode: ProcessingMode) -> DirectorOutput:
    """Phase 1 stub — topic-aware pedagogical script with DIV boundaries."""
    topic = _detect_topic(user_prompt)
    heading = user_prompt.strip()[:80] or "Mathematical insight"
    script = _topic_script(topic, heading, mode)
    div_markers = extract_div_markers(script)
    return DirectorOutput(
        script=script,
        mode=mode,
        div_markers=div_markers,
        tone="pedagogical",
    )


def stub_engineer_agent(session: ProjectSession) -> DecoupledArtifacts:
    """Phase 3 stub — decoupled configs + on-disk scenes.py/helpers.py via patch engine."""
    assert session.director_output is not None
    assert session.blueprint is not None
    from .writer import write_decoupled_project

    result = write_decoupled_project(
        session.project_dir,
        session.director_output.script,
        session.blueprint,
        session=session,
    )
    return result.artifacts


CompileFn = Callable[[], tuple[bool, str]]
PatchFn = Callable[[str], None]


def default_compile_success() -> tuple[bool, str]:
    return True, ""


def sidecar_compile_for(project_dir: Path | str) -> CompileFn:
    """Production compile_fn — PyInstaller sidecar check_project on workspace."""
    from pathlib import Path

    from .critic import make_sidecar_compile_fn, sidecar_binary_available

    if sidecar_binary_available():
        return make_sidecar_compile_fn(Path(project_dir))
    return default_compile_success


def default_visual_qc() -> bool:
    return True
