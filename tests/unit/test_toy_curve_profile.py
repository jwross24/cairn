import re
import subprocess
from pathlib import Path

import pytest

from cairn.profile import CostProfile, Evaluation, ProfileUndeclared, Production, SizeCost, Verification
from cairn.skills import toy_curve

BRIEF = Path(__file__).resolve().parent.parent.parent / "research" / "grounding" / "m0-stack-facts.md"
COLUMNS = ("bits", "seeds", "mean_tries", "sd_tries", "min_tries", "max_tries", "per_try_ms", "in_process_mean_wall_s", "mean_wall_s")


def committed_table():
    text = BRIEF.read_text()
    start = text.index("### 6a.")
    section = text[start:]
    end = re.search(r"^## ", section, re.M)
    section = section[: end.start()] if end else section
    rows = {}
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if len(cells) == len(COLUMNS) and cells[0].isdigit():
            row = dict(zip(COLUMNS, cells))
            rows[int(row["bits"])] = {k: (int(v) if k in ("bits", "seeds", "min_tries", "max_tries") else float(v)) for k, v in row.items()}
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
def test_profile_undeclared_sizes_raise_before_any_spawn(bits, monkeypatch):
    spawned = []
    real_popen = subprocess.Popen

    class Spy(real_popen):
        def __init__(self, args, *a, **kw):
            spawned.append(list(args))
            super().__init__(args, *a, **kw)

    monkeypatch.setattr(subprocess, "Popen", Spy)
    with pytest.raises(ProfileUndeclared, match=rf"no size {bits}"):
        toy_curve.COST_PROFILE.evaluate(bits)
    assert spawned == []


@pytest.mark.parametrize("bits", [True, "40", 40.0, None])
def test_profile_refuses_non_int_sizes(bits):
    with pytest.raises(ProfileUndeclared):
        toy_curve.COST_PROFILE.evaluate(bits)


def test_evaluate_accepts_an_inputs_mapping_by_its_bits_field():
    assert toy_curve.COST_PROFILE.evaluate({"bits": 40, "seed": 7}) == toy_curve.COST_PROFILE.evaluate(40)
    with pytest.raises(ProfileUndeclared):
        toy_curve.COST_PROFILE.evaluate({"seed": 7})


def test_synthetic_profile_evaluates_its_own_table():
    profile = CostProfile(0, Production("c_ln_p_tries", {8: SizeCost(1.0, 1.0, 0.001, 0.25)}), Verification("Replayable", "same_as_production"), "synthetic")
    assert profile.evaluate(8) == Evaluation(0.25, 0.25, 0.25)
    with pytest.raises(ProfileUndeclared) as info:
        profile.evaluate(9)
    assert info.value.declared == (8,)
