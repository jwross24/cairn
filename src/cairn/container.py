import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from cairn import canon, lean, log

SPEC_PATH = lean.REPO_ROOT / "bundle" / "container.json"
CONTAINERFILE_PATH = lean.REPO_ROOT / "bundle" / "Containerfile"
SPEC_KIND = "container"
FILE_KIND = "container_file"
TAG_CONTAINER_IDENTITY = "cairn/container-identity/v1"
DEV_ARM = "dev-macos-fake-landrun"
GOLD_ARM = "gold-linux-container"
ARMS = (DEV_ARM, GOLD_ARM)
IMAGE_REPOSITORY = "cairn-gate"
TAG_CHARS = 16
DOCKER = shutil.which("docker") or "/usr/local/bin/docker"
CONTEXT_ENV = "CAIRN_CONTAINER_CONTEXT"
BUILD_TIMEOUT_S = 3600.0
RUN_TIMEOUT_S = 900.0
ARG_RE = re.compile(r"^ARG ([A-Z0-9_]+)=(\S+)$", re.MULTILINE)
FROM_RE = re.compile(r"^FROM (\S+)@(sha256:[0-9a-f]{64})$", re.MULTILINE)
IMAGE_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

lg = log.get("container")


class ContainerError(RuntimeError):
    pass


class ArmUnknown(ContainerError):
    def __init__(self, arm):
        super().__init__(f"gate run names arm {arm!r}; a formalization gate run names one of {ARMS}")
        self.arm = arm


class DaemonUnavailable(ContainerError):
    pass


class BuildFailed(ContainerError):
    def __init__(self, run):
        super().__init__(f"container build exited {run.rc}: {run.stderr[-2000:]}")
        self.run = run


@dataclass(frozen=True)
class Image:
    identity: str
    tag: str
    image_id: str
    context: str | None


def assert_arm(arm):
    if arm not in ARMS:
        raise ArmUnknown(arm)
    return arm


def spec():
    return json.loads(SPEC_PATH.read_text())


def containerfile_text():
    return CONTAINERFILE_PATH.read_text()


def containerfile_bytes():
    return CONTAINERFILE_PATH.read_bytes()


def identity(spec_canonical, containerfile):
    # canonical bytes are self-delimiting, so the concatenation is unambiguous
    return canon.digest(TAG_CONTAINER_IDENTITY, bytes(spec_canonical) + bytes(containerfile))


def image_tag(identity_hash):
    return f"{IMAGE_REPOSITORY}:{identity_hash[:TAG_CHARS]}"


def containerfile_args(text):
    return dict(ARG_RE.findall(text))


def containerfile_base(text):
    match = FROM_RE.search(text)
    if match is None:
        raise ContainerError("Containerfile does not pin its base image by digest")
    return {"ref": match.group(1), "digest": match.group(2)}


def pinned_args(spec_obj):
    toolchain, elan, landrun, comparator = (
        spec_obj["toolchain"],
        spec_obj["elan"],
        spec_obj["landrun"],
        spec_obj["comparator"],
    )
    return {
        "APT_SNAPSHOT": spec_obj["apt_snapshot"],
        "ELAN_VERSION": elan["version"],
        "ELAN_ASSET": elan["asset"],
        "ELAN_SHA256": elan["sha256"],
        "LEAN_TOOLCHAIN": toolchain["name"],
        "LEAN_COMMIT": toolchain["lean_commit"],
        "LEAN_ASSET": toolchain["asset"],
        "LEAN_SHA256": toolchain["sha256"],
        "LANDRUN_VERSION": landrun["version"],
        "LANDRUN_ASSET": landrun["asset"],
        "LANDRUN_SHA256": landrun["sha256"],
        "COMPARATOR_REV": comparator["rev"],
    }


def context():
    return os.environ.get(CONTEXT_ENV) or None


def docker_argv(ctx, *args):
    prefix = [DOCKER] + (["--context", ctx] if ctx else [])
    return [*prefix, *args]


def run_docker(ctx, *args, timeout_s=RUN_TIMEOUT_S):
    return lean.run_argv(docker_argv(ctx, *args), timeout_s=timeout_s)


def daemon_info(ctx):
    try:
        result = run_docker(
            ctx, "info", "--format", "{{.ServerVersion}} {{.KernelVersion}} {{.OperatingSystem}}", timeout_s=60
        )
    except lean.LeanMissing as exc:
        raise DaemonUnavailable(f"docker client absent: {exc}") from None
    if result.rc != 0:
        raise DaemonUnavailable(
            f"docker daemon unreachable on context {ctx or 'default'}: {result.stderr.strip()[-400:]}"
        )
    return result.stdout.strip()


def build(ctx, identity_hash, *, spec_obj=None, timeout_s=BUILD_TIMEOUT_S):
    spec_obj = spec_obj or spec()
    tag = image_tag(identity_hash)
    result = run_docker(
        ctx,
        "build",
        "--platform",
        spec_obj["platform"],
        "--file",
        str(CONTAINERFILE_PATH),
        "--tag",
        tag,
        str(CONTAINERFILE_PATH.parent),
        timeout_s=timeout_s,
    )
    if result.rc != 0:
        lg.info("build_failed", tag=tag, rc=result.rc, wall_ms=result.wall_ms)
        raise BuildFailed(result)
    image = Image(identity_hash, tag, image_id(ctx, tag), ctx)
    lg.info("built", identity=identity_hash, tag=tag, image_id=image.image_id, wall_ms=result.wall_ms)
    return image


def image_id(ctx, tag):
    result = run_docker(ctx, "image", "inspect", "--format", "{{.Id}}", tag, timeout_s=60)
    if result.rc != 0 or not IMAGE_ID_RE.match(result.stdout.strip()):
        raise ContainerError(f"image {tag} has no inspectable id: rc={result.rc} stdout={result.stdout!r}")
    return result.stdout.strip()


def run(
    ctx, image, argv, *, user=None, cap_add=(), mounts=(), workdir=None, env=(), network="none", timeout_s=RUN_TIMEOUT_S
):
    args = ["run", "--rm", "--network", network]
    if user:
        args += ["--user", user]
    for cap in cap_add:
        args += ["--cap-add", cap]
    for host, guest, mode in mounts:
        args += ["--mount", f"type=bind,source={Path(host).resolve()},target={guest},{mode}"]
    if workdir:
        args += ["--workdir", workdir]
    for name, value in env:
        args += ["--env", f"{name}={value}"]
    tag = image.tag if isinstance(image, Image) else image
    return run_docker(ctx, *args, tag, *argv, timeout_s=timeout_s)
