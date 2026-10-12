import dataclasses
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from cairn import allowlist, bundle, ladder, runner, verifier
from cairn.substrate import blob_hash

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers
from test_ladder_run import RUN_ID, _dispatch_run
from test_ladder_run import hypothesis_object as hypothesis_object
from test_ladder_run import plan as plan

INTERPRETER = re.compile(r"\Apython3\.\d+\Z")
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


LADDER_METHOD = """
import json, pathlib, subprocess, sys
scratch, action, outside = sys.argv[1:4]
json.load(sys.stdin)
if action == "outside_write":
    pathlib.Path(outside).write_text("escaped")
elif action == "undeclared_exec":
    subprocess.run(["/bin/echo", "escaped"], check=True, capture_output=True)
elif action == "withheld_read":
    pathlib.Path(outside).read_bytes()
pathlib.Path(scratch, "completed").write_text("completed")
print('{"status":"OK"}')
"""


@pytest.fixture
def withhold_substrate(request):
    return getattr(request, "param", False)


@pytest.fixture
def ladder_method(writer, shipped, tmp_path, plan, hypothesis_object, monkeypatch, request, withhold_substrate):
    backend_paths = getattr(request, "param", None)
    if backend_paths:
        hypothesis_object = dataclasses.replace(
            hypothesis_object, claimed={**hypothesis_object.claimed, "uncounted_backends": ",".join(backend_paths)}
        )
    withheld = [f"{writer.path}{suffix}" for suffix in ("", "-wal", "-shm", "-journal")] if withhold_substrate else ()
    _dispatch_run(
        writer, shipped, tmp_path, plan, hypothesis_object, RUN_ID, backend_paths=backend_paths, withheld_roots=withheld
    )
    dispatch = ladder.dispatches_for(writer, RUN_ID)[ladder.CLAIMANT]
    outside = tmp_path / "outside.txt"

    def run(action, *, executable=BACKEND, target=outside):
        monkeypatch.setattr(
            runner,
            "skill_argv",
            lambda module, scratch: [executable, "-c", LADDER_METHOD, str(scratch), action, str(target)],
        )
        trial = ladder.run_arm(
            writer,
            shipped,
            dispatch,
            plan=plan,
            instance=verifier.Instance(p=97, a=2, b=3, n=5, P=(3, 6), Q=(3, 6)),
            instance_hash="aa" * 32,
            bits=28,
            trial=0,
            scratch_root=tmp_path / "runs",
            budget_remaining=10_000,
            backend_paths=backend_paths,
        )
        return trial, outside, dispatch

    return run


def _assert_ladder_confined(trial, outside, dispatch):
    assert not outside.exists()
    assert trial.status == runner.STATUS_FAIL
    assert not list(Path(dispatch.allow_list["writable_root"]).parent.rglob("completed"))


@pytest.mark.parametrize("action", ["outside_write", "undeclared_exec"])
def test_ladder_launch_confines_the_method(ladder_method, writer, action):
    trial, outside, dispatch = ladder_method(action)
    _assert_ladder_confined(trial, outside, dispatch)
    policy = allowlist.read(writer, trial.allow_list_hash)
    receipt = writer.get_receipt(writer.get_attempt(trial.attempt_id)["receipt_hash"])
    stderr = (outside.parent / "runs" / trial.attempt_id / "stderr").read_bytes()
    assert allowlist.detect_violation(receipt["exit_status"], stderr, policy) == action


