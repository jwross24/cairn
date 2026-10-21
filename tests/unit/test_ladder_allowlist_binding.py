import dataclasses
import os
from pathlib import Path

import pytest
from _ladder_allowlist_helpers import BACKEND, _hypothesis
from _ladder_allowlist_helpers import instance as instance
from _ladder_allowlist_helpers import scratch as scratch
from _ladder_allowlist_helpers import shipped as shipped

from cairn import allowlist
from cairn.substrate import Substrate, blob_hash

MACHO = b"\xcf\xfa\xed\xfe" + b"\x00" * 28


def test_the_binding_check_refuses_an_allow_list_the_gate_would_not_derive(shipped, scratch, tmp_path):
    declared = tmp_path / "declared"
    declared.write_text("#!/bin/sh\nexit 0\n")
    declared.chmod(0o755)
    bound = {
        "hypothesis": _hypothesis(uncounted_backends="gp"),
        "counted_object": BACKEND,
        "scratch_dir": scratch,
        "backend_paths": {"gp": declared},
    }
    value = allowlist.instantiate(shipped, **bound)
    assert allowlist.check_binding(value, shipped, **bound) is True
    swapped = tuple(sorted({BACKEND, "/bin/sh"}))
    tampered = dataclasses.replace(value, exec_paths=swapped, profile_hash=blob_hash(allowlist.profile_bytes(swapped)))
    assert allowlist.check_instantiation(tampered, shipped) is True
    with pytest.raises(allowlist.AllowListRefused, match="exec_paths"):
        allowlist.check_binding(tampered, shipped, **bound)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    with pytest.raises(allowlist.AllowListRefused, match="writable_root"):
        allowlist.check_binding(value, shipped, **{**bound, "scratch_dir": elsewhere})


def test_the_binding_check_refuses_a_launch_whose_declaration_differs(shipped, scratch, instance):
    with pytest.raises(allowlist.AllowListRefused, match="declared_backends"):
        allowlist.check_binding(
            instance,
            shipped,
            hypothesis=_hypothesis(uncounted_backends="gmpy2"),
            counted_object=BACKEND,
            scratch_dir=scratch,
        )


def _framework(tmp_path, name="Python", version="3.14", app=True):
    versions = tmp_path / f"{name}.framework" / "Versions" / version
    stub = versions / "bin" / f"python{version}"
    stub.parent.mkdir(parents=True)
    stub.write_bytes(MACHO)
    stub.chmod(0o755)
    if app:
        target = versions / "Resources" / f"{name}.app" / "Contents" / "MacOS" / name
        target.parent.mkdir(parents=True)
        target.write_bytes(MACHO)
        target.chmod(0o755)
        return str(stub), str(target)
    return str(stub), None


def test_a_framework_stub_derives_the_binary_it_re_execs_into(tmp_path):
    stub, target = _framework(tmp_path)
    assert allowlist.reexec_target(stub) == target


@pytest.mark.parametrize("path", ["/usr/bin/true", "/bin/sh"])
def test_a_plain_executable_derives_no_re_exec_target(path):
    assert allowlist.reexec_target(path) is None


def test_a_framework_layout_without_the_app_binary_derives_nothing(tmp_path):
    stub, _ = _framework(tmp_path, app=False)
    assert allowlist.reexec_target(stub) is None


def test_the_instantiation_admits_the_binary_its_counted_object_re_execs_into(shipped, scratch, tmp_path):
    stub, target = _framework(tmp_path)
    value = allowlist.instantiate(shipped, hypothesis=_hypothesis(), counted_object=stub, scratch_dir=scratch)
    assert value.counted_object == stub
    assert set(value.exec_paths) == {stub, target}
    assert allowlist.check_instantiation(value, shipped) is True


