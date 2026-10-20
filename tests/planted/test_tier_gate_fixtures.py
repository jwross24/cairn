import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _corpus
import family_tier_gate as plantings
import family_tier_gate_refusals as refusals
from _corpus import MUST_FAIL, MUST_PASS

FAMILY_ENTRIES = plantings.ENTRIES + refusals.ENTRIES
CONTROL_IDS = {
    plantings.KEEP_IN_SAMPLE_ADMIT_ID,
    plantings.BOTH_KINDS_ADMIT_ID,
    plantings.TIER_THREE_ADMIT_ID,
    refusals.BOUNDARY_FIT_ID,
    refusals.WAIVER_NO_TICKET_ID,
}


def test_the_family_registers_nine_cold_plantings_and_five_controls():
    assert len(FAMILY_ENTRIES) == 14
    assert {entry.family for entry in FAMILY_ENTRIES} == {"tier_gate"}
    assert all(entry.owner_bead == plantings.OWNER for entry in FAMILY_ENTRIES)
    assert {e.test_id for e in FAMILY_ENTRIES if e.expected_class == MUST_PASS} == CONTROL_IDS
    assert sum(e.expected_class == MUST_FAIL for e in FAMILY_ENTRIES) == 9
    assert not any(entry.launches for entry in FAMILY_ENTRIES)


def test_every_tier_gate_entry_lands_its_expected_verdict_on_a_real_gate_and_substrate(planted_registry, observe):
    entries = tuple(e for e in planted_registry.entries if e.owner_bead == plantings.OWNER)
    assert set(entries) == set(FAMILY_ENTRIES)
    observations = {e.test_id: observe(e) for e in entries}
    for observation in observations.values():
        assert observation.violation is None and observation.error is None, observation
    result = _corpus.rollup(_corpus.registry(entries), observations)
    assert (result.plantings, result.controls) == (9, 5)
    assert result.escapes == (), result.report()
    assert observations[refusals.WAIVER_TICKET_PRESENT_ID].observed_verdict == refusals.TICKET_PRESENT
