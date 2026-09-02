import dataclasses
import hashlib
import io
import json
from pathlib import Path

import pytest

from cairn import ec, instances, keys, selftest, selftest_skills, substrate
from cairn.skills import instance_maker

VECTORS = Path(__file__).resolve().parent.parent / "vectors"
KAT = json.loads((VECTORS / "canon_kat.json").read_text())
CORPUS = json.loads(Path(instance_maker.REPO_ROOT, "src/cairn/skills/instance_maker_corpus.json").read_text())
NONCE = "ab" * 32
HYPOTHESIS = "cd" * 32


def _vector(name):
    return next(v for v in KAT["vectors"] if v["name"] == name)


def _digest(text):
    return len(text), hashlib.sha256(text.encode()).hexdigest()


def test_the_derivation_matches_its_known_answer_vector():
    vector = _vector("trial_seed")
    assert vector["domain_tag"] == keys.TAG_TRIAL_SEED == "cairn/trial-seed/v1"
    assert keys.trial_seed_hash(vector["input"]) == vector["expected"]
    derived = instances.trial_seed(NONCE, HYPOTHESIS, 40, 7)
    assert derived == int.from_bytes(bytes.fromhex(vector["expected"])[:8], "big") % instances.SEED_MODULUS
    assert derived >= 1


def test_a_vector_with_one_flipped_byte_fails_the_known_answer_test():
    vector = _vector("trial_seed")
    flipped = {**vector["input"], "nonce": "ac" + vector["input"]["nonce"][2:]}
    assert keys.trial_seed_hash(flipped) != vector["expected"]
    assert instances.trial_seed(flipped["nonce"], HYPOTHESIS, 40, 7) != instances.trial_seed(NONCE, HYPOTHESIS, 40, 7)
    assert _vector("trial_seed_next_trial")["expected"] != vector["expected"]


@pytest.mark.parametrize(("bits", "trial"), [(40, 7), (28, 3)])
def test_deriving_one_trial_twice_yields_byte_identical_instances(bits, trial):
    seed = instances.trial_seed(NONCE, HYPOTHESIS, bits, trial)
    assert seed == instances.trial_seed(NONCE, HYPOTHESIS, bits, trial)
    first = instance_maker.run(bits, seed).to_json()
    second = instance_maker.run(bits, seed).to_json()
    assert _digest(first) == _digest(second)
    document = json.loads(first)
    assert document["seed"] == seed and document["bits"] == bits and document["status"] == "OK"


def test_different_nonces_give_different_instances():
    seeds = {instances.trial_seed(f"{i:02x}" * 32, HYPOTHESIS, 28, 0) for i in range(4)}
    assert len(seeds) == 4
    hashes = {instance_maker.run(28, seed).instance_hash for seed in seeds}
    assert len(hashes) == 4


def test_every_input_of_the_derivation_moves_the_seed():
    base = instances.trial_seed(NONCE, HYPOTHESIS, 40, 7)
    assert instances.trial_seed(NONCE, HYPOTHESIS, 40, 8) != base
    assert instances.trial_seed(NONCE, HYPOTHESIS, 41, 7) != base
    assert instances.trial_seed(NONCE, "ce" + HYPOTHESIS[2:], 40, 7) != base
    assert instances.trial_seed("ac" + NONCE[2:], HYPOTHESIS, 40, 7) != base


def test_the_maker_declares_its_output_non_memoizable():
    assert instance_maker.DO_NOT_CACHE is True
    assert instance_maker.REPLAY_GRADE == "Replayable"
    assert instance_maker.SEAM == "cairn.skills.bsgs.discrete_log"
    assert instance_maker.INDEPENDENT_RANGE == {"bits": [0, 28]}
    assert {"src/cairn/instances.py", "src/cairn/skills/toy_curve.py", "src/cairn/pari.py"} <= set(
        instance_maker.IDENTITY_SOURCES
    )


def test_the_answer_is_drawn_inside_the_group_and_q_is_its_multiple():
    out = instance_maker.run(28, 1)
    assert 1 <= out.x < out.n
    assert out.x == instance_maker.draw_x(1, out.n)
    assert ec.mul(out.p, out.a, tuple(out.P), out.x) == tuple(out.Q)
    assert out.instance_hash == keys.instance_hash(out.instance())
    assert instance_maker.check_postcondition(out) is out


