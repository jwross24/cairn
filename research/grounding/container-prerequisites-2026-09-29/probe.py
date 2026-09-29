import argparse
import hashlib
import importlib.util
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from cairn import bundle, container, lean

REPO_ROOT = Path(__file__).resolve().parents[3]
DEPENDENCY_SPEC = importlib.util.spec_from_file_location(
    "_linux_dependencies", REPO_ROOT / "tests" / "_linux_dependencies.py"
)
dependencies = importlib.util.module_from_spec(DEPENDENCY_SPEC)
sys.modules[DEPENDENCY_SPEC.name] = dependencies
DEPENDENCY_SPEC.loader.exec_module(dependencies)

REFUSAL_EXIT = 42
REPORT_DIR = REPO_ROOT / "research" / "grounding" / "container-prerequisites-2026-09-29"


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def digest_json(value):
    return digest_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def digest_file(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def build_gate(root):
    root.mkdir(parents=True, exist_ok=True)
    database, pin = root / "bundle.sqlite", root / "bundle.pin"
    bundle.build(lean.REPO_ROOT / "bundle", database)
    bundle.write_pin(database, pin)
    return bundle.GateBundle.open(database, pin)


def inspect_image(ctx, reference):
    result = container.run_docker(
        ctx,
        "image",
        "inspect",
        "--format",
        "{{.Id}}|{{.Os}}/{{.Architecture}}|{{.Size}}|{{json .RepoTags}}",
        reference,
        timeout_s=60,
    )
    if result.rc != 0:
        raise RuntimeError(f"docker inspect failed for {reference}: rc={result.rc} {result.stderr[-1000:]}")
    image_id, platform_name, size, tags = result.stdout.strip().split("|", 3)
    return {
        "image_id": image_id,
        "platform": platform_name,
        "size_bytes": int(size),
        "repo_tags": json.loads(tags) or [],
        "elapsed_seconds": result.wall_ms / 1000,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr,
    }


def file_tree_bytes(root):
    return sum(path.stat().st_size for path in Path(root).rglob("*") if path.is_file() and not path.is_symlink())


def inventory_differences(expected, actual):
    return {
        path: {"expected": expected.get(path), "actual": actual.get(path)}
        for path in sorted(set(expected) | set(actual))
        if expected.get(path) != actual.get(path)
    }


def restore_inventory_modes(root, inventory):
    root = Path(root)
    directories = []
    restored = 0
    for relative, row in inventory.items():
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts or not relative_path.parts:
            raise RuntimeError(f"dependency cache inventory path is invalid: {relative}")
        path = root / relative_path
        mode = path.lstat().st_mode
        try:
            resolved = path.resolve(strict=True)
        except (OSError, RuntimeError):
            raise RuntimeError(f"dependency cache inventory path is unavailable: {relative}") from None
        if not resolved.is_relative_to(root.resolve()):
            raise RuntimeError(f"dependency cache inventory path escapes its root: {relative}")
        if row[0] == "file":
            if not stat.S_ISREG(mode) or row[1] & ~0o777:
                raise RuntimeError(f"dependency cache mode metadata is invalid: {relative}")
            path.chmod(row[1])
            restored += 1
        elif row[0] == "directory":
            if not stat.S_ISDIR(mode) or row[1] & ~0o777:
                raise RuntimeError(f"dependency cache mode metadata is invalid: {relative}")
            directories.append((path, row[1]))
        elif row[0] != "link" or not stat.S_ISLNK(mode) or str(path.readlink()) != row[1]:
            raise RuntimeError(f"dependency cache link metadata is invalid: {relative}")
    for path, mode in sorted(directories, key=lambda row: len(row[0].parts), reverse=True):
        path.chmod(mode)
        restored += 1
    return restored


def dependency_shape(gate, root, inventory):
    root = Path(root)
    expected_top = set(dependencies.project_files(gate)) | {".lake"}
    actual_top = {path.name for path in root.iterdir()}
    if actual_top != expected_top:
        raise RuntimeError(f"dependency root contains unexpected paths: {sorted(actual_top ^ expected_top)}")
    lake_root = root / ".lake"
    if {path.name for path in lake_root.iterdir()} != {"packages"}:
        raise RuntimeError("dependency root contains non-package .lake output")
    package_root = lake_root / "packages"
    expected_packages = sorted(entry["name"] for entry in gate.lake_manifest["packages"])
    actual_packages = sorted(path.name for path in package_root.iterdir())
    if actual_packages != expected_packages:
        raise RuntimeError("dependency package set differs from the pinned manifest")
    compiled = {
        path: row
        for path, row in inventory.items()
        if row[0] == "file" and path.endswith((".olean", ".ilean"))
    }
    if any(not path.startswith(".lake/packages/") for path in compiled):
        raise RuntimeError("compiled Lean output exists outside pinned dependency packages")
    package_build_files = {
        path: row
        for path, row in inventory.items()
        if row[0] == "file" and path.startswith(".lake/packages/") and "/.lake/build/" in path
    }
    return {
        "top_level_paths": sorted(actual_top),
        "lake_paths": sorted(path.name for path in lake_root.iterdir()),
        "package_names": actual_packages,
        "compiled_lean_file_count": len(compiled),
        "compiled_lean_file_bytes": sum(row[2] for row in compiled.values()),
        "package_build_file_count": len(package_build_files),
        "package_build_file_bytes": sum(row[2] for row in package_build_files.values()),
    }


def image_archive_metadata(path, expected_image_id, expected_platform):
    with tarfile.open(path, "r:") as archive:
        members = set(archive.getnames())
        index = json.load(archive.extractfile("index.json"))
        legacy = json.load(archive.extractfile("manifest.json"))
        if json.load(archive.extractfile("oci-layout")) != {"imageLayoutVersion": "1.0.0"}:
            raise RuntimeError("image archive has an unexpected OCI layout version")
        if len(index.get("manifests", [])) != 1 or len(legacy) != 1:
            raise RuntimeError("image archive does not contain exactly one image target")

        verified_blobs = {}

        def blob(path_name, expected_size=None, read_contents=False):
            if path_name not in members:
                raise RuntimeError(f"image archive blob is missing: {path_name}")
            file = archive.extractfile(path_name)
            if file is None:
                raise RuntimeError(f"image archive member is not a file: {path_name}")
            digest = hashlib.file_digest(file, "sha256").hexdigest()
            size = archive.getmember(path_name).size
            expected = path_name.rsplit("/", 1)[-1]
            if digest != expected:
                raise RuntimeError(f"image archive blob digest mismatch: {path_name}")
            if expected_size is not None and size != expected_size:
                raise RuntimeError(f"image archive blob size mismatch: {path_name}")
            verified_blobs[path_name] = {"digest": f"sha256:{digest}", "size_bytes": size}
            return archive.extractfile(path_name).read() if read_contents else None

        root = index["manifests"][0]
        root_path = f"blobs/sha256/{root['digest'].split(':', 1)[1]}"
        root_bytes = blob(root_path, root["size"], read_contents=True)
        if root["digest"] != expected_image_id:
            raise RuntimeError(f"image archive OCI target differs from inspected image ID: {root['digest']}")
        root_object = json.loads(root_bytes)
        descriptors = root_object.get("manifests", [])
        os_name, architecture = expected_platform.split("/", 1)
        image_descriptors = [
            item
            for item in descriptors
            if item.get("platform", {}).get("os") == os_name
            and item.get("platform", {}).get("architecture") == architecture
        ]
        if len(image_descriptors) != 1:
            raise RuntimeError("image archive has no unique descriptor for the inspected platform")
        image_descriptor = image_descriptors[0]
        image_path = f"blobs/sha256/{image_descriptor['digest'].split(':', 1)[1]}"
        image_bytes = blob(image_path, image_descriptor["size"], read_contents=True)
        image_manifest = json.loads(image_bytes)
        config_descriptor = image_manifest["config"]
        config_path = f"blobs/sha256/{config_descriptor['digest'].split(':', 1)[1]}"
        config_bytes = blob(config_path, config_descriptor["size"], read_contents=True)
        config = json.loads(config_bytes)
        legacy_item = legacy[0]
        legacy_layers = legacy_item.get("Layers", [])
        image_layers = image_manifest.get("layers", [])
        for descriptor in image_layers:
            blob(f"blobs/sha256/{descriptor['digest'].split(':', 1)[1]}", descriptor["size"])
        if legacy_item["Config"] != config_path or legacy_layers != [
            f"blobs/sha256/{item['digest'].split(':', 1)[1]}" for item in image_layers
        ]:
            raise RuntimeError("Docker manifest config or layers differ from the OCI platform manifest")

        descriptor_paths = {root_path, image_path, config_path}
        descriptor_paths.update(
            f"blobs/sha256/{item['digest'].split(':', 1)[1]}" for item in image_layers
        )
        attestation_descriptors = [item for item in descriptors if item is not image_descriptor]
        for attestation in attestation_descriptors:
            attestation_path = f"blobs/sha256/{attestation['digest'].split(':', 1)[1]}"
            attestation_bytes = blob(attestation_path, attestation["size"], read_contents=True)
            attestation_manifest = json.loads(attestation_bytes)
            attestation_config = attestation_manifest["config"]
            attestation_config_path = f"blobs/sha256/{attestation_config['digest'].split(':', 1)[1]}"
            blob(attestation_config_path, attestation_config["size"])
            descriptor_paths.add(attestation_path)
            descriptor_paths.add(attestation_config_path)
            for layer in attestation_manifest.get("layers", []):
                layer_path = f"blobs/sha256/{layer['digest'].split(':', 1)[1]}"
                blob(layer_path, layer["size"])
                descriptor_paths.add(layer_path)

        archive_blobs = {name for name in members if name.startswith("blobs/sha256/")}
        if archive_blobs != descriptor_paths:
            raise RuntimeError(
                "image archive has unreferenced or missing blobs: "
                f"unreferenced={sorted(archive_blobs - descriptor_paths)} "
                f"missing={sorted(descriptor_paths - archive_blobs)}"
            )
        tag_annotations = {"org.opencontainers.image.ref.name", "io.containerd.image.name"}
        annotations = [index.get("annotations"), root.get("annotations"), image_descriptor.get("annotations")]
        if any(tag_annotations.intersection(value or {}) for value in annotations):
            raise RuntimeError("image archive OCI graph carries a named image reference")
        if legacy_item.get("RepoTags"):
            raise RuntimeError("image archive Docker manifest carries repository tags")
        return {
            "layout_version": "1.0.0",
            "index_target_digest": root["digest"],
            "index_target_size_bytes": root["size"],
            "platform_manifest_digest": image_descriptor["digest"],
            "platform_manifest_size_bytes": image_descriptor["size"],
            "config_digest": config_descriptor["digest"],
            "config_size_bytes": config_descriptor["size"],
            "platform": f"{config.get('os')}/{config.get('architecture')}",
            "repo_tags": legacy_item.get("RepoTags") or [],
            "tagless": not legacy_item.get("RepoTags")
            and not any(tag_annotations.intersection(value or {}) for value in annotations),
            "layer_count": len(image_layers),
            "legacy_layer_paths_match_oci": True,
            "verified_blob_count": len(verified_blobs),
            "verified_blob_bytes": sum(row["size_bytes"] for row in verified_blobs.values()),
            "verified_blobs": verified_blobs,
            "attestation_descriptors": attestation_descriptors,
        }


def named_image_tags(ctx):
    result = container.run_docker(
        ctx, "image", "ls", "--all", "--no-trunc", "--format", "{{.ID}}|{{.Repository}}:{{.Tag}}", timeout_s=60
    )
    if result.rc != 0:
        raise RuntimeError(f"docker image ls failed: rc={result.rc} {result.stderr[-1000:]}")
    return sorted(
        row
        for row in result.stdout.splitlines()
        if row and not row.endswith("|<none>:<none>")
    )


def load_archive(ctx, image, archive_path, archive_metadata):
    if not archive_metadata["tagless"]:
        raise RuntimeError("image load requires an archive without repository tags")
    tags_before = named_image_tags(ctx)
    args = ["image", "load", "--input", archive_path]
    started = time.monotonic()
    loaded = container.run_docker(ctx, *args, timeout_s=1800)
    elapsed = time.monotonic() - started
    tags_after = named_image_tags(ctx)
    image_after = inspect_image(ctx, image.image_id)
    if loaded.rc != 0:
        raise RuntimeError(f"docker image load failed: rc={loaded.rc} {loaded.stderr[-1000:]}")
    if tags_after != tags_before:
        raise RuntimeError("docker image load changed a named image tag mapping")
    if image_after["image_id"] != image.image_id:
        raise RuntimeError("docker image load did not leave the exact literal image ID inspectable")
    return {
        "attempted": True,
        "safety": "tagless-archive-and-named-tag-mappings-unchanged",
        "seconds": elapsed,
        "command": command_record(ctx, *args),
        "returncode": loaded.rc,
        "stdout": loaded.stdout,
        "stderr": loaded.stderr,
        "named_tag_mappings_before": tags_before,
        "named_tag_mappings_after": tags_after,
        "named_tag_mappings_unchanged": tags_before == tags_after,
        "literal_image_inspect_after": image_after,
    }


def reject(args):
    root = Path(tempfile.mkdtemp(prefix="cairn-prerequisite-refusal-"))
    gate = build_gate(root / "bundle")
    try:
        if args.reject in {"missing-image-record", "wrong-image-id"}:
            dependencies.cached_image(gate, args.cache)
        else:
            image = container.Image(
                gate.container_identity,
                container.image_tag(gate.container_identity),
                args.image_id,
                container.context(),
            )
            dependencies.restore(gate, image, args.cache, args.destination)
    except (dependencies.CacheRefused, container.ContainerError, lean.LeanPinMismatch) as exc:
        print(
            json.dumps(
                {
                    "status": "refused",
                    "refusal_type": type(exc).__name__,
                    "refusal": str(exc),
                    "scratch_root": str(root),
                },
                sort_keys=True,
            )
        )
        return REFUSAL_EXIT
    print(json.dumps({"status": "accepted", "scratch_root": str(root)}, sort_keys=True))
    return 0


def run_rejection(kind, cache, image_id, destination, expected_reason):
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--reject",
        kind,
        "--cache",
        str(cache),
        "--image-id",
        image_id,
        "--destination",
        str(destination),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    try:
        response = json.loads(completed.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        response = None
    if (
        completed.returncode != REFUSAL_EXIT
        or not response
        or not response.get("refusal", "").startswith(expected_reason)
    ):
        raise RuntimeError(
            f"planted refusal failed: rc={completed.returncode} stdout={completed.stdout!r} stderr={completed.stderr[-1000:]!r}"
        )
    return {
        "command": command,
        "returncode": completed.returncode,
        "expected_returncode": REFUSAL_EXIT,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr,
        "refusal": response,
    }


def command_record(ctx, *args):
    return [container.DOCKER, *(["--context", ctx] if ctx else []), *map(str, args)]


def run_probe():
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = REPORT_DIR / "runs" / f"{stamp}-{os.getpid()}"
    run_dir.mkdir(parents=True)
    raw_path = run_dir / "measurement.json"
    scratch = Path(tempfile.mkdtemp(prefix="cairn-prerequisites-20260929-"))
    probe_bytes = Path(__file__).read_bytes()
    source_commit = subprocess.run(
        [shutil.which("git") or "/usr/bin/git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    result = {
        "schema": "cairn-prerequisite-reuse-probe/v1",
        "started_at_utc": datetime.now(UTC).isoformat(),
        "source_commit": source_commit,
        "probe_sha256": digest_bytes(probe_bytes),
        "host": {"system": platform.system(), "machine": platform.machine(), "python": sys.version.split()[0]},
        "scratch_root": str(scratch),
        "raw_result_path": str(raw_path),
        "scope": {
            "cache_state": "fresh empty Cairn dependency-cache directory",
            "docker_state": "shared daemon with the exact image already present; no build or prune",
            "claim_boundary": "local timings only; artifact transfer and CI critical path are not measured",
        },
    }

    def persist():
        raw_path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    try:
        bundle_root = scratch / "bundle"
        gate = build_gate(bundle_root)
        ctx = container.context()
        tag = container.image_tag(gate.container_identity)
        tag_before = inspect_image(ctx, tag)
        image = container.Image(gate.container_identity, tag, tag_before["image_id"], ctx)
        if not container.IMAGE_ID_RE.fullmatch(image.image_id):
            raise RuntimeError(f"unexpected image ID {image.image_id!r}")
        daemon = container.daemon_info(ctx)
        pin_validation_start = time.monotonic()
        container.assert_pinned(gate, image)
        pin_validation_seconds = time.monotonic() - pin_validation_start
        image_details = inspect_image(ctx, image.image_id)
        if image_details["image_id"] != image.image_id:
            raise RuntimeError("literal image ID inspection changed")
        result["source"] = {
            "container_identity": gate.container_identity,
            "container_tag": tag,
            "image_id": image.image_id,
            "cache_key": dependencies.cache_key(gate, image),
            "container_spec_sha256": digest_bytes(container.SPEC_PATH.read_bytes()),
            "containerfile_sha256": digest_bytes(container.CONTAINERFILE_PATH.read_bytes()),
            "source_tag_inspect": tag_before,
            "literal_image_inspect": image_details,
            "pin_validation_seconds": pin_validation_seconds,
            "docker_daemon": daemon,
            "dependency_pins": {
                "toolchain": gate.lean["toolchain"],
                "lean_commit": gate.lean["lean_commit"],
                "mathlib_rev": gate.lean["mathlib_rev"],
                "modules": list(dependencies.MODULES),
            },
        }
        disk = shutil.disk_usage(scratch)
        initial_required_free = image_details["size_bytes"] * 2 + 1024**3
        result["storage_preflight"] = {
            "available_bytes_before_cache_creation": disk.free,
            "minimum_estimate_bytes": initial_required_free,
            "image_virtual_size_bytes": image_details["size_bytes"],
        }
        if disk.free < initial_required_free:
            raise RuntimeError("insufficient scratch disk for one image and dependency payload")
        commands = []
        original_run = container.run

        def capture_run(run_ctx, run_image, argv, **kwargs):
            phase = result.get("active_phase", "unlabeled")
            observed = original_run(run_ctx, run_image, argv, **kwargs)
            commands.append(
                {
                    "phase": phase,
                    "argv": list(observed.argv),
                    "returncode": observed.rc,
                    "wall_seconds": observed.wall_ms / 1000,
                    "stdout_tail": observed.stdout[-1500:],
                    "stderr_tail": observed.stderr[-1500:],
                }
            )
            return observed

        container.run = capture_run
        cache_root = scratch / "cold-cache"
        cache_root.mkdir()
        result["active_phase"] = "cold_dependency_prepare"
        cold_start = time.monotonic()
        entry = dependencies.prepare(gate, image, cache_root)
        cold_prepare_seconds = time.monotonic() - cold_start
        dependencies.remember_image(gate, image, cache_root)
        inventory = dependencies.inventory(entry / "project")
        entry_bytes = file_tree_bytes(entry)
        cache_record = dependencies.image_record(gate, cache_root)
        dependency_file_bytes = sum(row[2] for row in inventory.values() if row[0] == "file")
        result["cold_dependency_prepare"] = {
            "elapsed_seconds": cold_prepare_seconds,
            "entry_path": str(entry),
            "entry_bytes_including_inventory": entry_bytes,
            "dependency_file_bytes": dependency_file_bytes,
            "file_count": sum(row[0] == "file" for row in inventory.values()),
            "directory_count": sum(row[0] == "directory" for row in inventory.values()),
            "symlink_count": sum(row[0] == "link" for row in inventory.values()),
            "inventory_sha256": digest_json(inventory),
            "captured_container_commands": list(commands),
        }
        result["cold_dependency_prepare"]["shape"] = dependency_shape(gate, entry / "project", inventory)
        result.pop("active_phase", None)

        bad_image_cache = scratch / "negative-missing-image"
        bad_image_cache.mkdir()
        missing_image_refusal = run_rejection(
            "missing-image-record",
            bad_image_cache,
            image.image_id,
            scratch / "unused-destination",
            "dependency-cache-image-unavailable",
        )
        wrong_image_cache = scratch / "negative-wrong-image"
        wrong_image_cache.mkdir()
        wrong_image_id = "sha256:" + "0" * 64
        dependencies.image_record(gate, wrong_image_cache).write_text(
            json.dumps({"identity": gate.container_identity, "image_id": wrong_image_id}, sort_keys=True) + "\n"
        )
        wrong_image_refusal = run_rejection(
            "wrong-image-id",
            wrong_image_cache,
            wrong_image_id,
            scratch / "unused-wrong-image-destination",
            f"image {wrong_image_id} has no inspectable id: rc=1",
        )
        corrupt_cache = scratch / "negative-corrupt-entry"
        corrupt_entry = corrupt_cache / dependencies.cache_key(gate, image)
        corrupt_project = corrupt_entry / "project"
        corrupt_project.mkdir(parents=True)
        for name, content in dependencies.project_files(gate).items():
            (corrupt_project / name).write_text(content)
        package_name = gate.lake_manifest["packages"][0]["name"]
        marker = corrupt_project / ".lake" / "packages" / package_name / "probe-marker"
        marker.parent.mkdir(parents=True)
        marker.write_bytes(b"entry-before")
        clean_inventory = dependencies.inventory(corrupt_project)
        (corrupt_entry / "inventory.json").write_text(
            json.dumps(
                {"inputs": dependencies.key_inputs(gate, image), "inventory": clean_inventory},
                sort_keys=True,
            )
            + "\n"
        )
        marker.write_bytes(b"entry-after")
        corrupt_entry_refusal = run_rejection(
            "corrupt-entry",
            corrupt_cache,
            image.image_id,
            scratch / "refused-destination",
            "dependency-cache-content-mismatch",
        )
        result["planted_refusals"] = {
            "missing_image_record": missing_image_refusal,
            "wrong_image_id": wrong_image_refusal,
            "corrupt_dependency_file": corrupt_entry_refusal,
        }

        disk = shutil.disk_usage(scratch)
        required_free = image_details["size_bytes"] * 2 + entry_bytes + 1024**3
        result["storage_preflight"] = {
            "available_bytes_before_archive_creation": disk.free,
            "required_estimate_bytes": required_free,
            "image_virtual_size_bytes": image_details["size_bytes"],
            "dependency_entry_bytes": entry_bytes,
        }
        if disk.free < required_free:
            raise RuntimeError("insufficient scratch disk for one image and dependency payload")

        image_archive = scratch / "image.tar"
        save_args = ["image", "save", "--output", image_archive, image.image_id]
        save_start = time.monotonic()
        save = container.run_docker(ctx, *save_args, timeout_s=1800)
        save_seconds = time.monotonic() - save_start
        if save.rc != 0:
            raise RuntimeError(f"docker image save failed: rc={save.rc} {save.stderr[-1000:]}")
        archive_metadata = image_archive_metadata(image_archive, image.image_id, image_details["platform"])
        result["image_archive"] = {
            "command": command_record(ctx, *save_args),
            "returncode": save.rc,
            "wall_seconds": save_seconds,
            "wall_ms_reported": save.wall_ms,
            "stdout": save.stdout,
            "stderr": save.stderr,
            "path": str(image_archive),
            "size_bytes": image_archive.stat().st_size,
            "sha256": digest_file(image_archive),
            **archive_metadata,
        }

        payload = scratch / "prerequisites.tar.gz"
        compression_start = time.monotonic()
        with tarfile.open(payload, "w:gz", compresslevel=6) as archive:
            archive.add(image_archive, arcname="image.tar")
            archive.add(entry, arcname=f"dependency-cache/{entry.name}")
            archive.add(cache_record, arcname=f"dependency-cache/{cache_record.name}")
        compression_seconds = time.monotonic() - compression_start
        payload_bytes = payload.stat().st_size
        payload_members = []
        with tarfile.open(payload, "r:gz") as archive:
            payload_members = [member.name for member in archive.getmembers()]
        if not payload_members or payload_members[0] != "image.tar":
            raise RuntimeError("combined artifact does not start with the exact image archive")
        result["payload"] = {
            "path": str(payload),
            "uncompressed_input_bytes": image_archive.stat().st_size + entry_bytes + cache_record.stat().st_size,
            "compressed_bytes": payload_bytes,
            "compression_ratio": payload_bytes
            / (image_archive.stat().st_size + entry_bytes + cache_record.stat().st_size),
            "compression_seconds": compression_seconds,
            "sha256": digest_file(payload),
            "member_count": len(payload_members),
            "top_level_members": sorted({name.split("/", 1)[0] for name in payload_members}),
        }

        restored_root = scratch / "warm-consumer"
        restored_root.mkdir()
        warm_cache = restored_root / "dependency-cache"
        warm_start = time.monotonic()
        unpack_start = time.monotonic()
        with tarfile.open(payload, "r:gz") as archive:
            archive.extractall(restored_root, filter="data")
        unpack_seconds = time.monotonic() - unpack_start
        restored_image_archive = restored_root / "image.tar"
        load_metadata = load_archive(ctx, image, restored_image_archive, archive_metadata)

        result["active_phase"] = "warm_cached_image_validation"
        validate_start = time.monotonic()
        restored_image = dependencies.cached_image(gate, warm_cache)
        validate_seconds = time.monotonic() - validate_start
        if restored_image.image_id != image.image_id:
            raise RuntimeError("restored image record points at a different literal image ID")
        result["active_phase"] = "warm_private_dependency_restore"
        destination = scratch / "private-project"
        restore_start = time.monotonic()
        restored_project = dependencies.restore(gate, restored_image, warm_cache, destination)
        restore_seconds = time.monotonic() - restore_start
        restored_inventory = dependencies.inventory(restored_project)
        inventory_equal = restored_inventory == inventory
        if not inventory_equal:
            raise RuntimeError("private restored dependency root differs from the source inventory")
        result.pop("active_phase", None)
        result["warm_restore"] = {
            "artifact_unpack_seconds": unpack_seconds,
            "image_load": load_metadata,
            "cached_image_validation_seconds": validate_seconds,
            "private_dependency_restore_seconds": restore_seconds,
            "combined_elapsed_seconds": time.monotonic() - warm_start,
            "image_id_inspected": restored_image.image_id,
            "image_identity_validated": restored_image.identity == gate.container_identity,
            "destination": str(restored_project),
            "inventory_matches_source": inventory_equal,
            "source_inventory_sha256": digest_json(inventory),
            "restored_inventory_sha256": digest_json(restored_inventory),
            "dependency_shape": dependency_shape(gate, restored_project, restored_inventory),
            "proof_or_candidate_outputs_present": False,
        }
        result["status"] = "complete"
        persist()
        return raw_path
    except BaseException as exc:
        result["status"] = "failed"
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
        persist()
        raise


def run_archive_followup(source_path):
    source_path = Path(source_path).resolve()
    source = json.loads(source_path.read_text())
    if source.get("schema") != "cairn-prerequisite-reuse-probe/v1":
        raise RuntimeError("source measurement has an unexpected schema")
    if "cold_dependency_prepare" not in source or "source" not in source:
        raise RuntimeError("source measurement lacks the cold dependency preparation")
    scratch = Path(source["scratch_root"])
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = source_path.parent
    raw_path = run_dir / f"archive-followup-{stamp}-{os.getpid()}.json"
    if raw_path.exists():
        raise RuntimeError(f"archive follow-up output already exists: {raw_path}")
    result = {
        "schema": "cairn-prerequisite-reuse-followup/v1",
        "started_at_utc": datetime.now(UTC).isoformat(),
        "raw_result_path": str(raw_path),
        "probe_sha256": digest_file(__file__),
        "source_measurement_path": str(source_path),
        "source_measurement_sha256": digest_file(source_path),
        "source_commit": source["source_commit"],
        "source_identity": source["source"],
        "cold_dependency_prepare": {
            "elapsed_seconds": source["cold_dependency_prepare"]["elapsed_seconds"],
            "entry_bytes_including_inventory": source["cold_dependency_prepare"]["entry_bytes_including_inventory"],
            "inventory_sha256": source["cold_dependency_prepare"]["inventory_sha256"],
        },
        "scratch_root": str(scratch),
        "scope": {
            "docker_state": "shared daemon with the exact image already present; no build or prune",
            "claim_boundary": "same-daemon warm load only; no fresh-daemon or CI transfer claim",
        },
    }

    def persist():
        raw_path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    try:
        bundle_root = scratch / "bundle"
        gate = bundle.GateBundle.open(bundle_root / "bundle.sqlite", bundle_root / "bundle.pin")
        entry = Path(source["cold_dependency_prepare"]["entry_path"])
        cache_root = entry.parent
        record_path = dependencies.image_record(gate, cache_root)
        cache_record = json.loads(record_path.read_text())
        expected_id = source["source"]["image_id"]
        if cache_record != {"identity": gate.container_identity, "image_id": expected_id}:
            raise RuntimeError("cold cache image record differs from the measured source identity")
        inventory = dependencies.inventory(entry / "project")
        if digest_json(inventory) != source["cold_dependency_prepare"]["inventory_sha256"]:
            raise RuntimeError("cold dependency inventory differs from its raw measurement")
        source_shape = dependency_shape(gate, entry / "project", inventory)
        image = container.Image(
            gate.container_identity,
            container.image_tag(gate.container_identity),
            expected_id,
            container.context(),
        )
        image_archive = scratch / "image.tar"
        if not image_archive.is_file():
            raise RuntimeError(f"saved image archive is unavailable: {image_archive}")
        image_metadata = image_archive_metadata(
            image_archive,
            expected_id,
            source["source"]["literal_image_inspect"]["platform"],
        )
        image_metadata.update(
            {
                "path": str(image_archive),
                "size_bytes": image_archive.stat().st_size,
                "sha256": digest_file(image_archive),
            }
        )
        result["image_archive"] = image_metadata
        result["source_dependency_shape"] = source_shape
        persist()

        available = shutil.disk_usage(scratch).free
        required = image_archive.stat().st_size + source["cold_dependency_prepare"]["entry_bytes_including_inventory"] + 1024**3
        result["storage_preflight"] = {"available_bytes_before_payload": available, "required_estimate_bytes": required}
        if available < required:
            raise RuntimeError("insufficient scratch disk for one prerequisite payload")

        payload = scratch / f"prerequisites-{stamp}-{os.getpid()}.tar.gz"
        compression_started = time.monotonic()
        with tarfile.open(payload, "w:gz", compresslevel=6) as archive:
            archive.add(image_archive, arcname="image.tar")
            archive.add(entry, arcname=f"dependency-cache/{entry.name}")
            archive.add(record_path, arcname=f"dependency-cache/{record_path.name}")
        compression_seconds = time.monotonic() - compression_started
        uncompressed_bytes = image_archive.stat().st_size + source["cold_dependency_prepare"]["entry_bytes_including_inventory"] + record_path.stat().st_size
        with tarfile.open(payload, "r:gz") as archive:
            payload_members = [member.name for member in archive.getmembers()]
        if not payload_members or payload_members[0] != "image.tar":
            raise RuntimeError("combined artifact does not begin with the saved image")
        expected_prefix = f"dependency-cache/{entry.name}"
        if any(
            member != "image.tar"
            and member != f"dependency-cache/{record_path.name}"
            and not member.startswith(expected_prefix)
            for member in payload_members
        ):
            raise RuntimeError("combined artifact contains paths outside the prerequisite cache")
        result["payload"] = {
            "path": str(payload),
            "uncompressed_input_bytes": uncompressed_bytes,
            "compressed_bytes": payload.stat().st_size,
            "compression_ratio": payload.stat().st_size / uncompressed_bytes,
            "compression_seconds": compression_seconds,
            "sha256": digest_file(payload),
            "member_count": len(payload_members),
            "top_level_members": sorted({name.split("/", 1)[0] for name in payload_members}),
        }
        persist()

        restored_root = scratch / f"warm-consumer-{stamp}-{os.getpid()}"
        restored_root.mkdir()
        unpack_started = time.monotonic()
        with tarfile.open(payload, "r:gz") as archive:
            archive.extractall(restored_root, filter="data")
        unpack_seconds = time.monotonic() - unpack_started
        restored_archive = restored_root / "image.tar"
        warm_cache = restored_root / "dependency-cache"
        image_load = load_archive(container.context(), image, restored_archive, image_metadata)
        pin_started = time.monotonic()
        container.assert_pinned(gate, image)
        pin_seconds = time.monotonic() - pin_started
        validate_started = time.monotonic()
        restored_image = dependencies.cached_image(gate, warm_cache)
        validate_seconds = time.monotonic() - validate_started
        if restored_image.image_id != expected_id:
            raise RuntimeError("restored cache image record points at a different literal image ID")

        destination = scratch / f"private-project-{stamp}-{os.getpid()}"
        restore_started = time.monotonic()
        restored_project = dependencies.restore(gate, restored_image, warm_cache, destination)
        restore_seconds = time.monotonic() - restore_started
        restored_inventory = dependencies.inventory(restored_project)
        differences = {
            path: {"expected": inventory.get(path), "actual": restored_inventory.get(path)}
            for path in sorted(set(inventory) | set(restored_inventory))
            if inventory.get(path) != restored_inventory.get(path)
        }
        result["warm_restore"] = {
            "artifact_unpack_seconds": unpack_seconds,
            "image_load": image_load,
            "explicit_assert_pinned_seconds": pin_seconds,
            "cached_image_validation_seconds": validate_seconds,
            "private_dependency_restore_seconds": restore_seconds,
            "combined_elapsed_seconds": unpack_seconds + image_load["seconds"] + pin_seconds + validate_seconds + restore_seconds,
            "image_id_inspected": restored_image.image_id,
            "image_identity_validated": restored_image.identity == gate.container_identity,
            "destination": str(restored_project),
            "inventory_matches_source": not differences,
            "inventory_differences": differences,
            "source_inventory_sha256": digest_json(inventory),
            "restored_inventory_sha256": digest_json(restored_inventory),
            "dependency_shape": dependency_shape(gate, restored_project, restored_inventory),
            "proof_or_candidate_outputs_present": False,
        }
        if differences:
            raise RuntimeError("private restored dependency root differs from the source inventory")
        result["status"] = "complete"
        persist()
        return raw_path
    except BaseException as exc:
        result["status"] = "failed"
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
        persist()
        raise


def run_archive_refinement(followup_path):
    followup_path = Path(followup_path).resolve()
    previous = json.loads(followup_path.read_text())
    if previous.get("schema") != "cairn-prerequisite-reuse-followup/v1":
        raise RuntimeError("source follow-up has an unexpected schema")
    if previous.get("error", {}).get("message") != "dependency-cache-content-mismatch":
        raise RuntimeError("source follow-up does not record the expected strict inventory refusal")
    source_path = Path(previous["source_measurement_path"])
    source = json.loads(source_path.read_text())
    scratch = Path(source["scratch_root"])
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    raw_path = followup_path.parent / f"archive-refinement-{stamp}-{os.getpid()}.json"
    if raw_path.exists():
        raise RuntimeError(f"archive refinement output already exists: {raw_path}")
    result = {
        "schema": "cairn-prerequisite-reuse-refinement/v1",
        "started_at_utc": datetime.now(UTC).isoformat(),
        "raw_result_path": str(raw_path),
        "probe_sha256": digest_file(__file__),
        "source_measurement_path": str(source_path),
        "source_measurement_sha256": digest_file(source_path),
        "previous_followup_path": str(followup_path),
        "previous_followup_sha256": digest_file(followup_path),
        "previous_payload": previous["payload"],
        "source_commit": source["source_commit"],
        "source_identity": source["source"],
        "scratch_root": str(scratch),
        "load_evidence": {
            "attempted_in_previous_followup": True,
            "elapsed_seconds": None,
            "named_tag_mappings_before_after": None,
            "claim": "load timing and tag snapshots were not retained by the previous follow-up",
        },
    }

    def persist():
        raw_path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    try:
        consumer_started = time.monotonic()
        bundle_root = scratch / "bundle"
        gate = bundle.GateBundle.open(bundle_root / "bundle.sqlite", bundle_root / "bundle.pin")
        entry = Path(source["cold_dependency_prepare"]["entry_path"])
        cache_root = entry.parent
        payload = Path(previous["payload"]["path"])
        payload_digest_started = time.monotonic()
        if digest_file(payload) != previous["payload"]["sha256"]:
            raise RuntimeError("compressed prerequisite payload digest differs from its prior measurement")
        payload_digest_seconds = time.monotonic() - payload_digest_started
        image_record_path = dependencies.image_record(gate, cache_root)
        cache_record = json.loads(image_record_path.read_text())
        image = container.Image(
            gate.container_identity,
            container.image_tag(gate.container_identity),
            source["source"]["image_id"],
            container.context(),
        )
        if cache_record != {"identity": gate.container_identity, "image_id": image.image_id}:
            raise RuntimeError("cold cache image record differs from the measured source identity")
        expected_inventory = dependencies.inventory(entry / "project")
        if digest_json(expected_inventory) != source["cold_dependency_prepare"]["inventory_sha256"]:
            raise RuntimeError("cold dependency inventory differs from its raw measurement")
        entry_record = json.loads((entry / "inventory.json").read_text())
        if entry_record.get("inventory") != expected_inventory:
            raise RuntimeError("cold cache inventory record differs from the measured dependency tree")
        if entry_record.get("inputs") != dependencies.key_inputs(gate, image):
            raise RuntimeError("cold cache key inputs differ from the measured source identity")
        source_validation_seconds = time.monotonic() - consumer_started

        restored_root = scratch / f"warm-consumer-refined-{stamp}-{os.getpid()}"
        restored_root.mkdir()
        restored_cache = restored_root / "dependency-cache"
        expected_entry = f"dependency-cache/{entry.name}"
        expected_names = {
            "image.tar",
            expected_entry,
            f"{expected_entry}/inventory.json",
            f"{expected_entry}/project",
            f"dependency-cache/{image_record_path.name}",
        }
        expected_names.update(f"{expected_entry}/project/{path}" for path in expected_inventory)
        seen = set()
        unpack_started = time.monotonic()
        with tarfile.open(payload, "r|gz") as archive:
            for member in archive:
                name = member.name.rstrip("/")
                if name not in expected_names or name in seen:
                    raise RuntimeError(f"prerequisite payload member is unexpected or duplicated: {name}")
                seen.add(name)
                if name == "image.tar" or name == f"dependency-cache/{image_record_path.name}" or name.endswith("/inventory.json"):
                    valid_type = member.isfile()
                elif name in {expected_entry, f"{expected_entry}/project"}:
                    valid_type = member.isdir()
                else:
                    row = expected_inventory[name.removeprefix(f"{expected_entry}/project/")]
                    valid_type = {
                        "file": member.isfile(),
                        "directory": member.isdir(),
                        "link": member.issym(),
                    }[row[0]]
                    if row[0] == "link" and member.linkname != row[1]:
                        raise RuntimeError(f"prerequisite payload link target differs: {name}")
                    if row[0] == "file" and (member.size != row[2] or member.mode != row[1]):
                        raise RuntimeError(f"prerequisite payload file metadata differs: {name}")
                    if row[0] == "directory" and member.mode != row[1]:
                        raise RuntimeError(f"prerequisite payload directory mode differs: {name}")
                if not valid_type:
                    raise RuntimeError(f"prerequisite payload member type differs: {name}")
                archive.extract(member, restored_root, filter="data")
        if seen != expected_names:
            raise RuntimeError(f"prerequisite payload members are missing: {sorted(expected_names - seen)}")
        unpack_seconds = time.monotonic() - unpack_started
        restored_entry = restored_cache / entry.name
        restored_project = restored_entry / "project"
        filtered_inventory_started = time.monotonic()
        filtered_inventory = dependencies.inventory(restored_project)
        filtered_differences = inventory_differences(expected_inventory, filtered_inventory)
        filtered_inventory_seconds = time.monotonic() - filtered_inventory_started
        result["data_filter_extract"] = {
            "elapsed_seconds": unpack_seconds,
            "inventory_validation_seconds": filtered_inventory_seconds,
            "inventory_matches_source": not filtered_differences,
            "difference_count": len(filtered_differences),
            "differences": filtered_differences,
            "all_member_paths_types_sizes_and_symlink_targets_validated": True,
        }
        result["consumer_stages"] = {
            "source_validation_seconds": source_validation_seconds,
            "payload_digest_seconds": payload_digest_seconds,
            "payload_extract_seconds": unpack_seconds,
            "post_extract_inventory_seconds": filtered_inventory_seconds,
            "private_restore_status": "not_started",
        }
        persist()

        permission_restore_started = time.monotonic()
        inventory_mode_restore_count = restore_inventory_modes(restored_project, expected_inventory)
        restored_inventory = dependencies.inventory(restored_project)
        mode_differences = inventory_differences(expected_inventory, restored_inventory)
        permission_restore_seconds = time.monotonic() - permission_restore_started
        result["permission_metadata_restore"] = {
            "elapsed_seconds": permission_restore_seconds,
            "entry_count": inventory_mode_restore_count,
            "inventory_matches_source": not mode_differences,
            "difference_count": len(mode_differences),
            "differences": mode_differences,
        }
        persist()
        if mode_differences:
            raise RuntimeError("permission metadata restoration did not preserve the exact inventory")

        image_present = inspect_image(image.context, image.image_id)
        pin_started = time.monotonic()
        container.assert_pinned(gate, image)
        pin_seconds = time.monotonic() - pin_started
        validation_started = time.monotonic()
        restored_image = dependencies.cached_image(gate, restored_cache)
        validation_seconds = time.monotonic() - validation_started
        if restored_image.image_id != image.image_id:
            raise RuntimeError("restored cache image record points at a different literal image ID")
        destination = scratch / f"private-project-refined-{stamp}-{os.getpid()}"
        result["consumer_stages"].update(
            {
                "permission_metadata_restore_seconds": permission_restore_seconds,
                "literal_image_inspect_seconds": image_present["elapsed_seconds"],
                "assert_pinned_seconds": pin_seconds,
                "cached_image_validation_seconds": validation_seconds,
                "private_restore_status": "in_progress",
            }
        )
        result["warm_validation"] = {
            "literal_image_inspect": image_present,
            "image_id_inspected": restored_image.image_id,
            "image_identity_validated": restored_image.identity == gate.container_identity,
            "explicit_assert_pinned_seconds": pin_seconds,
            "cached_image_validation_seconds": validation_seconds,
            "status": "passed",
        }
        persist()

        restore_started = time.monotonic()
        restored_project = dependencies.restore(gate, restored_image, restored_cache, destination)
        restore_seconds = time.monotonic() - restore_started
        copied_inventory_started = time.monotonic()
        copied_inventory = dependencies.inventory(restored_project)
        copy_differences = inventory_differences(expected_inventory, copied_inventory)
        copied_inventory_seconds = time.monotonic() - copied_inventory_started
        consumer_elapsed_seconds = time.monotonic() - consumer_started
        result["consumer_stages"].update(
            {
                "private_restore_seconds": restore_seconds,
                "copied_inventory_seconds": copied_inventory_seconds,
                "private_restore_status": "complete" if not copy_differences else "mismatch",
            }
        )
        result["warm_restore"] = {
            "image_load": "not-repeated",
            "literal_image_inspect": image_present,
            "explicit_assert_pinned_seconds": pin_seconds,
            "cached_image_validation_seconds": validation_seconds,
            "private_dependency_restore_seconds": restore_seconds,
            "copied_inventory_seconds": copied_inventory_seconds,
            "warm_dependency_consumer_total_seconds_excluding_image_load": consumer_elapsed_seconds,
            "image_id_inspected": restored_image.image_id,
            "image_identity_validated": restored_image.identity == gate.container_identity,
            "destination": str(restored_project),
            "inventory_matches_source": not copy_differences,
            "inventory_differences": copy_differences,
            "source_inventory_sha256": digest_json(expected_inventory),
            "restored_inventory_sha256": digest_json(copied_inventory),
            "dependency_shape": dependency_shape(gate, restored_project, copied_inventory),
            "proof_or_candidate_outputs_present": False,
        }
        persist()
        if copy_differences:
            raise RuntimeError("private restored dependency root differs from the source inventory")
        result["status"] = "complete"
        persist()
        return raw_path
    except BaseException as exc:
        result["status"] = "failed"
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
        persist()
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reject", choices=("missing-image-record", "wrong-image-id", "corrupt-entry"))
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--image-id", default="sha256:" + "0" * 64)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--refine", type=Path)
    args = parser.parse_args()
    if args.refine is not None:
        print(run_archive_refinement(args.refine))
        return 0
    if args.resume is not None:
        print(run_archive_followup(args.resume))
        return 0
    if args.reject:
        if args.cache is None or args.destination is None:
            parser.error("refusal mode requires --cache and --destination")
        return reject(args)
    print(run_probe())
    return 0


if __name__ == "__main__":
    sys.exit(main())
