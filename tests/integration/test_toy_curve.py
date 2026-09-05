import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from cairn import canon, env, keys, log, pari
from cairn.skills import toy_curve

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tests"))
from _checks import bench_tries, curve_row, matches_vector  # noqa: E402
from mutants import toy_curve_mutants  # noqa: E402

SIZES = (30, 40, 50, 60)
SEEDS = (1, 2, 3)
BRIEF_TRIES = bench_tries(ROOT)
ROWS = sorted(BRIEF_TRIES)
GP_SEARCH = (
    "setrand({seed}); p = randomprime([2^{lo}, 2^{bits}]); tries = 0;\n"
    "while(1, a = random(p); b = random(p); if((4*a^3 + 27*b^2) % p == 0, next); tries++; E = ellinit([a,b], p); {count}; if({accept}, break));\n"
    "{confirm}\n"
    "P = random(E);\n"
    'print(p, " ", a, " ", b, " ", n, " ", tries, " ", lift(P[1]), " ", lift(P[2]));\n'
)
MODULE_ARGV = (sys.executable, "-m", "cairn.skills.toy_curve")


def gp_script(bits, seed):
    if bits <= toy_curve.SEA_SEARCH_ABOVE_BITS:
        return GP_SEARCH.format(
            seed=seed, lo=bits - 1, bits=bits, count="n = ellcard(E)", accept="isprime(n)", confirm=""
        )
    return GP_SEARCH.format(
        seed=seed,
        lo=bits - 1,
        bits=bits,
        count="n = ellsea(E, 1)",
        accept="n && isprime(n)",
        confirm='if(ellcard(E) != n, error("confirm"));',
    )


def mutated(out, **fields):
    merged: dict[str, Any] = {
        **out.to_dict(),
        "P": tuple(out.P),
        "cross_check": out.cross_check,
        "transcripts": None,
        **fields,
    }
    return toy_curve.ToyCurveOutput(**merged)


@pytest.fixture(scope="module")
def outputs():
    return {(bits, seed): toy_curve.run(bits, seed) for bits in SIZES for seed in SEEDS}


@pytest.fixture(scope="module")
def sample(outputs):
    return outputs[(30, 1)]


@pytest.fixture
def call_log(monkeypatch):
    events = []
    reals = {name: getattr(pari, name) for name in ("ellcard", "ellsea")}

    def spy_ellcard(E):
        events.append(("ellcard", None))
        return reals["ellcard"](E)

    def spy_ellsea(E, early_abort=0):
        events.append(("ellsea", early_abort))
        return reals["ellsea"](E, early_abort)

    real_draw = toy_curve._draw_point

    def spy_draw(E):
        events.append(("draw_point", None))
        return real_draw(E)

    monkeypatch.setattr(pari, "ellcard", spy_ellcard)
    monkeypatch.setattr(pari, "ellsea", spy_ellsea)
    monkeypatch.setattr(toy_curve, "_draw_point", spy_draw)
    return events


def test_brief_table_names_every_size_and_seed():
    assert set(BRIEF_TRIES) == {(bits, seed) for bits in SIZES for seed in SEEDS}


@pytest.mark.parametrize(("bits", "seed"), ROWS, ids=lambda v: str(v))
def test_rows_reproduce_the_grounding_brief_tries(outputs, bits, seed):
    assert outputs[(bits, seed)].tries == BRIEF_TRIES[(bits, seed)]


def test_rows_golden_toy_curve_rows_json(outputs, assert_golden):
    rows = [
        {"bits": bits, "seed": seed, "p": str(o.p), "a": str(o.a), "b": str(o.b), "n": str(o.n), "tries": o.tries}
        for (bits, seed), o in sorted(outputs.items())
    ]
    assert_golden("toy_curve_rows.json", json.dumps({"rows": rows}, indent=2) + "\n")


def test_rows_golden_file_covers_every_brief_row(load_vector):
    rows = {(r["bits"], r["seed"]): r for r in load_vector("toy_curve_rows.json")["rows"]}
    assert set(rows) == set(BRIEF_TRIES)
    assert {k: r["tries"] for k, r in rows.items()} == BRIEF_TRIES


def test_curve60_seed1_matches_the_committed_vector_field_for_field(outputs, load_vector):
    out = outputs[(60, 1)]
    assert (out.bits, out.seed) == (60, 1)
    assert matches_vector(out, load_vector("curve60_seed1.json"))


@pytest.mark.parametrize(("bits", "seed"), ROWS, ids=lambda v: str(v))
def test_gp_cypari2_rows_agree_plumbing_one_library_twice(outputs, bits, seed):
    out = outputs[(bits, seed)]
    rc, stdout, stderr = pari.run_gp([], gp_script(bits, seed), stack="64M")
    assert (rc, stderr) == (0, "")
    p, a, b, n, tries, x, y = stdout.split()
    assert (p, a, b, n, int(tries)) == curve_row(out)
    assert (x, y) == tuple(str(c) for c in out.P)


