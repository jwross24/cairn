from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import beads_doctor_gate as gate


def report(checks, health="healthy", anomalies=()):
    return {
        "ok": all(c.get("status") == "ok" for c in checks),
        "workspace_health": health,
        "reliability_audit": {
            "source": "doctor.inspect",
            "health": health,
            "anomaly_count": len(anomalies),
            "anomalies": list(anomalies),
        },
        "checks": list(checks),
    }


def ok(name):
    return {"name": name, "status": "ok", "details": {"finding_id": f"fm-{name}"}}


DEAD_EDGES = {
    "name": "dep.dead_closed_blocking_edges",
    "status": "warn",
    "message": "5 open issue(s) have dead blocking edges (blocker closed or missing): cairn-c8o, cairn-hcl",
    "details": {"remediation": "Remove or update the stale `blocks`/dependency edges (e.g. `br dep remove`)."},
}

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


def test_all_ok_is_clear():
    verdict = gate.classify(report([ok("jsonl.parse"), ok("schema.tables")]))
    assert verdict.outcome == "clear"
    assert verdict.blocking == []
    assert verdict.exit_code == 0


def test_the_two_dependency_warns_are_advisory():
    verdict = gate.classify(report([ok("jsonl.parse"), DEAD_EDGES, UNBLOCKED]))
    assert verdict.outcome == "advisory"
    assert verdict.blocking == []
    assert verdict.exit_code == 0
    assert len(verdict.advisory) == 2
    assert any("dep.dead_closed_blocking_edges [warn]" in line for line in verdict.advisory)
    assert any("br dep remove" in line for line in verdict.advisory)


def test_a_malformed_page_blocks():
    verdict = gate.classify(report([ok("jsonl.parse"), MALFORMED], health="recoverable"))
    assert verdict.outcome == "blocked"
    assert verdict.exit_code == 2
    joined = "\n".join(verdict.blocking)
    assert "sqlite.integrity_check" in joined
    assert "database disk image is malformed" in joined


def test_corruption_blocks_even_when_health_still_reads_healthy():
    verdict = gate.classify(report([ok("jsonl.parse"), MALFORMED], health="healthy"))
    assert verdict.outcome == "blocked"
    assert any("unrecognized status" in line for line in verdict.blocking)


def test_an_unrecognized_status_blocks():
    unknown = {"name": "some.future.check", "status": "degraded", "message": "a state this gate has not seen"}
    verdict = gate.classify(report([ok("jsonl.parse"), unknown]))
    assert verdict.outcome == "blocked"
    assert verdict.exit_code == 2
    assert any("unrecognized status — some.future.check [degraded]" in line for line in verdict.blocking)


@pytest.mark.parametrize("status", ["fail", "error", "critical", "FAIL", "", "unknown"])
def test_every_status_outside_ok_and_warn_blocks(status):
    verdict = gate.classify(report([{"name": "x.y", "status": status, "message": "m"}]))
    assert verdict.outcome == "blocked"


def test_a_non_string_status_blocks():
    verdict = gate.classify(report([{"name": "x.y", "status": None, "message": "m"}]))
    assert verdict.outcome == "blocked"


def test_a_warn_naming_corruption_blocks():
    warn_corrupt = {
        "name": "audit.suspect_close_reasons",
        "status": "warn",
        "message": "Failed to query closed beads: database disk image is malformed: failed to parse B-tree page 3",
    }
    verdict = gate.classify(report([warn_corrupt]))
    assert verdict.outcome == "blocked"
    assert any("corruption named in the message" in line for line in verdict.blocking)


def test_a_warn_on_an_integrity_check_blocks_whatever_the_message_says():
    quiet = {"name": "sqlite3.integrity_check", "status": "warn", "message": "nothing alarming here"}
    verdict = gate.classify(report([quiet]))
    assert verdict.outcome == "blocked"
    assert any("integrity check not ok" in line for line in verdict.blocking)


def test_a_recoverable_health_label_blocks_on_its_own():
    verdict = gate.classify(report([ok("jsonl.parse")], health="recoverable"))
    assert verdict.outcome == "blocked"
    assert any("workspace_health is 'recoverable'" in line for line in verdict.blocking)


def test_a_degraded_health_label_with_only_dep_warns_stays_advisory():
    verdict = gate.classify(report([DEAD_EDGES], health="degraded"))
    assert verdict.outcome == "advisory"


def test_a_missing_health_label_blocks():
    body = report([ok("jsonl.parse")])
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
    verdict = gate.classify(report([ok("jsonl.parse")], anomalies=[anomaly]))
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


def test_the_real_healthy_capture_from_this_repo_is_advisory(tmp_path):
    body = report([ok("jsonl.parse"), DEAD_EDGES, UNBLOCKED])
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
    path.write_text(json.dumps(report([ok("jsonl.parse")])))
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


def test_the_blocked_message_names_the_precondition_not_a_score(tmp_path, capsys):
    path = tmp_path / "doctor.json"
    path.write_text(json.dumps(report([MALFORMED], health="recoverable")))
    gate.main(["--report-file", str(path), "--log", str(tmp_path / "check.log")])
    err = capsys.readouterr().err
    assert "REFUSED: br doctor reports the bead store may not be sound." in err
    assert "No bead was scored; this is the audit's precondition, not a score." in err
    assert "score" not in err.replace("No bead was scored; this is the audit's precondition, not a score.", "")


def test_the_advisory_message_says_the_precondition_holds(tmp_path, capsys):
    path = tmp_path / "doctor.json"
    path.write_text(json.dumps(report([DEAD_EDGES, UNBLOCKED])))
    gate.main(["--report-file", str(path), "--log", str(tmp_path / "check.log")])
    err = capsys.readouterr().err
    assert "br doctor reports findings that do not bear on the store's integrity." in err
    assert "The compliance audit's precondition holds; proceeding." in err
