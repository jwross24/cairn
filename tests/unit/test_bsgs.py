import dataclasses
import hashlib
import io
import itertools
import json
import math
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from cairn import ec
from cairn.skills import bsgs

CORPUS = json.loads(Path(bsgs.REPO_ROOT, "src/cairn/skills/bsgs_corpus.json").read_text())


def _case(case_id):
    case = next(c for c in CORPUS["cases"] if c["id"] == case_id)
    return {name: field["value"] for name, field in case["fields"].items()}


def _args(inst, seed=1, **overrides):
    inst = {**inst, **overrides}
    return (inst["p"].bit_length(), seed, inst["p"], inst["a"], inst["b"], inst["n"], inst["P"], inst["Q"])


BITS20 = _case("bits20_seed1")
PASS_CASES = [c["id"] for c in CORPUS["cases"] if c["ledger"] == "pass"]


@pytest.mark.parametrize("case_id", PASS_CASES)
def test_every_pass_case_recovers_x_under_a_pinned_seed(case_id):
    inst = _case(case_id)
    out = bsgs.run(*_args(inst))
    assert out.x == inst["x"] and out.status == "OK"
    assert bsgs.check_postcondition(out) is out


def test_two_runs_are_byte_identical_and_the_seed_moves_only_the_giant_step_offset():
    first = bsgs.run(*_args(BITS20))
    second = bsgs.run(*_args(BITS20))
    texts = (first.to_json(), second.to_json())
    assert (len(texts[0]), hashlib.sha256(texts[0].encode()).hexdigest()) == (
        len(texts[1]),
        hashlib.sha256(texts[1].encode()).hexdigest(),
    )
    other = bsgs.run(*_args(BITS20, seed=2))
    assert other.x == first.x == BITS20["x"]
    assert other.offset == 2 % bsgs.table_entries(BITS20["n"]) and first.offset == 1
    assert (other.offset, other.giant_steps) != (first.offset, first.giant_steps)
    assert other.memory == first.memory


def test_table_size_accounting_is_exact(monkeypatch):
    out = bsgs.run(*_args(BITS20))
    m = bsgs.table_entries(BITS20["n"])
    assert m == math.isqrt(BITS20["n"] - 1) + 1
    memory = out.memory
    assert memory["model"] == bsgs.MEMORY_MODEL == "ceil_sqrt_n_entries"
    assert memory["entries"] == m - 1
    assert memory["slots"] & (memory["slots"] - 1) == 0 and memory["slots"] >= 2 * m
    assert memory["key_bytes"] == 8 and memory["slot_bytes"] == 4
    assert memory["table_bytes"] == memory["entries"] * 8 + memory["slots"] * 4


@given(keys_=st.lists(st.integers(min_value=0, max_value=(1 << 64) - 1), min_size=1, max_size=300, unique=True))
@settings(max_examples=80)
def test_the_baby_table_returns_the_insertion_position_and_none_for_absent_keys(keys_):
    table = bsgs.BabyTable(len(keys_))
    for key in keys_:
        table.insert(key)
    assert [table.lookup(key) for key in keys_] == list(range(len(keys_)))
    absent = next(k for k in range(1, 1 << 20) if k not in set(keys_))
    assert table.lookup(absent) is None
    assert table.entries == len(keys_) and table.table_bytes == 8 * len(keys_) + 4 * table.slot_count


def test_the_baby_table_survives_a_home_slot_collision():
    table = bsgs.BabyTable(2)
    home = table._home(1)
    colliding = next(k for k in range(2, 1 << 16) if table._home(k) == home)
    table.insert(1)
    table.insert(colliding)
    assert table.lookup(1) == 0 and table.lookup(colliding) == 1


@given(x=st.integers(min_value=1, max_value=BITS20["n"] - 1), seed=st.integers(min_value=1, max_value=1 << 20))
@settings(max_examples=60, deadline=None)
def test_property_bsgs_recovers_a_random_x(x, seed):
    p, a, b, n, P = BITS20["p"], BITS20["a"], BITS20["b"], BITS20["n"], tuple(BITS20["P"])
    Q = ec.mul(p, a, P, x)
    solution = bsgs.solve(p, a, b, n, P, Q, seed)
    assert solution.x == x
    assert solution.offset == seed % bsgs.table_entries(n)
    assert bsgs.discrete_log(p, a, b, n, P, Q, seed) == x


