import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _corpus
import family_escrow_yank as family
from _corpus import MUST_FAIL


def test_the_family_registers_four_cold_must_fail_plantings():
    assert len(family.ENTRIES) == 4
    assert all(entry.expected_class == MUST_FAIL for entry in family.ENTRIES)
    assert all(entry.owner_bead == family.OWNER for entry in family.ENTRIES)
    assert [entry.test_id for entry in family.ENTRIES] == [
        family.BUDGET_ID,
        family.SETTLEMENT_ID,
        family.DEFERRED_ID,
        family.YANK_ID,
    ]
    assert family.ENTRIES[0].launches is False
    assert all(entry.launches for entry in family.ENTRIES[1:])


def test_the_family_lands_four_refusals_through_real_rows_and_reads(planted_registry, observe):
    entries = tuple(entry for entry in planted_registry.entries if entry.owner_bead == family.OWNER)
    assert entries == family.ENTRIES
    observations = {entry.test_id: observe(entry) for entry in entries}
    for observation in observations.values():
        assert observation.violation is None and observation.error is None, observation
        assert all(skip == 1 for _, skip, _ in observation.attempts), observation
    assert observations[family.BUDGET_ID].attempts == ()
    assert len(observations[family.SETTLEMENT_ID].attempts) == 3
    assert len(observations[family.DEFERRED_ID].attempts) == 2
    assert len(observations[family.YANK_ID].attempts) == 3
    result = _corpus.rollup(_corpus.registry(entries), observations)
    assert (result.plantings, result.controls) == (4, 0)
    assert result.escapes == ()