def test_a_stored_instantiation_settles_after_its_framework_moves(shipped, scratch, tmp_path):
    stub, target = _framework(tmp_path)
    withheld = tmp_path / "store"
    withheld.mkdir()
    value = allowlist.instantiate(
        shipped, hypothesis=_hypothesis(), counted_object=stub, scratch_dir=scratch, withheld_roots=[withheld]
    )
    assert set(value.exec_paths) == {stub, target}
    assert allowlist.check_instantiation(value, shipped) is True
    with Substrate.open(tmp_path / "substrate.sqlite") as sub:
        digest = allowlist.record(sub, value)
        (tmp_path / "Python.framework").rename(tmp_path / "moved.framework")
        assert not Path(stub).exists()
        assert not Path(target).exists()
        stored = allowlist.read(sub, digest)
        assert stored == value
        assert stored.withheld_roots == (str(withheld),)
        assert allowlist.check_instantiation(stored, shipped) is True


def test_a_derived_re_exec_target_does_not_buy_room_for_an_unrelated_executable(shipped, scratch, tmp_path):
    stub, target = _framework(tmp_path)
    value = allowlist.instantiate(shipped, hypothesis=_hypothesis(), counted_object=stub, scratch_dir=scratch)
    smuggled = tuple(sorted({stub, target, "/bin/sh"}))
    tampered = dataclasses.replace(
        value, exec_paths=smuggled, profile_hash=blob_hash(allowlist.profile_bytes(smuggled))
    )
    with pytest.raises(allowlist.AllowListRefused, match="2 executables against 1"):
        allowlist.check_instantiation(tampered, shipped)


def test_the_profile_names_both_halves_of_a_framework_interpreter(shipped, scratch, tmp_path):
    stub, target = _framework(tmp_path)
    value = allowlist.instantiate(shipped, hypothesis=_hypothesis(), counted_object=stub, scratch_dir=scratch)
    rendered = allowlist.profile_bytes(value.exec_paths)
    assert f'(literal "{stub}")'.encode() in rendered
    assert f'(literal "{target}")'.encode() in rendered


def test_a_script_in_a_framework_bin_derives_no_re_exec_target(tmp_path):
    stub, _ = _framework(tmp_path)
    script = Path(stub).parent / "python3.14-config"
    script.write_text("#!/bin/sh\nexit 0\n")
    script.chmod(0o755)
    assert allowlist.reexec_target(str(script)) is None


def test_the_binding_check_refuses_a_framework_script_with_an_underived_app(shipped, scratch, tmp_path):
    stub, target = _framework(tmp_path)
    script = Path(stub).parent / "python3.14-config"
    script.write_text("#!/bin/sh\nexit 0\n")
    script.chmod(0o755)
    withheld = tmp_path / "store"
    withheld.mkdir()
    bound = {
        "hypothesis": _hypothesis(),
        "counted_object": script,
        "scratch_dir": scratch,
        "withheld_roots": [withheld],
    }
    value = allowlist.instantiate(shipped, **bound)
    assert value.exec_paths == (str(script),)
    assert allowlist.check_binding(value, shipped, **bound) is True
    paths = tuple(sorted({str(script), target}))
    tampered = dataclasses.replace(
        value, exec_paths=paths, profile_hash=blob_hash(allowlist.profile_bytes(paths, value.withheld_roots))
    )
    assert allowlist.check_instantiation(tampered, shipped) is True
    with pytest.raises(allowlist.AllowListRefused, match="allow-list differs from the one the gate derives"):
        allowlist.check_binding(tampered, shipped, **bound)


def test_the_binding_check_refuses_a_record_whose_framework_app_is_absent(shipped, scratch, tmp_path):
    stub, target = _framework(tmp_path)
    withheld = tmp_path / "store"
    withheld.mkdir()
    bound = {"hypothesis": _hypothesis(), "counted_object": stub, "scratch_dir": scratch, "withheld_roots": [withheld]}
    value = allowlist.instantiate(shipped, **bound)
    assert set(value.exec_paths) == {stub, target}
    assert allowlist.check_binding(value, shipped, **bound) is True
    Path(target).rename(tmp_path / "moved.app")
    assert not Path(target).exists()
    assert allowlist.check_instantiation(value, shipped) is True
    with pytest.raises(allowlist.AllowListRefused, match="exec_paths"):
        allowlist.check_binding(value, shipped, **bound)