def test_an_x_equal_to_the_offset_hits_the_identity_on_the_first_giant_step():
    inst = _case("GF101")
    p, a, b, n, P = inst["p"], inst["a"], inst["b"], inst["n"], tuple(inst["P"])
    with pytest.raises(bsgs.InputError, match="not on the curve"):
        bsgs.run(p.bit_length(), 1, p, a, b, n, P, [0, 0])
    with pytest.raises(ec.NotOnCurve, match="Q = None"):
        bsgs.solve(p, a, b, n, P, None, 1)
    x = 5
    solution = bsgs.solve(p, a, b, n, P, ec.mul(p, a, P, x), x)
    assert solution.x == x and solution.offset == x and solution.giant_steps == 0


def test_the_declared_profile_grows_as_sqrt_n_between_every_pair_of_sizes():
    sizes = bsgs.COST_PROFILE.declared_sizes()
    assert sizes == (28, 30, 40, 50)
    per_size = bsgs.COST_PROFILE.production.per_size
    for low, high in itertools.pairwise(sizes):
        ratio = per_size[high].mean_tries / per_size[low].mean_tries
        expected = 2 ** ((high - low) / 2)
        assert 0.5 * expected <= ratio <= 2.0 * expected, (low, high, ratio, expected)
    assert bsgs.COST_PROFILE.production.model == "c_sqrt_n_ops"
    assert bsgs.COST_PROFILE.tier == 1 and bsgs.REPLAY_GRADE == "Replayable" and bsgs.DO_NOT_CACHE is False


@pytest.mark.parametrize("case_id", PASS_CASES)
def test_measured_entries_follow_the_declared_memory_model(case_id):
    inst = _case(case_id)
    out = bsgs.run(*_args(inst))
    assert out.memory["entries"] + 1 == math.isqrt(inst["n"] - 1) + 1
    assert out.ops <= 3 * math.isqrt(inst["n"]) + 4 * inst["n"].bit_length() + 8


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"n": 21}, "not prime"),
        ({"Q": [1, 1]}, "not on the curve"),
        ({"P": [1, 1]}, "not on the curve"),
        ({"a": 0, "b": 0}, "singular"),
        ({"p": (1 << 65) + 1}, "not a prime|65 bits"),
    ],
)
def test_run_refuses_a_malformed_instance(override, match):
    with pytest.raises(bsgs.InputError, match=match):
        bsgs.run(*_args(BITS20, **override))


def test_the_table_key_width_refuses_a_prime_above_64_bits():
    p = (1 << 64) + 13
    with pytest.raises(bsgs.InputError, match="65 bits; the table keys hold 64"):
        bsgs.validate(65, 1, p, 1, 1, p, [0, 1], [0, 1])


def test_parse_inputs_and_io_round_trip():
    doc = {"bits": 20, "seed": 3, **{k: str(BITS20[k]) for k in ("p", "a", "b", "n")}}
    doc["P"] = [str(c) for c in BITS20["P"]]
    doc["Q"] = list(BITS20["Q"])
    parsed = bsgs.parse_inputs(json.dumps(doc))
    assert parsed["p"] == BITS20["p"] and parsed["Q"] == BITS20["Q"]
    out = bsgs.run(
        parsed["bits"], parsed["seed"], parsed["p"], parsed["a"], parsed["b"], parsed["n"], parsed["P"], parsed["Q"]
    )
    assert bsgs.BsgsOutput.from_json(out.to_json()).to_json() == out.to_json()
    assert bsgs.BsgsOutput.from_json(out.to_json()).manifest_hash() == out.manifest_hash()
    with pytest.raises(bsgs.InputError, match="does not match bsgs_output"):
        bsgs.BsgsOutput.from_json('{"bits": 20}')
    for text, match in (
        ("", "empty stdin"),
        ("7", "not a JSON object"),
        ('{"bits": 20}', "missing field"),
        ('{"bits": 20, "seed": 1, "p": "\\u00b2", "a": 1, "b": 1, "n": 7, "P": [0, 1], "Q": [3, 3]}', "decimal string"),
    ):
        with pytest.raises(bsgs.InputError, match=match):
            bsgs.parse_inputs(text)


