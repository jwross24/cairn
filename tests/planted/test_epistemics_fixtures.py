import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _corpus
import family_epistemics as family
from _corpus import MUST_FAIL, MUST_PASS


def test_the_family_registers_e_through_i_and_five_m_controls():
    assert len(family.ENTRIES) == 10
    assert {entry.family for entry in family.ENTRIES} == {"e", "f", "g", "h", "i", "m"}
    assert all(entry.owner_bead == family.OWNER for entry in family.ENTRIES)
    assert [entry.test_id for entry in family.ENTRIES] == [
        family.E_ID,
        family.F_ID,
        family.G_ID,
        family.H_ID,
        family.I_ID,
        family.M_ADMIT_ID,
        family.M_COST_STAT_ID,
        family.M_COST_REPRO_ID,
        family.M_AUTHOR_ID,
        family.M_AUDIT_ID,
    ]
    by_id = {entry.test_id: entry for entry in family.ENTRIES}
    assert all(
        by_id[test_id].expected_class == MUST_FAIL
        for test_id in (
            family.E_ID,
            family.F_ID,
            family.G_ID,
            family.H_ID,
            family.I_ID,
            family.M_COST_STAT_ID,
            family.M_COST_REPRO_ID,
            family.M_AUTHOR_ID,
            family.M_AUDIT_ID,
        )
    )
    assert by_id[family.M_ADMIT_ID].expected_class == MUST_PASS
    assert by_id[family.M_ADMIT_ID].expected_verdict == family.ADMIT
    assert not by_id[family.G_ID].launches
    assert not by_id[family.H_ID].launches
    assert not by_id[family.M_COST_STAT_ID].launches
    assert all(
        by_id[test_id].launches
        for test_id in (
            family.E_ID,
            family.F_ID,
            family.I_ID,
            family.M_ADMIT_ID,
            family.M_COST_REPRO_ID,
            family.M_AUTHOR_ID,
            family.M_AUDIT_ID,
        )
    )


def test_every_epistemics_planting_lands_on_real_cold_records(planted_registry, observe):
    entries = tuple(entry for entry in planted_registry.entries if entry.owner_bead == family.OWNER)
    assert entries == family.ENTRIES
    assert {entry.family for entry in entries} == {"e", "f", "g", "h", "i", "m"}
    observations = {entry.test_id: observe(entry) for entry in entries}
    for observation in observations.values():
        assert observation.violation is None and observation.error is None, observation
        assert observation.observed_verdict in (family.REJECT, family.ADMIT), observation
        assert all(skip == 1 and status == "OK" for _, skip, status in observation.attempts), observation
    assert observations[family.E_ID].observed_verdict == family.REJECT
    assert len(observations[family.E_ID].attempts) == 2
    assert len(observations[family.F_ID].attempts) == 1
    assert observations[family.G_ID].attempts == ()
    assert observations[family.H_ID].attempts == ()
    assert len(observations[family.I_ID].attempts) == 2
    assert observations[family.M_ADMIT_ID].observed_verdict == family.ADMIT
    assert len(observations[family.M_ADMIT_ID].attempts) == 3
    assert observations[family.M_COST_STAT_ID].attempts == ()
    assert len(observations[family.M_COST_REPRO_ID].attempts) == 2
    assert len(observations[family.M_AUTHOR_ID].attempts) == 2
    assert len(observations[family.M_AUDIT_ID].attempts) == 2
    result = _corpus.rollup(_corpus.registry(entries), observations)
    assert (result.plantings, result.controls) == (9, 1)
    assert result.escapes == ()