def test_ladder_honest_launch_records_the_effective_boundary(ladder_method, writer, tmp_path, shipped, popen_spy):
    trial, outside, dispatch = ladder_method("honest")
    assert trial.status == runner.STATUS_OK
    assert not outside.exists()
    effective = allowlist.read(writer, trial.allow_list_hash)
    scratch = Path(dispatch.allow_list["writable_root"]) / trial.attempt_id / "scratch"
    assert effective.writable_root == trial.writable_root == str(scratch.resolve())
    assert (scratch / "completed").read_text() == "completed"
    assert effective.counted_object == dispatch.allow_list["counted_object"] == BACKEND
    assert effective.exec_paths == tuple(dispatch.allow_list["exec_paths"])
    assert effective.profile_hash == dispatch.allow_list["profile_hash"]
    profile = tmp_path / "runs" / trial.attempt_id / "method.sb"
    assert blob_hash(profile.read_bytes()) == effective.profile_hash
    assert popen_spy == [allowlist.argv_for(effective, profile, popen_spy[0][5:])]
    record = writer.conn.execute("SELECT canonical, hash FROM nodes WHERE kind = 'method_launch'").fetchone()
    recorded = bundle._decode(bytes(record["canonical"]))
    assert recorded["attempt_id"] == trial.attempt_id
    assert recorded["dispatch_hash"] == dispatch.hash
    assert recorded["allow_list_hash"] == effective.hash
    assert recorded["writable_root"] == effective.writable_root
    assert recorded["argv"] == popen_spy[0]
    assert {edge["parent_hash"] for edge in writer.lineage_of(record["hash"])} == {dispatch.hash, effective.hash}
    assert allowlist.check_instantiation(effective, shipped)


@pytest.mark.parametrize("withhold_substrate", [True], indirect=True)
def test_ladder_launch_withholds_the_substrate_the_dispatch_withholds(ladder_method, writer):
    trial, _, dispatch = ladder_method("withheld_read", target=writer.path)
    assert trial.status == runner.STATUS_FAIL
    effective = allowlist.read(writer, trial.allow_list_hash)
    assert effective.withheld_roots == tuple(dispatch.allow_list["withheld_roots"])
    assert os.path.realpath(writer.path) in effective.withheld_roots
    assert not list(Path(dispatch.allow_list["writable_root"]).rglob("completed"))
    receipt = writer.get_receipt(writer.get_attempt(trial.attempt_id)["receipt_hash"])
    stderr = (Path(writer.path).parent / "runs" / trial.attempt_id / "stderr").read_bytes()
    assert allowlist.detect_violation(receipt["exit_status"], stderr, effective) == "withheld_read"


@pytest.mark.parametrize("withhold_substrate", [True], indirect=True)
def test_ladder_honest_launch_completes_beside_a_withheld_substrate(ladder_method, writer):
    trial, _, dispatch = ladder_method("honest")
    assert trial.status == runner.STATUS_OK
    effective = allowlist.read(writer, trial.allow_list_hash)
    assert effective.withheld_roots == tuple(dispatch.allow_list["withheld_roots"])
    assert effective.profile_hash == dispatch.allow_list["profile_hash"]


def test_the_same_ladder_read_without_a_withheld_root_completes(ladder_method, writer):
    trial, _, dispatch = ladder_method("withheld_read", target=writer.path)
    assert dispatch.allow_list["withheld_roots"] == []
    assert trial.status == runner.STATUS_OK


@pytest.mark.parametrize("action", ["outside_write", "undeclared_exec"])
def test_ladder_confinement_assertions_refuse_a_removed_wrapper(ladder_method, monkeypatch, action):
    monkeypatch.setattr(allowlist, "argv_for", lambda value, path, argv: argv)
    observed = ladder_method(action)
    assert observed[0].status == runner.STATUS_OK
    with pytest.raises(AssertionError):
        _assert_ladder_confined(*observed)


@pytest.mark.parametrize("ladder_method", [{"gp": "/bin/echo"}], indirect=True)
def test_ladder_launch_allows_a_declared_backend(ladder_method, writer):
    trial, outside, _ = ladder_method("undeclared_exec")
    assert trial.status == runner.STATUS_OK
    assert not outside.exists()
    policy = allowlist.read(writer, trial.allow_list_hash)
    assert policy.declared_backends == ("gp",)
    assert "/bin/echo" in policy.exec_paths
    assert (Path(trial.writable_root) / "completed").read_text() == "completed"


