import re
from pathlib import Path

import pytest

from cairn.profile import CostProfile, Evaluation, Production, ProfileUndeclared, SizeCost, Verification
from cairn.skills import toy_curve

BRIEF = Path(__file__).resolve().parent.parent.parent / "research" / "grounding" / "m0-stack-facts.md"
COLUMNS = (
    "bits",
    "seeds",
    "mean_tries",
    "sd_tries",
    "min_tries",
    "max_tries",
    "per_try_ms",
    "in_process_mean_wall_s",
    "mean_wall_s",
)


def committed_table():
    text = BRIEF.read_text()
    start = text.index("### 6a.")
    section = text[start:]
    end = re.search(r"^## ", section, re.MULTILINE)
    section = section[: end.start()] if end else section
    rows = {}
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if len(cells) == len(COLUMNS) and cells[0].isdigit():
            row = dict(zip(COLUMNS, cells, strict=True))
            rows[int(row["bits"])] = {
                k: (int(v) if k in ("bits", "seeds", "min_tries", "max_tries") else float(v)) for k, v in row.items()
            }
    return rows


def test_evaluate_40_equals_the_committed_table_mean_wall_s():
    table = committed_table()
    ev = toy_curve.COST_PROFILE.evaluate(40)
    assert isinstance(ev, Evaluation)
    assert ev.expected_wall_s == ev.expected_core_s == ev.expected_verification_core_s == table[40]["mean_wall_s"]


def test_profile_per_size_cites_the_committed_table():
    table = committed_table()
    profile = toy_curve.COST_PROFILE
    assert profile.declared_sizes() == (30, 40, 50, 60) == tuple(sorted(table))
    for bits, row in table.items():
        cost = profile.production.per_size[bits]
        assert row["seeds"] >= 50
        assert cost.mean_tries == row["mean_tries"] and cost.sd_tries == row["sd_tries"]
        assert cost.per_try_s == pytest.approx(row["per_try_ms"] / 1000, rel=1e-9)
        assert cost.mean_wall_s == row["mean_wall_s"]
    assert profile.tier == 0 and profile.production.model == "c_ln_p_tries"
    assert profile.verification == Verification(grade="Replayable", cost_model="same_as_production")
    assert "§6a" in profile.source and "seeds 50" in profile.source
    assert toy_curve.REPLAY_GRADE == "Replayable" and toy_curve.DO_NOT_CACHE is False


@pytest.mark.parametrize("bits", [0, 29, 45, 61, 10**6])
def test_profile_undeclared_sizes_raise_and_name_the_declared_ones(bits):
    with pytest.raises(ProfileUndeclared, match=rf"no size {bits}") as info:
        toy_curve.COST_PROFILE.evaluate(bits)
    assert info.value.bits == bits and info.value.declared == (30, 40, 50, 60)
    assert "[30, 40, 50, 60]" in str(info.value)


@pytest.mark.parametrize("bits", [True, "40", 40.0, None], ids=["bool", "str", "float", "none"])
def test_profile_refuses_non_int_sizes(bits):
    with pytest.raises(ProfileUndeclared, match="declares no size"):
        toy_curve.COST_PROFILE.evaluate(bits)


def test_evaluate_accepts_an_inputs_mapping_by_its_bits_field():
    assert toy_curve.COST_PROFILE.evaluate({"bits": 40, "seed": 7}) == toy_curve.COST_PROFILE.evaluate(40)
    with pytest.raises(ProfileUndeclared, match="no size None"):
        toy_curve.COST_PROFILE.evaluate({"seed": 7})


def test_synthetic_profile_evaluates_its_own_table():
    profile = CostProfile(
        0,
        Production("c_ln_p_tries", {8: SizeCost(1.0, 1.0, 0.001, 0.25)}),
        Verification("Replayable", "same_as_production"),
        "synthetic",
    )
    assert profile.evaluate(8) == Evaluation(0.25, 0.25, 0.25)
    with pytest.raises(ProfileUndeclared) as info:
        profile.evaluate(9)
    assert info.value.declared == (8,)


def test_a_constant_verification_cost_model_charges_its_own_core_seconds():
    profile = CostProfile(
        1,
        Production("c_sqrt_n_ops", {40: SizeCost(1.0, 0.5, 4e-6, 5.0)}),
        Verification("Verifiable", "constant", core_s=0.002),
        "synthetic",
    )
    assert profile.evaluate(40) == Evaluation(5.0, 5.0, 0.002)


@pytest.mark.parametrize("core_s", [None, 0, -1.0, True], ids=["none", "zero", "negative", "bool"])
def test_a_constant_verification_cost_model_needs_a_positive_core_s(core_s):
    profile = CostProfile(
        1,
        Production("c_sqrt_n_ops", {40: SizeCost(1.0, 0.5, 4e-6, 5.0)}),
        Verification("Verifiable", "constant", core_s=core_s),
        "synthetic",
    )
    with pytest.raises(ValueError, match="positive core_s"):
        profile.evaluate(40)


def test_unknown_verification_cost_model_is_refused():
    profile = CostProfile(
        0,
        Production("c_ln_p_tries", {8: SizeCost(1.0, 1.0, 0.001, 0.25)}),
        Verification("Replayable", "amortized"),
        "synthetic",
    )
    with pytest.raises(ValueError, match="unknown verification cost model 'amortized'"):
        profile.evaluate(8)