def test_main_writes_canonical_json_and_refuses_bad_stdin():
    doc = {"bits": 20, "seed": 1, **{k: BITS20[k] for k in ("p", "a", "b", "n", "P", "Q")}}
    out, err = io.StringIO(), io.StringIO()
    assert bsgs.main(io.StringIO(json.dumps(doc)), out, err) == 0
    text = out.getvalue()
    assert text == json.dumps(json.loads(text), sort_keys=True, separators=(",", ":")) + "\n"
    assert json.loads(text)["x"] == str(BITS20["x"])
    assert bsgs.main(io.StringIO("nope"), io.StringIO(), err) == 1 and err.getvalue().startswith("error:")


def test_the_second_opinion_is_a_rho_walk_and_a_planted_disagreement_surfaces(monkeypatch):
    from cairn.skills import rho_dp

    real = rho_dp.discrete_log
    monkeypatch.setattr(rho_dp, "discrete_log", lambda *a, **k: real(*a, **k) + 2)
    out = bsgs.run(*_args(BITS20))
    assert out.status == "DISAGREE" and out.cross_check["result"] == "disagree"
    assert out.transcripts is not None and len({t["digest"] for t in out.transcripts}) == 2
    assert [t["call"] for t in out.transcripts] == ["bsgs", "rho_dp"]
    assert out.x == BITS20["x"]


@pytest.mark.parametrize(
    ("mutate", "clause"),
    [
        (lambda o: dataclasses.replace(o, x=o.x % (o.n - 1) + 1), "xP-eq-Q"),
        (lambda o: dataclasses.replace(o, x=o.n), "x-range"),
        (lambda o: dataclasses.replace(o, memory={**o.memory, "entries": o.memory["entries"] + 1}), "table"),
        (lambda o: dataclasses.replace(o, P=(o.P[0], (o.P[1] + 1) % o.p)), "oncurve"),
        (lambda o: dataclasses.replace(o, Q=(o.Q[0], (o.Q[1] + 1) % o.p)), "oncurve"),
    ],
    ids=["x-plus-one", "x-out-of-range", "entries", "P-off-curve", "Q-off-curve"],
)
def test_the_postcondition_refuses_each_planted_wrong_answer(mutate, clause):
    out = bsgs.run(*_args(BITS20))
    with pytest.raises(bsgs.PostconditionFailed, match=clause):
        bsgs.check_postcondition(mutate(out))


def test_a_point_outside_the_subgroup_has_no_solution():
    c = _case("composite_order")
    with pytest.raises(bsgs.NoSolution, match=r"no x in \[0, 21\)"):
        bsgs.solve(c["p"], c["a"], c["b"], c["n"], tuple(c["P"]), tuple(c["Q"]), 1)


@pytest.mark.parametrize(
    ("args", "match"),
    [
        ((7, 0, 101, 90, 44, 89, [2, 38], [12, 23]), "seed must be >= 1"),
        ((7, 1, 101, 90 + 101, 44, 89, [2, 38], [12, 23]), "not reduced coordinates"),
        ((7, 1, 101, 90, 44, 83, [2, 38], [12, 23]), r"\[n\]P is not the identity"),
        ((7, 1, 101, 90, 44, 89, [2, 38], [12, 23, 1]), "pair of ints"),
    ],
    ids=["seed-floor", "unreduced-a", "wrong-prime-order", "triple-not-pair"],
)
def test_validate_refuses_each_malformed_field_with_its_reason(args, match):
    with pytest.raises(bsgs.InputError, match=match):
        bsgs.validate(*args)
