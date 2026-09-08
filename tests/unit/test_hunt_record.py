import json

import pytest

from cairn import claims, hunt, instances, substrate


def test_uniform_integer_sampler_is_deterministic_and_supports_wide_ranges():
    distribution = hunt.Distribution({"n": (0, 1 << 64)})

    first = hunt.sample_point(distribution, 17)
    second = hunt.sample_point(distribution, 17)

    assert first == second
    assert 0 <= first["n"] <= 1 << 64


def test_uniform_integer_sampler_rejects_a_planted_word_before_accepting_the_next_hash_word():
    distribution = hunt.Distribution({"n": (0, 2)})

    assert hunt._uniform_word(7, "n", 0, 2) == 3
    assert hunt._uniform_word(7, "n", 1, 2) == 1
    assert hunt.sample_point(distribution, 7) == {"n": 1}


def test_hunt_seed_is_domain_separated_from_ladder_seed():
    nonce = "ab" * 32
    hypothesis = "cd" * 32

    assert hunt.hunt_trial_seed(nonce, hypothesis, 0) != instances.trial_seed(nonce, hypothesis, 28, 0)


def test_unsupported_distribution_is_refused():
    with pytest.raises(hunt.DistributionRefused):
        hunt.Distribution({"n": (1, 2)}, kind="weighted")


def test_plan_rejects_distribution_outside_declared_family_bounds():
    with pytest.raises(hunt.PlanRefused):
        hunt.HuntPlan(
            "s" * 64,
            "h" * 64,
            hunt.Distribution({"n": (4, 8)}),
            2,
            {"n": (5, 8)},
        )


def test_record_carries_every_trial_and_verdict_fields():
    plan = hunt.HuntPlan(
        "s" * 64,
        "h" * 64,
        hunt.Distribution({"n": (1, 2)}),
        1,
        {"n": (1, 2)},
    )
    trial = hunt.TrialRecord(0, {"n": 1}, 9, "attempt", "OK", "execution", "SURVIVED_TRIAL", "NOT_REQUIRED", "verifier")
    record = hunt.HuntRecord(
        plan.hash,
        plan.distribution.hash,
        plan.statement_hash,
        plan.hypothesis_key,
        "ab" * 32,
        1,
        1,
        "FULL_DECLARED_BUDGET",
        "SURVIVED",
        None,
        True,
        (trial,),
    )

    encoded = hunt.run_canonical(record)
    assert hunt.canon.decode(hunt.RUN, encoded)["trials"][0]["attempt_id"] == "attempt"
    assert record.verdict == "SURVIVED"
    assert record.standing is True


def test_record_rejects_survival_with_an_incomplete_transcript():
    plan = hunt.HuntPlan(
        "s" * 64,
        "h" * 64,
        hunt.Distribution({"n": (1, 2)}),
        1,
        {"n": (1, 2)},
    )
    trial = hunt.TrialRecord(0, {"n": 1}, 9, "attempt", "OK", "execution", "SURVIVED_TRIAL", "NOT_REQUIRED", "verifier")

    with pytest.raises(ValueError, match="SURVIVED requires"):
        hunt.HuntRecord(
            plan.hash,
            plan.distribution.hash,
            plan.statement_hash,
            plan.hypothesis_key,
            "ab" * 32,
            2,
            1,
            "FULL_DECLARED_BUDGET",
            "SURVIVED",
            None,
            True,
            (trial,),
        )


def test_record_rejects_kill_without_a_verified_counterexample():
    plan = hunt.HuntPlan(
        "s" * 64,
        "h" * 64,
        hunt.Distribution({"n": (1, 1)}),
        1,
        {"n": (1, 1)},
    )
    trial = hunt.TrialRecord(
        0,
        {"n": 1},
        9,
        "attempt",
        "OK",
        "execution",
        "VERIFIER_FAILED",
        "FAIL",
        "verifier-evidence",
        "verifier",
    )
    with pytest.raises(ValueError, match=r"\AKILLED requires one final verifier-passed counterexample\Z"):
        hunt.HuntRecord(
            plan.hash,
            plan.distribution.hash,
            plan.statement_hash,
            plan.hypothesis_key,
            "ab" * 32,
            1,
            1,
            "FULL_DECLARED_BUDGET",
            "KILLED",
            0,
            False,
            (trial,),
        )


