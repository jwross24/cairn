import contextlib
import fcntl
import hashlib
import os
import select
import signal
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from cairn import log, runner

SOURCE = Path(__file__).with_name("rss_reporter.c")
COMPILER = Path("/usr/bin/cc")
CFLAGS = ("-O2", "-std=c11", "-Wall", "-Wextra", "-Werror", "-x", "c", "-")
BUILD_TIMEOUT_S = 20
PROTOCOL_TIMEOUT_S = 5.0
FORBIDDEN_CAPABILITIES = (1 << 19) | (1 << 21)
CAPABILITY_FIELDS = ("CapInh", "CapPrm", "CapEff", "CapAmb")
_build_lock = threading.Lock()
_binary = None
_compiler = None
_build_request = None
F_ADD_SEALS = 1033
F_GET_SEALS = 1034
SEALS = 15
SCM_CREDENTIALS = 2
SO_PASSCRED = 16


class ReporterError(runner.RunnerError, OSError):
    pass


@dataclass(frozen=True)
class Binary:
    fd: int
    source_digest: str
    compiler_digest: str
    binary_digest: str

    @property
    def path(self):
        return f"/proc/self/fd/{self.fd}"


def _seals():
    return SEALS


def _compiler_digest():
    global _compiler
    compiler = COMPILER.resolve(strict=True)
    metadata = compiler.stat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != 0 or metadata.st_mode & 0o022:
        raise ReporterError("RSS compiler is not a protected root-owned executable")
    if not os.access(compiler, os.X_OK):
        raise ReporterError("RSS compiler is not executable")
    fingerprint = (str(compiler), metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns)
    if _compiler is not None and _compiler[0] == fingerprint:
        return _compiler[1]
    digest = hashlib.sha256(compiler.read_bytes()).hexdigest()
    _compiler = (fingerprint, digest)
    return digest


def build_binary():
    global _binary, _build_request
    if sys.platform != "linux":
        raise ReporterError("native RSS reporter requires Linux")
    with _build_lock:
        source = SOURCE.read_bytes()
        source_digest = hashlib.sha256(source).hexdigest()
        compiler_digest = _compiler_digest()
        if _binary is not None:
            if (_binary.source_digest, _binary.compiler_digest) != (source_digest, compiler_digest):
                raise ReporterError("RSS reporter build inputs changed within the process")
            validate_binary(_binary)
            return _binary
        directory = Path(tempfile.mkdtemp(prefix="cairn-rss-build-"))
        target = directory / "reporter"
        began = time.monotonic()
        command = [str(COMPILER), *CFLAGS, "-o", str(target)]
        _build_request = tuple(command)
        try:
            proc = subprocess.Popen(
                command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True
            )
            try:
                _, stderr = proc.communicate(input=source, timeout=BUILD_TIMEOUT_S)
            except BaseException as exc:
                runner._signal_group(proc.pid, proc.pid, signal.SIGKILL)
                proc.communicate(timeout=PROTOCOL_TIMEOUT_S)
                if isinstance(exc, subprocess.TimeoutExpired):
                    raise ReporterError("RSS reporter compiler timed out") from exc
                raise
        finally:
            _build_request = None
        if proc.returncode != 0:
            raise ReporterError(f"RSS reporter compiler failed: {stderr.decode('utf-8', 'replace')}")
        if _compiler_digest() != compiler_digest:
            raise ReporterError("RSS reporter compiler changed during build")
        with target.open("rb") as handle:
            image = handle.read()
        if not image.startswith(b"\x7fELF"):
            raise ReporterError("RSS reporter compiler did not produce an ELF executable")
        fd = os.memfd_create("cairn-rss-reporter", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
        try:
            with os.fdopen(os.dup(fd), "wb") as handle:
                handle.write(image)
            os.fchmod(fd, 0o500)
            fcntl.fcntl(fd, F_ADD_SEALS, _seals())
            binary = Binary(fd, source_digest, compiler_digest, hashlib.sha256(image).hexdigest())
            validate_binary(binary)
        except BaseException:
            os.close(fd)
            raise
        _binary = binary
        log.get("runner").info(
            "rss_reporter_build",
            source_sha256=source_digest,
            compiler_sha256=compiler_digest,
            binary_sha256=binary.binary_digest,
            build_s=time.monotonic() - began,
        )
        return binary


def validate_binary(binary):
    if fcntl.fcntl(binary.fd, F_GET_SEALS) & _seals() != _seals():
        raise ReporterError("RSS reporter executable is not sealed")
    metadata = os.fstat(binary.fd)
    image = os.pread(binary.fd, metadata.st_size, 0)
    if hashlib.sha256(image).hexdigest() != binary.binary_digest:
        raise ReporterError("RSS reporter executable digest mismatch")


def command_is_reporter(args, kwargs):
    if _binary is None or not isinstance(args, (list, tuple)) or len(args) < 4:
        return False
    try:
        validate_binary(_binary)
        if args[0] != _binary.path or args[2] != str(_binary.fd) or kwargs.get("shell"):
            return False
        sender = int(args[1])
        return (
            set(kwargs.get("pass_fds", ())) == {sender, _binary.fd}
            and sender != _binary.fd
            and kwargs.get("executable") is None
            and kwargs.get("close_fds") is True
            and kwargs.get("start_new_session") is True
        )
    except OSError, ValueError, ReporterError:
        return False


def command_is_build(args, kwargs):
    return (
        _build_request is not None
        and isinstance(args, (list, tuple))
        and tuple(args) == _build_request
        and kwargs.get("stdin") == subprocess.PIPE
        and kwargs.get("stdout") == subprocess.PIPE
        and kwargs.get("stderr") == subprocess.PIPE
        and not kwargs.get("shell")
        and kwargs.get("executable") is None
    )


def check_capabilities():
    fields = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines())
    try:
        values = [int(fields[name].strip(), 16) for name in CAPABILITY_FIELDS]
    except (KeyError, ValueError) as exc:
        raise ReporterError("RSS reporter capability boundary is unavailable") from exc
    if any(value & FORBIDDEN_CAPABILITIES for value in values):
        raise ReporterError("RSS reporter refuses CAP_SYS_ADMIN or CAP_SYS_PTRACE")