def test_the_binding_check_refuses_a_record_whose_framework_app_is_not_executable(shipped, scratch, tmp_path):
    stub, target = _framework(tmp_path)
    withheld = tmp_path / "store"
    withheld.mkdir()
    bound = {"hypothesis": _hypothesis(), "counted_object": stub, "scratch_dir": scratch, "withheld_roots": [withheld]}
    value = allowlist.instantiate(shipped, **bound)
    assert set(value.exec_paths) == {stub, target}
    assert allowlist.check_binding(value, shipped, **bound) is True
    Path(target).chmod(0o644)
    assert not os.access(target, os.X_OK)
    assert allowlist.check_instantiation(value, shipped) is True
    with pytest.raises(allowlist.AllowListRefused, match="exec_paths"):
        allowlist.check_binding(value, shipped, **bound)


def test_withheld_roots_are_resolved_denied_after_the_read_grant_and_addressed(shipped, scratch, tmp_path):
    secret = tmp_path / "store"
    secret.mkdir()
    value = allowlist.instantiate(
        shipped, hypothesis=_hypothesis(), counted_object=BACKEND, scratch_dir=scratch, withheld_roots=[secret, secret]
    )
    resolved = os.path.realpath(secret)
    assert value.withheld_roots == (resolved,)
    text = allowlist.profile_bytes(value.exec_paths, value.withheld_roots).decode()
    grant, deny = (
        text.index('(allow file-read* (subpath "/"))'),
        text.index(f'(deny file-read* (subpath "{resolved}"))'),
    )
    assert grant < deny
    assert value.profile_hash == blob_hash(text.encode())
    assert allowlist.check_instantiation(value, shipped) is True


def test_no_withheld_roots_leaves_the_profile_bytes_unchanged(instance):
    assert b"deny file-read*" not in allowlist.profile_bytes(instance.exec_paths)
    assert instance.withheld_roots == ()


@pytest.mark.parametrize("covers", ["scratch", "executable", "root"])
def test_a_withheld_root_that_would_blind_the_method_is_refused(shipped, scratch, covers):
    root = {"scratch": scratch.parent, "executable": Path(BACKEND).parent, "root": Path(os.sep)}[covers]
    with pytest.raises(allowlist.AllowListRefused, match="withheld root"):
        allowlist.instantiate(
            shipped, hypothesis=_hypothesis(), counted_object=BACKEND, scratch_dir=scratch, withheld_roots=[root]
        )


def test_a_withheld_root_the_profile_cannot_name_is_refused(shipped, scratch, tmp_path):
    hostile = tmp_path / 'qu"ote'
    with pytest.raises(allowlist.AllowListRefused, match="sandbox profile literal"):
        allowlist.instantiate(
            shipped, hypothesis=_hypothesis(), counted_object=BACKEND, scratch_dir=scratch, withheld_roots=[hostile]
        )


def test_dropping_a_withheld_root_from_a_record_is_refused_by_the_binding(shipped, scratch, tmp_path):
    secret = tmp_path / "store"
    secret.mkdir()
    kwargs = {"hypothesis": _hypothesis(), "counted_object": BACKEND, "scratch_dir": scratch}
    held = allowlist.instantiate(shipped, withheld_roots=[secret], **kwargs)
    bare = allowlist.instantiate(shipped, **kwargs)
    assert allowlist.check_binding(held, shipped, withheld_roots=[secret], **kwargs) is True
    with pytest.raises(allowlist.AllowListRefused, match="differs from the one the gate derives"):
        allowlist.check_binding(bare, shipped, withheld_roots=[secret], **kwargs)
