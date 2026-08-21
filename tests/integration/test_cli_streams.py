import json
import subprocess
import sys

from cairn import exits


def _cairn(*args):
    return subprocess.run([sys.executable, "-m", "cairn", *args], capture_output=True, text=True)


def test_env_json_stdout_is_one_document_and_stderr_is_log_records():
    proc = _cairn("env", "--json")
    assert proc.returncode == exits.OK
    document = json.loads(proc.stdout)
    assert document["command"] == "env" and document["schema_version"] == 1
    for line in proc.stderr.splitlines():
        json.loads(line)


def test_env_json_with_debug_logging_keeps_stdout_clean():
    proc = _cairn("env", "--json", "--log", "DEBUG")
    assert proc.returncode == exits.OK
    json.loads(proc.stdout)
    assert proc.stdout.count("\n") == 1
    assert "\x1b" not in proc.stdout and "\x1b" not in proc.stderr


def test_bare_invocation_exits_user_input_with_usage_on_stderr():
    proc = _cairn()
    assert proc.returncode == exits.USER_INPUT
    assert proc.stdout == ""
    assert "usage:" in proc.stderr and "robot-docs" in proc.stderr


def test_kat_drift_exits_gate_refused(tmp_path):
    from cairn import kat

    copy = tmp_path / "canon_kat.json"
    data = json.loads(kat.DEFAULT_VECTORS.read_text())
    data["vectors"][0]["expected"] = "00" * 32
    copy.write_text(json.dumps(data))
    proc = _cairn("kat", "canon", "--vectors", str(copy), "--json")
    assert proc.returncode == exits.GATE_REFUSED
    assert json.loads(proc.stdout)["ok"] is False