@pytest.mark.parametrize(("bits", "seed"), ROWS, ids=lambda v: str(v))
def test_cross_check_is_differential_on_algorithm_axis(outputs, bits, seed):
    out = outputs[(bits, seed)]
    assert out.cross_check["axis"] == "algorithm"
    assert out.cross_check["independent_range"] == {"bits": [0, 50]}
    assert out.cross_check["result"] == ("agree" if bits <= toy_curve.SEA_SEARCH_ABOVE_BITS else "untested")
    assert out.status == "OK"
    assert bool(pari.pari.isprime(out.n))


def test_declared_seam_is_the_ellsea_wrapper():
    assert toy_curve.SEAM == "cairn.pari.ellsea"
    module, attribute = toy_curve.SEAM.rsplit(".", 1)
    assert module == pari.__name__ and callable(getattr(pari, attribute))


@pytest.mark.parametrize(("bits", "seed"), ROWS, ids=lambda v: str(v))
def test_postcondition_arm_holds_on_every_output(outputs, bits, seed):
    out = outputs[(bits, seed)]
    assert toy_curve.check_postcondition(out) is out


@pytest.mark.parametrize(
    ("field", "clause"),
    [
        ("composite_n", "isprime"),
        ("far_prime_n", "hasse"),
        ("off_curve_point", "ellisoncurve"),
        ("other_prime_n", "ellmul"),
    ],
    ids=["composite-n", "n-outside-hasse", "P-off-curve", "n-not-the-order"],
)
def test_each_postcondition_clause_has_a_negative(sample, field, clause):
    if field == "composite_n":
        broken = mutated(sample, n=sample.n + 1)
    elif field == "far_prime_n":
        broken = mutated(sample, n=int(pari.pari.nextprime(3 * sample.p)))
    elif field == "off_curve_point":
        broken = mutated(sample, P=(sample.P[0], (sample.P[1] + 1) % sample.p))
    else:
        broken = mutated(sample, n=int(pari.pari.nextprime(sample.n + 1)))
    assert (sample.n - (sample.p + 1)) ** 2 <= 4 * sample.p
    with pytest.raises(toy_curve.PostconditionFailed, match=clause) as info:
        toy_curve.check_postcondition(broken)
    assert info.value.clause == clause


@pytest.mark.parametrize("bits", [30, 40, 50])
def test_call_order_guard_ellsea_once_and_only_after_the_point_is_drawn(call_log, bits):
    out = toy_curve.run(bits, 1)
    assert out.tries == BRIEF_TRIES[(bits, 1)]
    assert call_log[-2:] == [("draw_point", None), ("ellsea", 0)]
    assert call_log[: out.tries] == [("ellcard", None)] * out.tries
    assert len(call_log) == out.tries + 2


def test_call_order_guard_at_60_bits_confirms_with_ellcard_immediately_before_the_point(call_log):
    out = toy_curve.run(60, 1)
    assert call_log[: out.tries] == [("ellsea", 1)] * out.tries
    assert call_log[out.tries :] == [("ellcard", None), ("draw_point", None)]


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


def _assert_disagree(out, calls, results):
    assert out.status == "DISAGREE"
    assert out.cross_check == {"axis": "algorithm", "independent_range": {"bits": [0, 50]}, "result": "disagree"}
    assert [t["call"] for t in out.transcripts] == calls
    first, second = out.transcripts
    assert (first["result"], second["result"]) == results
    assert first["curve"] == second["curve"] == [out.a, out.b, out.p]
    assert len(first["digest"]) == 64 and len(second["digest"]) == 64 and first["digest"] != second["digest"]
    assert toy_curve.ToyCurveOutput.from_json(out.to_json()) == out


def test_disagree_path_via_the_ellsea_seam_returns_both_transcripts_and_no_ok(monkeypatch, caplog):
    real = pari.ellsea
    monkeypatch.setattr(pari, "ellsea", lambda E, early_abort=0: real(E, early_abort) + 2)
    caplog.set_level(logging.INFO, logger=log.LOGGER_NAME)
    out = toy_curve.run(40, 1)
    _assert_disagree(out, ["ellcard", "ellsea"], (out.n, out.n + 2))
    assert out.tries == BRIEF_TRIES[(40, 1)]
    assert toy_curve.check_postcondition(out) is out
    digests = [t["digest"] for t in out.transcripts]
    records = [r for r in caplog.records if r.name == log.LOGGER_NAME and r.getMessage() == "disagree"]
    assert records and records[-1].fields["transcript_digests"] == digests
    run_records = [r for r in caplog.records if r.name == log.LOGGER_NAME and r.getMessage() == "run"]
    assert run_records[-1].fields["status"] == "DISAGREE"


def test_disagree_path_at_60_bits_via_the_ellcard_confirm_seam(monkeypatch, caplog, load_vector):
    real = pari.ellcard
    monkeypatch.setattr(pari, "ellcard", lambda E: real(E) + 2)
    caplog.set_level(logging.INFO, logger=log.LOGGER_NAME)
    out = toy_curve.run(60, 1)
    _assert_disagree(out, ["ellsea_early_abort", "ellcard"], (out.n, out.n + 2))
    assert matches_vector(out, load_vector("curve60_seed1.json"))
    assert toy_curve.check_postcondition(out) is out
    records = [r for r in caplog.records if r.name == log.LOGGER_NAME and r.getMessage() == "disagree"]
    assert records and records[-1].fields["transcript_digests"] == [t["digest"] for t in out.transcripts]


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


