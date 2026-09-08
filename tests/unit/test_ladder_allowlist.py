import copy
import dataclasses
import json
import os
import sys
from pathlib import Path

import pytest

from cairn import allowlist, bundle
from cairn.substrate import blob_hash

BACKEND = os.path.realpath(sys.executable)


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
def scratch(tmp_path):
    path = tmp_path / "scratch"
    path.mkdir()
    return path


@pytest.fixture
def instance(shipped, scratch):
    return allowlist.instantiate(shipped, hypothesis=_hypothesis(), counted_object=BACKEND, scratch_dir=scratch)


def _planted(pinned_bundle, tmp_path, obj, name="planted"):
    source = tmp_path / name
    source.mkdir()
    for path in (bundle.REPO_ROOT / "bundle").glob("*.json"):
        (source / path.name).write_text(path.read_text())
    (source / "allow_lists.json").write_text(json.dumps(obj))
    return bundle.GateBundle.open(*pinned_bundle(name=name, src=source))


def test_module_defined_public_api_is_closed():
    public = {
        name
        for name, value in vars(allowlist).items()
        if not name.startswith("_") and callable(value) and getattr(value, "__module__", None) == allowlist.__name__
    }
    assert public == {
        "AllowListError",
        "AllowListRefused",
        "AllowList",
        "template",
        "declared_backends",
        "mechanism_for",
        "profile_bytes",
        "instantiate",
        "check_instantiation",
        "write_profile",
        "argv_for",
        "detect_violation",
        "record",
        "read",
    }
    assert allowlist.BUNDLE_KIND == "allow_lists"
    assert allowlist.LADDER_METHOD == "ladder_method"
    assert allowlist.MECHANISMS == ("sandbox-exec",)
    assert allowlist.SANDBOX_EXEC == "/usr/bin/sandbox-exec"


def test_the_shipped_template_is_the_bundle_object_field_for_field(shipped):
    entry = allowlist.template(shipped)
    shipped_source = json.loads((bundle.REPO_ROOT / "bundle" / "allow_lists.json").read_text())
    assert entry == shipped_source["templates"][allowlist.LADDER_METHOD]
    assert entry["network_egress"] is False
    assert entry["process_spawn"] == "declared_backends_only"
    assert entry["writable_roots"] == ["scratch"]
    assert entry["counted_object_slot"] == "counted_object"
    assert sorted(entry["backend_catalog"]) == ["counted_object", "gmpy2", "gp"]


def test_an_absent_template_fails_closed(shipped):
    with pytest.raises(allowlist.AllowListRefused, match="carries no allow_lists template 'skeptic'"):
        allowlist.template(shipped, "skeptic")


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda o: o.update(version=2), "version 2"),
        (lambda o: o.pop("provenance"), "version, templates and provenance"),
        (lambda o: o["templates"]["ladder_method"].pop("mechanisms"), "must carry exactly"),
        (lambda o: o["templates"]["ladder_method"].update(extra=1), "must carry exactly"),
        (lambda o: o["templates"]["ladder_method"].update(network_egress=True), "permits network egress"),
        (lambda o: o["templates"]["ladder_method"].update(process_spawn="any"), "process_spawn"),
        (
            lambda o: o["templates"]["ladder_method"].update(writable_roots=["scratch", "artifacts"]),
            "only writable root",
        ),
        (lambda o: o["templates"]["ladder_method"].update(readable_roots=["scratch"]), "readable roots"),
        (lambda o: o["templates"]["ladder_method"].update(mechanisms=["seatbelt"]), "outside"),
        (lambda o: o["templates"]["ladder_method"].update(mechanisms=[]), "outside"),
        (
            lambda o: o["templates"]["ladder_method"].update(
                mechanisms=["sandbox-exec", "sandbox-exec"],
            ),
            "repeats a mechanism",
        ),
        (
            lambda o: o["templates"]["ladder_method"]["backend_catalog"].update(
                gp={"counted": True, "kind": "process"}
            ),
            "must count exactly",
        ),
        (
            lambda o: o["templates"]["ladder_method"]["backend_catalog"].__setitem__(
                "counted_object", {"counted": True, "kind": "in_process"}
            ),
            "must be a process backend",
        ),
        (
            lambda o: o["templates"]["ladder_method"]["backend_catalog"].update(
                GP={"counted": False, "kind": "process"}
            ),
            "outside",
        ),
        (
            lambda o: o["templates"]["ladder_method"]["backend_catalog"].update(z={"counted": 1, "kind": "process"}),
            "counted must be a boolean",
        ),
        (
            lambda o: o["templates"]["ladder_method"]["backend_catalog"].update(z={"counted": False, "kind": "thread"}),
            "kind must be",
        ),
        (lambda o: o["templates"]["ladder_method"].update(backend_catalog={}), "nonempty mapping"),
    ],
)
def test_a_malformed_template_fails_closed(shipped, monkeypatch, mutate, match):
    obj = copy.deepcopy(shipped.object(allowlist.BUNDLE_KIND))
    mutate(obj)
    monkeypatch.setitem(shipped._decoded, allowlist.BUNDLE_KIND, obj)
    with pytest.raises(allowlist.AllowListRefused, match=match):
        allowlist.template(shipped)