class Reports:
    def __init__(self, reporter_pid):
        self.reporter_pid = reporter_pid
        self.worker_pid = None
        self.exec_error = None
        self.final = None
        self.exited = False
        self.eof = False

    def accept(self, data, ancillary, flags):
        if flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC):
            raise ReporterError("truncated RSS reporter packet")
        credentials = []
        for level, kind, payload in ancillary:
            if level != socket.SOL_SOCKET or kind != SCM_CREDENTIALS or len(payload) != 12:
                raise ReporterError("invalid RSS reporter credentials")
            credentials.append(struct.unpack("3i", payload))
        if len(credentials) != 1 or credentials[0][0] != self.reporter_pid:
            raise ReporterError("wrong or missing RSS reporter sender")
        try:
            fields = data.decode("ascii").split(" ")
            values = [int(value) for value in fields[1:]]
        except (UnicodeError, ValueError) as exc:
            raise ReporterError("malformed RSS reporter packet") from exc
        if fields[0] == "START" and len(values) == 1 and values[0] > 0:
            if self.worker_pid is None and self.exec_error is None and self.final is None:
                self.worker_pid = values[0]
                return
        elif fields[0] == "EXEC" and len(values) == 2:
            stage, error = values
            if (
                self.worker_pid is not None
                and self.exec_error is None
                and self.final is None
                and stage in (0, 1, 2)
                and error >= 0
                and (stage == 0) == (error == 0)
            ):
                self.exec_error = (stage, error)
                return
        elif fields[0] == "FINAL" and len(values) == 5:
            worker, status, rss, user, system = values
            if (
                self.exec_error is not None
                and self.exited
                and self.final is None
                and worker == self.worker_pid
                and 0 <= status <= 65535
                and rss > 0
                and user >= 0
                and system >= 0
                and (os.WIFEXITED(status) or os.WIFSIGNALED(status))
            ):
                self.final = (status, rss, user, system)
                return
        elif (
            fields[0] == "EXIT"
            and len(values) == 1
            and self.exec_error is not None
            and not self.exited
            and values[0] == self.worker_pid
        ):
            self.exited = True
            return
        raise ReporterError("malformed, duplicate, or out-of-order RSS reporter packet")

    def drain(self, endpoint):
        while not self.eof:
            try:
                data, ancillary, flags, _ = endpoint.recvmsg(256, socket.CMSG_SPACE(12))
            except BlockingIOError:
                return
            for level, kind, payload in ancillary:
                if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                    for offset in range(0, len(payload) - 3, 4):
                        os.close(struct.unpack_from("i", payload, offset)[0])
            if not data:
                self.eof = True
                return
            self.accept(data, ancillary, flags)

    def result(self, reporter_exit):
        if reporter_exit != 0 or not self.eof or self.final is None or self.exec_error is None:
            raise ReporterError("RSS reporter exited without one complete measurement")
        stage, error = self.exec_error
        if stage:
            raise OSError(error, "RSS worker setup failed" if stage == 1 else "RSS worker exec failed")
        return self.final