@pytest.mark.parametrize(
    ("mutate", "clause"),
    [
        (lambda o: dataclasses.replace(o, x=o.x % (o.n - 1) + 1), "ellmul"),
        (lambda o: dataclasses.replace(o, instance_hash="0" * 64), "instance_hash"),
        (lambda o: dataclasses.replace(o, Q=(o.Q[0], (o.Q[1] + 1) % o.p)), "oncurve"),
        (lambda o: dataclasses.replace(o, n=o.n + 2), "isprime|hasse|ellmul"),
        (lambda o: dataclasses.replace(o, x=0), "x-range"),
        (lambda o: dataclasses.replace(o, x=o.n), "x-range"),
    ],
    ids=["x-plus-one", "hash", "Q-off-curve", "n", "x-zero", "x-equals-n"],
)
def test_the_postcondition_refuses_a_planted_wrong_answer(mutate, clause):
    out = instance_maker.run(28, 1)
    with pytest.raises(instance_maker.PostconditionFailed, match=clause):
        instance_maker.check_postcondition(mutate(out))


def test_a_planted_disagreement_at_the_seam_surfaces_as_disagree(monkeypatch):
    from cairn.skills import bsgs

    real = bsgs.discrete_log
    monkeypatch.setattr(bsgs, "discrete_log", lambda *a, **k: real(*a, **k) + 2)
    out = instance_maker.run(28, 1)
    assert out.status == "DISAGREE" and out.cross_check["result"] == "disagree"
    assert out.transcripts is not None and len({t["digest"] for t in out.transcripts}) == 2
    assert instance_maker.run(30, 1).cross_check["result"] == "untested"


@pytest.mark.parametrize(
    ("text", "match"),
    [("", "empty stdin"), ("[]", "not a JSON object"), ('{"bits": 28}', "missing"), ('{"bits": 2, "seed": 1}', ">= 3")],
)
def test_parse_inputs_refuses_malformed_stdin(text, match):
    with pytest.raises(instance_maker.InputError, match=match):
        instance_maker.parse_inputs(text)


def test_main_writes_canonical_json_and_round_trips():
    out, err = io.StringIO(), io.StringIO()
    assert instance_maker.main(io.StringIO('{"bits": 28, "seed": 1}'), out, err) == 0
    text = out.getvalue()
    assert text == json.dumps(json.loads(text), sort_keys=True, separators=(",", ":")) + "\n"
    parsed = instance_maker.InstanceOutput.from_json(text)
    assert parsed.to_json() == text and parsed.x == instance_maker.run(28, 1).x
    assert instance_maker.main(io.StringIO("{}"), io.StringIO(), err) == 1 and err.getvalue().startswith("error:")
    with pytest.raises(instance_maker.InputError, match="does not match instance_maker_output"):
        instance_maker.InstanceOutput.from_json('{"bits": 28}')


@pytest.fixture
def sub(tmp_path):
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as writer:
        yield writer


def test_a_nonce_is_withheld_until_published_and_recorded_with_its_trials(sub):
    record = instances.commit_nonce(sub, HYPOTHESIS, "run-1", NONCE, at="2026-09-01T00:00:00.000000+00:00")
    assert record.withheld and instances.withheld(sub, NONCE)
    assert instances.nonces_for(sub, HYPOTHESIS) == [record]
    instances.record_trial(sub, NONCE, 28, 0, 5, "0" * 64, 12345, None)
    published = instances.publish_nonce(sub, NONCE, at="2026-09-01T00:00:01.000000+00:00")
    assert not published.withheld and not instances.withheld(sub, NONCE)
    assert instances.get_nonce(sub, NONCE) == published
    assert instances.trials_for(sub, NONCE) == [
        {"nonce": NONCE, "bits": 28, "trial": 0, "seed": 5, "instance_hash": "0" * 64, "x": "12345", "attempt_id": None}
    ]


def test_a_second_run_requesting_the_same_nonce_for_the_same_object_is_refused(sub):
    instances.commit_nonce(sub, HYPOTHESIS, "run-1", NONCE)
    with pytest.raises(instances.NonceReused, match="nonce-reused") as info:
        instances.commit_nonce(sub, HYPOTHESIS, "run-2", NONCE)
    assert info.value.reason == instances.NONCE_REUSED
    with pytest.raises(instances.NonceReused, match=HYPOTHESIS[:12]):
        instances.commit_nonce(sub, "ef" * 32, "run-3", NONCE)
    assert instances.commit_nonce(sub, "ef" * 32, "run-3", "ac" * 32).hypothesis_key == "ef" * 32


