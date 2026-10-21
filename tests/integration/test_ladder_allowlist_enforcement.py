import dataclasses
import os
from pathlib import Path

import pytest
from _ladder_run_helpers import BACKEND, RUN_ID, _dispatch_run
from _ladder_run_helpers import hypothesis_object as hypothesis_object
from _ladder_run_helpers import plan as plan
from _ladder_run_helpers import shipped as shipped
from _ladder_run_helpers import writer as writer

from cairn import allowlist, bundle, ladder, runner, verifier
from cairn.substrate import blob_hash

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
    return getattr(request, "param", True)


@pytest.fixture
def ladder_method(writer, shipped, tmp_path, plan, hypothesis_object, monkeypatch, request, withhold_substrate):
    backend_paths = getattr(request, "param", None)
    if backend_paths:
        hypothesis_object = dataclasses.replace(
            hypothesis_object, claimed={**hypothesis_object.claimed, "uncounted_backends": ",".join(backend_paths)}
        )
    withheld = allowlist.store_roots(writer.path) if withhold_substrate else ()
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


@pytest.mark.parametrize("withhold_substrate", [False], indirect=True)
def test_a_ladder_launch_whose_dispatch_leaves_the_substrate_readable_is_refused_before_any_spawn(
    ladder_method, writer, monkeypatch
):
    spawned = []
    monkeypatch.setattr(runner, "spawn_and_wait", lambda *a, **k: spawned.append(a))
    with pytest.raises(ladder.RunRefused) as raised:
        ladder_method("withheld_read", target=writer.path)
    assert raised.value.reason == ladder.SUBSTRATE_READABLE
    assert spawned == []


@pytest.mark.parametrize("missing", ["", "-wal", "-shm", "-journal"])
def test_a_dispatch_withholding_all_but_one_store_file_is_refused(ladder_method, writer, missing):
    value = ladder.dispatches_for(writer, RUN_ID)[ladder.CLAIMANT]
    kept = tuple(r for r in allowlist.store_roots(writer.path) if r != os.path.realpath(f"{writer.path}{missing}"))
    partial = dataclasses.replace(ladder._allow_list(value), withheld_roots=kept)
    assert allowlist.unwithheld_store_roots(partial, writer.path) == (os.path.realpath(f"{writer.path}{missing}"),)
    assert (
        allowlist.unwithheld_store_roots(
            dataclasses.replace(partial, withheld_roots=allowlist.store_roots(writer.path)), writer.path
        )
        == ()
    )


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