@pytest.mark.parametrize("binding", ["scratch", "executable", "unavailable", "missing"])
def test_ladder_policy_refuses_before_spawn(ladder_method, monkeypatch, popen_spy, binding, tmp_path):
    if binding == "scratch":
        original = runner.MethodPolicy

        def substitute(**kwargs):
            return original(**{**kwargs, "scratch_root": tmp_path})

        monkeypatch.setattr(runner, "MethodPolicy", substitute)
    elif binding == "executable":
        original = runner.MethodPolicy

        def substitute(**kwargs):
            value = allowlist.instantiate(
                kwargs["gate_bundle"],
                hypothesis=kwargs["hypothesis"],
                counted_object="/bin/echo",
                scratch_dir=kwargs["scratch_root"],
            )
            return original(**{**kwargs, "allow_list": value})

        monkeypatch.setattr(runner, "MethodPolicy", substitute)
    elif binding == "unavailable":
        monkeypatch.setattr(allowlist, "ARMS", {allowlist.MECHANISM_SANDBOX_EXEC: (("darwin",), "/unavailable")})
    else:
        original = runner.launch

        def without_policy(*args, **kwargs):
            return original(*args, **{**kwargs, "method_policy": None})

        monkeypatch.setattr(runner, "launch", without_policy)
    with pytest.raises(allowlist.AllowListRefused):
        ladder_method("honest")
    assert popen_spy == []
    assert not list(tmp_path.rglob("completed"))


def test_ladder_refuses_a_substituted_launch_executable(ladder_method, popen_spy):
    with pytest.raises(allowlist.AllowListRefused):
        ladder_method("honest", executable="/bin/echo")
    assert popen_spy == []


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
    assert value.exec_paths == BACKEND_EXECS
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
    assert set(declared.exec_paths) == {*BACKEND_EXECS, "/bin/echo"}
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


def test_a_withheld_root_survives_the_record_round_trip(confined, writer, tmp_path):
    value, _, _ = confined(withheld_roots=[tmp_path / "substrate.sqlite"])
    assert value.withheld_roots == (os.path.realpath(tmp_path / "substrate.sqlite"),)
    assert allowlist.read(writer, allowlist.record(writer, value)) == value


def test_a_stored_record_lacking_withheld_roots_is_refused_and_could_not_address_itself(confined, writer):
    value, _, _ = confined()
    stored = {key: field for key, field in value.as_dict().items() if key != "withheld_roots"}
    digest = writer.put_node(
        allowlist.RECORD_KIND, bundle.canonical_bytes(allowlist.RECORD_KIND, stored), replay_grade="AuditOnly"
    )
    assert allowlist.AllowList(**stored).hash != digest
    with pytest.raises(allowlist.AllowListRefused, match="does not carry the allow-list fields"):
        allowlist.read(writer, digest)


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


def _app_binary(path):
    versions = Path(path).parent.parent
    framework = versions.parent.parent
    if Path(path).parent.name != "bin" or not framework.name.endswith(".framework"):
        return None
    name = framework.name.removesuffix(".framework")
    target = versions / "Resources" / f"{name}.app" / "Contents" / "MacOS" / name
    return target if target.is_file() and os.access(target, os.X_OK) else None


def _framework_interpreters():
    found = []
    discovered = (os.path.realpath(p) for p in Path("/opt/homebrew/bin").glob("python3.*") if INTERPRETER.match(p.name))
    for candidate in [BACKEND, *discovered]:
        if _app_binary(candidate) is not None and candidate not in found:
            found.append(candidate)
    return found


FRAMEWORK_INTERPRETERS = _framework_interpreters()
BACKEND_EXECS = tuple(sorted({BACKEND} | ({str(_app_binary(BACKEND))} if _app_binary(BACKEND) else set())))


