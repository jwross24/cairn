import json
import logging
import os
import sqlite3
from pathlib import Path

import pytest

from cairn import cli, exits, log

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "bundle"
STEP_SEQUENCE = [1, 2, 3, 4, 5, 6, 7, 8, 9]


def _run(argv, capsys):
    code = cli.main(argv)
    out, err = capsys.readouterr()
    return code, out, err


def _counts(db):
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts = {t: conn.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in tables}
        counts["nodes_by_kind"] = {r["kind"]: r["n"] for r in conn.execute("SELECT kind, count(*) n FROM nodes GROUP BY kind")}
        counts["verifier_gate_runs"] = [(r["plan_step"], r["result"], json.loads(r["reasons"])) for r in conn.execute("SELECT * FROM gate_runs WHERE gate='verifier' ORDER BY rowid")]
        return counts
    finally:
        conn.close()


@pytest.fixture
def deploy(tmp_path, clear_flags, capsys):
    paths = {
        "db": tmp_path / "substrate.sqlite",
        "bundle": tmp_path / "gate-bundle.sqlite",
        "pin": tmp_path / "gate-bundle.pin",
        "attest": tmp_path / "attestations.log",
    }
    clear_flags(paths["pin"])
    clear_flags(paths["attest"])

    def flags(*names):
        return [arg for name in names for arg in (f"--{name}", str(paths[name]))]

    def build_and_pin():
        assert _run(["bundle", "build", "--src", str(SRC), *flags("bundle"), "--force"], capsys)[0] == exits.OK
        assert _run(["bundle", "pin", *flags("bundle", "pin"), "--force"], capsys)[0] == exits.OK

    def attest_init():
        assert _run(["attest", "init", *flags("bundle", "pin", "attest")], capsys)[0] == exits.OK

    def certify():
        assert _run(["selftest", "toy-curve", *flags("bundle", "pin", "db")], capsys)[0] == exits.OK

    def m0_run(*extra):
        return _run(["m0-run", *extra, *flags("bundle", "pin", "attest", "db")], capsys)

    return {"paths": paths, "flags": flags, "build_and_pin": build_and_pin, "attest_init": attest_init, "certify": certify, "m0_run": m0_run}


def test_the_operator_sequence_produces_four_nodes_two_negatives_and_one_refusal(deploy, capsys, db_snapshot):
    deploy["build_and_pin"]()
    deploy["attest_init"]()
    deploy["certify"]()
    code, out, err = deploy["m0_run"]("--bits", "40", "--seed", "1", "--json")
    assert code == exits.OK, err
    document = json.loads(out)

    assert [node["label"] for node in document["nodes"]] == ["A", "B", "C", "D"]
    assert [node["kind"] for node in document["nodes"]] == ["m0_generator", "m0_derivation", "verifier_result", "gate_run"]
    assert all(node["cost_tag"] == "tier0" and node["selftest_ref"] for node in document["nodes"])
    assert len({node["hash"] for node in document["nodes"]}) == 4
    assert len(document["negatives"]) == 2
    assert document["refused_submission"]
    assert document["served_from_cache"] is False

    counts = _counts(deploy["paths"]["db"])
    db_snapshot(str(deploy["paths"]["db"]), "m0-slice-green")
    assert counts["attempts"] == 1
    assert counts["nodes_by_kind"]["verifier_result"] == 3
    assert counts["nodes_by_kind"]["m0_generator"] == 1 and counts["nodes_by_kind"]["m0_derivation"] == 1
    assert counts["nodes_by_kind"]["claim_statement"] == 1
    assert counts["verifier_gate_runs"] == [
        ("slice_positive", "pass", []),
        ("negative_coordinate", "fail", ["Q-off-curve"]),
        ("negative_scalar", "fail", ["xP-ne-Q"]),
        ("submitter_named", "refused", ["submitter-named-instance"]),
    ]
    passing = [step for step, result, _ in counts["verifier_gate_runs"] if result == "pass"]
    assert passing == ["slice_positive"]
    assert document["nodes"][2]["hash"] not in document["negatives"]


def test_the_submitter_named_submission_is_refused_with_no_node_and_no_backend_spawn(deploy, capsys):
    deploy["build_and_pin"]()
    deploy["attest_init"]()
    deploy["certify"]()
    code, out, _ = deploy["m0_run"]("--json")
    assert code == exits.OK
    document = json.loads(out)
    conn = sqlite3.connect(f"file:{deploy['paths']['db']}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM gate_runs WHERE run_id = ?", (document["refused_submission"],)).fetchone()
        assert row["result"] == "refused" and json.loads(row["reasons"]) == ["submitter-named-instance"]
        assert conn.execute("SELECT count(*) FROM nodes WHERE kind='verifier_result'").fetchone()[0] == 3
    finally:
        conn.close()


