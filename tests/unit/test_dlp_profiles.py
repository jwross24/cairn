import re
from pathlib import Path

import pytest

from cairn.profile import CONSTANT, SAME_AS_PRODUCTION, MemoryProfile
from cairn.skills import bsgs, instance_maker, rho_dp

NOTE = Path(__file__).resolve().parent.parent.parent / "research" / "grounding" / "m1-dlp-skill-costs.md"
SECTIONS = {rho_dp: "## 1.", bsgs: "## 3.", instance_maker: "## 4."}


def committed_table(module):
    text = NOTE.read_text()
    start = text.index(SECTIONS[module])
    section = text[start + 1 :]
    end = re.search(r"^## ", section, re.MULTILINE)
    section = section[: end.start()] if end else section
    header = None
    rows = {}
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if cells[0].isdigit():
            rows[int(cells[0])] = dict(zip(header, cells, strict=True))
    return rows


@pytest.mark.parametrize("module", [rho_dp, bsgs, instance_maker], ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def test_every_declared_size_is_the_committed_measurement(module):
    table = committed_table(module)
    profile = module.COST_PROFILE
    assert profile.declared_sizes() == tuple(sorted(table))
    for bits, row in table.items():
        cost = profile.production.per_size[bits]
        assert cost.mean_tries == float(row["mean ops"])
        assert cost.sd_tries == float(row["sd ops"])
        assert cost.per_try_s == pytest.approx(float(row["per-op us"]) * 1e-6, rel=1e-9)
        assert cost.mean_wall_s == float(row["mean wall s"])
        assert int(row["seeds"]) >= 2
    assert "m1-dlp-skill-costs.md" in profile.source and "cairn measure dlp" in profile.source


def test_rho_dp_declares_a_constant_witness_check_at_the_fifty_bit_measurement():
    table = committed_table(rho_dp)
    verification = rho_dp.COST_PROFILE.verification
    assert verification.cost_model == CONSTANT and verification.grade == "Verifiable"
    assert verification.core_s == float(table[50]["verify s"])
    assert rho_dp.COST_PROFILE.evaluate(50).expected_verification_core_s == verification.core_s
    assert rho_dp.COST_PROFILE.tier == 1 and rho_dp.COST_PROFILE.memory is None


def test_bsgs_declares_its_measured_memory_profile():
    table = committed_table(bsgs)
    memory = bsgs.COST_PROFILE.memory
    assert isinstance(memory, MemoryProfile) and memory.model == bsgs.MEMORY_MODEL
    assert memory.bytes_per_entry_bounds == (16.0, 24.0)
    for bits, row in table.items():
        assert memory.measured_bytes_per_entry[bits] == float(row["bytes/entry"])
        assert 16.0 <= memory.measured_bytes_per_entry[bits] <= 24.0
        assert f"{memory.measured_maxrss_bytes[bits] / 2**20:.1f}" == row["maxrss MB"]
    assert bsgs.COST_PROFILE.verification.cost_model == SAME_AS_PRODUCTION


def test_the_instance_maker_stays_tier_zero_through_the_completion_rung():
    profile = instance_maker.COST_PROFILE
    assert profile.tier == 0 and profile.declared_sizes() == (28, 30, 40, 50, 60)
    assert all(cost.mean_wall_s < 1.0 for cost in profile.production.per_size.values())
    assert profile.verification.cost_model == SAME_AS_PRODUCTION


def test_the_sixty_bit_cap_in_the_note_is_two_to_the_thirty_times_the_fifty_bit_bytes_per_entry():
    text = NOTE.read_text()
    memory = bsgs.COST_PROFILE.memory
    assert memory is not None
    bytes_per_entry = memory.measured_bytes_per_entry[50]
    assert f"({bytes_per_entry}), is {int(2**30 * bytes_per_entry)} bytes" in text