@pytest.mark.skipif(not FRAMEWORK_INTERPRETERS, reason="no framework-build interpreter on this host")
@pytest.mark.parametrize("interpreter", FRAMEWORK_INTERPRETERS)
def test_a_framework_interpreter_runs_the_honest_method_and_still_names_a_violation(shipped, tmp_path, interpreter):
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    value = allowlist.instantiate(shipped, hypothesis=_hypothesis(), counted_object=interpreter, scratch_dir=scratch)
    assert str(_app_binary(interpreter)) in value.exec_paths
    profile = allowlist.write_profile(value, tmp_path / f"{value.profile_hash[:16]}.sb")
    outside = tmp_path / "outside.txt"

    def run(action):
        argv = allowlist.argv_for(
            value, profile, [interpreter, "-c", METHOD, str(scratch), action, str(outside), interpreter]
        )
        done = subprocess.run(argv, capture_output=True)
        return done.returncode, done.stdout, done.stderr

    rc, out, err = run("honest")
    assert (rc, out, err) == (0, b"METHOD_COMPLETED", b"")

    rc, out, err = run("network")
    assert out == b""
    assert allowlist.detect_violation(rc, err, value) == "network_egress"

    rc, out, err = run("outside_write")
    assert out == b""
    assert not outside.exists()
    assert allowlist.detect_violation(rc, err, value) == "outside_write"


SECRET = b"SECRET-X-918273645"
READER = "import sys; sys.stdout.write('X=' + ('SECRET' if sys.argv[2].encode() in open(sys.argv[1], 'rb').read() else 'absent'))"


def _substrate_holding_the_answer(tmp_path):
    sub = helpers.open_writer(tmp_path)
    sub.put_blob(SECRET)
    sub.close()
    return tmp_path / "substrate.sqlite"


def _read_as_method(value, profile, target):
    argv = allowlist.argv_for(value, profile, [BACKEND, "-c", READER, str(target), SECRET.decode()])
    done = subprocess.run(argv, capture_output=True)
    return done.returncode, done.stdout, done.stderr


def test_a_method_cannot_read_the_substrate_that_holds_the_answer(confined, tmp_path):
    substrate = _substrate_holding_the_answer(tmp_path)
    value, _, profile = confined(withheld_roots=[substrate])
    rc, out, err = _read_as_method(value, profile, substrate)
    assert rc != 0
    assert out == b""
    assert b"Operation not permitted" in err
    assert value.withheld_roots == (os.path.realpath(substrate),)
    assert allowlist.detect_violation(rc, err, value) == "withheld_read"


def test_the_same_read_without_a_withheld_root_still_succeeds(confined, tmp_path):
    substrate = _substrate_holding_the_answer(tmp_path)
    value, _, profile = confined()
    assert _read_as_method(value, profile, substrate)[:2] == (0, b"X=SECRET")


def test_a_symlink_to_a_withheld_substrate_is_refused(confined, tmp_path):
    substrate = _substrate_holding_the_answer(tmp_path)
    value, scratch, profile = confined(withheld_roots=[substrate])
    alias = scratch / "alias.sqlite"
    alias.symlink_to(substrate)
    rc, out, err = _read_as_method(value, profile, alias)
    assert rc != 0
    assert out == b""
    assert b"Operation not permitted" in err
    assert allowlist.detect_violation(rc, err, value) == "withheld_read"


def test_an_alias_spelling_of_a_withheld_root_is_refused_too(confined, tmp_path):
    substrate = _substrate_holding_the_answer(tmp_path)
    spelled = Path(str(substrate).replace("/private/var", "/var", 1))
    value, _, profile = confined(withheld_roots=[spelled])
    for target in (spelled, substrate):
        rc, out, err = _read_as_method(value, profile, target)
        assert rc != 0
        assert allowlist.detect_violation(rc, err, value) == "withheld_read"


def test_the_honest_method_still_completes_beside_a_withheld_root(confined, tmp_path):
    substrate = _substrate_holding_the_answer(tmp_path)
    value, scratch, profile = confined(withheld_roots=[substrate])
    rc, out, err = _run(value, profile, scratch, "honest", tmp_path / "outside.txt")
    assert (rc, out) == (0, b"METHOD_COMPLETED"), err
