import re

import pytest
from _ci_workflow import (
    LINUX_CACHE_ACTION,
    LINUX_CACHE_EXPORT,
    LINUX_CACHE_IMPORT,
    LINUX_CACHE_INPUTS,
    LINUX_CACHE_KEY,
    LINUX_CACHE_PATHS,
    LINUX_CACHE_PREPARE,
    LINUX_CACHE_RESTORE,
    LINUX_CACHE_SAVE,
    WORKFLOW,
    _assert_ci_lanes,
    _assert_container_lane,
    _step,
    _step_body,
    _steps,
)


def _cache_paths(step):
    match = re.search(r"(?m)^          path: \|\n((?:            .*\n)+)", step)
    assert match, "cache step has no bounded path list"
    return tuple(line.strip() for line in match.group(1).splitlines())


def _assert_linux_prerequisite_cache(text):
    job = text.split("  container:\n", 1)[1].split("  check:\n", 1)[0]
    steps = _steps(job)
    order = (
        "Sync Linux locked environment",
        LINUX_CACHE_KEY,
        LINUX_CACHE_RESTORE,
        LINUX_CACHE_IMPORT,
        LINUX_CACHE_PREPARE,
        "Linux container gates",
        "Linux adapter types",
        LINUX_CACHE_EXPORT,
        LINUX_CACHE_SAVE,
    )
    for name in order:
        assert name in steps, f"CI has no {name.lower()} step"
    assert [steps[name] for name in order] == sorted(steps[name] for name in order)

    key = _step(job, LINUX_CACHE_KEY)
    assert "id: linux-prerequisite-key" in key
    assert "CAIRN_CACHE_RUNNER_OS: ${{ runner.os }}" in key
    assert "CAIRN_CACHE_RUNNER_ARCH: ${{ runner.arch }}" in key
    key_body = _step_body(job, LINUX_CACHE_KEY)
    assert "for name in inputs:" in key_body
    assert "Path(name).read_bytes()" in key_body
    assert "identity_hash = inputs_hash.hexdigest()" in key_body
    assert "os.environ['CAIRN_CACHE_RUNNER_OS']" in key_body
    assert "os.environ['CAIRN_CACHE_RUNNER_ARCH']" in key_body
    for path in LINUX_CACHE_INPUTS:
        assert f'"{path}"' in key_body
    for field in ("ServerVersion", "Driver", "DriverStatus"):
        assert f'info["{field}"]' in key_body
    assert '"server_version": info["ServerVersion"]' in key_body
    assert '"driver": info["Driver"]' in key_body
    assert '"driver_status": info["DriverStatus"]' in key_body
    assert "hashlib.sha256(backend)" in key_body
    assert "{docker_hash}-{identity_hash}" in key_body
    assert '["docker", "info", "--format", "{{json .}}"]' in key_body
    assert "key={key}" in key_body

    cache_key = "key: ${{ steps.linux-prerequisite-key.outputs.key }}"
    restore = _step(job, LINUX_CACHE_RESTORE)
    assert f"actions/cache/restore@{LINUX_CACHE_ACTION}" in restore
    assert "id: linux-prerequisite-cache" in restore
    assert cache_key in restore
    assert "restore-keys:" not in restore
    assert _cache_paths(restore) == LINUX_CACHE_PATHS

    cache_hit = "steps.linux-prerequisite-cache.outputs.cache-hit"
    import_step = _step(job, LINUX_CACHE_IMPORT)
    assert f"if: {cache_hit} == 'true'" in import_step
    assert (
        "run: uv run python tests/_linux_dependencies.py --cache "
        '"$RUNNER_TEMP/cairn-linux-prerequisites/dependencies" --import-archive '
        '"$RUNNER_TEMP/cairn-linux-prerequisites/image.tar"'
    ) in import_step
    assert "--export-archive" not in import_step

    prepare = _step(job, LINUX_CACHE_PREPARE)
    assert f"if: {cache_hit} != 'true'" in prepare
    assert (
        'run: uv run python tests/_linux_dependencies.py --cache "$RUNNER_TEMP/cairn-linux-prerequisites/dependencies"'
    ) in prepare
    assert "--import-archive" not in prepare
    assert "--export-archive" not in prepare

    gates = _step(job, "Linux container gates")
    assert "if:" not in gates
    assert "PYTEST_DEBUG_TEMPROOT: ${{ runner.temp }}" in gates
    assert ("CAIRN_LINUX_DEPENDENCY_CACHE: ${{ runner.temp }}/cairn-linux-prerequisites/dependencies") in gates
    types = _step(job, "Linux adapter types")
    assert "if:" not in types

    writer = (
        "if: success() && matrix.lane == 'container' && github.event_name == 'push' "
        "&& github.ref == 'refs/heads/main' && "
        f"{cache_hit} != 'true'"
    )
    export = _step(job, LINUX_CACHE_EXPORT)
    assert writer in export
    assert (
        "run: uv run python tests/_linux_dependencies.py --cache "
        '"$RUNNER_TEMP/cairn-linux-prerequisites/dependencies" --export-archive '
        '"$RUNNER_TEMP/cairn-linux-prerequisites/image.tar"'
    ) in export
    save = _step(job, LINUX_CACHE_SAVE)
    assert writer in save
    assert f"actions/cache/save@{LINUX_CACHE_ACTION}" in save
    assert cache_key in save
    assert _cache_paths(save) == LINUX_CACHE_PATHS
    assert job.count("actions/cache/save@") == 1
    assert job.count("--export-archive") == 1

    _assert_ci_lanes(text)
    _assert_container_lane(text)


