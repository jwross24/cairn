import json
import logging
import sys
import time
from pathlib import Path

import pytest

from cairn import log, pari
from cairn.skills import toy_curve

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mutants import toy_curve_mutants  # noqa: E402

SIZES = (30, 40, 50, 60)
SEEDS = (1, 2, 3)
BRIEF_TRIES = {
    (30, 1): 48, (30, 2): 148, (30, 3): 20,
    (40, 1): 40, (40, 2): 52, (40, 3): 57,
    (50, 1): 36, (50, 2): 11, (50, 3): 220,
    (60, 1): 45, (60, 2): 72, (60, 3): 140,
}
GP_SEARCH = (
    "setrand({seed}); p = randomprime([2^{lo}, 2^{bits}]); tries = 0;\n"
    "while(1, a = random(p); b = random(p); if((4*a^3 + 27*b^2) % p == 0, next); tries++; E = ellinit([a,b], p); {count}; if({accept}, break));\n"
    "{confirm}\n"
    "P = random(E);\n"
    'print(p, " ", a, " ", b, " ", n, " ", tries, " ", lift(P[1]), " ", lift(P[2]));\n'
)


def gp_script(bits, seed):
    if bits <= toy_curve.SEA_SEARCH_ABOVE_BITS:
        return GP_SEARCH.format(seed=seed, lo=bits - 1, bits=bits, count="n = ellcard(E)", accept="isprime(n)", confirm="")
    return GP_SEARCH.format(seed=seed, lo=bits - 1, bits=bits, count="n = ellsea(E, 1)", accept="n && isprime(n)", confirm='if(ellcard(E) != n, error("confirm"));')


def row_of(out):
    return (str(out.p), str(out.a), str(out.b), str(out.n), out.tries)


@pytest.fixture(scope="module")
def outputs():
    return {(bits, seed): toy_curve.run(bits, seed) for bits in SIZES for seed in SEEDS}


@pytest.fixture
def call_log(monkeypatch):
    events = []
    real_ellsea = pari.ellsea
    real_draw = toy_curve._draw_point

    def spy_ellsea(E, early_abort=0):
        events.append(("ellsea", early_abort))
        return real_ellsea(E, early_abort)

    def spy_draw(E):
        events.append(("draw_point", None))
        return real_draw(E)

    monkeypatch.setattr(pari, "ellsea", spy_ellsea)
    monkeypatch.setattr(toy_curve, "_draw_point", spy_draw)
    return events


@pytest.mark.parametrize(("bits", "seed"), sorted(BRIEF_TRIES), ids=lambda v: str(v))
def test_rows_reproduce_the_grounding_brief_tries(outputs, bits, seed):
    assert outputs[(bits, seed)].tries == BRIEF_TRIES[(bits, seed)]


def test_rows_golden_toy_curve_rows_json(outputs, assert_golden):
    rows = [{"bits": bits, "seed": seed, "p": str(o.p), "a": str(o.a), "b": str(o.b), "n": str(o.n), "tries": o.tries} for (bits, seed), o in sorted(outputs.items())]
    assert_golden("toy_curve_rows.json", json.dumps({"rows": rows}, indent=2) + "\n")


def test_rows_golden_file_covers_every_brief_row(load_vector):
    rows = {(r["bits"], r["seed"]): r for r in load_vector("toy_curve_rows.json")["rows"]}
    assert set(rows) == set(BRIEF_TRIES)
    assert {k: r["tries"] for k, r in rows.items()} == BRIEF_TRIES


def test_curve60_seed1_matches_the_committed_vector_field_for_field(outputs, load_vector):
    v = load_vector("curve60_seed1.json")
    out = outputs[(60, 1)]
    assert (out.bits, out.seed) == (v["bits"], v["seed"])
    assert row_of(out) == (v["p"], v["a"], v["b"], v["n"], v["tries"])
    assert [str(c) for c in out.P] == v["P"]


@pytest.mark.parametrize("seed", SEEDS)
def test_60bit_seed_completes_within_a_minute_with_prime_n_and_untested_cross_check(seed):
    start = time.monotonic()
    out = toy_curve.run(60, seed)
    wall = time.monotonic() - start
    assert wall < 60.0
    assert bool(pari.pari.isprime(out.n))
    assert out.tries == BRIEF_TRIES[(60, seed)]
    assert out.cross_check["result"] == "untested" and out.status == "OK"


def test_gp_cypari2_rows_agree_plumbing_one_library_twice(outputs):
    for (bits, seed), out in sorted(outputs.items()):
        rc, stdout, stderr = pari.run_gp([], gp_script(bits, seed), stack="64M")
        assert (rc, stderr) == (0, ""), (bits, seed, stderr)
        p, a, b, n, tries, x, y = stdout.split()
        assert (p, a, b, n, int(tries)) == row_of(out), (bits, seed)
        assert (x, y) == tuple(str(c) for c in out.P), (bits, seed)


def test_cross_check_is_differential_on_algorithm_axis(outputs):
    for (bits, seed), out in outputs.items():
        assert out.cross_check["axis"] == "algorithm"
        assert out.cross_check["independent_range"] == {"bits": [0, 50]}
        assert out.cross_check["result"] == ("agree" if bits <= 50 else "untested"), (bits, seed)
        assert out.status == "OK"
    assert toy_curve.SEAM == "cairn.pari.ellsea"


