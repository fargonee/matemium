"""Timing blueprint builders for Audio-First and Beat-Cadence paths."""

from __future__ import annotations

from typing import Any, Callable

from .models import NarrativeBlock, ProcessingMode, TimingBlueprint, TimingSegment
from .script_parser import parse_narrative_blocks, script_fingerprint
from .stubs import (
    TTSResult,
    WhisperTranscript,
    WhisperWord,
    stub_tts,
    stub_whisper_json,
    whisper_transcript_from_payload,
)

BASE_SECONDS_PER_WORD = 0.35
INTER_BLOCK_GAP = 0.4
PADDING_TAIL = 0.6
MS_PRECISION = 4

TTSCallable = Callable[[str], TTSResult]
WhisperCallable = Callable[[TTSResult, str], WhisperTranscript]


def round_ms(value: float) -> float:
    """Millisecond precision — 4 decimal places in seconds."""
    return round(value, MS_PRECISION)


def expected_mute_total_duration(segments: tuple[TimingSegment, ...]) -> float:
    """sum(waits) + (N-1)*gaps + tail padding — canonical mute total semantics."""
    if not segments:
        return PADDING_TAIL
    waits = sum(s.wait_duration for s in segments)
    gaps = INTER_BLOCK_GAP * max(0, len(segments) - 1)
    return round_ms(waits + gaps + PADDING_TAIL)


def _word_span(words: tuple[WhisperWord, ...] | list[WhisperWord]) -> tuple[float, float]:
    """Earliest start and latest end across a word collection (order-independent)."""
    if not words:
        return (0.0, 0.0)
    return (min(w.start for w in words), max(w.end for w in words))


def expected_audio_total_duration(transcript: WhisperTranscript) -> float:
    """Latest word end across payload + tail padding (independent of list order)."""
    if not transcript.words:
        return PADDING_TAIL
    _, audio_end = _word_span(transcript.words)
    return round_ms(audio_end + PADDING_TAIL)


def _round_segment(segment: TimingSegment) -> TimingSegment:
    """Round whisper segment times; allow zero-width instant cuts at boundaries."""
    start_time = round_ms(segment.start_time)
    raw_duration = segment.end_time - segment.start_time
    if raw_duration <= 0:
        return TimingSegment(
            block_id=segment.block_id,
            start_time=start_time,
            end_time=start_time,
            duration=0.0,
            wait_duration=0.0,
            source=segment.source,
            words=tuple(
                {
                    "word": w["word"],
                    "start": round_ms(float(w["start"])),
                    "end": round_ms(float(w["end"])),
                }
                for w in segment.words
            ),
        )
    duration = round_ms(raw_duration)
    end_time = round_ms(segment.end_time)
    return TimingSegment(
        block_id=segment.block_id,
        start_time=start_time,
        end_time=end_time,
        duration=duration,
        wait_duration=duration,
        source=segment.source,
        words=tuple(
            {
                "word": w["word"],
                "start": round_ms(float(w["start"])),
                "end": round_ms(float(w["end"])),
            }
            for w in segment.words
        ),
    )


def _word_slices_for_blocks(
    blocks: tuple[NarrativeBlock, ...],
    words: list[WhisperWord],
) -> tuple[tuple[WhisperWord, ...], ...]:
    """Pure word allocation — no timing logic; each word appears at most once."""
    n_blocks = len(blocks)
    n_words = len(words)
    slices: list[tuple[WhisperWord, ...]] = [() for _ in range(n_blocks)]
    if n_words == 0:
        return tuple(slices)

    if n_words < n_blocks:
        for idx in range(n_words):
            slices[idx] = (words[idx],)
        return tuple(slices)

    total_block_words = sum(max(b.word_count, 1) for b in blocks)
    word_idx = 0
    cumulative = 0
    for idx, block in enumerate(blocks):
        cumulative += max(block.word_count, 1)
        if idx == n_blocks - 1:
            slices[idx] = tuple(words[word_idx:])
        else:
            remaining_blocks = n_blocks - idx - 1
            words_remaining = n_words - word_idx
            max_take = max(1, words_remaining - remaining_blocks)
            want = max(1, round(cumulative / total_block_words * n_words))
            take = min(max(want, 1), max_take)
            slices[idx] = tuple(words[word_idx : word_idx + take])
            word_idx += take
    return tuple(slices)


def _make_whisper_segment(
    block: NarrativeBlock,
    start: float,
    end: float,
    words: tuple[WhisperWord, ...],
) -> TimingSegment:
    duration = max(end - start, 0.0)
    return TimingSegment(
        block_id=block.block_id,
        start_time=start,
        end_time=end,
        duration=duration,
        wait_duration=duration,
        source="whisper",
        words=tuple(w.as_dict() for w in words),
    )