def test_a_run_draws_exactly_one_nonce(sub):
    instances.commit_nonce(sub, HYPOTHESIS, "run-1", NONCE)
    with pytest.raises(instances.RunHasNonce, match="run-has-nonce"):
        instances.commit_nonce(sub, HYPOTHESIS, "run-1", "ac" * 32)


def test_the_remaining_lifecycle_refusals_are_typed(sub):
    with pytest.raises(instances.UnknownNonce, match="unknown-nonce"):
        instances.publish_nonce(sub, NONCE)
    with pytest.raises(instances.UnknownNonce):
        instances.withheld(sub, NONCE)
    with pytest.raises(instances.UnknownNonce):
        instances.record_trial(sub, NONCE, 28, 0, 5, "0" * 64, 1, None)
    with pytest.raises(instances.InstanceError, match="bad-nonce"):
        instances.commit_nonce(sub, HYPOTHESIS, "run-1", "xyz")
    instances.commit_nonce(sub, HYPOTHESIS, "run-1", NONCE)
    instances.publish_nonce(sub, NONCE)
    with pytest.raises(instances.NoncePublished, match="nonce-published"):
        instances.publish_nonce(sub, NONCE)
    instances.record_trial(sub, NONCE, 28, 0, 5, "0" * 64, 1, None)
    with pytest.raises(instances.TrialRecorded, match="trial-recorded"):
        instances.record_trial(sub, NONCE, 28, 0, 6, "0" * 64, 1, None)


def test_draw_nonce_takes_its_entropy_from_secrets_and_never_from_the_hypothesis(sub, monkeypatch):
    calls = []

    def token_bytes(size):
        calls.append(size)
        return bytes([len(calls)]) * size

    monkeypatch.setattr(instances.secrets, "token_bytes", token_bytes)
    first = instances.draw_nonce(sub, HYPOTHESIS, "run-1")
    second = instances.draw_nonce(sub, HYPOTHESIS, "run-2")
    assert calls == [instances.NONCE_BYTES, instances.NONCE_BYTES]
    assert (first.nonce, second.nonce) == ("01" * 32, "02" * 32)
    assert first.hypothesis_key == second.hypothesis_key == HYPOTHESIS and first.withheld and second.withheld
    assert len(instances.fresh_nonce()) == 64


def test_the_corpus_vectors_pin_the_same_encoding_as_the_kat():
    case = next(c for c in CORPUS["cases"] if c["id"] == "vector_bits40_trial7")
    fields = {name: field["value"] for name, field in case["fields"].items()}
    assert fields["seed"] == instances.trial_seed(fields["nonce"], fields["hypothesis_key"], 40, 7)
    assert fields["nonce"] == _vector("trial_seed")["input"]["nonce"]


def test_a_toy_curve_disagreement_propagates_with_its_transcripts(monkeypatch):
    from cairn.skills import toy_curve

    real = toy_curve.run

    def disagreeing(bits, seed):
        out = real(bits, seed)
        curve = (out.a, out.b, out.p)
        return toy_curve._disagree(
            out, toy_curve._transcript("ellcard", curve, out.n), toy_curve._transcript("ellsea", curve, out.n + 2)
        )

    monkeypatch.setattr(toy_curve, "run", disagreeing)
    outside = instance_maker.run(30, 1)
    assert outside.status == "DISAGREE" and outside.cross_check["result"] == "untested"
    assert outside.transcripts is not None and [t["call"] for t in outside.transcripts] == ["ellcard", "ellsea"]
    inside = instance_maker.run(28, 1)
    assert inside.status == "DISAGREE" and inside.cross_check["result"] == "disagree"
    assert inside.transcripts is not None and [t["call"] for t in inside.transcripts] == ["ellcard", "ellsea"]


@pytest.mark.parametrize("nonce", ["ab" * 31, 12, "zz" * 32, "AB" * 32], ids=["short", "int", "non-hex", "uppercase"])
def test_a_malformed_nonce_is_refused_before_any_row_is_written(sub, nonce):
    with pytest.raises(instances.InstanceError, match="bad-nonce") as info:
        instances.commit_nonce(sub, HYPOTHESIS, "run-1", nonce)
    assert info.value.reason == "bad-nonce"
    assert sub.conn.execute("SELECT count(*) FROM instance_nonces").fetchone()[0] == 0


