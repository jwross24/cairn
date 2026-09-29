import argparse
import fcntl
import hashlib
import json
import os
import shutil
import stat
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

from cairn import bundle, container, lean, log, solutionbuild

MODULES = ("Mathlib.AlgebraicGeometry.EllipticCurve.Affine.Point",)
CACHE_ENV = "CAIRN_LINUX_DEPENDENCY_CACHE"
ARCHIVE_LAYOUT = "docker-save-image-id-v1"
lg = log.get("linux_dependencies")


class CacheRefused(RuntimeError):
    pass


def project_files(gate):
    return {
        "lean-toolchain": gate.lean["toolchain"] + "\n",
        "lake-manifest.json": json.dumps(gate.lake_manifest, sort_keys=True, indent=2) + "\n",
        "lakefile.toml": (
            'name = "cairn_lean"\n\n[[lean_lib]]\nname = "Challenge"\nglobs = ["Challenge.+"]\n\n'
            '[[require]]\nname = "mathlib"\ngit = "https://github.com/leanprover-community/mathlib4"\n'
            f'rev = "{gate.lean["mathlib_rev"]}"\n'
        ),
    }


def key_inputs(gate, image):
    if image.identity != gate.container_identity or not container.IMAGE_ID_RE.fullmatch(image.image_id):
        raise CacheRefused("dependency-cache-image-mismatch")
    return {
        "layout": 1,
        "image_id": image.image_id,
        "image_identity": image.identity,
        "lean": gate.lean,
        "files": project_files(gate),
        "modules": list(MODULES),
    }


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def cache_key(gate, image):
    return digest(key_inputs(gate, image))


