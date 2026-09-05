import contextlib
import json
import os
import signal
import stat
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from cairn import canon, cli, escrow, exits, keys, log
from cairn.errors import CliError
from cairn.substrate import blob_hash

LOG_STEP = "runner"
SCRUB_PREFIX = "CAIRN_DB"
HARNESS_ONLY_KEYS = ("receipt",)
SKILL_STATUSES = ("OK", "FAIL", "DISAGREE")
STATUS_OK = "OK"
STATUS_FAIL = "FAIL"
STATUS_DISAGREE = "DISAGREE"
STATUS_BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
STATUS_BLOCKED = "BLOCKED"
STATUS_SKILL_YANKED = "SKILL_YANKED"
STATUS_INTERRUPTED = "INTERRUPTED"
ENV_ALLOWLIST = ("PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "TZ")
MAXRSS_UNIT_BYTES = ("darwin",)
MAXRSS_UNIT_KB = ("linux", "freebsd", "openbsd", "netbsd", "sunos")
TICK_S = 0.005
GRACE_S = 0.25
WALL_CAP_MULTIPLIER = 4.0
WALL_CAP_FLOOR_S = 120.0
UTF8_BOM = b"\xef\xbb\xbf"


@dataclass(frozen=True)
class ParsedOutput:
    well_formed: bool
    status: str | None = None
    reason: str | None = None
    document: dict = field(default_factory=dict)

    @classmethod
    def of(cls, document, status):
        return cls(True, status, None, document)

    @classmethod
    def malformed(cls, reason):
        return cls(False, None, reason, {})


def _decoded(stdout_bytes):
    if stdout_bytes.startswith(UTF8_BOM):
        raise ValueError("stdout starts with a UTF-8 BOM")
    return stdout_bytes.decode("utf-8")


def _reject_constant(token):
    raise ValueError(f"stdout carries the non-JSON constant {token}")


def parse_skill_output(stdout_bytes):
    try:
        text = _decoded(stdout_bytes)
    except (UnicodeDecodeError, ValueError) as exc:
        return ParsedOutput.malformed(str(exc))
    if not text.strip():
        return ParsedOutput.malformed("stdout is empty")
    try:
        document, end = json.JSONDecoder(parse_constant=_reject_constant).raw_decode(text)
    except RecursionError:
        return ParsedOutput.malformed("stdout nests deeper than the decoder allows")
    except (ValueError, TypeError) as exc:
        return ParsedOutput.malformed(f"stdout is not one JSON document: {exc}")
    if text[end:].strip():
        return ParsedOutput.malformed("stdout carries trailing bytes after the document")
    if not isinstance(document, dict):
        return ParsedOutput.malformed(f"stdout is not a JSON object, got {type(document).__name__}")
    status = document.get("status")
    if status not in SKILL_STATUSES:
        return ParsedOutput.malformed(f"status must be one of {SKILL_STATUSES}, got {status!r}")
    return ParsedOutput.of({k: v for k, v in document.items() if k not in HARNESS_ONLY_KEYS}, status)


def status_for(parsed, exit_status, cpu_s, ceiling_s, *, wall_capped=False):
    if ceiling_s is not None and cpu_s > ceiling_s:
        return STATUS_BUDGET_EXCEEDED
    if wall_capped:
        return STATUS_BLOCKED
    if exit_status != 0:
        return STATUS_FAIL
    if not parsed.well_formed:
        return STATUS_FAIL
    if parsed.status == STATUS_DISAGREE:
        return STATUS_DISAGREE
    if parsed.status == STATUS_OK:
        return STATUS_OK
    return STATUS_FAIL


def ceiling_for(declared_expectation_s, ceiling_multiplier):
    return float(ceiling_multiplier) * float(declared_expectation_s)


def wall_cap_for(ceiling_s, wall_cap_multiplier=WALL_CAP_MULTIPLIER, wall_cap_floor_s=WALL_CAP_FLOOR_S):
    if ceiling_s is None:
        return None
    ceiling_s = float(ceiling_s)
    return max(float(wall_cap_multiplier) * ceiling_s, ceiling_s + float(wall_cap_floor_s))


def child_env(extra=None, base=None):
    source = os.environ if base is None else base
    env = {k: v for k, v in source.items() if k in ENV_ALLOWLIST}
    for key, value in dict(extra or {}).items():
        if key.startswith(SCRUB_PREFIX):
            raise ValueError(f"{key} would hand the child a substrate path")
        env[key] = value
    return env


def maxrss_bytes(ru_maxrss, platform=None):
    plat = sys.platform if platform is None else platform
    if plat in MAXRSS_UNIT_BYTES:
        return int(ru_maxrss)
    if plat.startswith(MAXRSS_UNIT_KB):
        return int(ru_maxrss) * 1024
    raise NotImplementedError(f"ru_maxrss units are unknown for {plat!r}")


def tool_digests_hash(tool_digests):
    return keys.node_hash(
        "tool_digests",
        canon.encode(canon.Map(canon.STR, canon.STR), dict(tool_digests)),
    )


def skill_argv(module, scratch_dir):
    return [sys.executable, "-m", str(module), str(scratch_dir)]


def allocated_bytes(root):
    total = 0
    for dirpath, _, filenames in os.walk(root, followlinks=False):
        total += os.lstat(dirpath).st_blocks * 512
        for name in filenames:
            total += os.lstat(Path(dirpath) / name).st_blocks * 512
    return total


def _signal_group(pgid, pid, sig):
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError, PermissionError:
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, sig)