def test_record_rejects_a_valid_killed_counterexample_with_standing_true():
    plan = hunt.HuntPlan(
        "s" * 64,
        "h" * 64,
        hunt.Distribution({"n": (1, 1)}),
        1,
        {"n": (1, 1)},
    )
    trial = hunt.TrialRecord(
        0,
        {"n": 1},
        9,
        "attempt",
        "OK",
        "execution",
        "COUNTEREXAMPLE",
        "OK",
        "verifier-evidence",
        "verifier",
    )
    valid = hunt.HuntRecord(
        plan.hash,
        plan.distribution.hash,
        plan.statement_hash,
        plan.hypothesis_key,
        "ab" * 32,
        1,
        1,
        "FULL_DECLARED_BUDGET",
        "KILLED",
        0,
        False,
        (trial,),
    )
    assert valid.verdict == "KILLED" and valid.standing is False

    with pytest.raises(ValueError, match=r"\AKILLED requires one final verifier-passed counterexample\Z"):
        hunt.HuntRecord(
            plan.hash,
            plan.distribution.hash,
            plan.statement_hash,
            plan.hypothesis_key,
            "ab" * 32,
            1,
            1,
            "FULL_DECLARED_BUDGET",
            "KILLED",
            0,
            True,
            (trial,),
        )


def test_multi_axis_size_axis_selects_population_and_plan_identity(tmp_path):
    distribution = hunt.Distribution({"a": (1, 2), "n": (40, 41)})
    statement_scope = {
        "target_family": "hunt-family",
        "size_interval": [40, 41],
        "param_ranges": {"a": [1, 2], "n": [40, 41]},
        "assumption_set": [],
    }
    statement = claims.ClaimStatement("claim", 1, "n", statement_scope, {"units": {}, "cost_model": None})

    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        claims.write_claim_statement(sub, statement)
        plan_n = hunt.HuntPlan(
            statement.hash,
            "h" * 64,
            distribution,
            1,
            {"a": (1, 2), "n": (40, 41)},
            size_axis="n",
        )
        population, stored = hunt._scope(sub, plan_n)

        assert plan_n.size_axis == "n"
        assert json.loads(stored["scope"])["size_interval"] == [40, 41]
        assert population["size_interval"] == [40, 41]

        plan_a = hunt.HuntPlan(
            statement.hash,
            "h" * 64,
            distribution,
            1,
            {"a": (1, 2), "n": (40, 41)},
            size_axis="a",
        )
        assert plan_n.hash != plan_a.hash


def test_multi_axis_plan_without_a_size_axis_is_refused():
    with pytest.raises(hunt.PlanRefused, match="size_axis"):
        hunt.HuntPlan(
            "s" * 64,
            "h" * 64,
            hunt.Distribution({"a": (1, 2), "n": (40, 41)}),
            1,
            {"a": (1, 2), "n": (40, 41)},
        )


def test_multi_axis_plan_with_an_unknown_size_axis_is_refused():
    with pytest.raises(hunt.PlanRefused, match="size_axis"):
        hunt.HuntPlan(
            "s" * 64,
            "h" * 64,
            hunt.Distribution({"a": (1, 2), "n": (40, 41)}),
            1,
            {"a": (1, 2), "n": (40, 41)},
            size_axis="missing",
        )


def test_record_rejects_budget_exceeded_with_survival_standing():
    trial = hunt.TrialRecord(0, {"n": 1}, 1, "attempt", "OK", "execution", "SURVIVED_TRIAL", "NOT_REQUIRED", "verifier")
    with pytest.raises(ValueError, match="SURVIVED requires"):
        hunt.HuntRecord(
            "plan",
            "distribution",
            "statement",
            "hypothesis",
            "ab" * 32,
            1,
            1,
            "BUDGET_EXCEEDED",
            "SURVIVED",
            None,
            True,
            (trial,),
        )
