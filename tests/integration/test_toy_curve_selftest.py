import copy
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

from cairn import bundle, cli, env, exits, keys, pari, selftest, substrate, verifier
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


def test_selftest_certifies_the_revision_and_records_every_row(
    tmp_path, pinned_bundle, capsys, json_test_log
):
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
        assert [
            (r["parent_hash"], r["edge_kind"])
            for r in sub.lineage_of(document["certificate"])
        ] == [(identity_hash, substrate.EDGE_CERTIFIES)]
        row = sub.get_certificate(identity_hash)
    assert row["cert_hash"] == document["certificate"]
    assert row["transcript_hash"] == document["transcript_hash"]
    assert row["env_manifest_hash"] == keys.env_manifest_digest(env.manifest())

    summary = json.loads(row["selftest_summary"])
    assert summary["pass"] == 4 and summary["floor"] == 4
    assert summary["randomized_arm"] is True
    assert summary["cross_check"]["axis"] == toy_curve.CROSS_CHECK_AXIS
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


def test_selftest_is_idempotent_for_an_unchanged_revision(
    tmp_path, pinned_bundle, capsys
):
    argv, _, _ = _paths(tmp_path, pinned_bundle)
    first_code, first_out, _ = _run(["selftest", "toy-curve", *argv, "--json"], capsys)
    second_code, second_out, err = _run(
        ["selftest", "toy-curve", *argv, "--json"], capsys
    )
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


def test_certificate_golden_recomputes_from_the_golden_transcript(
    tmp_path, pinned_bundle, assert_golden, caplog
):
    bundle_path, pin_path = pinned_bundle()
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        result = selftest.certify(sub, _config(bundle_path, pin_path))
    live_identity = result["identity_bundle_hash"]
    live_env = keys.env_manifest_digest(env.manifest())
    assert_golden(
        CERTIFICATE_GOLDEN,
        json.dumps(
            {
                "certificate": result["certificate"],
                "identity_bundle_hash": live_identity,
                "env_manifest_hash": live_env,
                "transcript_hash": result["transcript_hash"],
                "implementation_revision": toy_curve.implementation_revision(),
            },
            indent=1,
            sort_keys=True,
        )
        + "\n",
    )
    golden = json.loads((GOLDENS / f"{CERTIFICATE_GOLDEN}.golden").read_text())
    recomputed = selftest.certificate_hash(
        live_identity, golden["transcript_hash"], live_env
    )
    assert result["certificate"] == recomputed
    if (live_identity, live_env) == (
        golden["identity_bundle_hash"],
        golden["env_manifest_hash"],
    ):
        assert result["certificate"] == golden["certificate"]
    else:
        caplog.set_level("INFO", logger="cairn")


def test_a_changed_expected_output_refuses_and_writes_no_certificate(
    tmp_path, pinned_bundle
):
    bundle_path, pin_path = pinned_bundle()
    doc = copy.deepcopy(selftest.load_corpus())
    doc["cases"][0]["fields"]["Q"]["value"] = [3, 2]
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        with pytest.raises(selftest.SelftestFailed, match="ellmul"):
            selftest.certify(sub, _config(bundle_path, pin_path), doc=doc)
        assert not sub.certified(toy_curve.skill_identity_hash())
    assert _certificate_rows(tmp_path / "substrate.sqlite") == []


def test_the_negative_control_point_must_not_be_killed_by_the_order(tmp_path):
    case = next(
        c for c in selftest.load_corpus()["cases"] if c["id"] == "negative_control"
    )
    observed, held, per_check = selftest.run_case(case)
    assert held and per_check["order_does_not_kill"]
    assert len(observed["order_does_not_kill"]) == 2

    killed = copy.deepcopy(case)
    killed["fields"]["Q"]["value"] = killed["fields"]["P"]["value"]
    _, held_after, per_check_after = selftest.run_case(killed)
    assert not held_after and not per_check_after["order_does_not_kill"]


def test_a_bumped_revision_is_not_certified(tmp_path, pinned_bundle, capsys):
    argv, _, _ = _paths(tmp_path, pinned_bundle)
    code, out, err = _run(["selftest", "toy-curve", *argv, "--json"], capsys)
    assert code == exits.OK, err
    certified_identity = json.loads(out)["identity_bundle_hash"]
    bumped = {
        **toy_curve.identity_bundle(),
        "implementation_revision": "ab" * 32,
    }
    bumped_identity = keys.identity_bundle_hash(bumped)
    assert bumped_identity != certified_identity
    with substrate.Substrate.open(tmp_path / "substrate.sqlite", role="reader") as sub:
        assert sub.certified(certified_identity)
        assert not sub.certified(bumped_identity)


def test_the_verifier_arm_refuses_every_wrong_draw(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    config = _config(bundle_path, pin_path)
    seed = selftest.arm_seed(toy_curve.implementation_revision()) or 1
    out, _ = selftest.postcondition_arm(seed)
    body = selftest.verifier_arm(out, config, seed)
    assert body["ok"] == body["fail"] == selftest.DRAW_COUNT
    assert body["reasons"] == {"xP-ne-Q": selftest.DRAW_COUNT}

    driver = verifier.Verifier(config)
    E = pari.pari.ellinit([out.a, out.b], out.p)
    x = 7
    Q = tuple(int(c) for c in pari.pari.ellmul(E, list(out.P), x))
    instance = verifier.Instance(out.p, out.a, out.b, out.n, tuple(out.P), Q)
    assert driver.run(instance, x).accepted
    refused = driver.run(instance, x + 1)
    assert not refused.accepted and refused.reason == "xP-ne-Q"


def test_a_field_without_an_origin_is_refused_before_any_case_runs(
    tmp_path, pinned_bundle, monkeypatch
):
    bundle_path, pin_path = pinned_bundle()
    calls = []
    for name in ("ellcard", "ellsea", "ellorder"):
        real = getattr(pari, name)
        monkeypatch.setattr(
            pari,
            name,
            lambda *a, _n=name, _r=real, **k: (calls.append(_n), _r(*a, **k))[1],
        )
    doc = copy.deepcopy(selftest.load_corpus())
    del doc["cases"][1]["fields"]["P"]["origin"]
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        with pytest.raises(
            selftest.CorpusSchemaError, match=r"\$\.cases\[1\]\.fields\.P"
        ):
            selftest.certify(sub, _config(bundle_path, pin_path), doc=doc)
    assert calls == []
    assert _certificate_rows(tmp_path / "substrate.sqlite") == []


def test_a_pin_that_does_not_match_aborts_before_any_case_runs(
    tmp_path, pinned_bundle, capsys, monkeypatch
):
    bundle_path, pin_path = pinned_bundle()
    tampered = _writable_copy(bundle_path, tmp_path / "tampered.sqlite")
    _edit_one_row(tampered)
    calls = []
    monkeypatch.setattr(
        selftest, "run_case", lambda case: calls.append(case["id"]) or (None, True, {})
    )
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