def test_the_same_seed_replays_to_the_same_node_a_from_cache_and_a_different_seed_diverges(deploy, capsys):
    deploy["build_and_pin"]()
    deploy["attest_init"]()
    deploy["certify"]()
    first = json.loads(deploy["m0_run"]("--seed", "1", "--json")[1])
    replay = json.loads(deploy["m0_run"]("--seed", "1", "--json")[1])
    other = json.loads(deploy["m0_run"]("--seed", "2", "--json")[1])
    fresh = json.loads(deploy["m0_run"]("--seed", "1", "--skip-cache-lookup", "--json")[1])

    assert replay["nodes"][0]["hash"] == first["nodes"][0]["hash"]
    assert replay["served_from_cache"] is True and replay["attempt_id"] == first["attempt_id"]
    assert other["nodes"][0]["hash"] != first["nodes"][0]["hash"]
    assert fresh["served_from_cache"] is False and fresh["attempt_id"] != first["attempt_id"]
    assert fresh["nodes"][0]["hash"] == first["nodes"][0]["hash"]

    conn = sqlite3.connect(f"file:{deploy['paths']['db']}?mode=ro", uri=True)
    try:
        assert conn.execute("SELECT count(*) FROM attempts").fetchone()[0] == 3
    finally:
        conn.close()


def test_the_green_run_logs_one_record_per_step_in_order(deploy, capsys, caplog):
    deploy["build_and_pin"]()
    deploy["attest_init"]()
    deploy["certify"]()
    caplog.set_level(logging.INFO, logger=log.LOGGER_NAME)
    assert deploy["m0_run"]("--json")[0] == exits.OK
    steps = [r.fields["step"] for r in caplog.records if r.name == log.LOGGER_NAME and r.getMessage() == "step" and isinstance(r.fields.get("step"), int)]
    assert steps == STEP_SEQUENCE
    named = {r.fields["step"]: r.fields["name"] for r in caplog.records if r.getMessage() == "step" and isinstance(r.fields.get("step"), int)}
    assert named[1] == "gate_plan" and named[6] == "verify" and named[9] == "summary"


def _corrupt_pin(deploy):
    pin = deploy["paths"]["pin"]
    os.chflags(pin, 0)
    os.chmod(pin, 0o644)
    pin.write_text("0" * 64 + "\n")


def _skip_certify(deploy):
    deploy["paths"]["db"] = deploy["paths"]["db"].with_name("uncertified.sqlite")


def _empty_attestation(deploy):
    os.chflags(deploy["paths"]["attest"], 0)
    deploy["paths"]["attest"].write_bytes(b"")


ABORTS = [
    ("pin_mismatch", _corrupt_pin, "differs from the pin"),
    ("uncertified_skill", _skip_certify, "uncertified-revision"),
    ("gate_plan_failure", _empty_attestation, "gate-plan-failed:waiver_cannot_advance"),
]


@pytest.mark.parametrize("name,setup_delta,expected_reason", ABORTS, ids=[a[0] for a in ABORTS])
def test_each_abort_path_exits_gate_refused_before_any_skill_launch(deploy, capsys, name, setup_delta, expected_reason):
    deploy["build_and_pin"]()
    deploy["attest_init"]()
    deploy["certify"]()
    setup_delta(deploy)
    code, out, err = deploy["m0_run"]("--json")
    assert code == exits.GATE_REFUSED, err
    assert expected_reason in err
    assert out == ""
    db = deploy["paths"]["db"]
    if not db.exists():
        return
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        assert conn.execute("SELECT count(*) FROM attempts").fetchone()[0] == 0
    finally:
        conn.close()


def test_a_refusal_names_a_next_command_that_actually_resolves_it(deploy, capsys):
    deploy["build_and_pin"]()
    deploy["attest_init"]()
    deploy["paths"]["db"] = deploy["paths"]["db"].with_name("uncertified.sqlite")
    code, _, err = deploy["m0_run"]()
    assert code == exits.GATE_REFUSED
    suggested = err.strip().split("; run: ")[-1].split()
    assert suggested[:3] == ["cairn", "selftest", "toy-curve"]
    assert str(deploy["paths"]["db"]) in suggested
    assert _run(suggested[1:], capsys)[0] == exits.OK
    assert deploy["m0_run"]()[0] == exits.OK
