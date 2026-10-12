import json
import subprocess
import sys
from pathlib import Path

import pytest

from cairn import countedvm

CHILD = Path(__file__).resolve().parents[1] / "fixtures" / "countedvm_child.py"
INSTANCE = [23, 1, 1, 28, [3, 10], [3, 10]]
PROGRAM = "setp p0 P\nsset s0 5\nmulp p0 p0 s0\nhalt"
BUDGET = 10_000
EXPECTED_COUNT = countedvm.expected_mul_ops(5)
REQUIRED = countedvm.SANDBOX_REQUIRED.get(sys.platform)
CONTAINMENT_ONLY = pytest.mark.skipif(REQUIRED is None, reason="containment supports macOS and Linux")


def _child(request):
    completed = subprocess.run(
        [sys.executable, str(CHILD)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=countedvm.REPO_ROOT,
        timeout=180,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


@pytest.fixture(scope="module")
def genuine(tmp_path_factory):
    return _child({"op": "build", "scratch": str(tmp_path_factory.mktemp("vm-genuine"))})


def _launch(binary, digest, tmp_path, *, attempt_id="attempt-1", program=PROGRAM, budget=BUDGET, wall_cap_s=None):
    return _child(
        {
            "op": "launch",
            "binary": str(binary),
            "digest": digest,
            "instance": INSTANCE,
            "program": program,
            "budget": budget,
            "attempt_id": attempt_id,
            "scratch": str(tmp_path / "run"),
            "wall_cap_s": wall_cap_s,
        }
    )


def test_a_direct_launch_binds_the_count_to_the_attempt_the_program_the_instance_and_the_binary(genuine, tmp_path):
    run = _launch(genuine["binary"], genuine["digest"], tmp_path)
    assert run["outcome"]["status"] == countedvm.STATUS_OK
    assert run["outcome"]["count"] == EXPECTED_COUNT
    assert run["argv"] == [genuine["binary"]]
    assert run["binary_digest"] == genuine["digest"]
    assert run["program_digest"] == countedvm.blob_hash(PROGRAM.encode())
    assert run["measurement_scope"] == "tree"
    assert run["cpu_user_s"] + run["cpu_sys_s"] > 0
    other = _launch(genuine["binary"], genuine["digest"], tmp_path, attempt_id="attempt-2")
    assert other["binding"] != run["binding"]
    assert _launch(genuine["binary"], genuine["digest"], tmp_path)["binding"] == run["binding"]


@CONTAINMENT_ONLY
def test_the_launched_vm_reports_the_containment_it_applied(genuine, tmp_path):
    run = _launch(genuine["binary"], genuine["digest"], tmp_path)
    assert run["outcome"]["sandbox"] == REQUIRED


def test_a_relay_wrapper_that_forwards_the_genuine_vm_and_rewrites_its_count_is_refused_before_it_runs(
    genuine, tmp_path
):
    relay = tmp_path / "relay.sh"
    relay.write_text(
        f'#!/bin/sh\n{genuine["binary"]} | sed \'s/"count":[0-9]*/"count":1/\'\n',
    )
    relay.chmod(0o755)
    refused = _launch(relay, genuine["digest"], tmp_path)
    assert refused == {"refused": "binary_digest_mismatch"}
    assert not (tmp_path / "run" / "stdout").exists()


def test_an_unpinned_binary_that_prints_a_plausible_success_line_is_refused_on_its_digest(genuine, tmp_path):
    forged = tmp_path / "forged.sh"
    forged.write_text(
        "#!/bin/sh\n"
        'echo \'{"status":"OK","sandbox":"pure-computation","count":0,"executed":4,'
        '"result":null,"p0":null,"i0":0}\'\n'
    )
    forged.chmod(0o755)
    assert _launch(forged, genuine["digest"], tmp_path) == {"refused": "binary_digest_mismatch"}


@CONTAINMENT_ONLY
def test_a_vm_built_without_its_containment_call_is_refused_even_when_its_digest_is_pinned(tmp_path):
    mutant = _child(
        {"op": "mutant", "scratch": str(tmp_path / "mutant"), "old": "if (!contain()) {", "new": "if (0) {"}
    )
    assert _launch(mutant["binary"], mutant["digest"], tmp_path) == {"refused": "containment_missing"}


@CONTAINMENT_ONLY
def test_the_containment_the_vm_applies_stops_a_file_read_that_an_uncontained_process_completes(tmp_path):
    results = _child({"op": "probe", "scratch": str(tmp_path / "probe")})
    assert results["uncontained"] == {"rc": 0, "stdout": "open=3 read=1\n"}
    assert results["contained"]["rc"] == 1
    assert results["contained"]["stdout"].startswith("open=-1")


def test_a_wall_capped_vm_is_refused_not_decoded(genuine, tmp_path):
    spin = "iset i0 1\nloop:\njnz i0 loop\nhalt"
    refused = _launch(genuine["binary"], genuine["digest"], tmp_path, program=spin, budget=10**12, wall_cap_s=1.0)
    assert refused == {"refused": "wall_cap_exceeded"}