def test_a_hypothesis_declaring_nothing_declares_no_backend(shipped):
    assert allowlist.declared_backends(_hypothesis(), allowlist.template(shipped)) == ()


def test_a_declaration_is_read_from_the_hypothesis_object_alone(shipped):
    entry = allowlist.template(shipped)
    assert allowlist.declared_backends(_hypothesis(uncounted_backends="gmpy2"), entry) == ("gmpy2",)
    assert allowlist.declared_backends(_hypothesis(uncounted_backends="gmpy2,gp"), entry) == ("gmpy2", "gp")


@pytest.mark.parametrize(
    ("declaration", "match"),
    [
        ("", "nonempty string"),
        ("gp,gmpy2", "strictly sorted"),
        ("gp,gp", "strictly sorted"),
        ("gmpy2, gp", "comma-separated"),
        ("GP", "comma-separated"),
        ("gp,", "comma-separated"),
        ("flint", "outside the template catalog"),
        ("counted_object", "not declarable as uncounted"),
    ],
)
def test_a_malformed_declaration_fails_closed(shipped, declaration, match):
    with pytest.raises(allowlist.AllowListRefused, match=match):
        allowlist.declared_backends(_hypothesis(uncounted_backends=declaration), allowlist.template(shipped))


def test_a_hypothesis_with_no_claimed_map_fails_closed(shipped):
    with pytest.raises(allowlist.AllowListRefused, match="no claimed map"):
        allowlist.declared_backends({"target_family": "toy_curve"}, allowlist.template(shipped))


def test_the_instantiation_matches_the_template_it_came_from(shipped, instance):
    entry = allowlist.template(shipped)
    assert instance.template_name == allowlist.LADDER_METHOD
    assert instance.template_hash == blob_hash(shipped.raw(allowlist.BUNDLE_KIND))
    assert instance.bundle_hash == shipped.hash
    assert instance.network_egress == entry["network_egress"]
    assert instance.mechanism in entry["mechanisms"]
    assert instance.exec_paths == (BACKEND,)
    assert instance.counted_object == BACKEND
    assert instance.declared_backends == ()
    assert instance.profile_hash == blob_hash(allowlist.profile_bytes(instance.exec_paths))
    assert allowlist.check_instantiation(instance, shipped) is True


def test_the_instantiation_is_content_addressed_by_its_own_fields(shipped, instance):
    assert instance.hash == allowlist.AllowList(**instance.as_dict()).hash
    other = dataclasses.replace(instance, counted_object="/usr/bin/true")
    assert other.hash != instance.hash