def test_drawn_point_is_always_affine(sample):
    E = pari.pari.ellinit([sample.a, sample.b], sample.p)
    for _ in range(50):
        point = toy_curve._draw_point(E)
        assert len(point) == 2 and bool(pari.pari.ellisoncurve(E, list(point)))


def test_forced_composite_n_is_refused_by_the_arm_inside_run():
    with toy_curve_mutants.composite_n_skill(), pytest.raises(toy_curve.PostconditionFailed, match="isprime"):
        toy_curve.run(30, 1)


def test_every_run_logs_the_declared_fields(caplog):
    caplog.set_level(logging.INFO, logger=log.LOGGER_NAME)
    toy_curve.run(30, 3)
    record = [r for r in caplog.records if r.name == log.LOGGER_NAME and r.getMessage() == "run"][-1]
    assert record.fields["bits"] == 30 and record.fields["seed"] == 3 and record.fields["tries"] == BRIEF_TRIES[(30, 3)]
    assert record.fields["n_bits"] == 30 and record.fields["cross_check"] == "agree" and record.fields["status"] == "OK"
    assert record.fields["wall_ms"] > 0
    json.loads(log.JsonFormatter().format(record))


def test_identity_bundle_is_stable_and_carries_the_live_toolchain():
    first = toy_curve.skill_identity_hash()
    bundle = toy_curve.identity_bundle()
    assert first == toy_curve.skill_identity_hash() == keys.identity_bundle_hash(bundle)
    assert bundle["interface_version"] == "toy_curve/1"
    assert set(bundle["tool_digests"]) == {"gp_binary_sha256", "cypari2", "libpari"}
    assert bundle["tool_digests"]["libpari"] == pari.pari_versions()["libpari"]
    assert bundle["tool_digests"]["gp_binary_sha256"] == env.gp_binary_sha256()
    assert bundle["container_digest"] == keys.env_manifest_digest(env.manifest())
    assert bundle["implementation_revision"] == toy_curve.implementation_revision()
    assert bundle["numeric_profile"] == pari.NUMERIC_PROFILE == "libpari nbthreads=1"
    canon.encode(keys.IDENTITY_BUNDLE, bundle)


def test_identity_hash_moves_with_the_implementation_revision(tmp_path):
    for rel in toy_curve.IDENTITY_SOURCES:
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        source = toy_curve.REPO_ROOT / rel
        assert source.is_file(), f"{rel} is named in IDENTITY_SOURCES but absent"
        target.write_bytes(source.read_bytes())
    base = toy_curve.skill_identity_hash(root=tmp_path)
    assert base == toy_curve.skill_identity_hash()
    path = tmp_path / toy_curve.IDENTITY_SOURCES[0]
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 0x01
    path.write_bytes(bytes(data))
    assert toy_curve.skill_identity_hash(root=tmp_path) != base


def test_env_manifest_refuses_a_missing_gp_binary(monkeypatch):
    assert set(env.manifest()) == set(keys.ENV_MANIFEST.names)
    monkeypatch.setattr(pari, "GP_BIN", "/nonexistent/gp")
    with pytest.raises(pari.GpMissing, match="/nonexistent/gp"):
        env.gp_binary_sha256()
    with pytest.raises(pari.GpMissing):
        env.manifest()


@pytest.mark.parametrize(
    ("stdin", "code", "empty_stdout"),
    [('{"bits": 40, "seed": 1}', 0, False), ('{"bits": 40}', 1, True), ("not json", 1, True)],
    ids=["well-formed", "missing-seed", "non-json"],
)
def test_module_entry_reads_stdin_and_writes_one_canonical_document(stdin, code, empty_stdout):
    proc = subprocess.run(list(MODULE_ARGV), input=stdin, capture_output=True, text=True, timeout=120)
    assert proc.returncode == code
    if empty_stdout:
        assert proc.stdout == "" and proc.stderr.splitlines()[-1].startswith("error: ")
        return
    assert proc.stdout.count("\n") == 1
    assert toy_curve.ToyCurveOutput.from_json(proc.stdout) == toy_curve.run(40, 1)
    assert proc.stdout == toy_curve.run(40, 1).to_json()


def test_module_entry_writes_a_disagree_document(monkeypatch):
    import io

    real = pari.ellsea
    monkeypatch.setattr(pari, "ellsea", lambda E, early_abort=0: real(E, early_abort) + 2)
    out, err = io.StringIO(), io.StringIO()
    assert toy_curve.main(stdin=io.StringIO('{"bits": 40, "seed": 1}'), stdout=out, stderr=err) == 0
    document = json.loads(out.getvalue())
    assert document["status"] == "DISAGREE" and document["cross_check"]["result"] == "disagree"
    assert [t["call"] for t in document["transcripts"]] == ["ellcard", "ellsea"]
    assert err.getvalue() == ""