def test_ci_reuses_only_identity_bound_linux_prerequisites_after_validation():
    _assert_linux_prerequisite_cache(WORKFLOW.read_text())


@pytest.mark.parametrize(
    "removed",
    [*LINUX_CACHE_INPUTS, 'info["ServerVersion"]', 'info["Driver"]', 'info["DriverStatus"]'],
)
def test_linux_prerequisite_cache_contract_refuses_incomplete_identity(removed):
    text = WORKFLOW.read_text()
    key = _step(text, LINUX_CACHE_KEY)
    assert removed in key
    with pytest.raises(AssertionError):
        _assert_linux_prerequisite_cache(text.replace(key, key.replace(removed, "", 1), 1))


@pytest.mark.parametrize("step_name", [LINUX_CACHE_EXPORT, LINUX_CACHE_SAVE])
def test_linux_prerequisite_cache_contract_refuses_pull_request_publication(step_name):
    text = WORKFLOW.read_text()
    step = _step(text, step_name)
    assert "github.event_name == 'push'" in step
    broken = text.replace(
        step, step.replace("github.event_name == 'push'", "github.event_name == 'pull_request'", 1), 1
    )
    with pytest.raises(AssertionError):
        _assert_linux_prerequisite_cache(broken)


def test_linux_prerequisite_cache_contract_refuses_unvalidated_hits():
    text = WORKFLOW.read_text()
    import_step = _step(text, LINUX_CACHE_IMPORT)
    assert "--import-archive" in import_step
    broken = text.replace(import_step, import_step.replace("--import-archive", "--export-archive", 1), 1)
    with pytest.raises(AssertionError):
        _assert_linux_prerequisite_cache(broken)


def test_linux_prerequisite_cache_contract_refuses_restore_key_fallbacks():
    text = WORKFLOW.read_text()
    restore = _step(text, LINUX_CACHE_RESTORE)
    assert "restore-keys:" not in restore
    broken = text.replace(
        restore, restore.replace("key: ", "restore-keys: cairn-linux-prerequisites-\n          key: ", 1), 1
    )
    with pytest.raises(AssertionError, match="restore-keys"):
        _assert_linux_prerequisite_cache(broken)


def test_linux_prerequisite_cache_contract_refuses_broad_paths():
    text = WORKFLOW.read_text()
    restore = _step(text, LINUX_CACHE_RESTORE)
    assert LINUX_CACHE_PATHS[0] in restore
    broken = text.replace(
        restore,
        restore.replace(LINUX_CACHE_PATHS[0], "${{ runner.temp }}/cairn-linux-prerequisites", 1),
        1,
    )
    with pytest.raises(AssertionError):
        _assert_linux_prerequisite_cache(broken)