def test_an_in_process_declaration_needs_no_path_and_a_process_one_does(shipped, scratch):
    value = allowlist.instantiate(
        shipped, hypothesis=_hypothesis(uncounted_backends="gmpy2"), counted_object=BACKEND, scratch_dir=scratch
    )
    assert value.declared_backends == ("gmpy2",)
    assert value.exec_paths == (BACKEND,)
    with pytest.raises(allowlist.AllowListRefused, match="do not match the declared process backends"):
        allowlist.instantiate(
            shipped, hypothesis=_hypothesis(uncounted_backends="gp"), counted_object=BACKEND, scratch_dir=scratch
        )
    with pytest.raises(allowlist.AllowListRefused, match="do not match the declared process backends"):
        allowlist.instantiate(
            shipped,
            hypothesis=_hypothesis(),
            counted_object=BACKEND,
            scratch_dir=scratch,
            backend_paths={"gp": BACKEND},
        )


def test_a_declared_process_backend_joins_the_exec_paths(shipped, scratch, tmp_path):
    second = tmp_path / "gp-stand-in"
    second.write_text("#!/bin/sh\nexit 0\n")
    second.chmod(0o755)
    value = allowlist.instantiate(
        shipped,
        hypothesis=_hypothesis(uncounted_backends="gp"),
        counted_object=BACKEND,
        scratch_dir=scratch,
        backend_paths={"gp": second},
    )
    assert value.exec_paths == tuple(sorted({BACKEND, os.path.realpath(second)}))
    assert allowlist.check_instantiation(value, shipped) is True


def test_every_path_in_the_instantiation_is_resolved(shipped, tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    value = allowlist.instantiate(shipped, hypothesis=_hypothesis(), counted_object=sys.executable, scratch_dir=link)
    assert value.writable_root == os.path.realpath(real)
    assert value.counted_object == BACKEND
    assert str(link) not in allowlist.profile_bytes(value.exec_paths).decode()


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"counted_object": "/nonexistent/counted"}, "not an executable file"),
        ({"scratch_dir": "/nonexistent/scratch"}, "not a directory"),
    ],
)
def test_an_unusable_path_fails_closed(shipped, scratch, kwargs, match):
    base = {"hypothesis": _hypothesis(), "counted_object": BACKEND, "scratch_dir": scratch}
    with pytest.raises(allowlist.AllowListRefused, match=match):
        allowlist.instantiate(shipped, **{**base, **kwargs})


def test_a_path_a_profile_literal_cannot_name_fails_closed(shipped, scratch, tmp_path):
    hostile = tmp_path / 'quo"te'
    hostile.mkdir()
    with pytest.raises(allowlist.AllowListRefused, match="sandbox profile literal"):
        allowlist.instantiate(shipped, hypothesis=_hypothesis(), counted_object=BACKEND, scratch_dir=hostile)


def test_the_profile_denies_by_default_and_allows_only_the_named_paths(instance):
    text = allowlist.profile_bytes(instance.exec_paths).decode()
    assert "(deny default)" in text
    assert f'(literal "{BACKEND}")' in text
    assert '(allow file-write* (subpath (param "SCRATCH")))' in text
    assert "network" not in text
    assert text.count("(allow ") == 6


def test_the_argv_wraps_the_method_in_the_mechanism(instance, tmp_path):
    profile = tmp_path / "method.sb"
    argv = allowlist.argv_for(instance, profile, [BACKEND, "-m", "cairn.skills.toy_curve"])
    assert argv[:5] == [
        allowlist.SANDBOX_EXEC,
        "-D",
        f"SCRATCH={instance.writable_root}",
        "-f",
        str(profile),
    ]
    assert argv[5:] == [BACKEND, "-m", "cairn.skills.toy_curve"]


def test_an_argv0_outside_the_exec_paths_is_refused(instance, tmp_path):
    with pytest.raises(allowlist.AllowListRefused, match="outside the allow-list exec paths"):
        allowlist.argv_for(instance, tmp_path / "method.sb", ["/bin/echo", "hi"])