def _abort(proc, endpoint):
    endpoint.close()
    with contextlib.suppress(ProcessLookupError):
        os.kill(proc.pid, signal.SIGTERM)
    deadline = time.monotonic() + PROTOCOL_TIMEOUT_S
    while True:
        pid, status = os.waitpid(proc.pid, os.WNOHANG)
        if pid == proc.pid:
            proc.returncode = os.waitstatus_to_exitcode(status)
            return
        if time.monotonic() >= deadline:
            proc.kill()
            _, status = os.waitpid(proc.pid, 0)
            proc.returncode = os.waitstatus_to_exitcode(status)
            return
        select.select([], [], [], 0.005)


def spawn_and_wait(argv, out_path, err_path, *, wall_cap_s, env, stdin_bytes, tick, grace, is_yanked):
    from cairn.substrate import blob_hash

    check_capabilities()
    binary = build_binary()
    lg = log.get("runner")
    lg.debug("spawn", argv=list(argv), stdin_digest=blob_hash(stdin_bytes))
    stdin_path = Path(out_path).with_name("stdin")
    stdin_path.write_bytes(stdin_bytes)
    receiver, sender = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    receiver.setsockopt(socket.SOL_SOCKET, SO_PASSCRED, 1)
    receiver.setblocking(False)
    proc = None
    reports = None
    try:
        with (
            stdin_path.open("rb") as handle_in,
            Path(out_path).open("wb", buffering=0) as handle_out,
            Path(err_path).open("wb", buffering=0) as handle_err,
        ):
            start = time.monotonic()
            proc = subprocess.Popen(
                [binary.path, str(sender.fileno()), str(binary.fd), *argv],
                stdin=handle_in,
                stdout=handle_out,
                stderr=handle_err,
                env=env,
                pass_fds=(sender.fileno(), binary.fd),
                start_new_session=True,
                close_fds=True,
            )
            sender.close()
            reports = Reports(proc.pid)
            sampled = runner._PGRP_LISTER is not None
            sampled_extra = False
            terminated_at = None
            timed_out = False
            skill_yanked = False
            final_at = None
            acknowledged = False
            survivors = frozenset()
            while True:
                reports.drain(receiver)
                elapsed = time.monotonic() - start
                worker = reports.worker_pid
                if reports.exited and not acknowledged:
                    survivors = runner._PGRP_LISTER(worker) - {worker} if sampled else frozenset()
                    sampled_extra = sampled_extra or bool(survivors)
                    receiver.send(b"ACK")
                    acknowledged = True
                    final_at = elapsed
                if sampled and worker is not None and not sampled_extra and not acknowledged:
                    sampled_extra = bool(runner._PGRP_LISTER(worker) - {worker})
                if reports.eof:
                    try:
                        proc.wait(timeout=PROTOCOL_TIMEOUT_S)
                    except subprocess.TimeoutExpired as exc:
                        raise ReporterError("RSS reporter exited its channel but did not terminate") from exc
                    break
                if reports.exec_error is None and elapsed >= PROTOCOL_TIMEOUT_S:
                    raise ReporterError("RSS reporter launch handshake timed out")
                if final_at is not None and elapsed >= final_at + PROTOCOL_TIMEOUT_S:
                    raise ReporterError("RSS reporter final measurement or EOF timed out")
                if not acknowledged:
                    if is_yanked is not None and is_yanked():
                        skill_yanked = True
                    if worker is not None and terminated_at is None:
                        if skill_yanked or (wall_cap_s is not None and elapsed >= wall_cap_s):
                            terminated_at = elapsed
                            timed_out = not skill_yanked
                            receiver.send(b"TERM")
                    elif worker is not None and elapsed >= terminated_at + grace:
                        receiver.send(b"KILL")
                if terminated_at is not None and elapsed >= terminated_at + grace + PROTOCOL_TIMEOUT_S:
                    raise ReporterError("RSS reporter did not finish after worker termination")
                time.sleep(tick)
            status, rss, user, system = reports.result(proc.returncode)
            end = time.monotonic()
    except BaseException:
        if proc is not None and proc.returncode is None:
            _abort(proc, receiver)
        raise
    finally:
        sender.close()
        receiver.close()
    launch = runner.Launch(
        exit_status=os.waitstatus_to_exitcode(status),
        start_mono=start,
        end_mono=end,
        wall_s=end - start,
        cpu_user_s=user / 1_000_000,
        cpu_sys_s=system / 1_000_000,
        peak_rss_bytes=runner.maxrss_bytes(rss),
        timed_out=timed_out,
        skill_yanked=skill_yanked,
        argv=tuple(argv),
        measurement_scope=runner.measurement_scope(
            sampled_extra=sampled_extra, survivors=survivors, killed=terminated_at is not None, sampled=sampled
        ),
    )
    lg.info(
        "exit",
        rc=launch.exit_status,
        wall_ms=round(launch.wall_s * 1000, 3),
        cpu_s=round(launch.cpu_user_s + launch.cpu_sys_s, 6),
        rss=launch.peak_rss_bytes,
        timed_out=timed_out,
        skill_yanked=skill_yanked,
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
