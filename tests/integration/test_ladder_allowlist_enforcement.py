import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from cairn import allowlist, bundle
from cairn.substrate import blob_hash

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers

BACKEND = os.path.realpath(sys.executable)
METHOD = """
import os, socket, subprocess, sys
scratch, action, outside, backend = sys.argv[1:5]
if action == "honest":
    with open(os.path.join(scratch, "trial.json"), "w") as fh:
        fh.write('{"answer": %d}' % pow(3, 41, 2**61 - 1))
elif action == "outside_write":
    with open(outside, "w") as fh:
        fh.write("exfiltrated")
elif action == "network":
    s = socket.socket(); s.settimeout(5); s.connect(("1.1.1.1", 80)); s.close()
elif action == "undeclared_exec":
    subprocess.run(["/bin/echo", "spawned"], check=True)
elif action == "declared_exec":
    subprocess.run([backend, "-c", "pass"], check=True)
sys.stdout.write("METHOD_COMPLETED")
"""


def _hypothesis(**claimed):
    return {
        "target_family": "toy_curve",
        "claimed": {"model": "c_ln_p_tries", **claimed},
        "method_identity": {"interface_version": "toy_curve/1", "params": {}},
        "declared_parameter_ranges": {"bits": [40, 40]},
        "sampling_distribution": None,
    }


@pytest.fixture
def shipped(pinned_bundle):
    return bundle.GateBundle.open(*pinned_bundle())


@pytest.fixture
def writer(tmp_path):
    sub = helpers.open_writer(tmp_path)
    yield sub
    sub.close()


@pytest.fixture
def confined(shipped, tmp_path):
    def make(**kwargs):
        scratch = tmp_path / "scratch"
        scratch.mkdir(exist_ok=True)
        value = allowlist.instantiate(
            shipped,
            hypothesis=kwargs.pop("hypothesis", _hypothesis()),
            counted_object=BACKEND,
            scratch_dir=scratch,
            **kwargs,
        )
        profile = allowlist.write_profile(value, tmp_path / f"{value.profile_hash[:16]}.sb")
        return value, scratch, profile

    return make


def _run(value, profile, scratch, action, outside):
    argv = allowlist.argv_for(value, profile, [BACKEND, "-c", METHOD, str(scratch), action, str(outside), BACKEND])
    done = subprocess.run(argv, capture_output=True)
    return done.returncode, done.stdout, done.stderr


def test_the_honest_method_completes_and_its_allow_list_matches_the_bundle_template(shipped, confined, tmp_path):
    value, scratch, profile = confined()
    rc, out, err = _run(value, profile, scratch, "honest", tmp_path / "outside.txt")
    assert (rc, out) == (0, b"METHOD_COMPLETED"), err
    assert (scratch / "trial.json").read_text() == '{"answer": 1885351238965377138}'
    assert allowlist.check_instantiation(value, shipped) is True
    entry = allowlist.template(shipped)
    assert value.template_hash == blob_hash(shipped.raw(allowlist.BUNDLE_KIND))
    assert (value.bundle_hash, value.network_egress) == (shipped.hash, entry["network_egress"])
    assert value.mechanism in entry["mechanisms"]
    assert value.exec_paths == (BACKEND,)
    assert allowlist.detect_violation(rc, err, value) is None


def test_a_write_outside_the_scratch_path_is_confined_and_named(confined, tmp_path):
    value, scratch, profile = confined()
    outside = tmp_path / "outside.txt"
    rc, out, err = _run(value, profile, scratch, "outside_write", outside)
    assert rc != 0
    assert out == b""
    assert not outside.exists()
    assert b"Operation not permitted" in err
    assert allowlist.detect_violation(rc, err, value) == "outside_write"


def test_the_same_write_inside_a_permitting_writable_root_completes(shipped, tmp_path):
    inside = tmp_path / "widened"
    inside.mkdir()
    value = allowlist.instantiate(shipped, hypothesis=_hypothesis(), counted_object=BACKEND, scratch_dir=inside)
    profile = allowlist.write_profile(value, tmp_path / "widened.sb")
    target = inside / "outside.txt"
    rc, out, err = _run(value, profile, inside, "outside_write", target)
    assert (rc, out) == (0, b"METHOD_COMPLETED"), err
    assert target.read_text() == "exfiltrated"
    assert allowlist.detect_violation(rc, err, value) is None


def test_a_network_socket_is_confined_and_named(confined, tmp_path):
    value, scratch, profile = confined()
    rc, out, err = _run(value, profile, scratch, "network", tmp_path / "outside.txt")
    assert rc != 0
    assert out == b""
    assert allowlist.detect_violation(rc, err, value) == "network_egress"
    with socket.socket() as control:
        control.settimeout(10)
        control.connect(("1.1.1.1", 80))


def test_an_undeclared_subprocess_is_confined_and_named(confined, tmp_path):
    value, scratch, profile = confined()
    rc, out, err = _run(value, profile, scratch, "undeclared_exec", tmp_path / "outside.txt")
    assert rc != 0
    assert out == b""
    assert b"/bin/echo" in err
    assert allowlist.detect_violation(rc, err, value) == "undeclared_exec"


def test_the_same_spawn_declared_as_a_backend_completes(confined, tmp_path):
    declared, scratch, profile = confined(
        hypothesis=_hypothesis(uncounted_backends="gp"), backend_paths={"gp": "/bin/echo"}
    )
    assert "/bin/echo" in declared.exec_paths
    rc, out, err = _run(declared, profile, scratch, "undeclared_exec", tmp_path / "outside.txt")
    assert (rc, out) == (0, b"spawned\nMETHOD_COMPLETED"), err
    assert allowlist.detect_violation(rc, err, declared) is None


def test_a_declared_backend_is_admitted_on_the_declaration_alone_and_is_recorded(confined, writer, tmp_path):
    hypothesis = _hypothesis(uncounted_backends="gp")
    value, scratch, profile = confined(hypothesis=hypothesis, backend_paths={"gp": BACKEND})
    rc, out, err = _run(value, profile, scratch, "declared_exec", tmp_path / "outside.txt")
    assert (rc, out) == (0, b"METHOD_COMPLETED"), err
    assert value.declared_backends == ("gp",)
    digest = allowlist.record(writer, value)
    assert allowlist.read(writer, digest) == value
    assert allowlist.read(writer, digest).declared_backends == ("gp",)


def test_the_same_method_without_the_declaration_is_confined(confined, tmp_path):
    value, scratch, profile = confined()
    assert value.declared_backends == ()
    argv = allowlist.argv_for(
        value, profile, [BACKEND, "-c", METHOD, str(scratch), "declared_exec", str(tmp_path / "o.txt"), "/bin/echo"]
    )
    done = subprocess.run(argv, capture_output=True)
    assert done.returncode != 0
    assert done.stdout == b""
    assert b"Operation not permitted" in done.stderr


def test_the_profile_the_gate_wrote_is_the_one_the_allow_list_addresses(confined):
    value, _, profile = confined()
    assert blob_hash(Path(profile).read_bytes()) == value.profile_hash
    assert Path(profile).stat().st_mode & 0o222 == 0