@dataclass(frozen=True)
class Launch:
    exit_status: int
    start_mono: float
    end_mono: float
    wall_s: float
    cpu_user_s: float
    cpu_sys_s: float
    peak_rss_bytes: int
    timed_out: bool
    argv: tuple


def spawn_and_wait(
    argv,
    out_path,
    err_path,
    *,
    wall_cap_s,
    env,
    stdin_bytes=b"",
    tick=TICK_S,
    grace=GRACE_S,
):
    lg = log.get(LOG_STEP)
    lg.debug("spawn", argv=list(argv), stdin_digest=blob_hash(stdin_bytes))
    stdin_path = Path(out_path).with_name("stdin")
    Path(stdin_path).write_bytes(stdin_bytes)
    handle_out = Path(out_path).open("wb", buffering=0)
    handle_err = Path(err_path).open("wb", buffering=0)
    handle_in = stdin_path.open("rb")
    try:
        start = time.monotonic()
        proc = subprocess.Popen(
            list(argv),
            stdin=handle_in,
            stdout=handle_out,
            stderr=handle_err,
            env=env,
            start_new_session=True,
            close_fds=True,
        )
        pgid = proc.pid
        reaped = False
        terminated_at = None
        status = 0
        usage = None
        try:
            while True:
                pid, status, usage = os.wait4(proc.pid, os.WNOHANG)
                if pid == proc.pid:
                    reaped = True
                    break
                elapsed = time.monotonic() - start
                if wall_cap_s is not None and terminated_at is None and elapsed >= wall_cap_s:
                    terminated_at = elapsed
                    _signal_group(pgid, proc.pid, signal.SIGTERM)
                elif terminated_at is not None and elapsed >= terminated_at + grace:
                    _signal_group(pgid, proc.pid, signal.SIGKILL)
                remaining = tick if wall_cap_s is None else min(tick, max(0.0, wall_cap_s - elapsed))
                time.sleep(remaining or tick)
        finally:
            if not reaped:
                _signal_group(pgid, proc.pid, signal.SIGKILL)
                _, status, usage = os.wait4(proc.pid, 0)
        _signal_group(pgid, proc.pid, signal.SIGKILL)
        end = time.monotonic()
        proc.returncode = os.waitstatus_to_exitcode(status)
    finally:
        handle_out.close()
        handle_err.close()
        handle_in.close()
    launch = Launch(
        exit_status=proc.returncode,
        start_mono=start,
        end_mono=end,
        wall_s=end - start,
        cpu_user_s=usage.ru_utime,
        cpu_sys_s=usage.ru_stime,
        peak_rss_bytes=maxrss_bytes(usage.ru_maxrss),
        timed_out=terminated_at is not None,
        argv=tuple(argv),
    )
    lg.info(
        "exit",
        rc=launch.exit_status,
        wall_ms=round(launch.wall_s * 1000, 3),
        cpu_s=round(launch.cpu_user_s + launch.cpu_sys_s, 6),
        rss=launch.peak_rss_bytes,
        timed_out=terminated_at is not None,
    )
    if terminated_at is not None:
        lg.warning(
            "kill",
            wall_cap_s=wall_cap_s,
            terminated_at_s=round(terminated_at, 6),
            wall_s=round(launch.wall_s, 6),
            rc=launch.exit_status,
        )
    return launch


class RunnerError(Exception):
    pass


