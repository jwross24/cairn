import json
import os
import re
import shutil
import uuid
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
CLEANUP_TIMEOUT_S = 60.0
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
    toolchain, elan, go, landrun, comparator = (
        spec_obj["toolchain"],
        spec_obj["elan"],
        spec_obj["go"],
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
        "GO_VERSION": go["version"],
        "GO_ASSET": go["asset"],
        "GO_SHA256": go["sha256"],
        "LANDRUN_VERSION": landrun["version"],
        "LANDRUN_COMMIT": landrun["commit"],
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
    name = "cairn-run-" + uuid.uuid4().hex
    args = ["run", "--rm", "--name", name, "--network", network]
    if user:
        args += ["--user", user]
    for cap in cap_add:
        args += ["--cap-add", cap]
    for host, guest, mode in mounts:
        args += ["--mount", f"type=bind,source={Path(host).absolute()},target={guest},{mode}"]
    if workdir:
        args += ["--workdir", workdir]
    for key, value in env:
        args += ["--env", f"{key}={value}"]
    tag = image.tag if isinstance(image, Image) else image
    try:
        return run_docker(ctx, *args, tag, *argv, timeout_s=timeout_s)
    except lean.LeanTimeout as timeout:
        try:
            stopped = run_docker(ctx, "stop", "--time", "0", name, timeout_s=CLEANUP_TIMEOUT_S)
        except (lean.LeanMissing, lean.LeanTimeout, OSError) as exc:
            lg.info("timeout_cleanup_failed", name=name, context=ctx, reason=str(exc))
            raise ContainerError(f"container-timeout-cleanup-unconfirmed:{name}") from exc
        if stopped.rc != 0:
            lg.info("timeout_cleanup_failed", name=name, context=ctx, rc=stopped.rc, stderr=stopped.stderr)
            raise ContainerError(f"container-timeout-cleanup-unconfirmed:{name}:{stopped.stderr.strip()}") from timeout
        lg.info("timeout_stopped", name=name, context=ctx)
        raise


def host_user():
    uid = os.getuid()
    if uid == 0:
        raise ContainerError("container-host-user-root")
    return f"{uid}:{os.getgid()}"


def assert_pinned(gate, image, *, timeout_s=RUN_TIMEOUT_S):
    if image.identity != gate.container_identity or not IMAGE_ID_RE.fullmatch(image.image_id):
        raise ContainerError("statement-hasher-image-mismatch")
    pins = gate.lean
    user = host_user()
    result = run(
        image.context, image.image_id, ["lean", f"+{pins['toolchain']}", "--version"], user=user, timeout_s=timeout_s
    )
    lean.require_success(result)
    observed = lean.VERSION_RE.match(result.stdout)
    expected = {"version": lean.toolchain_version(pins["toolchain"]), "commit": pins["lean_commit"]}
    if observed is None or any(observed[key] != value for key, value in expected.items()):
        raise lean.LeanPinMismatch(expected, observed.groupdict() if observed else result.stdout)
    if observed["target"] != "aarch64-unknown-linux-gnu":
        raise ContainerError(f"statement-hasher-target-mismatch:{observed['target']}")


def check_axioms(gate, image, module, theorem_names, *, project_dir, work_dir, timeout_s=RUN_TIMEOUT_S):
    if not theorem_names:
        raise lean.LeanRejected("empty-theorem-names")
    assert_pinned(gate, image, timeout_s=timeout_s)
    pins = gate.lean
    root = lean.write_axiom_tool(gate, work_dir)
    project_mount = (project_dir, "/project", "readonly=false")

    def invoke(name, cwd, mounts, **fields):
        tool, *arguments = pins["checker"][name]
        if tool not in lean.TOOLS:
            raise ContainerError(f"axiom-checker-tool-unknown:{tool}")
        argv = [tool, f"+{pins['toolchain']}", *(part.format(**fields) for part in arguments)]
        if name == "axioms":
            argv.extend(theorem_names)
        return run(
            image.context,
            image.image_id,
            argv,
            user=host_user(),
            mounts=mounts,
            workdir=cwd,
            env=(("HOME", cwd),),
            timeout_s=timeout_s,
        )

    lean.require_success(invoke("build", "/axiom-tool", ((root, "/axiom-tool", "readonly=false"),), module="axioms"))
    lean.require_success(invoke("build", "/project", (project_mount,), module=module))
    result = invoke(
        "axioms",
        "/project",
        (project_mount, (root, "/axiom-tool", "readonly=true")),
        module=module,
        executable="/axiom-tool/.lake/build/bin/axioms",
    )
    record = lean.axiom_result(result, theorem_names, pins["permitted_axioms"])
    lg.info("axiom_check", module=module, record=record, image_id=image.image_id, result=result.__dict__)
    return record


def formal_statement_hash(gate, image, module, theorem_names, *, project_dir, work_dir, timeout_s=RUN_TIMEOUT_S):
    assert_pinned(gate, image, timeout_s=timeout_s)
    pins = gate.lean
    user = host_user()
    root = lean.write_statement_tool(gate, work_dir)
    mounts = ((project_dir, "/project", "readonly=false"), (root, "/statement-tool", "readonly=false"))

    def invoke(name, cwd, **fields):
        tool, *arguments = pins["checker"][name]
        if tool not in lean.TOOLS:
            raise ContainerError(f"statement-hasher-tool-unknown:{tool}")
        argv = [tool, f"+{pins['toolchain']}", *(part.format(**fields) for part in arguments)]
        if name == "statement_hash":
            argv.extend(theorem_names)
        return run(
            image.context,
            image.image_id,
            argv,
            user=user,
            mounts=mounts,
            workdir=cwd,
            env=(("HOME", cwd),),
            timeout_s=timeout_s,
        )

    lean.require_success(invoke("build", "/statement-tool", module="statement_hash"))
    lean.require_success(invoke("build", "/project", module=module))
    result = invoke(
        "statement_hash", "/project", module=module, executable="/statement-tool/.lake/build/bin/statement_hash"
    )
    digest = lean.statement_digest(result)
    lg.info(
        "formal_statement_hash",
        module=module,
        theorem_names=theorem_names,
        digest=digest,
        identity=image.identity,
        image_id=image.image_id,
        context=image.context,
        wall_ms=result.wall_ms,
    )
    return digest
