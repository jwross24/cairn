from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import beads_doctor_gate as gate

REPO_ROOT = Path(__file__).resolve().parents[2]


def report(checks, health="healthy", anomalies=(), audit_health=None, ok=True):
    return {
        "ok": ok,
        "workspace_health": health,
        "reliability_audit": {
            "source": "doctor.inspect",
            "health": health if audit_health is None else audit_health,
            "anomaly_count": len(anomalies),
            "anomalies": list(anomalies),
        },
        "checks": list(checks),
    }


def ok_check(name):
    return {"name": name, "status": "ok", "details": {"finding_id": f"fm-{name}"}}


DEAD_EDGES = {
    "name": "dep.dead_closed_blocking_edges",
    "status": "warn",
    "message": "5 open issue(s) have dead blocking edges (blocker closed or missing): cairn-c8o, cairn-hcl",
    "details": {"remediation": "Remove or update the stale `blocks`/dependency edges (e.g. `br dep remove`)."},
}

DEAD_EDGES_DESCRIBED = (
    "dep.dead_closed_blocking_edges [warn]: "
    "5 open issue(s) have dead blocking edges (blocker closed or missing): cairn-c8o, cairn-hcl"
)

UNBLOCKED = {
    "name": "dep.fully_unblocked_open",
    "status": "warn",
    "message": "4 open issue(s) are fully unblocked (all blockers closed) but may not be surfaced as ready",
    "details": {"remediation": "These issues are ready to work — run `br ready` to confirm."},
}

MALFORMED = {
    "name": "sqlite.integrity_check",
    "status": "error",
    "message": "database disk image is malformed: table `issues` root: page 3 header invalid",
    "details": {"finding_id": "fm-state_files-sqlite-page-malformed"},
}

MALFORMED_DESCRIBED = (
    "sqlite.integrity_check [error]: database disk image is malformed: table `issues` root: page 3 header invalid"
)

# Benign status, a name INTEGRITY_NAME_RE does not match: the only branch left
# that can block this is the message.
QUIET_NAME_CORRUPT_MESSAGE = {
    "name": "audit.suspect_close_reasons",
    "status": "warn",
    "message": "Failed to query closed beads: database disk image is malformed: failed to parse B-tree page 3",
}


def test_all_ok_is_clear():
    verdict = gate.classify(report([ok_check("jsonl.parse"), ok_check("schema.tables")]))
    assert verdict.outcome == "clear"
    assert verdict.blocking == []
    assert verdict.exit_code == 0


def test_the_two_dependency_warns_are_advisory():
    verdict = gate.classify(report([ok_check("jsonl.parse"), DEAD_EDGES, UNBLOCKED]))
    assert verdict.outcome == "advisory"
    assert verdict.blocking == []
    assert verdict.exit_code == 0
    assert len(verdict.advisory) == 2
    assert any("dep.dead_closed_blocking_edges [warn]" in line for line in verdict.advisory)
    assert any("br dep remove" in line for line in verdict.advisory)


def test_a_malformed_page_blocks_on_two_separable_causes():
    verdict = gate.classify(report([ok_check("jsonl.parse"), MALFORMED], health="recoverable"))
    assert verdict.outcome == "blocked"
    assert verdict.exit_code == 2
    assert verdict.blocking == [
        "workspace_health is 'recoverable', which is not a label this gate has cleared",
        f"unrecognized status — {MALFORMED_DESCRIBED}",
    ]


def test_a_non_benign_status_blocks_ahead_of_the_integrity_name_branch():
    verdict = gate.classify(report([ok_check("jsonl.parse"), MALFORMED], health="healthy"))
    assert verdict.outcome == "blocked"
    assert verdict.blocking == [f"unrecognized status — {MALFORMED_DESCRIBED}"]


def test_a_corrupt_message_is_the_sole_blocker_when_status_and_name_are_benign():
    verdict = gate.classify(report([QUIET_NAME_CORRUPT_MESSAGE], health="healthy"))
    assert verdict.outcome == "blocked"
    assert verdict.blocking == [
        "corruption named in the message — audit.suspect_close_reasons [warn]: "
        "Failed to query closed beads: database disk image is malformed: failed to parse B-tree page 3"
    ]


