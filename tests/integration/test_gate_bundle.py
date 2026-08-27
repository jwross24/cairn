import json
import os
import shutil
import sqlite3
import stat
import sys
from pathlib import Path

import blake3
import pytest

from cairn import attest, bundle, claims, cli, exits, substrate, verifier

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="uappnd is a macOS/BSD chflags bit; the Linux chattr +a boundary belongs to the M1 container bead",
)

SRC = bundle.REPO_ROOT / "bundle"
EXPECTED_ACCEPT = {"rc": 0, "stdout": "OK", "stderr_empty": True}


def _run(argv, capsys):
    code = cli.main(argv)
    out, err = capsys.readouterr()
    return code, out, err


def _paths(bundle_path, pin_path):
    return ["--bundle", str(bundle_path), "--pin", str(pin_path)]


def _writable_copy(bundle_path, destination):
    shutil.copy(bundle_path, destination)
    destination.chmod(0o644)
    return destination


def _edit_one_row(path, kind="tiers"):
    conn = sqlite3.connect(str(path))
    conn.execute("UPDATE objects SET canonical = ? WHERE kind = ?", (b"tampered", kind))
    conn.commit()
    conn.close()


def test_build_is_deterministic_and_pin_opens(pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    first = bundle.bundle_hash(bundle.read_rows(bundle_path))
    second = bundle.build(SRC, bundle_path)
    assert first == second
    gate = bundle.GateBundle.open(bundle_path, pin_path)
    assert gate.hash == gate.pin_hash == first
    assert stat.S_IMODE(bundle_path.stat().st_mode) == 0o444
    assert stat.S_IMODE(pin_path.stat().st_mode) == 0o444
    assert pin_path.stat().st_flags & stat.UF_APPEND


def test_bundle_hash_golden(tmp_path, assert_golden, clear_flags):
    first = bundle.build(SRC, tmp_path / "a.sqlite")
    second = bundle.build(SRC, tmp_path / "b.sqlite")
    assert first == second
    assert_golden("gate_bundle_hash", first + "\n")


def test_bundle_carries_the_verifier_accept_predicate_and_the_script_it_pins(pinned_bundle):
    gate = bundle.GateBundle.open(*pinned_bundle())
    assert gate.object("verifier")["accept"] == EXPECTED_ACCEPT
    assert gate.digest_of(bundle.SCRIPT_KIND) == blake3.blake3(verifier.SCRIPT_PATH.read_bytes()).hexdigest()
    assert gate.verifier_script == verifier.script_bytes()
    config = gate.verifier_config()
    assert config.accept.as_dict() == EXPECTED_ACCEPT
    assert config.bundle_hash == gate.hash


def test_show_reports_pin_match_and_exits_zero(pinned_bundle, capsys):
    bundle_path, pin_path = pinned_bundle()
    code, out, err = _run(["bundle", "show", *_paths(bundle_path, pin_path), "--json"], capsys)
    document = json.loads(out)
    assert code == exits.OK
    assert document["pin_match"] is True
    assert document["bundle_hash"] == document["pin_hash"]
    assert {row["kind"] for row in document["objects"]} >= {"tiers", "verifier", bundle.SCRIPT_KIND, "gate_plan"}


def test_show_exits_gate_refused_after_a_bundle_edit(pinned_bundle, tmp_path, capsys):
    bundle_path, pin_path = pinned_bundle()
    tampered = _writable_copy(bundle_path, tmp_path / "tampered.sqlite")
    _edit_one_row(tampered)
    code, out, err = _run(["bundle", "show", *_paths(tampered, pin_path), "--json"], capsys)
    assert code == exits.GATE_REFUSED
    assert json.loads(out)["pin_match"] is False
    assert "chflags nouappnd" in err


def test_show_exits_environment_when_an_artifact_is_missing(tmp_path, capsys):
    code, out, err = _run(
        ["bundle", "show", "--bundle", str(tmp_path / "absent.sqlite"), "--pin", str(tmp_path / "absent.pin")], capsys
    )
    assert code == exits.ENVIRONMENT
    assert out == "" and "absent.sqlite" in err


def test_edited_bundle_fails_closed_and_records_why(pinned_bundle, tmp_path, capsys):
    bundle_path, pin_path = pinned_bundle()
    tampered = _writable_copy(bundle_path, tmp_path / "tampered.sqlite")
    _edit_one_row(tampered)
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        with pytest.raises(bundle.BundlePinMismatch, match="does not match the pin"):
            bundle.open_for_gate(sub, tampered, pin_path)
        rows = [dict(r) for r in sub.conn.execute("SELECT * FROM gate_runs WHERE gate = 'bundle_open'")]
    assert len(rows) == 1
    assert rows[0]["result"] == "refused"
    assert json.loads(rows[0]["reasons"]) == [bundle.PIN_MISMATCH_REASON]
    assert rows[0]["bundle_hash"] != rows[0]["pin_hash"]


@pytest.mark.parametrize(
    ("sub_argv", "target"),
    [(("build", "--src", str(SRC)), "bundle"), (("pin",), "pin")],
    ids=["build-over-bundle", "pin-over-pin"],
)
def test_dangerous_subcommands_refuse_to_overwrite_without_force(pinned_bundle, capsys, sub_argv, target):
    bundle_path, pin_path = pinned_bundle()
    victim = bundle_path if target == "bundle" else pin_path
    before = victim.read_bytes()
    code, out, err = _run(["bundle", *sub_argv, *_paths(bundle_path, pin_path)], capsys)
    assert code == exits.GATE_REFUSED
    assert "--force" in err and out == ""
    assert victim.read_bytes() == before


def test_pin_with_force_meets_the_os_refusal_and_names_the_repin_sequence(pinned_bundle, capsys):
    bundle_path, pin_path = pinned_bundle()
    before = pin_path.read_bytes()
    code, out, err = _run(["bundle", "pin", *_paths(bundle_path, pin_path), "--force"], capsys)
    assert code == exits.ENVIRONMENT
    assert f"chflags nouappnd {pin_path}" in err
    assert pin_path.read_bytes() == before
    assert pin_path.stat().st_flags & stat.UF_APPEND


def test_build_with_force_rewrites_the_read_only_bundle(pinned_bundle, capsys):
    bundle_path, pin_path = pinned_bundle()
    before = bundle.bundle_hash(bundle.read_rows(bundle_path))
    code, out, err = _run(["bundle", "build", "--src", str(SRC), *_paths(bundle_path, pin_path), "--force"], capsys)
    assert code == exits.OK
    assert out.strip() == before
    assert stat.S_IMODE(bundle_path.stat().st_mode) == 0o444


def test_attest_init_writes_the_fixture_waiver_at_record_zero(pinned_bundle, tmp_path, clear_flags, capsys):
    bundle_path, pin_path = pinned_bundle()
    log_path = tmp_path / "attestations.log"
    clear_flags(log_path)
    code, out, err = _run(
        ["attest", "init", *_paths(bundle_path, pin_path), "--attest", str(log_path), "--json"], capsys
    )
    document = json.loads(out)
    gate = bundle.GateBundle.open(bundle_path, pin_path)
    assert code == exits.OK
    assert document["offset"] == 0
    assert document["target"] == gate.waiver_target()
    assert attest.attestation_record_matches(log_path, 0, document["record_digest"])
    assert stat.S_IMODE(log_path.stat().st_mode) == 0o644
    assert log_path.stat().st_flags & stat.UF_APPEND
    offsets = [offset for offset, _ in attest.records(log_path)]
    assert offsets == [0]


def test_attest_init_over_an_existing_file_is_refused(pinned_bundle, tmp_path, clear_flags, capsys):
    bundle_path, pin_path = pinned_bundle()
    log_path = tmp_path / "attestations.log"
    clear_flags(log_path)
    _run(["attest", "init", *_paths(bundle_path, pin_path), "--attest", str(log_path)], capsys)
    before = log_path.read_bytes()
    code, out, err = _run(["attest", "init", *_paths(bundle_path, pin_path), "--attest", str(log_path)], capsys)
    assert code == exits.GATE_REFUSED
    assert "cairn attest append" in err and out == ""
    assert log_path.read_bytes() == before


def test_attest_init_fails_closed_on_a_pin_mismatch(pinned_bundle, tmp_path, capsys):
    bundle_path, pin_path = pinned_bundle()
    tampered = _writable_copy(bundle_path, tmp_path / "tampered.sqlite")
    _edit_one_row(tampered)
    log_path = tmp_path / "attestations.log"
    code, out, err = _run(
        ["attest", "init", "--bundle", str(tampered), "--pin", str(pin_path), "--attest", str(log_path)], capsys
    )
    assert code == exits.GATE_REFUSED
    assert not log_path.exists()
    assert "chflags nouappnd" in err


PIN_OPS = ("open_w", "open_a", "chmod", "unlink", "rename")
ATTEST_OPS = ("open_w", "truncate", "unlink", "rename")


def _apply(op, path):
    if op == "open_w":
        Path(path).open("w").close()
    elif op == "open_a":
        with Path(path).open("a") as fh:
            fh.write("x")
    elif op == "truncate":
        os.truncate(path, 0)
    elif op == "chmod":
        Path(path).chmod(0o644)
    elif op == "unlink":
        Path(path).unlink()
    elif op == "rename":
        Path(path).rename(str(path) + ".moved")
    else:
        raise AssertionError(f"unknown op {op}")


@pytest.mark.parametrize(
    ("role", "op", "refused"),
    [("pin", op, True) for op in PIN_OPS] + [("attest", op, True) for op in ATTEST_OPS] + [("attest", "open_a", False)],
    ids=[f"pin-{op}-PermissionError" for op in PIN_OPS]
    + [f"attest-{op}-PermissionError" for op in ATTEST_OPS]
    + ["attest-open_a-OK"],
)
def test_os_write_boundary_on_the_deployed_artifacts(pinned_bundle, tmp_path, clear_flags, capsys, role, op, refused):
    bundle_path, pin_path = pinned_bundle()
    log_path = tmp_path / "attestations.log"
    clear_flags(log_path)
    _run(["attest", "init", *_paths(bundle_path, pin_path), "--attest", str(log_path)], capsys)
    path = pin_path if role == "pin" else log_path
    before = path.read_bytes()
    if refused:
        with pytest.raises(PermissionError):
            _apply(op, path)
        assert path.exists() and path.read_bytes() == before
        assert not os.path.lexists(str(path) + ".moved")
    else:
        _apply(op, path)
        assert path.read_bytes() == before + b"x"


def test_mirrored_review_verdict_is_visible_only_on_an_exact_digest_and_offset(
    pinned_bundle, tmp_path, clear_flags, capsys
):
    bundle_path, pin_path = pinned_bundle()
    log_path = tmp_path / "attestations.log"
    db_path = tmp_path / "substrate.sqlite"
    clear_flags(log_path)
    _run(["attest", "init", *_paths(bundle_path, pin_path), "--attest", str(log_path)], capsys)
    statement_hash = "a" * 64
    record = tmp_path / "verdict.json"
    record.write_text(
        json.dumps(
            {
                "statement_hash": statement_hash,
                "reviewer": "operator",
                "verdict": "approve",
                "checklist_template_hash": "b" * 64,
                "at": "2026-08-23T00:00:00Z",
            }
        )
    )
    code, out, err = _run(
        [
            "attest",
            "append",
            "--kind",
            "review_verdict",
            "--record",
            str(record),
            *_paths(bundle_path, pin_path),
            "--attest",
            str(log_path),
            "--db",
            str(db_path),
            "--json",
        ],
        capsys,
    )
    assert code == exits.OK
    offset = json.loads(out)["offset"]
    assert offset > 0
    with substrate.Substrate.open(db_path, role="reader") as sub:
        visible = attest.visible_review_verdicts(sub, statement_hash, log_path)
        assert [row["file_offset"] for row in visible] == [offset]
    forged = claims.ReviewVerdict(
        statement_hash=statement_hash,
        reviewer="forger",
        verdict="approve",
        checklist_template_hash="c" * 64,
        gate_bundle_hash="d" * 64,
        at="2026-08-23T00:00:00Z",
        file_offset=offset,
    )
    with substrate.Substrate.open(db_path) as sub:
        claims.write_review_verdict(sub, forged)
        stored = claims.review_verdicts_for(sub, statement_hash)
        visible = attest.visible_review_verdicts(sub, statement_hash, log_path)
    assert len(stored) == 2
    assert [row["reviewer"] for row in visible] == ["operator"]


def test_appended_waiver_mirrors_no_substrate_row(pinned_bundle, tmp_path, clear_flags, capsys):
    bundle_path, pin_path = pinned_bundle()
    log_path = tmp_path / "attestations.log"
    db_path = tmp_path / "substrate.sqlite"
    clear_flags(log_path)
    _run(["attest", "init", *_paths(bundle_path, pin_path), "--attest", str(log_path)], capsys)
    record = tmp_path / "waiver.json"
    record.write_text(
        json.dumps(
            {
                "target_kind": "hypothesis_key",
                "target": "e" * 64,
                "check": "tier_gate",
                "reason": "operator waiver",
                "issued_by": "operator",
                "expires_at": "2027-01-01T00:00:00Z",
            }
        )
    )
    code, out, err = _run(
        [
            "attest",
            "append",
            "--kind",
            "waiver",
            "--record",
            str(record),
            *_paths(bundle_path, pin_path),
            "--attest",
            str(log_path),
            "--db",
            str(db_path),
            "--json",
        ],
        capsys,
    )
    assert code == exits.OK
    assert json.loads(out)["row_id"] is None
    assert len(list(attest.records(log_path))) == 2
    assert not db_path.exists()


def test_no_admission_check_is_waivable(pinned_bundle):
    gate = bundle.GateBundle.open(*pinned_bundle())
    assert gate.waivable_checks == []


def test_pin_through_the_cli_writes_the_hash_and_the_operator_owned_modes(tmp_path, clear_flags, capsys):
    bundle_path, pin_path = tmp_path / "gate-bundle.sqlite", tmp_path / "gate-bundle.pin"
    clear_flags(pin_path)
    build_code, build_out, _ = _run(["bundle", "build", "--src", str(SRC), *_paths(bundle_path, pin_path)], capsys)
    assert build_code == exits.OK
    digest = build_out.strip()

    code, out, err = _run(["bundle", "pin", *_paths(bundle_path, pin_path)], capsys)
    assert code == exits.OK
    assert out.strip() == digest
    assert pin_path.read_text().strip() == digest
    assert stat.S_IMODE(pin_path.stat().st_mode) == 0o444
    assert stat.S_IMODE(bundle_path.stat().st_mode) == 0o444
    assert pin_path.stat().st_flags & stat.UF_APPEND
    assert bundle.GateBundle.open(bundle_path, pin_path).hash == digest


def test_show_without_json_prints_the_same_facts_as_the_document(pinned_bundle, capsys):
    bundle_path, pin_path = pinned_bundle()
    _, document, _ = _run(["bundle", "show", *_paths(bundle_path, pin_path), "--json"], capsys)
    payload = json.loads(document)
    code, out, err = _run(["bundle", "show", *_paths(bundle_path, pin_path)], capsys)
    assert code == exits.OK
    assert f"bundle_hash {payload['bundle_hash']}" in out
    assert f"pin_hash    {payload['pin_hash']}" in out
    assert "pin_match   true" in out
    for row in payload["objects"]:
        assert row["hash"] in out and row["kind"] in out


@pytest.mark.parametrize(
    ("src", "why"),
    [("absent", "does not exist"), ("empty", "holds no")],
    ids=["missing-directory", "no-json-object"],
)
def test_build_from_an_unusable_source_directory_exits_environment(tmp_path, capsys, src, why):
    source = tmp_path / src
    if src == "empty":
        source.mkdir()
    bundle_path = tmp_path / "gate-bundle.sqlite"
    code, out, err = _run(
        ["bundle", "build", "--src", str(source), "--bundle", str(bundle_path), "--pin", str(tmp_path / "p")], capsys
    )
    assert code == exits.ENVIRONMENT
    assert why in err and out == ""
    assert not bundle_path.exists()


def test_pin_without_a_bundle_exits_environment_and_names_build(tmp_path, capsys):
    pin_path = tmp_path / "gate-bundle.pin"
    code, out, err = _run(
        ["bundle", "pin", "--bundle", str(tmp_path / "absent.sqlite"), "--pin", str(pin_path)], capsys
    )
    assert code == exits.ENVIRONMENT
    assert "cairn bundle build" in err and out == ""
    assert not pin_path.exists()


def test_append_without_an_initialized_attestation_file_exits_environment_and_names_init(
    pinned_bundle, tmp_path, capsys
):
    bundle_path, pin_path = pinned_bundle()
    log_path = tmp_path / "attestations.log"
    record = tmp_path / "waiver.json"
    record.write_text(
        json.dumps(
            {
                "target_kind": "hypothesis_key",
                "target": "e" * 64,
                "check": "tier_gate",
                "reason": "r",
                "issued_by": "operator",
                "expires_at": "2027-01-01T00:00:00Z",
            }
        )
    )
    code, out, err = _run(
        [
            "attest",
            "append",
            "--kind",
            "waiver",
            "--record",
            str(record),
            *_paths(bundle_path, pin_path),
            "--attest",
            str(log_path),
        ],
        capsys,
    )
    assert code == exits.ENVIRONMENT
    assert "cairn attest init" in err and out == ""
    assert not log_path.exists()


def test_build_and_pin_emit_one_json_document_carrying_the_same_hash(tmp_path, clear_flags, capsys):
    bundle_path, pin_path = tmp_path / "gate-bundle.sqlite", tmp_path / "gate-bundle.pin"
    clear_flags(pin_path)
    code, out, err = _run(["bundle", "build", "--src", str(SRC), *_paths(bundle_path, pin_path), "--json"], capsys)
    built = json.loads(out)
    assert code == exits.OK and built["sub"] == "build" and out.count("\n") == 1
    code, out, err = _run(["bundle", "pin", *_paths(bundle_path, pin_path), "--json"], capsys)
    pinned = json.loads(out)
    assert code == exits.OK and pinned["sub"] == "pin" and out.count("\n") == 1
    assert built["bundle_hash"] == pinned["bundle_hash"] == pin_path.read_text().strip()


@pytest.mark.parametrize("missing", ["bundle", "pin"], ids=["no-bundle", "no-pin"])
def test_attest_init_without_the_gate_artifacts_exits_environment(pinned_bundle, tmp_path, capsys, missing):
    bundle_path, pin_path = pinned_bundle()
    paths = {"bundle": bundle_path, "pin": pin_path, missing: tmp_path / f"absent-{missing}"}
    log_path = tmp_path / "attestations.log"
    code, out, err = _run(["attest", "init", *_paths(paths["bundle"], paths["pin"]), "--attest", str(log_path)], capsys)
    assert code == exits.ENVIRONMENT
    assert f"absent-{missing}" in err and out == ""
    assert not log_path.exists()