def test_the_written_profile_is_read_only_and_addressed_by_the_allow_list(instance, tmp_path):
    path = allowlist.write_profile(instance, tmp_path / "method.sb")
    assert blob_hash(path.read_bytes()) == instance.profile_hash
    assert Path(path).stat().st_mode & 0o222 == 0


def test_a_profile_that_does_not_address_its_allow_list_is_refused(instance, tmp_path):
    tampered = dataclasses.replace(instance, profile_hash=blob_hash(b"other"))
    with pytest.raises(allowlist.AllowListRefused, match="does not match the allow-list profile hash"):
        allowlist.write_profile(tampered, tmp_path / "method.sb")


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("template_name", "other", "names template"),
        ("template_hash", blob_hash(b"other"), "template hash differs"),
        ("bundle_hash", "0" * 64, "bundle hash differs"),
        ("network_egress", True, "network egress differs"),
        ("mechanism", "seatbelt", "outside the template"),
        ("declared_backends", ("flint",), "does not offer as uncounted"),
        ("declared_backends", ("counted_object",), "does not offer as uncounted"),
        ("profile_hash", blob_hash(b"other"), "does not address its own exec paths"),
        ("exec_paths", (BACKEND, "/bin/echo"), "does not address its own exec paths"),
    ],
)
def test_an_instantiation_that_drifts_from_its_template_is_refused(shipped, instance, field, value, match):
    tampered = dataclasses.replace(instance, **{field: value})
    with pytest.raises(allowlist.AllowListRefused, match=match):
        allowlist.check_instantiation(tampered, shipped)


def test_an_instantiation_permitting_more_executables_than_the_template_allows_is_refused(shipped, instance):
    paths = (BACKEND, "/bin/echo")
    tampered = dataclasses.replace(instance, exec_paths=paths, profile_hash=blob_hash(allowlist.profile_bytes(paths)))
    with pytest.raises(allowlist.AllowListRefused, match="permits 2 executables against 1"):
        allowlist.check_instantiation(tampered, shipped)


def test_an_unresolved_path_in_an_instantiation_is_refused(shipped, instance):
    tampered = dataclasses.replace(instance, writable_root="/var")
    with pytest.raises(allowlist.AllowListRefused, match="is unresolved"):
        allowlist.check_instantiation(tampered, shipped)


def test_a_platform_with_no_probed_mechanism_refuses_rather_than_running_unenforced(shipped):
    with pytest.raises(allowlist.AllowListRefused, match="is available on 'win32'"):
        allowlist.mechanism_for(allowlist.template(shipped), platform="win32")


def test_editing_the_template_moves_the_bundle_hash(shipped, pinned_bundle, tmp_path):
    obj = copy.deepcopy(shipped.object(allowlist.BUNDLE_KIND))
    obj["templates"]["ladder_method"]["network_egress"] = True
    planted = _planted(pinned_bundle, tmp_path, obj)
    assert planted.hash != shipped.hash
    with pytest.raises(allowlist.AllowListRefused, match="permits network egress"):
        allowlist.template(planted)


@pytest.mark.parametrize(
    ("exit_status", "stderr", "expected"),
    [
        (0, b"Operation not permitted", None),
        (9, b"", None),
        (9, b"CHILD_ERR PermissionError: [Errno 1] Operation not permitted\n", "network_egress"),
        (9, b"PermissionError: [Errno 1] Operation not permitted: '/bin/echo'\n", "undeclared_exec"),
        (1, b"PermissionError: [Errno 1] Operation not permitted: '/etc/planted.txt'\n", "outside_write"),
    ],
)
def test_a_named_violation_is_read_from_the_child_report(instance, exit_status, stderr, expected):
    assert allowlist.detect_violation(exit_status, stderr, instance) == expected


def test_a_denial_naming_only_permitted_paths_names_no_violation(instance):
    stderr = f"Operation not permitted: '{instance.writable_root}/out.json'".encode()
    assert allowlist.detect_violation(9, stderr, instance) is None
