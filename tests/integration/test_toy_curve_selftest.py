import copy
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

from cairn import bundle, canon, cli, env, exits, keys, pari, selftest, substrate, verifier
from cairn.skills import toy_curve

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="pinned_bundle pins through uappnd, a macOS/BSD chflags bit; the Linux arm is cairn-hcl",
)

TRANSCRIPT_GOLDEN = "toy_curve_selftest_transcript"
FLOOR_GOLDEN = "toy_curve_floor"
CERTIFICATE_GOLDEN = "toy_curve_certificate"
GOLDENS = Path(__file__).resolve().parent.parent / "goldens"


def _run(argv, capsys):
    code = cli.main(argv)
    out, err = capsys.readouterr()
    return code, out, err


def _paths(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    return (
        (
            "--bundle",
            str(bundle_path),
            "--pin",
            str(pin_path),
            "--db",
            str(tmp_path / "substrate.sqlite"),
        ),
        bundle_path,
        pin_path,
    )


def _config(bundle_path, pin_path):
    return bundle.GateBundle.open(bundle_path, pin_path).verifier_config()


def _writable_copy(source, destination):
    shutil.copy(source, destination)
    os.chmod(destination, 0o644)
    return destination


def _edit_one_row(path, kind="tiers"):
    conn = sqlite3.connect(str(path))
    conn.execute("UPDATE objects SET canonical = ? WHERE kind = ?", (b"tampered", kind))
    conn.commit()
    conn.close()


def _certificate_rows(db_path):
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return conn.execute("SELECT * FROM skill_certificates").fetchall()
    finally:
        conn.close()


def _records(log_path, event):
    return [
        json.loads(line)
        for line in log_path.read_text().splitlines()
        if line.strip() and json.loads(line).get("event") == event
    ]


def test_selftest_certifies_the_revision_and_records_every_row(tmp_path, pinned_bundle, capsys, json_test_log):
    argv, bundle_path, pin_path = _paths(tmp_path, pinned_bundle)
    code, out, err = _run(["selftest", "toy-curve", *argv, "--json"], capsys)
    assert code == exits.OK, err
    document = json.loads(out)
    assert out.count("\n") == 1
    assert document["schema_version"] == cli.SCHEMA_VERSION
    assert document["command"] == "selftest"
    assert document["pass"] == 4 and document["floor"] == 4
    assert document["arms"] == {
        "postcondition": "pass",
        "verifier": {"ok": 20, "fail": 20},
    }
    assert document["double_run"] == "byte-equal"
    assert document["bundle"] == bundle.GateBundle.open(bundle_path, pin_path).hash

    identity_hash = toy_curve.skill_identity_hash()
    assert document["identity_bundle_hash"] == identity_hash
    with substrate.Substrate.open(tmp_path / "substrate.sqlite", role="reader") as sub:
        assert sub.certified(identity_hash)
        assert sub.get_node(identity_hash) is not None
        assert sub.get_node(document["certificate"]) is not None
        assert sub.is_root("certificate", document["certificate"])
        assert [(r["parent_hash"], r["edge_kind"]) for r in sub.lineage_of(document["certificate"])] == [
            (identity_hash, substrate.EDGE_CERTIFIES)
        ]
        row = sub.get_certificate(identity_hash)
    assert row["cert_hash"] == document["certificate"]
    assert row["transcript_hash"] == document["transcript_hash"]
    assert row["env_manifest_hash"] == keys.env_manifest_digest(env.manifest())

    summary = json.loads(row["selftest_summary"])
    assert summary["pass"] == 4 and summary["floor"] == 4
    assert summary["randomized_arm"] is True
    assert summary["cross_check"]["axis"] == toy_curve.CROSS_CHECK_AXIS
    assert summary["cross_check"]["independent_range"] == toy_curve.INDEPENDENT_RANGE
    origins = summary["corpus_origins"]
    assert origins["F5"]["P"] == "author_supplied"
    assert origins["F5"]["Q"] == "author_supplied"
    assert origins["F5"]["x"] == "author_supplied"
    assert origins["GF101"]["P"] == "author_supplied"
    assert origins["F5"]["p"] == "upstream_vendored"
    assert origins["bits150"]["P"] == "upstream_vendored"

    arms = _records(json_test_log, "arm")
    verifier_record = next(r for r in arms if r["name"] == "verifier")
    assert verifier_record["bundle_hash"] == document["bundle"]
    assert verifier_record["ok"] == verifier_record["fail"] == 20
    assert {r["id"] for r in _records(json_test_log, "case")} == {
        "F5",
        "GF101",
        "bits150",
        "negative_control",
    }


def test_selftest_is_idempotent_for_an_unchanged_revision(tmp_path, pinned_bundle, capsys):
    argv, _, _ = _paths(tmp_path, pinned_bundle)
    first_code, first_out, _ = _run(["selftest", "toy-curve", *argv, "--json"], capsys)
    second_code, second_out, err = _run(["selftest", "toy-curve", *argv, "--json"], capsys)
    assert (first_code, second_code) == (exits.OK, exits.OK), err
    first, second = json.loads(first_out), json.loads(second_out)
    assert first["recorded"] == "inserted" and second["recorded"] == "present"
    assert first["certificate"] == second["certificate"]
    assert len(_certificate_rows(tmp_path / "substrate.sqlite")) == 1


def test_the_alias_resolves(tmp_path, pinned_bundle, capsys):
    argv, _, _ = _paths(tmp_path, pinned_bundle)
    code, out, err = _run(["self-test", "toy-curve", *argv, "--json"], capsys)
    assert code == exits.OK, err
    assert json.loads(out)["command"] == "selftest"


def test_transcript_and_floor_goldens(tmp_path, pinned_bundle, assert_golden):
    bundle_path, pin_path = pinned_bundle()
    result = selftest.run_once(_config(bundle_path, pin_path))
    assert_golden(
        TRANSCRIPT_GOLDEN,
        "\n".join(selftest.transcript_lines(result["records"])) + "\n",
    )
    assert_golden(
        FLOOR_GOLDEN,
        json.dumps(
            {
                "pass": result["passes"],
                "floor": result["floor"],
                "arms": result["arms"],
            },
            indent=1,
            sort_keys=True,
        )
        + "\n",
    )


def test_transcript_golden_guard(tmp_path, pinned_bundle, assert_golden, monkeypatch):
    bundle_path, pin_path = pinned_bundle()
    monkeypatch.delenv("UPDATE_GOLDENS", raising=False)
    result = selftest.run_once(_config(bundle_path, pin_path))
    live = "\n".join(selftest.transcript_lines(result["records"])) + "\n"
    assert_golden(TRANSCRIPT_GOLDEN, live)
    with pytest.raises(AssertionError, match="UPDATE_GOLDENS=1"):
        assert_golden(TRANSCRIPT_GOLDEN, live + "0\n")


def test_the_certificate_is_the_digest_of_its_three_inputs(tmp_path, pinned_bundle, assert_golden):
    bundle_path, pin_path = pinned_bundle()
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        result = selftest.certify(sub, _config(bundle_path, pin_path))
    recomputed = canon.digest(
        keys.TAG_SELFTEST_CERT,
        substrate.certificate_canonical(
            result["identity_bundle_hash"],
            result["transcript_hash"],
            keys.env_manifest_digest(env.manifest()),
        ),
    )
    assert recomputed == result["certificate"]
    assert_golden(
        CERTIFICATE_GOLDEN,
        json.dumps({"implementation_revision": toy_curve.implementation_revision()}, indent=1, sort_keys=True) + "\n",
    )


def test_a_changed_expected_output_refuses_and_writes_no_certificate(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    doc = copy.deepcopy(selftest.load_corpus())
    doc["cases"][0]["fields"]["Q"]["value"] = [3, 2]
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        with pytest.raises(selftest.SelftestFailed, match="ellmul"):
            selftest.certify(sub, _config(bundle_path, pin_path), doc=doc)
        assert not sub.certified(toy_curve.skill_identity_hash())
    assert _certificate_rows(tmp_path / "substrate.sqlite") == []


def test_the_negative_control_point_must_not_be_killed_by_the_order(tmp_path):
    case = next(c for c in selftest.load_corpus()["cases"] if c["id"] == "negative_control")
    observed, held, per_check = selftest.run_case(case)
    assert held and per_check["order_does_not_kill"]
    assert observed["order_does_not_kill"] == [61, 319]
    assert observed["ellorder"] == 21

    killed = copy.deepcopy(case)
    killed["fields"]["Q"]["value"] = killed["fields"]["P"]["value"]
    _, held_after, per_check_after = selftest.run_case(killed)
    assert not held_after and not per_check_after["order_does_not_kill"]


def test_a_bumped_revision_is_not_certified(tmp_path, pinned_bundle, capsys):
    argv, _, _ = _paths(tmp_path, pinned_bundle)
    code, out, err = _run(["selftest", "toy-curve", *argv, "--json"], capsys)
    assert code == exits.OK, err
    certified_identity = json.loads(out)["identity_bundle_hash"]
    tree = tmp_path / "bumped"
    for rel in toy_curve.IDENTITY_SOURCES:
        target = tree / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((toy_curve.REPO_ROOT / rel).read_bytes())
    edited = tree / toy_curve.IDENTITY_SOURCES[0]
    edited.write_bytes(edited.read_bytes() + b"\n")

    bumped_identity = keys.identity_bundle_hash(toy_curve.identity_bundle(tree))
    assert bumped_identity != certified_identity
    assert toy_curve.implementation_revision(tree) != toy_curve.implementation_revision()
    assert selftest.arm_seed(toy_curve.implementation_revision(tree)) != selftest.arm_seed(
        toy_curve.implementation_revision()
    )
    with substrate.Substrate.open(tmp_path / "substrate.sqlite", role="reader") as sub:
        assert sub.certified(certified_identity)
        assert not sub.certified(bumped_identity)
        assert sub.get_certificate(bumped_identity) is None


def test_the_verifier_arm_refuses_every_wrong_draw(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    config = _config(bundle_path, pin_path)
    seed = selftest.arm_seed(toy_curve.implementation_revision()) or 1
    out, _ = selftest.postcondition_arm(seed)
    body = selftest.verifier_arm(out, config, seed)
    assert body["reasons"] == {"xP-ne-Q": selftest.DRAW_COUNT}


def test_a_field_without_an_origin_is_refused_before_any_case_runs(tmp_path, pinned_bundle, monkeypatch):
    bundle_path, pin_path = pinned_bundle()
    calls = []
    for name in ("ellcard", "ellsea", "ellorder"):
        real = getattr(pari, name)
        monkeypatch.setattr(
            pari,
            name,
            lambda *a, _n=name, _r=real, **k: (calls.append(_n), _r(*a, **k))[1],
        )
    reached = []
    monkeypatch.setattr(
        selftest,
        "run_case",
        lambda case: reached.append(case["id"]) or (None, True, {}),
    )
    doc = copy.deepcopy(selftest.load_corpus())
    del doc["cases"][1]["fields"]["P"]["origin"]
    with (
        substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub,
        pytest.raises(selftest.CorpusSchemaError, match=r"\$\.cases\[1\]\.fields\.P"),
    ):
        selftest.certify(sub, _config(bundle_path, pin_path), doc=doc)
    assert calls == [] and reached == []
    assert _certificate_rows(tmp_path / "substrate.sqlite") == []


def test_a_pin_that_does_not_match_aborts_before_any_case_runs(tmp_path, pinned_bundle, capsys, monkeypatch):
    bundle_path, pin_path = pinned_bundle()
    tampered = _writable_copy(bundle_path, tmp_path / "tampered.sqlite")
    _edit_one_row(tampered)
    calls = []
    monkeypatch.setattr(selftest, "run_case", lambda case: calls.append(case["id"]) or (None, True, {}))
    db = tmp_path / "substrate.sqlite"
    code, out, err = _run(
        [
            "selftest",
            "toy-curve",
            "--bundle",
            str(tampered),
            "--pin",
            str(pin_path),
            "--db",
            str(db),
            "--json",
        ],
        capsys,
    )
    assert code == exits.GATE_REFUSED
    assert out == "" and "chflags nouappnd" in err
    assert calls == []
    assert _certificate_rows(db) == []


def test_a_missing_bundle_exits_environment(tmp_path, capsys):
    code, out, err = _run(
        [
            "selftest",
            "toy-curve",
            "--bundle",
            str(tmp_path / "absent.sqlite"),
            "--pin",
            str(tmp_path / "absent.pin"),
            "--db",
            str(tmp_path / "substrate.sqlite"),
        ],
        capsys,
    )
    assert code == exits.ENVIRONMENT
    assert out == "" and "absent.sqlite" in err
    assert _certificate_rows(tmp_path / "substrate.sqlite") == []


def test_the_double_run_is_byte_equal(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    config = _config(bundle_path, pin_path)
    first = selftest.run_once(config)
    second = selftest.run_once(config)
    assert first["transcript"] == second["transcript"]
    assert first["transcript_hash"] == second["transcript_hash"]
    assert len(first["records"]) == 6


LEDGER_CASES = [
    ("F5", "pass", "ellmul"),
    ("GF101", "pass", "ellorder"),
    ("bits150", "pass", "order_kills"),
    ("negative_control", "pass", "order_does_not_kill"),
]


@pytest.mark.parametrize(
    ("case_id", "expected_ledger", "postcondition"),
    LEDGER_CASES,
    ids=["F5", "GF101", "bits150", "negative_control"],
)
def test_the_ledger_entry_and_postcondition_of_every_case(case_id, expected_ledger, postcondition):
    case = next(c for c in selftest.load_corpus()["cases"] if c["id"] == case_id)
    assert case["ledger"] == expected_ledger
    assert postcondition in case["postconditions"]
    observed, held, per_check = selftest.run_case(case)
    assert held and per_check[postcondition]
    assert set(observed) == set(case["postconditions"])


def _result(accepted, reason):
    return verifier.VerifierResult(
        instance_hash="00" * 32,
        x=1,
        accepted=accepted,
        reason=reason,
        reasons=() if reason is None else (reason,),
        stdout_digest="00" * 32,
        stderr_digest="00" * 32,
        rc=0 if accepted else 1,
        wall_s=0.0,
    )


@pytest.mark.parametrize(
    ("behavior", "match"),
    [
        ("accept_everything", "was accepted"),
        ("refuse_everything", "was refused"),
        ("wrong_reason", "unexpected refusal reasons"),
    ],
)
def test_the_verifier_arm_refuses_a_driver_that_misbehaves(tmp_path, pinned_bundle, monkeypatch, behavior, match):
    bundle_path, pin_path = pinned_bundle()
    config = _config(bundle_path, pin_path)
    seed = selftest.arm_seed(toy_curve.implementation_revision()) or 1
    out, _ = selftest.postcondition_arm(seed)
    real = verifier.Verifier.run
    if behavior == "accept_everything":
        replacement = lambda self, instance, x: _result(True, None)  # noqa: E731
    elif behavior == "refuse_everything":
        replacement = lambda self, instance, x: _result(False, "xP-ne-Q")  # noqa: E731
    else:

        def replacement(self, instance, x):
            result = real(self, instance, x)
            return result if result.accepted else _result(False, "nQ-not-O")

    monkeypatch.setattr(verifier.Verifier, "run", replacement)
    with pytest.raises(selftest.SelftestFailed, match=match):
        selftest.verifier_arm(out, config, seed)


def test_the_verifier_arm_drives_the_real_verifier_once_per_draw(tmp_path, pinned_bundle, monkeypatch):
    bundle_path, pin_path = pinned_bundle()
    config = _config(bundle_path, pin_path)
    seed = selftest.arm_seed(toy_curve.implementation_revision()) or 1
    out, _ = selftest.postcondition_arm(seed)
    submitted = []
    real = verifier.Verifier.run

    def spy(self, instance, x):
        submitted.append(x)
        return real(self, instance, x)

    monkeypatch.setattr(verifier.Verifier, "run", spy)
    body = selftest.verifier_arm(out, config, seed)
    assert body["ok"] == body["fail"] == selftest.DRAW_COUNT
    assert len(submitted) == 2 * selftest.DRAW_COUNT
    assert submitted[0::2] == selftest._draws(seed, out.n, selftest.DRAW_COUNT, b"verifier-x")
    assert all(a != b for a, b in zip(submitted[0::2], submitted[1::2], strict=True))


def test_a_case_below_the_floor_refuses(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    doc = copy.deepcopy(selftest.load_corpus())
    doc["cases"][2]["ledger"] = "known_gap"
    with (
        substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub,
        pytest.raises(selftest.SelftestFailed, match="below the floor 4"),
    ):
        selftest.certify(sub, _config(bundle_path, pin_path), doc=doc)
    assert _certificate_rows(tmp_path / "substrate.sqlite") == []


def test_a_diverging_double_run_refuses(tmp_path, pinned_bundle, monkeypatch):
    bundle_path, pin_path = pinned_bundle()
    real = selftest.run_once
    seen = []

    def drifting(config, *, doc=None, root=None):
        result = real(config, doc=doc, root=root)
        seen.append(1)
        if len(seen) == 2:
            result = {**result, "transcript": result["transcript"] + b"drift"}
        return result

    monkeypatch.setattr(selftest, "run_once", drifting)
    with (
        substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub,
        pytest.raises(selftest.SelftestFailed, match="double-run"),
    ):
        selftest.certify(sub, _config(bundle_path, pin_path))
    assert _certificate_rows(tmp_path / "substrate.sqlite") == []


def test_a_recorded_certificate_that_differs_from_the_minted_one_refuses(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    identity = toy_curve.identity_bundle()
    identity_hash = keys.identity_bundle_hash(identity)
    env_hash = keys.env_manifest_digest(env.manifest())
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        sub.put_identity_bundle(identity)
        planted = sub.put_certificate(identity_hash, "ab" * 32, env_hash, {"planted": 1})
        with pytest.raises(selftest.SelftestFailed, match="differs from the minted"):
            selftest.certify(sub, _config(bundle_path, pin_path))
        assert sub.get_certificate(identity_hash)["cert_hash"] == planted
    assert len(_certificate_rows(tmp_path / "substrate.sqlite")) == 1


def test_a_malformed_corpus_exits_user_input(tmp_path, pinned_bundle, capsys, monkeypatch):
    argv, _, _ = _paths(tmp_path, pinned_bundle)

    def raiser(*a, **k):
        raise selftest.CorpusSchemaError("$.cases[0].fields.P", "field is missing origin")

    monkeypatch.setattr(selftest, "certify", raiser)
    code, out, err = _run(["selftest", "toy-curve", *argv, "--json"], capsys)
    assert code == exits.USER_INPUT
    assert out == "" and "$.cases[0].fields.P" in err and "--log DEBUG" in err
    assert _certificate_rows(tmp_path / "substrate.sqlite") == []


@pytest.mark.parametrize(
    "error",
    [
        selftest.SelftestFailed("floor", "3 passing cases is below the floor 4"),
        toy_curve.PostconditionFailed("isprime", "n is not prime"),
    ],
    ids=["selftest-failed", "postcondition-failed"],
)
def test_a_failing_selftest_exits_gate_refused(tmp_path, pinned_bundle, capsys, monkeypatch, error):
    argv, _, _ = _paths(tmp_path, pinned_bundle)

    def raiser(*a, **k):
        raise error

    monkeypatch.setattr(selftest, "certify", raiser)
    code, out, err = _run(["selftest", "toy-curve", *argv, "--json"], capsys)
    assert code == exits.GATE_REFUSED
    assert out == "" and "--log DEBUG" in err
    assert _certificate_rows(tmp_path / "substrate.sqlite") == []


def test_without_json_the_command_prints_the_certificate_hash(tmp_path, pinned_bundle, capsys):
    argv, _, _ = _paths(tmp_path, pinned_bundle)
    code, out, err = _run(["selftest", "toy-curve", *argv], capsys)
    assert code == exits.OK, err
    with substrate.Substrate.open(tmp_path / "substrate.sqlite", role="reader") as sub:
        row = sub.get_certificate(toy_curve.skill_identity_hash())
    assert out.strip() == row["cert_hash"]


def test_an_identity_node_already_present_is_not_written_twice(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    identity = toy_curve.identity_bundle()
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        sub.put_identity_bundle(identity)
        result = selftest.certify(sub, _config(bundle_path, pin_path))
        assert result["recorded"] == "inserted"
        assert sub.certified(result["identity_bundle_hash"])
    assert len(_certificate_rows(tmp_path / "substrate.sqlite")) == 1
