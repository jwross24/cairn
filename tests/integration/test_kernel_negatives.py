import gzip
import hashlib
import json
import shutil
from pathlib import Path

import pytest
import test_container_statement_hash as linux_tests

from cairn import challenge, container, log, solutionchecks

lg = log.get("test")
linux_bundle = linux_tests.linux_bundle
linux_image = linux_tests.linux_image
linux_dependencies = linux_tests.linux_dependencies
linux_project = linux_tests.linux_project
linux_prepared = linux_tests.linux_prepared

VECTORS = Path(__file__).resolve().parents[1] / "vectors" / "kernel_negatives"
MANIFEST = json.loads((VECTORS / "manifest.json").read_text())
ENTRIES = MANIFEST["entries"]
EXPORT_LIBRARY = "/home/cairn/comparator/.lake/packages/lean4export/.lake/build/lib/lean"
COMPARATOR_SOURCE = "/home/cairn/comparator/Main.lean"
NANODA = "/usr/local/bin/nanoda_bin"
GUEST = "/vectors"
# nanoda exits nonzero on these without having judged the proof.
NOT_A_VERDICT = ("Declined", "unpermitted axiom", "This program expects")
NANODA_CONFIG = {
    "use_stdin": False,
    "unpermitted_axiom_hard_error": True,
    "num_threads": 4,
    "nat_extension": True,
    "string_extension": True,
}


@pytest.fixture(scope="module")
def unpacked(tmp_path_factory, linux_bundle):
    root = tmp_path_factory.mktemp("kernel-negatives")
    shutil.copy(VECTORS / "probe.lean", root / "probe.lean")
    for entry in ENTRIES:
        raw = gzip.decompress((VECTORS / f"{entry['name']}.ndjson.gz").read_bytes())
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
        (root / f"{entry['name']}.ndjson").write_bytes(raw)
        config = {
            **NANODA_CONFIG,
            "export_file_path": f"{GUEST}/{entry['name']}.ndjson",
            "permitted_axioms": list(linux_bundle.lean["permitted_axioms"]),
        }
        (root / f"{entry['name']}.json").write_text(json.dumps(config))
    return root


def in_image(image, root, argv):
    return container.run(
        image.context,
        image.image_id,
        argv,
        user=container.host_user(),
        mounts=((root, GUEST, "readonly=true"),),
        workdir=GUEST,
        env=(("HOME", "/work"), ("LEAN_PATH", EXPORT_LIBRARY)),
        timeout_s=300,
    )


def official(bundle, image, root, name):
    toolchain = bundle.lean["toolchain"]
    return in_image(image, root, ["lean", f"+{toolchain}", "--run", "probe.lean", f"{name}.ndjson"])


def nanoda(image, root, name):
    return in_image(image, root, [NANODA, f"{GUEST}/{name}.json"])


@pytest.mark.timeout(600)
@pytest.mark.parametrize("entry", ENTRIES, ids=lambda entry: entry["name"])
def test_the_pinned_official_kernel_returns_the_recorded_verdict(linux_bundle, linux_image, unpacked, entry):
    result = official(linux_bundle, linux_image, unpacked, entry["name"])
    lg.info("official_kernel", name=entry["name"], rc=result.rc, stdout=result.stdout[-300:])
    if entry["official"] == "accept":
        assert (result.rc, result.stdout[:6]) == (0, "ACCEPT"), result.stdout + result.stderr
    else:
        assert (result.rc, result.stdout[:6]) == (1, "REJECT"), result.stdout + result.stderr


@pytest.mark.timeout(600)
@pytest.mark.parametrize("entry", ENTRIES, ids=lambda entry: entry["name"])
def test_the_pinned_nanoda_returns_the_recorded_verdict(linux_image, unpacked, entry):
    result = nanoda(linux_image, unpacked, entry["name"])
    lg.info("nanoda_kernel", name=entry["name"], rc=result.rc, stderr=result.stderr[-300:])
    if entry["nanoda"] == "accept":
        assert result.rc == 0, result.stdout + result.stderr
    else:
        output = result.stdout + result.stderr
        assert result.rc != 0, output
        assert not any(marker in output for marker in NOT_A_VERDICT), output


@pytest.mark.timeout(1800)
def test_a_kernel_exploit_submitted_as_a_solution_stops_at_the_pinned_kernel(
    linux_bundle, linux_image, linux_prepared, tmp_path
):
    statement, prepared = linux_prepared
    source = linux_bundle.challenge_prelude + (VECTORS / "exploit_solution.lean").read_bytes()
    compilation = solutionchecks.compile_container(
        linux_bundle,
        linux_image,
        statement,
        challenge.Submission(solution_module=source, formal_statement_hash=prepared.formal_statement_hash),
        ("challenge_curve",),
        prepared=prepared,
        root=tmp_path / "candidate",
    )
    result = compilation.result
    lg.info("exploit_solution", rc=result.rc, stdout=result.stdout[-600:])
    assert result.rc != 0
    assert "kernel error" in result.stdout, result.stdout + result.stderr


def test_no_invalid_proof_is_recorded_as_passing_both_kernels():
    both = [e["name"] for e in ENTRIES if e["invalid"] and e["official"] == "accept" and e["nanoda"] == "accept"]
    assert both == []


def test_each_kernel_has_a_valid_control_it_accepts():
    controls = [e for e in ENTRIES if not e["invalid"]]
    assert controls
    assert all(e["official"] == "accept" and e["nanoda"] == "accept" for e in controls)


def test_an_invalid_input_nanoda_accepts_is_named_with_its_open_issue():
    accepted = {e["name"]: e.get("open_issue") for e in ENTRIES if e["invalid"] and e["nanoda"] == "accept"}
    assert all(accepted.values()), accepted


@pytest.mark.timeout(600)
def test_the_nanoda_config_is_the_one_the_comparator_writes(linux_image, unpacked):
    result = in_image(linux_image, unpacked, ["cat", COMPARATOR_SOURCE])
    assert result.rc == 0, result.stderr
    for key, value in NANODA_CONFIG.items():
        rendered = json.dumps(value) if not isinstance(value, bool) else str(value).lower()
        assert f'("{key}", {rendered})' in result.stdout, key
