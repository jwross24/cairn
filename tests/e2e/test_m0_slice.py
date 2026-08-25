import json
import logging
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import blake3
import pytest

from cairn import cli, exits, log, m0

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "bundle"
STEP_SEQUENCE = [1, 2, 3, 4, 5, 6, 7, 8, 9]
ARM_ORDER = ["slice_positive", "negative_coordinate", "negative_scalar", "submitter_named"]
TRANSCRIPT_EVENTS = ("step", "verifier_arm", "verifier_refused")


def _run(argv, capsys):
    code = cli.main(argv)
    out, err = capsys.readouterr()
    return code, out, err


def _reader(db):
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _curve(db, statement_hash):
    conn = _reader(db)
    try:
        row = conn.execute("SELECT quantities FROM claim_statements WHERE hash = ?", (statement_hash,)).fetchone()
    finally:
        conn.close()
    units = json.loads(row["quantities"])["units"]
    return tuple(units[field] for field in ("p", "a", "b", "n", "Px", "Py"))


def _counts(db):
    conn = _reader(db)
    try:
        tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts = {t: conn.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in tables}
        counts["nodes_by_kind"] = {
            r["kind"]: r["n"] for r in conn.execute("SELECT kind, count(*) n FROM nodes GROUP BY kind")
        }
        counts["verifier_gate_runs"] = [
            (r["plan_step"], r["result"], json.loads(r["reasons"]))
            for r in conn.execute("SELECT * FROM gate_runs WHERE gate='verifier' ORDER BY rowid")
        ]
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

    def ready():
        build_and_pin()
        attest_init()
        certify()

    return {
        "paths": paths,
        "flags": flags,
        "build_and_pin": build_and_pin,
        "attest_init": attest_init,
        "certify": certify,
        "m0_run": m0_run,
        "ready": ready,
    }


def test_the_operator_sequence_produces_four_nodes_two_negatives_and_one_refusal(deploy, capsys, db_snapshot):
    deploy["ready"]()
    code, out, err = deploy["m0_run"]("--bits", "40", "--seed", "1", "--json")
    assert code == exits.OK, err
    document = json.loads(out)

    assert document["schema_version"] == cli.SCHEMA_VERSION and document["command"] == "m0-run"
    assert document["exit_code"] == exits.OK
    assert [node["label"] for node in document["nodes"]] == ["A", "B", "C", "D"]
    assert [node["kind"] for node in document["nodes"]] == [
        "m0_generator",
        "m0_derivation",
        "verifier_result",
        "gate_run",
    ]
    assert [node["replay_grade"] for node in document["nodes"]] == [
        "Replayable",
        "Verifiable",
        "Verifiable",
        "Replayable",
    ]
    assert all(node["cost_tag"] == "tier0" and node["selftest_ref"] for node in document["nodes"])
    assert len({node["hash"] for node in document["nodes"]}) == 4
    assert document["served_from_cache"] is False

    assert [arm["arm"] for arm in document["arms"]] == ARM_ORDER
    assert [arm["accepted"] for arm in document["arms"]] == [True, False, False, False]
    assert [arm["reason"] for arm in document["arms"]] == [None, "Q-off-curve", "xP-ne-Q", "submitter-named-instance"]
    assert [arm["spawned"] for arm in document["arms"]] == [True, True, True, False]
    assert document["arms"][0]["node"] == document["nodes"][2]["hash"]
    assert document["arms"][3]["node"] is None
    assert document["negatives"] == [arm["node"] for arm in document["arms"][1:3]]

    for arm in document["arms"]:
        if arm["node"] is None:
            continue
        rebuilt = m0.canon.encode(
            m0.VERIFIER_RESULT_NODE,
            {
                "instance_hash": arm["instance_hash"],
                "accepted": arm["accepted"],
                "reason": arm["reason"],
                "reasons": arm["reasons"],
                "stdout_digest": arm["stdout_digest"],
                "stderr_digest": arm["stderr_digest"],
                "rc": arm["rc"],
                "arm": arm["arm"],
            },
        )
        assert m0.keys.node_hash(m0.KIND_VERIFIER_RESULT, rebuilt) == arm["node"]

    conn = _reader(deploy["paths"]["db"])
    try:
        persisted = {
            node["hash"]: conn.execute("SELECT replay_grade FROM nodes WHERE hash = ?", (node["hash"],)).fetchone()[0]
            for node in document["nodes"][:3]
        }
    finally:
        conn.close()
    assert [persisted[node["hash"]] for node in document["nodes"][:3]] == ["Replayable", "Verifiable", "Verifiable"]

    counts = _counts(deploy["paths"]["db"])
    db_snapshot(str(deploy["paths"]["db"]), "m0-slice-green")
    assert counts["attempts"] == 1
    assert counts["nodes_by_kind"]["verifier_result"] == 3
    assert counts["nodes_by_kind"]["m0_generator"] == 1 and counts["nodes_by_kind"]["m0_derivation"] == 1
    assert counts["nodes_by_kind"]["claim_statement"] == 1
    assert counts["hypothesis_objects"] >= 1
    assert counts["verifier_gate_runs"] == [
        ("slice_positive", "pass", []),
        ("negative_coordinate", "fail", ["Q-off-curve"]),
        ("negative_scalar", "fail", ["xP-ne-Q"]),
        ("submitter_named", "refused", ["submitter-named-instance"]),
    ]