def test_the_ok_flag_is_not_a_signal_the_gate_reads():
    verdict = gate.classify(report([QUIET_NAME_CORRUPT_MESSAGE], health="healthy", ok=True))
    assert verdict.outcome == "blocked"


def test_the_reliability_audit_health_label_is_not_the_one_the_gate_reads():
    verdict = gate.classify(report([ok_check("jsonl.parse")], health="healthy", audit_health="recoverable"))
    assert verdict.outcome == "clear"


def test_an_unrecognized_status_blocks():
    unknown = {"name": "some.future.check", "status": "degraded", "message": "a state this gate has not seen"}
    verdict = gate.classify(report([ok_check("jsonl.parse"), unknown]))
    assert verdict.outcome == "blocked"
    assert verdict.exit_code == 2
    assert any("unrecognized status — some.future.check [degraded]" in line for line in verdict.blocking)


@pytest.mark.parametrize(
    ("status", "rendered"),
    [
        ("fail", "x.y [fail]"),
        ("error", "x.y [error]"),
        ("critical", "x.y [critical]"),
        ("FAIL", "x.y [FAIL]"),
        ("", "x.y []"),
        ("unknown", "x.y [unknown]"),
        (None, "x.y [None]"),
    ],
)
def test_every_status_outside_ok_and_warn_blocks(status, rendered):
    verdict = gate.classify(report([{"name": "x.y", "status": status, "message": "m"}]))
    assert verdict.outcome == "blocked"
    assert verdict.blocking == [f"unrecognized status — {rendered}: m"]


def test_a_non_object_check_entry_blocks():
    verdict = gate.classify(report(["sqlite.integrity_check: ok"]))
    assert verdict.outcome == "blocked"
    assert verdict.blocking == ["a check entry is str, not an object"]


def test_a_non_object_reliability_anomaly_blocks():
    verdict = gate.classify(report([ok_check("jsonl.parse")], anomalies=["database_corrupt"]))
    assert verdict.outcome == "blocked"
    assert verdict.blocking == ["a reliability anomaly is str, not an object"]


def test_a_warn_naming_corruption_blocks():
    verdict = gate.classify(report([QUIET_NAME_CORRUPT_MESSAGE]))
    assert verdict.outcome == "blocked"
    assert any("corruption named in the message" in line for line in verdict.blocking)


def test_a_warn_on_an_integrity_check_blocks_whatever_the_message_says():
    quiet = {"name": "sqlite3.integrity_check", "status": "warn", "message": "nothing alarming here"}
    verdict = gate.classify(report([quiet]))
    assert verdict.outcome == "blocked"
    assert verdict.blocking == ["integrity check not ok — sqlite3.integrity_check [warn]: nothing alarming here"]


def test_a_recoverable_health_label_blocks_on_its_own():
    verdict = gate.classify(report([ok_check("jsonl.parse")], health="recoverable"))
    assert verdict.outcome == "blocked"
    assert verdict.blocking == ["workspace_health is 'recoverable', which is not a label this gate has cleared"]


def test_a_degraded_health_label_with_only_dep_warns_stays_advisory():
    verdict = gate.classify(report([DEAD_EDGES], health="degraded"))
    assert verdict.outcome == "advisory"


def test_a_missing_health_label_blocks():
    body = report([ok_check("jsonl.parse")])
    del body["workspace_health"]
    verdict = gate.classify(body)
    assert verdict.outcome == "blocked"
    assert any("workspace_health is None" in line for line in verdict.blocking)


def test_any_reliability_anomaly_blocks():
    anomaly = {
        "code": "database_corrupt",
        "severity": "recoverable",
        "message": "database corrupt: database disk image is malformed",
    }
    verdict = gate.classify(report([ok_check("jsonl.parse")], anomalies=[anomaly]))
    assert verdict.outcome == "blocked"
    assert any("reliability anomaly database_corrupt [recoverable]" in line for line in verdict.blocking)