class BudgetRefused(RunnerError):
    def __init__(self, remaining, ceiling_s):
        self.remaining = remaining
        self.ceiling_s = ceiling_s
        super().__init__(f"remaining budget {remaining} cannot cover the ceiling {ceiling_s}")


@dataclass(frozen=True)
class Attempt:
    attempt_id: str
    recipe_key: str
    status: str
    output_manifest_hash: str | None = None
    receipt_hash: str | None = None
    served_from_cache: bool = False
    launch: Launch | None = None
    parsed: ParsedOutput | None = None
    diverged: tuple = ()


def running_attempts(sub):
    rows = sub.conn.execute(
        "SELECT attempt_id FROM attempts WHERE status = 'RUNNING' AND ended_at IS NULL ORDER BY rowid"
    ).fetchall()
    return [row["attempt_id"] for row in rows]


def startup_scan(sub, *, at=None, dry_run=False):
    interrupted = running_attempts(sub)
    if not dry_run:
        for attempt_id in interrupted:
            sub.close_attempt(attempt_id, STATUS_INTERRUPTED, ended_at=at)
            escrow.settle_on_close(sub, attempt_id, STATUS_INTERRUPTED, at=at)
    log.get(LOG_STEP).info(
        "startup_scan",
        interrupted=interrupted,
        count=len(interrupted),
        dry_run=dry_run,
    )
    return interrupted


def _artifacts(sub, stdout_bytes, scratch_dir):
    lg = log.get(LOG_STEP)
    artifacts = {"output.json": (sub.put_blob(stdout_bytes), len(stdout_bytes))}
    root = Path(scratch_dir)
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in sorted(dirnames + filenames):
            path = Path(dirpath) / name
            if not stat.S_ISREG(os.lstat(path).st_mode):
                lg.warning(
                    "artifact_skipped",
                    path=str(path.relative_to(root)),
                    reason="not a regular file",
                )
                continue
            data = path.read_bytes()
            artifacts[str(path.relative_to(root))] = (sub.put_blob(data), len(data))
    return artifacts


def _diverged(sub, recipe_key):
    rows = sub.conn.execute(
        "SELECT output_manifest_hash FROM attempts WHERE recipe_key = ? AND status = 'OK' AND disowned_at IS NULL AND replay_grade = 'Replayable'",
        (recipe_key,),
    ).fetchall()
    manifests = {r["output_manifest_hash"] for r in rows if r["output_manifest_hash"]}
    if len(manifests) < 2:
        return ()
    return tuple(sub.mark_non_reproducible(recipe_key))