def test_the_slice_records_its_hypothesis_object_and_the_derivation_lineage(deploy, capsys):
    deploy["ready"]()
    document = json.loads(deploy["m0_run"]("--bits", "40", "--json")[1])
    node_a, node_b = document["nodes"][0]["hash"], document["nodes"][1]["hash"]
    conn = _reader(deploy["paths"]["db"])
    try:
        key = m0.keys.hypothesis_key(m0._hypothesis(40))
        assert conn.execute("SELECT count(*) FROM hypothesis_objects WHERE hash = ?", (key,)).fetchone()[0] == 1
        edges = [
            (r["parent_hash"], r["edge_kind"])
            for r in conn.execute("SELECT * FROM lineage WHERE child_hash = ?", (node_b,))
        ]
        assert (node_a, "derives") in edges
    finally:
        conn.close()


def test_the_derivation_commits_to_the_x_the_generator_output_determines(deploy, capsys):
    deploy["ready"]()
    document = json.loads(deploy["m0_run"]("--bits", "40", "--seed", "1", "--json")[1])
    conn = _reader(deploy["paths"]["db"])
    try:
        row = conn.execute(
            "SELECT quantities FROM claim_statements WHERE hash = ?", (document["statement_hash"],)
        ).fetchone()
    finally:
        conn.close()
    units = json.loads(row["quantities"])["units"]
    node_a = document["nodes"][0]["hash"]
    x = m0._draw(bytes.fromhex(node_a), int(units["n"]) - 1, m0.DERIVE_LABEL)
    rebuilt = m0.canon.encode(
        m0.DERIVATION_NODE,
        {
            "instance_hash": document["instance_hash"],
            "x_commit": blake3.blake3(str(x).encode()).hexdigest(),
            "Q": [units["Qx"], units["Qy"]],
            "source_node": node_a,
        },
    )
    assert m0.keys.node_hash(m0.KIND_DERIVATION, rebuilt) == document["nodes"][1]["hash"]


def test_the_same_seed_replays_from_cache_and_a_different_seed_derives_a_different_instance(deploy, capsys):
    deploy["ready"]()
    first = json.loads(deploy["m0_run"]("--seed", "1", "--json")[1])
    replay = json.loads(deploy["m0_run"]("--seed", "1", "--json")[1])
    other = json.loads(deploy["m0_run"]("--seed", "2", "--json")[1])
    fresh = json.loads(deploy["m0_run"]("--seed", "1", "--skip-cache-lookup", "--json")[1])

    assert replay["nodes"][0]["hash"] == first["nodes"][0]["hash"]
    assert replay["served_from_cache"] is True and replay["attempt_id"] == first["attempt_id"]
    assert replay["instance_hash"] == first["instance_hash"]
    assert replay["nodes"][1]["hash"] == first["nodes"][1]["hash"]

    assert other["nodes"][0]["hash"] != first["nodes"][0]["hash"]
    assert other["instance_hash"] != first["instance_hash"]
    assert other["statement_hash"] != first["statement_hash"]
    assert _curve(deploy["paths"]["db"], other["statement_hash"]) != _curve(
        deploy["paths"]["db"], first["statement_hash"]
    )

    assert fresh["served_from_cache"] is False and fresh["attempt_id"] != first["attempt_id"]
    assert fresh["nodes"][0]["hash"] == first["nodes"][0]["hash"]
    assert fresh["instance_hash"] == first["instance_hash"]

    conn = _reader(deploy["paths"]["db"])
    try:
        assert conn.execute("SELECT count(*) FROM attempts").fetchone()[0] == 3
    finally:
        conn.close()


def test_the_human_rendering_names_every_node_negative_and_refusal(deploy, capsys):
    deploy["ready"]()
    code, out, err = deploy["m0_run"]("--bits", "40", "--seed", "1")
    assert code == exits.OK, err
    lines = out.strip().splitlines()
    assert len(lines) == 7
    assert [line.split()[0] for line in lines[:4]] == ["A", "B", "C", "D"]
    assert [line.split()[1] for line in lines[:4]] == ["m0_generator", "m0_derivation", "verifier_result", "gate_run"]
    assert lines[4].startswith("- FAIL Q-off-curve negative_coordinate ")
    assert lines[5].startswith("- FAIL xP-ne-Q negative_scalar ")
    assert lines[6].startswith("- refused submitter_named ")