def test_postcondition_arm_holds_on_every_output(outputs):
    for out in outputs.values():
        assert toy_curve.check_postcondition(out) is out


@pytest.mark.parametrize("bits", [30, 40, 50])
def test_call_order_guard_ellsea_once_and_only_after_the_point_is_drawn(call_log, bits):
    out = toy_curve.run(bits, 1)
    assert out.tries == BRIEF_TRIES[(bits, 1)]
    assert call_log == [("draw_point", None), ("ellsea", 0)]


def test_call_order_guard_at_60_bits_sees_only_early_abort_calls_before_the_point(call_log):
    toy_curve.run(60, 1)
    draws = [i for i, (name, _) in enumerate(call_log) if name == "draw_point"]
    assert len(draws) == 1
    assert all(name == "ellsea" and flag == 1 for name, flag in call_log[: draws[0]])
    assert call_log[draws[0] + 1 :] == []


def test_cross_check_planted_inside_the_loop_breaks_tries_and_trips_the_guard(call_log):
    with toy_curve_mutants.cross_check_in_loop_skill():
        out = toy_curve.run(40, 1)
    assert out.tries != BRIEF_TRIES[(40, 1)]
    first_draw = call_log.index(("draw_point", None))
    assert ("ellsea", 0) in call_log[:first_draw]
    assert call_log.count(("ellsea", 0)) > 1


def test_double_run_same_seed_is_byte_identical_and_another_seed_moves_p():
    first = toy_curve.run(40, 2)
    second = toy_curve.run(40, 2)
    assert first == second
    assert first.manifest() == second.manifest()
    assert first.to_json() == second.to_json()
    assert first.manifest_hash() == second.manifest_hash()
    other = toy_curve.run(40, 3)
    assert other.p != first.p
    assert other.manifest_hash() != first.manifest_hash()


def test_disagree_path_via_the_ellsea_seam_returns_both_transcripts_and_no_ok(monkeypatch, caplog):
    real = pari.ellsea
    monkeypatch.setattr(pari, "ellsea", lambda E, early_abort=0: real(E, early_abort) + 2)
    caplog.set_level(logging.INFO, logger=log.LOGGER_NAME)
    out = toy_curve.run(40, 1)
    assert out.status == "DISAGREE"
    assert out.cross_check == {"axis": "algorithm", "independent_range": {"bits": [0, 50]}, "result": "disagree"}
    assert [t["call"] for t in out.transcripts] == ["ellcard", "ellsea"]
    card, sea = out.transcripts
    assert card["result"] == out.n and sea["result"] == out.n + 2
    assert card["curve"] == sea["curve"] == [out.a, out.b, out.p]
    assert len(card["digest"]) == 64 and len(sea["digest"]) == 64 and card["digest"] != sea["digest"]
    assert out.tries == BRIEF_TRIES[(40, 1)]
    again = toy_curve.ToyCurveOutput.from_json(out.to_json())
    assert again == out
    records = [r for r in caplog.records if r.name == log.LOGGER_NAME and r.getMessage() == "disagree"]
    assert records and records[-1].fields["transcript_digests"] == [card["digest"], sea["digest"]]
    run_records = [r for r in caplog.records if r.name == log.LOGGER_NAME and r.getMessage() == "run"]
    assert run_records[-1].fields["status"] == "DISAGREE"


def test_singular_pairs_are_skipped_and_not_counted(monkeypatch):
    drawn = []
    real = toy_curve._draw_pair

    def spy(p):
        pair = real(p)
        drawn.append(pair)
        return pair

    monkeypatch.setattr(toy_curve, "_draw_pair", spy)
    p = 7
    singular_seen = 0
    for seed in range(1, 21):
        drawn.clear()
        pari.pari.setrand(seed)
        a, b, n, tries, E, call = toy_curve._search(4, p)
        singular = [pair for pair in drawn if toy_curve._singular(pair[0], pair[1], p)]
        singular_seen += len(singular)
        assert tries == len(drawn) - len(singular)
        assert (a, b) == drawn[-1] and not toy_curve._singular(a, b, p)
        assert call == "ellcard" and bool(pari.pari.isprime(n))
    assert singular_seen > 0


def test_forced_composite_n_fails_the_postcondition_arm():
    with toy_curve_mutants.composite_n_skill(), pytest.raises(toy_curve.PostconditionFailed, match="isprime"):
        toy_curve.run(30, 1)


def test_every_run_logs_the_declared_fields(caplog):
    caplog.set_level(logging.INFO, logger=log.LOGGER_NAME)
    toy_curve.run(30, 3)
    record = [r for r in caplog.records if r.name == log.LOGGER_NAME and r.getMessage() == "run"][-1]
    assert record.fields["bits"] == 30 and record.fields["seed"] == 3 and record.fields["tries"] == 20
    assert record.fields["n_bits"] == 30 and record.fields["cross_check"] == "agree" and record.fields["status"] == "OK"
    assert record.fields["wall_ms"] > 0
    json.loads(log.JsonFormatter().format(record))