def _segments_from_slices(
    blocks: tuple[NarrativeBlock, ...],
    slices: tuple[tuple[WhisperWord, ...], ...],
    audio_start: float,
    audio_end: float,
) -> tuple[TimingSegment, ...]:
    """Assemble segments: word slices use payload bounds; empty runs split interstitial gaps."""
    n = len(blocks)
    segments: list[TimingSegment] = []
    prev_end = audio_start
    idx = 0

    while idx < n:
        if slices[idx]:
            words = slices[idx]
            seg_start, seg_end = _word_span(words)
            segments.append(_make_whisper_segment(blocks[idx], seg_start, seg_end, words))
            prev_end = seg_end
            idx += 1
            continue

        run_start = idx
        while idx < n and not slices[idx]:
            idx += 1

        gap_end = slices[idx][0].start if idx < n and slices[idx] else audio_end
        gap = max(gap_end - prev_end, 0.0)
        run_len = idx - run_start
        cursor = prev_end

        for j in range(run_start, idx):
            if gap > 0:
                slot = gap / run_len
                seg_start = cursor
                seg_end = gap_end if j == idx - 1 else cursor + slot
            else:
                seg_start = prev_end
                seg_end = prev_end
            segments.append(_make_whisper_segment(blocks[j], seg_start, seg_end, ()))
            cursor = seg_end

        prev_end = gap_end

    return tuple(_round_segment(s) for s in segments)


def _sorted_transcript_words(transcript: WhisperTranscript) -> list[WhisperWord]:
    return sorted(transcript.words, key=lambda w: (w.start, w.end))


def _segments_from_whisper(
    blocks: tuple[NarrativeBlock, ...],
    transcript: WhisperTranscript,
) -> tuple[TimingSegment, ...]:
    """Map whisper words onto DIV blocks via pure slice + assembly pipeline."""
    words = _sorted_transcript_words(transcript)
    if not words or not blocks:
        return ()
    slices = _word_slices_for_blocks(blocks, words)
    audio_start, audio_end = _word_span(words)
    return _segments_from_slices(blocks, slices, audio_start, audio_end)


def _assemble_audio_blueprint(
    script: str,
    transcript: WhisperTranscript,
    *,
    fallback_duration: float | None = None,
) -> TimingBlueprint:
    """Shared assembly for stub and payload-driven audio blueprints."""
    blocks = parse_narrative_blocks(script)
    segments = _segments_from_whisper(blocks, transcript)
    if transcript.words:
        total = expected_audio_total_duration(transcript)
    elif segments:
        total = round_ms(segments[-1].end_time + PADDING_TAIL)
    elif fallback_duration is not None:
        total = round_ms(fallback_duration + PADDING_TAIL)
    else:
        total = PADDING_TAIL
    return TimingBlueprint(
        mode=ProcessingMode.AUDIO,
        segments=segments,
        total_duration=total,
        script_fingerprint=script_fingerprint(script),
    )


def parse_whisper_timing_blueprint(
    script: str,
    whisper_payload: dict[str, Any],
) -> TimingBlueprint:
    """Parse OpenAI Whisper JSON (word-level timestamps) into a TimingBlueprint.

    Accepts the in-memory dict produced by ``json.loads`` on an OpenAI
    ``verbose_json`` transcription response. Maps payload words onto script
    ``# ---DIV:`` narrative blocks proportionally, yielding millisecond-precise
    ``start_time``, ``end_time``, ``duration``, and ``wait_duration`` values
    that drive visual cuts and text reveals downstream.
    """
    transcript = whisper_transcript_from_payload(whisper_payload)
    return _assemble_audio_blueprint(script, transcript)


def build_audio_blueprint(
    script: str,
    *,
    tts_fn: TTSCallable = stub_tts,
    whisper_fn: WhisperCallable = stub_whisper_json,
) -> TimingBlueprint:
    """Audio Mode — TTS then Whisper JSON yields a precise TimingBlueprint."""
    tts_result = tts_fn(script)
    transcript = whisper_fn(tts_result, script)
    return _assemble_audio_blueprint(script, transcript, fallback_duration=tts_result.duration_hint)


def _mute_duration_for_block(block: NarrativeBlock) -> float:
    """Beat-cadence: word count scaled by mathematical complexity."""
    raw = block.word_count * BASE_SECONDS_PER_WORD * block.complexity_score
    if block.has_3d:
        raw += 1.5
    return round_ms(max(raw, 0.5))


def build_mute_blueprint(script: str) -> TimingBlueprint:
    """Mute Mode — deterministic wait(duration) layout from word/complexity math."""
    blocks = parse_narrative_blocks(script)
    segments: list[TimingSegment] = []
    cursor = 0.0
    for idx, block in enumerate(blocks):
        wait = _mute_duration_for_block(block)
        start = cursor
        end = cursor + wait
        segments.append(
            TimingSegment(
                block_id=block.block_id,
                start_time=round_ms(start),
                end_time=round_ms(end),
                duration=wait,
                wait_duration=wait,
                source="beat_cadence",
            )
        )
        cursor = end
        if idx < len(blocks) - 1:
            cursor += INTER_BLOCK_GAP

    segment_tuple = tuple(segments)
    total = expected_mute_total_duration(segment_tuple)
    return TimingBlueprint(
        mode=ProcessingMode.MUTE,
        segments=segment_tuple,
        total_duration=total,
        script_fingerprint=script_fingerprint(script),
    )


def instantiate_timing_blueprint(
    script: str,
    mode: ProcessingMode,
    *,
    tts_fn: TTSCallable = stub_tts,
    whisper_fn: WhisperCallable = stub_whisper_json,
) -> TimingBlueprint:
    """Phase 2 dispatcher — single entry for both processing paths."""
    if mode is ProcessingMode.AUDIO:
        return build_audio_blueprint(script, tts_fn=tts_fn, whisper_fn=whisper_fn)
    return build_mute_blueprint(script)