def test_the_green_run_logs_one_record_per_step_in_order(deploy, capsys, caplog):
    deploy["ready"]()
    caplog.set_level(logging.INFO, logger=log.LOGGER_NAME)
    assert deploy["m0_run"]("--json")[0] == exits.OK
    records = [
        r
        for r in caplog.records
        if r.name == log.LOGGER_NAME and r.getMessage() == "step" and isinstance(r.fields.get("step"), int)
    ]
    assert [r.fields["step"] for r in records] == STEP_SEQUENCE
    named = {r.fields["step"]: r.fields["name"] for r in records}
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
    ("pin_mismatch", _corrupt_pin, "differs from the pin", 0),
    ("uncertified_skill", _skip_certify, "uncertified-revision", 7),
    ("gate_plan_failure", _empty_attestation, "gate-plan-failed:waiver_cannot_advance", 7),
]


@pytest.mark.parametrize(
    ("name", "setup_delta", "expected_reason", "gate_plan_rows"), ABORTS, ids=[a[0] for a in ABORTS]
)
def test_each_abort_path_exits_gate_refused_before_any_skill_launch(
    deploy, capsys, name, setup_delta, expected_reason, gate_plan_rows
):
    deploy["ready"]()
    setup_delta(deploy)
    code, out, err = deploy["m0_run"]("--json")
    assert code == exits.GATE_REFUSED, err
    assert expected_reason in err
    assert out == ""
    db = deploy["paths"]["db"]
    assert db.exists()
    conn = _reader(db)
    try:
        assert conn.execute("SELECT count(*) FROM attempts").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM gate_runs WHERE gate='gate_plan'").fetchone()[0] == gate_plan_rows
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


def test_a_missing_attestation_file_exits_environment(deploy, capsys):
    deploy["ready"]()
    deploy["paths"]["attest"] = deploy["paths"]["attest"].with_name("absent.log")
    code, out, err = deploy["m0_run"]()
    assert code == exits.ENVIRONMENT
    assert "attestation file" in err and "cairn attest init" in err
    assert out == ""


def test_the_module_entry_point_runs_the_slice_with_globals_before_the_subcommand(deploy):
    deploy["ready"]()
    paths = deploy["paths"]
    argv = [
        sys.executable,
        "-m",
        "cairn",
        "--db",
        str(paths["db"]),
        "--bundle",
        str(paths["bundle"]),
        "--pin",
        str(paths["pin"]),
        "--attest",
        str(paths["attest"]),
        "m0-run",
        "--bits",
        "40",
        "--seed",
        "1",
        "--json",
    ]
    proc = subprocess.run(argv, cwd=str(ROOT), capture_output=True, text=True, timeout=600)
    assert proc.returncode == exits.OK, proc.stderr
    document = json.loads(proc.stdout)
    assert proc.stdout.count("\n") == 1
    assert document["command"] == "m0-run" and document["exit_code"] == exits.OK
    assert [arm["accepted"] for arm in document["arms"]] == [True, False, False, False]
    assert proc.stderr and all(line.startswith("{") for line in proc.stderr.strip().splitlines())


def _transcript(records):
    lines = []
    for record in records:
        event = record.getMessage()
        if event not in TRANSCRIPT_EVENTS or record.name != log.LOGGER_NAME:
            continue
        fields = record.fields
        if event == "step" and "name" not in fields:
            lines.append(
                f"gate_step {fields['step']} expected={fields['expected']} observed={fields['observed']} result={fields['result']} reasons={fields['reasons']} run={fields['run_id']} wall_ms={fields['wall_ms']}"
            )
        elif event == "step":
            lines.append(f"step {fields['step']} {fields['name']}")
        elif event == "verifier_arm":
            lines.append(
                f"verifier_arm {fields['arm']} accepted={fields['accepted']} reason={fields['reason']} gate_result={fields['gate_result']} node={fields['node']} gate_run={fields['gate_run']}"
            )
        else:
            lines.append(
                f"verifier_refused {fields['arm']} reasons={fields['reasons']} spawned={fields['spawned']} gate_run={fields['gate_run']}"
            )
    return "\n".join(lines) + "\n"


def test_the_step_transcript_matches_its_golden_after_scrubbing(deploy, capsys, caplog, assert_golden, scrub):
    deploy["ready"]()
    caplog.set_level(logging.INFO, logger=log.LOGGER_NAME)
    code, out, err = deploy["m0_run"]("--bits", "40", "--seed", "1", "--json")
    assert code == exits.OK, err
    document = json.loads(out)
    raw = _transcript(caplog.records)
    assert document["nodes"][2]["hash"] in raw and raw.count("wall_ms=") == 7
    transcript = scrub(raw, bundle_hash=document["bundle_hash"])
    assert transcript.count("[HASH]") >= 10 and transcript.count("[MS]") == 7
    assert not any(token in transcript for token in (document["nodes"][2]["hash"], document["bundle_hash"]))
    assert_golden("m0_run_transcript", transcript)
