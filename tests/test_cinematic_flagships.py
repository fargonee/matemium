"""Focused contracts for the three world-first flagship productions."""

from __future__ import annotations

import pytest

from projects.dna_to_protein.helpers import biology_world_state, sequence_records, transcribe
from projects.feedback_control.helpers import (
    TUNINGS,
    sample_near,
    simulate,
    vehicle_world_state,
    world_sample,
)
from projects.sn2_reaction.helpers import energy_marker, reaction_world_state


def test_sn2_world_and_energy_share_transition_state() -> None:
    world = reaction_world_state(0.5, cue="energy", show_energy=True)
    marker = energy_marker("transition")[0]

    assert world["progress"] == 0.5
    assert world["cue"] == "energy"
    assert world["show_energy"] is True
    assert world["comparison"] is False
    assert marker["point"][0] == pytest.approx(world["progress"])


def test_feedback_world_snapshot_uses_the_dashboard_simulation() -> None:
    state = vehicle_world_state(
        6.0,
        feedback=True,
        tuning="balanced",
        stage="correction",
    )
    actual = world_sample(state)
    gains = TUNINGS["balanced"]
    expected = sample_near(
        simulate(float(gains["kp"]), float(gains["ki"]), feedback=True),
        6.0,
    )

    assert actual == expected
    assert state["stage"] == "correction"


def test_dna_world_sequence_identity_is_generated_from_one_source() -> None:
    state = biology_world_state("translation", sequence_index=4)
    records = sequence_records()

    assert state == {"stage": "translation", "sequence_index": 4}
    assert " ".join(record["rna"] for record in records) == transcribe()
    assert [record["amino"] for record in records] == ["Met", "Pro", "Lys", "Gly", "Stop"]