def test_a_zero_digest_prefix_derives_seed_one_rather_than_zero(monkeypatch):
    monkeypatch.setattr(keys, "trial_seed_hash", lambda trial: "00" * 32)
    assert instances.trial_seed(NONCE, HYPOTHESIS, 40, 7) == 1


def test_an_unknown_selftest_name_is_a_typed_key_error():
    with pytest.raises(KeyError, match="no self-test for 'nope'"):
        selftest_skills.module_for("nope")
    assert selftest_skills.postcondition_errors()[1:] == tuple(
        selftest_skills.module_for(name).PostconditionFailed for name in selftest_skills.NAMES
    )


def test_the_other_scalar_moves_off_a_colliding_draw():
    n = 1000003
    drawn = selftest._draws(7, n, 1, b"probe")[0]
    other = selftest_skills._other_scalar(7, n, drawn, b"probe")
    assert other != drawn and other == drawn % (n - 1) + 1
    assert selftest_skills._other_scalar(7, n, drawn + 1, b"probe") == drawn


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda d: d.pop("pass_floor"), "missing pass_floor"),
        (lambda d: d.pop("cases"), "missing cases"),
        (lambda d: d.update(schema_version=2), "schema_version must be 1"),
        (lambda d: d.update(cases=[]), "non-empty list"),
        (lambda d: d["cases"].append("case"), "must be an object"),
        (lambda d: d["cases"].append(dict(d["cases"][0])), "unique non-empty string"),
        (lambda d: d["cases"][0].pop("source"), "missing source"),
        (lambda d: d["cases"][0].update(source=""), "non-empty string"),
        (lambda d: d["cases"][0].update(ledger="maybe"), "ledger must be one of"),
        (lambda d: d["cases"][0].update(fields=[]), "fields must be an object"),
        (lambda d: d["cases"][0]["fields"].pop("seed"), "missing required fields seed"),
        (lambda d: d["cases"][0]["fields"].update(extra={"value": 1, "origin": "author_supplied"}), "unknown fields"),
        (lambda d: d["cases"][0]["fields"]["nonce"].update(value="zz"), "64 lowercase hex"),
        (lambda d: d["cases"][0]["fields"]["nonce"].update(origin="made_up"), "origin must be one of"),
        (lambda d: d["cases"][0]["fields"]["bits"].update(value=-1), "non-negative integer"),
        (lambda d: d["cases"][0]["fields"]["bits"].update(note="x"), "exactly"),
        (lambda d: d["cases"][2]["fields"].pop("Q"), "all of p, a, b, n, P, Q, x"),
        (lambda d: d["cases"][2]["fields"]["P"].update(value=[1]), "pair of integers"),
        (lambda d: d.update(pass_floor=99), "within"),
    ],
)
def test_a_malformed_maker_corpus_is_refused_before_any_case_runs(mutate, match):
    import copy

    doc = copy.deepcopy(selftest_skills.load_maker_corpus())
    mutate(doc)
    with pytest.raises(selftest.CorpusSchemaError, match=match):
        selftest_skills.check_maker_corpus(doc)


def test_the_committed_maker_corpus_loads_from_its_default_path_and_from_an_explicit_one(tmp_path):
    doc = selftest_skills.load_maker_corpus()
    copy_path = tmp_path / "corpus.json"
    copy_path.write_text(json.dumps(doc))
    assert selftest_skills.load_maker_corpus(copy_path) == doc
    copy_path.write_text("{")
    with pytest.raises(selftest.CorpusSchemaError, match="not valid JSON"):
        selftest_skills.load_maker_corpus(copy_path)


def test_the_nonce_and_trial_tables_are_append_only(sub):
    import sqlite3

    instances.commit_nonce(sub, HYPOTHESIS, "run-1", NONCE)
    instances.record_trial(sub, NONCE, 28, 0, 5, "0" * 64, 1, None)
    for statement in (
        "DELETE FROM instance_nonces",
        "DELETE FROM instance_trials",
        "UPDATE instance_trials SET seed = 6",
        "UPDATE instance_nonces SET hypothesis_key = 'ef'",
        "UPDATE instance_nonces SET nonce = 'ac'",
    ):
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            sub.conn.execute(statement)
    instances.publish_nonce(sub, NONCE)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        sub.conn.execute("UPDATE instance_nonces SET published_at = NULL")