def test_a_report_with_no_checks_array_blocks():
    verdict = gate.classify({"ok": True, "workspace_health": "healthy"})
    assert verdict.outcome == "blocked"
    assert any("carries no `checks` array" in line for line in verdict.blocking)


def test_a_doctor_error_envelope_blocks():
    envelope = {"error": {"code": "CONFIG_ERROR", "message": "Refusing configured database route"}}
    verdict = gate.classify(envelope)
    assert verdict.outcome == "blocked"
    assert any("doctor refused to inspect the store" in line for line in verdict.blocking)


def test_a_non_object_report_blocks():
    assert gate.classify([1, 2, 3]).outcome == "blocked"


def test_an_explicit_db_path_wins_over_the_glob(tmp_path):
    beads = tmp_path / ".beads"
    beads.mkdir()
    (beads / "beads.db").touch()
    assert gate.resolve_db(tmp_path, "/elsewhere/chosen.db") == Path("/elsewhere/chosen.db")


def test_the_glob_takes_the_sorted_first_database(tmp_path):
    beads = tmp_path / ".beads"
    beads.mkdir()
    (beads / "zeta.db").touch()
    (beads / "alpha.db").touch()
    assert gate.resolve_db(tmp_path, None) == beads / "alpha.db"


def test_an_empty_beads_directory_resolves_to_no_database(tmp_path):
    (tmp_path / ".beads").mkdir()
    assert gate.resolve_db(tmp_path, None) is None


def test_a_missing_beads_directory_resolves_to_no_database(tmp_path):
    assert gate.resolve_db(tmp_path, None) is None


def test_the_live_branch_denies_when_br_is_not_on_path(tmp_path, monkeypatch):
    monkeypatch.setattr(gate.shutil, "which", lambda _: None)
    log = tmp_path / "check.log"
    rc = gate.main(["--root", str(tmp_path), "--log", str(log)])
    assert rc == 3
    assert "DOCTOR-INFRA beads-doctor-gate: br not on PATH" in log.read_text()


def test_the_live_branch_denies_when_no_database_is_present(tmp_path, monkeypatch):
    monkeypatch.setattr(gate.shutil, "which", lambda _: "/usr/local/bin/br")
    log = tmp_path / "check.log"
    rc = gate.main(["--root", str(tmp_path), "--log", str(log)])
    assert rc == 3
    assert "DOCTOR-INFRA beads-doctor-gate: no database at None" in log.read_text()


def test_the_live_branch_denies_when_doctor_output_does_not_parse(tmp_path, monkeypatch):
    db = tmp_path / "beads.db"
    db.touch()

    def unparsable(_db):
        raise json.JSONDecodeError("Expecting value", "not json", 0)

    monkeypatch.setattr(gate.shutil, "which", lambda _: "/usr/local/bin/br")
    monkeypatch.setattr(gate, "run_doctor", unparsable)
    log = tmp_path / "check.log"
    rc = gate.main(["--root", str(tmp_path), "--db", str(db), "--log", str(log)])
    assert rc == 3
    assert "DOCTOR-INFRA beads-doctor-gate: br doctor unusable" in log.read_text()


def test_the_live_branch_clears_on_a_healthy_report(tmp_path, monkeypatch):
    db = tmp_path / "beads.db"
    db.touch()
    seen = {}

    def healthy(passed_db):
        seen["db"] = passed_db
        return report([ok_check("jsonl.parse")]), "{}"

    monkeypatch.setattr(gate.shutil, "which", lambda _: "/usr/local/bin/br")
    monkeypatch.setattr(gate, "run_doctor", healthy)
    log = tmp_path / "check.log"
    rc = gate.main(["--root", str(tmp_path), "--db", str(db), "--log", str(log)])
    assert rc == 0
    assert seen["db"] == db
    assert "DOCTOR-CLEAR beads-doctor-gate: every check ok" in log.read_text()


def test_the_real_healthy_capture_from_this_repo_is_advisory(tmp_path):
    body = report([ok_check("jsonl.parse"), DEAD_EDGES, UNBLOCKED])
    path = tmp_path / "doctor.json"
    path.write_text(json.dumps(body))
    log = tmp_path / "check.log"
    rc = gate.main(["--report-file", str(path), "--log", str(log)])
    assert rc == 0
    assert "DOCTOR-ADVISORY beads-doctor-gate: 2 advisory finding(s)" in log.read_text()