def launch(
    sub,
    skill_module,
    recipe,
    *,
    bundle_hash,
    evaluation,
    ceiling_multiplier,
    tool_digests,
    scratch_root,
    wall_cap_multiplier=WALL_CAP_MULTIPLIER,
    wall_cap_floor_s=WALL_CAP_FLOOR_S,
    replay="Replayable",
    skip_cache_lookup=False,
    do_not_cache=False,
    budget_remaining=None,
    env_extra=None,
    stdin_document=None,
):
    lg = log.get(LOG_STEP)
    startup_scan(sub)
    ceiling_s = ceiling_for(evaluation.expected_wall_s, ceiling_multiplier)
    wall_cap_s = wall_cap_for(ceiling_s, wall_cap_multiplier, wall_cap_floor_s)
    if budget_remaining is not None and budget_remaining < ceiling_s:
        raise BudgetRefused(budget_remaining, ceiling_s)
    recipe_key = sub.put_recipe(recipe, do_not_cache=do_not_cache)
    if not skip_cache_lookup:
        served = sub.serve(recipe_key)
        if served is not None:
            lg.info(
                "launch",
                recipe_key=recipe_key,
                served=True,
                attempt_id=served.attempt_id,
            )
            return Attempt(
                served.attempt_id,
                recipe_key,
                STATUS_OK,
                served.output_manifest_hash,
                served_from_cache=True,
            )
    attempt_id = sub.start_attempt(recipe_key, replay_grade=replay, skip_cache_lookup=skip_cache_lookup)
    sub.add_escrow(
        attempt_id,
        declared_production_cost=evaluation.expected_core_s,
        declared_verification_cost=evaluation.expected_verification_core_s,
        reserved=evaluation.expected_verification_core_s,
        ceiling_multiplier=float(ceiling_multiplier),
    )
    try:
        attempt_dir = Path(scratch_root) / attempt_id
        scratch_dir = attempt_dir / "scratch"
        scratch_dir.mkdir(parents=True)
        out_path, err_path = attempt_dir / "stdout", attempt_dir / "stderr"
        document = {} if stdin_document is None else stdin_document
        stdin_bytes = (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        before = allocated_bytes(scratch_dir)
        run = spawn_and_wait(
            skill_argv(skill_module, scratch_dir),
            out_path,
            err_path,
            wall_cap_s=wall_cap_s,
            env=child_env(env_extra),
            stdin_bytes=stdin_bytes,
        )
        scratch_written = max(0, allocated_bytes(scratch_dir) - before)
        stdout_bytes, stderr_bytes = out_path.read_bytes(), err_path.read_bytes()
        parsed = parse_skill_output(stdout_bytes)
        status = status_for(
            parsed,
            run.exit_status,
            run.cpu_user_s + run.cpu_sys_s,
            ceiling_s,
            wall_capped=run.timed_out,
        )
        manifest = None
        if parsed.well_formed:
            manifest = sub.put_output_manifest(
                _artifacts(sub, stdout_bytes, scratch_dir),
                recipe_key=recipe_key,
                input_blobs=[h for h, _ in recipe["inputs"].values()],
                producer_identity=recipe["skill_identity_hash"],
                replay_grade=replay,
            )
        receipt = sub.put_receipt(
            {
                "gate_bundle_hash": bundle_hash,
                "start_mono": run.start_mono,
                "end_mono": run.end_mono,
                "cpu_user_s": run.cpu_user_s,
                "cpu_sys_s": run.cpu_sys_s,
                "wall_s": run.wall_s,
                "peak_rss_bytes": run.peak_rss_bytes,
                "scratch_bytes_written": scratch_written,
                "exit_status": run.exit_status,
                "stdout_digest": blob_hash(stdout_bytes),
                "stderr_digest": blob_hash(stderr_bytes),
                "tool_digests_hash": tool_digests_hash(tool_digests),
            }
        )
        sub.close_attempt(attempt_id, status, output_manifest_hash=manifest, receipt_hash=receipt)
        escrow.settle_on_close(sub, attempt_id, status)
        diverged = _diverged(sub, recipe_key) if status == STATUS_OK else ()
        lg.info(
            "launch",
            recipe_key=recipe_key,
            served=False,
            attempt_id=attempt_id,
            status=status,
            wall_ms=round(run.wall_s * 1000, 3),
            cpu_s=round(run.cpu_user_s + run.cpu_sys_s, 6),
            rss=run.peak_rss_bytes,
            scratch_bytes=scratch_written,
            diverged=list(diverged),
        )
        return Attempt(
            attempt_id,
            recipe_key,
            status,
            manifest,
            receipt,
            False,
            run,
            parsed,
            diverged,
        )
    except Exception:
        if sub.get_attempt(attempt_id)["ended_at"] is None:
            sub.close_attempt(attempt_id, STATUS_FAIL)
            escrow.settle_on_close(sub, attempt_id, STATUS_FAIL)
            lg.warning("launch_aborted", attempt_id=attempt_id, recipe_key=recipe_key)
        raise


def _configure(parser):
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="report at most N attempt ids in the document",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would be interrupted and change nothing; the transition is append-only and cannot be undone",
    )


def _run(ns):
    from cairn import substrate

    if not Path(ns.db).exists():
        raise CliError(
            exits.ENVIRONMENT,
            f"the substrate {ns.db} does not exist; a substrate is created by the first command that writes to it",
            where=str(ns.db),
            next_command=f"cairn selftest toy-curve --db {ns.db}",
        )
    dry_run = getattr(ns, "dry_run", False)
    try:
        with substrate.Substrate.open(ns.db) as sub:
            interrupted = startup_scan(sub, dry_run=dry_run)
    except substrate.WriterAlreadyOpen as exc:
        raise CliError(
            exits.CONFLICT,
            f"another writer already holds {ns.db}: {exc}",
            where=str(ns.db),
            next_command=f"cairn startup-scan --db {ns.db} --dry-run",
        ) from None
    shown = interrupted if ns.limit is None else interrupted[: ns.limit]
    if getattr(ns, "json", False):
        cli.emit_json(
            "startup-scan",
            {"interrupted": shown, "count": len(interrupted), "dry_run": dry_run},
        )
    else:
        for attempt_id in shown:
            print(attempt_id)
    return exits.OK


cli.register(
    "startup-scan",
    _configure,
    _run,
    summary="move every attempt left RUNNING by a dead harness to INTERRUPTED before any new launch",
    read_only=False,
    json=True,
)