def inventory(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise CacheRefused("dependency-cache-project-unavailable")
    rows = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            target = path.readlink()
            try:
                resolved = path.resolve(strict=True)
            except OSError, RuntimeError:
                raise CacheRefused(f"dependency-cache-invalid-link:{relative}") from None
            if target.is_absolute() or not resolved.is_relative_to(root.resolve()):
                raise CacheRefused(f"dependency-cache-escaping-link:{relative}")
            rows[relative] = ["link", str(target)]
        elif stat.S_ISREG(mode):
            with path.open("rb") as stream:
                checksum = hashlib.file_digest(stream, "sha256").hexdigest()
            rows[relative] = ["file", stat.S_IMODE(mode), path.stat().st_size, checksum]
        elif stat.S_ISDIR(mode):
            rows[relative] = ["directory", stat.S_IMODE(mode)]
        else:
            raise CacheRefused(f"dependency-cache-special-file:{relative}")
    return rows


def validate(gate, image, entry):
    start = time.monotonic()
    entry = Path(entry)
    if entry.is_symlink():
        raise CacheRefused("dependency-cache-entry-symlink")
    try:
        record = json.loads((entry / "inventory.json").read_text())
    except OSError, ValueError:
        raise CacheRefused("dependency-cache-incomplete") from None
    if not isinstance(record, dict) or record.get("inputs") != key_inputs(gate, image):
        raise CacheRefused("dependency-cache-key-mismatch")
    root = entry / "project"
    if record.get("inventory") != inventory(root):
        raise CacheRefused("dependency-cache-content-mismatch")
    for name, content in project_files(gate).items():
        if (root / name).read_text() != content:
            raise CacheRefused(f"dependency-cache-config-mismatch:{name}")
    if (root / ".lake/package-overrides.json").exists():
        raise CacheRefused("dependency-cache-overrides-refused")
    solutionbuild._dependency_packages(root, gate.lake_manifest, gate.lean)
    lg.info("validated", key=entry.name, seconds=time.monotonic() - start)
    return record["inventory"]


@contextmanager
def population_lock(cache, key, *, timeout_s=1000):
    with (cache / f"{key}.lock").open("a") as lock:
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise CacheRefused("dependency-cache-lock-timeout") from None
                time.sleep(0.1)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def prepare(gate, image, cache):
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    key = cache_key(gate, image)
    entry = cache / key
    with population_lock(cache, key):
        if entry.exists() or entry.is_symlink():
            validate(gate, image, entry)
            lg.info("hit", key=key)
            return entry
        start = time.monotonic()
        container.assert_pinned(gate, image)
        partial = Path(tempfile.mkdtemp(prefix=f".partial-{key}-", dir=cache))
        work = Path(tempfile.mkdtemp(prefix="linux-mathlib-"))
        for name, content in project_files(gate).items():
            (work / name).write_text(content)
        result = container.run(
            image.context,
            image.image_id,
            ["lake", f"+{gate.lean['toolchain']}", "exe", "cache", "get", *MODULES],
            mounts=((work, "/project", "readonly=false"),),
            workdir="/project",
            user=container.host_user(),
            env=(("HOME", "/project"),),
            network="bridge",
        )
        lg.info("provisioned", rc=result.rc, stdout=result.stdout[-1500:], stderr=result.stderr[-1500:])
        lean.require_success(result)
        packages = solutionbuild._dependency_packages(work, gate.lake_manifest, gate.lean)
        root = partial / "project"
        root.mkdir()
        for name, content in project_files(gate).items():
            if (work / name).read_text() != content:
                raise CacheRefused(f"dependency-cache-provision-config-changed:{name}")
            (root / name).write_text(content)
        for package in packages:
            shutil.copytree(package, root / ".lake/packages" / package.name, symlinks=True)
        record = {"inputs": key_inputs(gate, image), "inventory": inventory(root)}
        (partial / "inventory.json").write_text(json.dumps(record, sort_keys=True) + "\n")
        validate(gate, image, partial)
        partial.rename(entry)
        lg.info("published", key=key, seconds=time.monotonic() - start, work=str(work))
        return entry


def restore(gate, image, cache, destination):
    entry = Path(cache) / cache_key(gate, image)
    expected = validate(gate, image, entry)
    start = time.monotonic()
    destination = Path(destination)
    shutil.copytree(entry / "project", destination, symlinks=True)
    if inventory(destination) != expected:
        raise CacheRefused("dependency-cache-copy-mismatch")
    solutionbuild._dependency_packages(destination, gate.lake_manifest, gate.lean)
    lg.info("copied", key=entry.name, seconds=time.monotonic() - start, destination=str(destination))
    return destination


def image_record(gate, cache):
    return Path(cache) / f"image-{gate.container_identity}.json"


def recorded_image(gate, cache):
    record_path = image_record(gate, cache)
    try:
        record_info = record_path.lstat()
        if not stat.S_ISREG(record_info.st_mode):
            raise CacheRefused("dependency-cache-image-unavailable")
        record = json.loads(record_path.read_text())
    except OSError, ValueError:
        raise CacheRefused("dependency-cache-image-unavailable") from None
    if (
        not isinstance(record, dict)
        or record.get("identity") != gate.container_identity
        or not isinstance(record.get("image_id"), str)
        or not container.IMAGE_ID_RE.fullmatch(record["image_id"])
    ):
        raise CacheRefused("dependency-cache-image-mismatch")
    ctx = container.context()
    return container.Image(
        gate.container_identity, container.image_tag(gate.container_identity), record["image_id"], ctx
    )


def cached_image(gate, cache):
    image = recorded_image(gate, cache)
    if container.image_id(image.context, image.image_id) != image.image_id:
        raise CacheRefused("dependency-cache-image-mismatch")
    container.assert_pinned(gate, image)
    return image


def remember_image(gate, image, cache):
    validate(gate, image, Path(cache) / cache_key(gate, image))
    container.assert_pinned(gate, image)
    record = image_record(gate, cache)
    if record.exists():
        if cached_image(gate, cache).image_id != image.image_id:
            raise CacheRefused("dependency-cache-image-record-conflict")
        return
    with tempfile.NamedTemporaryFile(mode="w", dir=cache, prefix=".image-", delete=False) as stream:
        json.dump({"identity": image.identity, "image_id": image.image_id}, stream)
    Path(stream.name).rename(record)


def archive_metadata_path(archive):
    archive = Path(archive)
    return archive.with_name(archive.name + ".metadata.json")


def archive_info(path):
    path = Path(path)
    try:
        details = path.lstat()
        if not stat.S_ISREG(details.st_mode):
            raise CacheRefused("dependency-cache-archive-invalid")
        with path.open("rb") as stream:
            checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError:
        raise CacheRefused("dependency-cache-archive-unavailable") from None
    return {"archive_sha256": checksum, "archive_size": details.st_size}


def _archive_metadata(gate, image, info):
    return {
        "archive_sha256": info["archive_sha256"],
        "archive_size": info["archive_size"],
        "container_identity": gate.container_identity,
        "image_id": image.image_id,
        "layout": ARCHIVE_LAYOUT,
        "schema": 1,
    }


def _read_archive_metadata(path):
    path = Path(path)
    try:
        details = path.lstat()
        if not stat.S_ISREG(details.st_mode):
            raise CacheRefused("dependency-cache-archive-metadata-invalid")
        text = path.read_text()
        metadata = json.loads(text)
    except OSError, ValueError:
        raise CacheRefused("dependency-cache-archive-metadata-unavailable") from None
    fields = {
        "archive_sha256",
        "archive_size",
        "container_identity",
        "image_id",
        "layout",
        "schema",
    }
    if not isinstance(metadata, dict) or set(metadata) != fields:
        raise CacheRefused("dependency-cache-archive-metadata-invalid")
    if json.dumps(metadata, sort_keys=True) + "\n" != text:
        raise CacheRefused("dependency-cache-archive-metadata-invalid")
    if (
        type(metadata["schema"]) is not int
        or metadata["schema"] != 1
        or not isinstance(metadata["archive_size"], int)
        or isinstance(metadata["archive_size"], bool)
        or metadata["archive_size"] < 1
        or not isinstance(metadata["archive_sha256"], str)
        or len(metadata["archive_sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in metadata["archive_sha256"])
        or not isinstance(metadata["container_identity"], str)
        or not isinstance(metadata["image_id"], str)
    ):
        raise CacheRefused("dependency-cache-archive-metadata-invalid")
    return metadata


def _validate_archive(gate, image, archive, metadata_path):
    metadata = _read_archive_metadata(metadata_path)
    if metadata["container_identity"] != gate.container_identity or metadata["image_id"] != image.image_id:
        raise CacheRefused("dependency-cache-archive-identity-mismatch")
    if metadata["layout"] != ARCHIVE_LAYOUT:
        raise CacheRefused("dependency-cache-archive-layout-mismatch")
    info = archive_info(archive)
    if metadata["archive_size"] != info["archive_size"]:
        raise CacheRefused("dependency-cache-archive-size-mismatch")
    if metadata["archive_sha256"] != info["archive_sha256"]:
        raise CacheRefused("dependency-cache-archive-digest-mismatch")
    return metadata


def _archive_pair_exists(archive, metadata_path):
    archive_exists = archive.exists() or archive.is_symlink()
    metadata_exists = metadata_path.exists() or metadata_path.is_symlink()
    return archive_exists, metadata_exists


def _archive_staging_directory(cache, archive):
    cache_root = cache.resolve()
    archive_parent = archive.parent.resolve()
    for parent in (archive_parent, *archive_parent.parents):
        if not parent.is_relative_to(cache_root):
            return Path(tempfile.mkdtemp(prefix="cairn-linux-dependency-archive-", dir=parent))
    raise CacheRefused("dependency-cache-archive-staging-unavailable")


def export_archive(gate, image, cache, archive):
    cache = Path(cache)
    archive = Path(archive)
    metadata_path = archive_metadata_path(archive)
    cache.mkdir(parents=True, exist_ok=True)
    archive.parent.mkdir(parents=True, exist_ok=True)
    with population_lock(cache, f"image-{gate.container_identity}"):
        current = cached_image(gate, cache)
        if image.identity != gate.container_identity or image.image_id != current.image_id:
            raise CacheRefused("dependency-cache-image-mismatch")
        entry = cache / cache_key(gate, current)
        validate(gate, current, entry)
        archive_exists, metadata_exists = _archive_pair_exists(archive, metadata_path)
        if archive_exists or metadata_exists:
            if not archive_exists or not metadata_exists:
                raise CacheRefused("dependency-cache-archive-conflict")
            _validate_archive(gate, current, archive, metadata_path)
            lg.info("archive_hit", image_id=current.image_id, archive=str(archive))
            return archive
        staging_directory = _archive_staging_directory(cache, archive)
        temporary_archive = staging_directory / "image.tar"
        temporary_metadata = staging_directory / "metadata.json"
        try:
            result = container.run_docker(
                current.context, "image", "save", "--output", str(temporary_archive), current.image_id
            )
        except (lean.LeanMissing, lean.LeanTimeout, OSError) as exc:
            raise CacheRefused(f"dependency-cache-archive-save-failed:{type(exc).__name__}") from None
        if result.rc != 0:
            raise CacheRefused(f"dependency-cache-archive-save-failed:rc={result.rc}")
        metadata = _archive_metadata(gate, current, archive_info(temporary_archive))
        try:
            with temporary_metadata.open("x") as stream:
                stream.write(json.dumps(metadata, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary_archive, archive)
            os.link(temporary_metadata, metadata_path)
        except FileExistsError:
            raise CacheRefused("dependency-cache-archive-conflict") from None
        except OSError as exc:
            raise CacheRefused(f"dependency-cache-archive-publish-failed:{type(exc).__name__}") from None
        lg.info("archive_published", image_id=current.image_id, archive=str(archive))
        return archive


def import_archive(gate, cache, archive):
    cache = Path(cache)
    archive = Path(archive)
    metadata_path = archive_metadata_path(archive)
    if cache.is_symlink() or not cache.is_dir():
        raise CacheRefused("dependency-cache-image-unavailable")
    with population_lock(cache, f"image-{gate.container_identity}"):
        expected = recorded_image(gate, cache)
        _validate_archive(gate, expected, archive, metadata_path)
        try:
            result = container.run_docker(expected.context, "load", "--input", str(archive))
        except (lean.LeanMissing, lean.LeanTimeout, OSError) as exc:
            raise CacheRefused(f"dependency-cache-archive-load-failed:{type(exc).__name__}") from None
        if result.rc != 0:
            raise CacheRefused(f"dependency-cache-archive-load-failed:rc={result.rc}")
        try:
            image = cached_image(gate, cache)
        except (
            CacheRefused,
            container.ContainerError,
            lean.LeanMissing,
            lean.LeanPinMismatch,
            lean.LeanRejected,
            lean.LeanTimeout,
            OSError,
        ):
            raise CacheRefused("dependency-cache-import-image-validation-failed") from None
        if image.image_id != expected.image_id:
            raise CacheRefused("dependency-cache-import-image-validation-failed")
        try:
            entry = cache / cache_key(gate, image)
            validate(gate, image, entry)
        except CacheRefused, OSError, ValueError:
            raise CacheRefused("dependency-cache-import-entry-invalid") from None
        lg.info("archive_imported", image_id=image.image_id, archive=str(archive))
        return image


def main():
    parser = argparse.ArgumentParser(description="Provision dependency-only Linux test artifacts; never proof verdicts")
    parser.add_argument("--cache", required=True, type=Path)
    transport = parser.add_mutually_exclusive_group()
    transport.add_argument("--export-archive", type=Path)
    transport.add_argument("--import-archive", type=Path)
    args = parser.parse_args()
    log.configure()
    root = Path(tempfile.mkdtemp(prefix="cairn-linux-dependency-bundle-"))
    database, pin = root / "bundle.sqlite", root / "bundle.pin"
    bundle.build(lean.REPO_ROOT / "bundle", database)
    bundle.write_pin(database, pin)
    gate = bundle.GateBundle.open(database, pin)
    if args.import_archive:
        image = import_archive(gate, args.cache, args.import_archive)
        entry = args.cache / cache_key(gate, image)
        lean.require_success(
            container.run_docker(
                image.context, "tag", image.image_id, f"cairn-linux-dependencies:{cache_key(gate, image)}"
            )
        )
    else:
        args.cache.mkdir(parents=True, exist_ok=True)
        with population_lock(args.cache, f"image-{gate.container_identity}"):
            image = (
                cached_image(gate, args.cache)
                if image_record(gate, args.cache).exists()
                else container.build(container.context(), gate.container_identity)
            )
            lean.require_success(
                container.run_docker(
                    image.context, "tag", image.image_id, f"cairn-linux-dependencies:{cache_key(gate, image)}"
                )
            )
            entry = prepare(gate, image, args.cache)
            remember_image(gate, image, args.cache)
        if args.export_archive:
            export_archive(gate, image, args.cache, args.export_archive)
    print(json.dumps({"cache": str(args.cache.resolve()), "entry": str(entry.resolve()), "image_id": image.image_id}))


if __name__ == "__main__":
    main()