def test_a_corrupt_capture_exits_two_and_logs_blocked(tmp_path):
    body = report([MALFORMED], health="recoverable")
    path = tmp_path / "doctor.json"
    path.write_text(json.dumps(body))
    log = tmp_path / "check.log"
    rc = gate.main(["--report-file", str(path), "--log", str(log)])
    assert rc == 2
    assert "DOCTOR-BLOCKED beads-doctor-gate:" in log.read_text()


def test_a_clean_capture_logs_clear(tmp_path):
    path = tmp_path / "doctor.json"
    path.write_text(json.dumps(report([ok_check("jsonl.parse")])))
    log = tmp_path / "check.log"
    assert gate.main(["--report-file", str(path), "--log", str(log)]) == 0
    assert "DOCTOR-CLEAR beads-doctor-gate: every check ok" in log.read_text()


def test_an_unreadable_report_file_denies(tmp_path):
    log = tmp_path / "check.log"
    rc = gate.main(["--report-file", str(tmp_path / "absent.json"), "--log", str(log)])
    assert rc == 3
    assert "DOCTOR-INFRA beads-doctor-gate:" in log.read_text()


def test_unparsable_json_denies(tmp_path):
    path = tmp_path / "doctor.json"
    path.write_text("{not json")
    log = tmp_path / "check.log"
    assert gate.main(["--report-file", str(path), "--log", str(log)]) == 3


def test_the_bypass_is_named_and_logged(tmp_path, monkeypatch):
    body = report([MALFORMED], health="recoverable")
    path = tmp_path / "doctor.json"
    path.write_text(json.dumps(body))
    log = tmp_path / "check.log"
    monkeypatch.setenv("CAIRN_DOCTOR_GATE_OK", "restoring from issues.jsonl")
    assert gate.main(["--report-file", str(path), "--log", str(log)]) == 0
    assert "BYPASS beads-doctor-gate: restoring from issues.jsonl" in log.read_text()


def test_a_usage_error_is_distinguishable_from_a_refused_store():
    assert gate.main(["--bogus"]) == gate.EXIT_USAGE
    assert gate.EXIT_USAGE != gate.EXIT_REFUSED


def test_the_blocked_message_names_the_precondition_not_a_score(tmp_path, capsys):
    path = tmp_path / "doctor.json"
    path.write_text(json.dumps(report([MALFORMED], health="recoverable")))
    gate.main(["--report-file", str(path), "--log", str(tmp_path / "check.log")])
    err = capsys.readouterr().err
    assert "REFUSED: br doctor reports the bead store may not be sound." in err
    assert "No bead was scored; this is the audit's precondition, not a score." in err
    assert f"    BLOCKS: unrecognized status — {MALFORMED_DESCRIBED}\n" in err


def test_the_advisory_message_says_the_precondition_holds(tmp_path, capsys):
    path = tmp_path / "doctor.json"
    path.write_text(json.dumps(report([DEAD_EDGES, UNBLOCKED])))
    gate.main(["--report-file", str(path), "--log", str(tmp_path / "check.log")])
    err = capsys.readouterr().err
    assert "br doctor reports findings that do not bear on the store's integrity." in err
    assert "The compliance audit's precondition holds; proceeding." in err
    assert f"    advisory: {DEAD_EDGES_DESCRIBED}\n" in err


def test_the_pre_commit_hook_runs_this_gate_and_stops_on_a_nonzero_return():
    hook = (REPO_ROOT / ".githooks" / "pre-commit").read_text()
    assert "scripts/beads_doctor_gate.py" in hook
    invocation = hook.split("scripts/beads_doctor_gate.py", 1)[1]
    assert "DOCTOR_GATE_RC=$?" in invocation
    guard = invocation.split("DOCTOR_GATE_RC=$?", 1)[1]
    assert '"$DOCTOR_GATE_RC" -ne 0' in guard
    assert "exit 1" in guard.split('"$DOCTOR_GATE_RC" -ne 0', 1)[1]
