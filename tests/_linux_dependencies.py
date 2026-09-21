import argparse
import fcntl
import hashlib
import json
import shutil
import stat
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

from cairn import bundle, container, lean, log, solutionbuild

MODULES = ("Mathlib.AlgebraicGeometry.EllipticCurve.Affine.Point",)
CACHE_ENV = "CAIRN_LINUX_DEPENDENCY_CACHE"
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


def cached_image(gate, cache):
    try:
        record = json.loads(image_record(gate, cache).read_text())
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
    image = container.Image(
        gate.container_identity, container.image_tag(gate.container_identity), record["image_id"], ctx
    )
    if container.image_id(ctx, image.image_id) != image.image_id:
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


def main():
    parser = argparse.ArgumentParser(description="Provision dependency-only Linux test artifacts; never proof verdicts")
    parser.add_argument("--cache", required=True, type=Path)
    args = parser.parse_args()
    log.configure()
    root = Path(tempfile.mkdtemp(prefix="cairn-linux-dependency-bundle-"))
    database, pin = root / "bundle.sqlite", root / "bundle.pin"
    bundle.build(lean.REPO_ROOT / "bundle", database)
    bundle.write_pin(database, pin)
    gate = bundle.GateBundle.open(database, pin)
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
    print(json.dumps({"cache": str(args.cache.resolve()), "entry": str(entry.resolve()), "image_id": image.image_id}))


if __name__ == "__main__":
    main()
