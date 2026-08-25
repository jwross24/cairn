import atexit
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import blake3

from cairn import canon, keys, log, pari

SCRIPT_PATH = Path(__file__).with_name("gp") / "verify.gp"
DEFAULT_STACK_CEILING = "64M"
DEFAULT_TIMEOUT_S = 30.0
ARITY = 9
FIELD_NAMES = ("p", "a", "b", "n", "Px", "Py", "Qx", "Qy", "x")
SCRIPT_REASONS = ("p-not-prime", "singular", "P-off-curve", "Q-off-curve", "nQ-not-O", "xP-ne-Q")
BACKEND_REASONS = ("backend-crash", "timeout")
PRE_SPAWN_REASONS = ("bad-arity", "bad-field", "submitter-named-instance")
REASONS = SCRIPT_REASONS + BACKEND_REASONS + PRE_SPAWN_REASONS
ACCEPT_KEYS = ("rc", "stdout", "stderr_empty")
STACK_CEILING_SHAPE = re.compile(r"[0-9]+[kKmMgG]?")
FAIL_PREFIX = "FAIL "
CODE_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9-]*")
_MATERIALIZED = {}


class VerifierConfigError(ValueError):
    pass


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _digest(text):
    return blake3.blake3(text.encode("utf-8", "surrogatepass")).hexdigest()


@dataclass(frozen=True)
class AcceptPredicate:
    rc: int
    stdout: str | None
    stderr_empty: bool

    def __post_init__(self):
        if not _is_int(self.rc):
            raise VerifierConfigError("accept.rc must be an int")
        if self.stdout is not None and not isinstance(self.stdout, str):
            raise VerifierConfigError("accept.stdout must be a str or null")
        if not isinstance(self.stderr_empty, bool):
            raise VerifierConfigError("accept.stderr_empty must be a bool")

    @classmethod
    def from_dict(cls, obj):
        if not isinstance(obj, dict):
            raise VerifierConfigError("accept predicate must be a mapping")
        missing = [key for key in ACCEPT_KEYS if key not in obj]
        if missing:
            raise VerifierConfigError(f"accept predicate missing {missing}")
        return cls(obj["rc"], obj["stdout"], obj["stderr_empty"])

    def as_dict(self):
        return {"rc": self.rc, "stdout": self.stdout, "stderr_empty": self.stderr_empty}

    def holds(self, rc, stdout, stderr):
        if rc != self.rc:
            return False
        if self.stdout is not None and (not isinstance(stdout, str) or stdout.strip() != self.stdout):
            return False
        return not (self.stderr_empty and stderr != "")


DEFAULT_ACCEPT = AcceptPredicate(0, "OK", True)


def script_bytes():
    return SCRIPT_PATH.read_bytes()


@dataclass(frozen=True)
class VerifierConfig:
    script: bytes
    backend_path: str = pari.GP_BIN
    stack_ceiling: str = DEFAULT_STACK_CEILING
    timeout_s: float = DEFAULT_TIMEOUT_S
    accept: AcceptPredicate = DEFAULT_ACCEPT
    bundle_hash: str | None = None

    def __post_init__(self):
        if not isinstance(self.script, bytes) or not self.script:
            raise VerifierConfigError("verifier script must be non-empty bytes")
        if not isinstance(self.backend_path, str) or not self.backend_path:
            raise VerifierConfigError("backend_path must be a non-empty str")
        if not isinstance(self.stack_ceiling, str) or not STACK_CEILING_SHAPE.fullmatch(self.stack_ceiling):
            raise VerifierConfigError(f"stack_ceiling {self.stack_ceiling!r} is not a gp -s size")
        if isinstance(self.timeout_s, bool) or not isinstance(self.timeout_s, (int, float)) or not self.timeout_s > 0:
            raise VerifierConfigError("timeout_s must be a positive number")
        if not isinstance(self.accept, AcceptPredicate):
            raise VerifierConfigError("accept must be an AcceptPredicate")
        if self.bundle_hash is None:
            object.__setattr__(self, "bundle_hash", self.script_hash)
        elif not isinstance(self.bundle_hash, str) or not self.bundle_hash:
            raise VerifierConfigError("bundle_hash must be a non-empty str")

    @property
    def script_hash(self):
        return blake3.blake3(self.script).hexdigest()

    @classmethod
    def from_bundle(cls, verifier_obj, script, bundle_hash):
        if not isinstance(verifier_obj, dict):
            raise VerifierConfigError("bundle verifier object must be a mapping")
        missing = [key for key in ("backend_path", "stack_ceiling", "timeout_s", "accept") if key not in verifier_obj]
        if missing:
            raise VerifierConfigError(f"bundle verifier object missing {missing}")
        return cls(
            script=script,
            backend_path=verifier_obj["backend_path"],
            stack_ceiling=verifier_obj["stack_ceiling"],
            timeout_s=verifier_obj["timeout_s"],
            accept=AcceptPredicate.from_dict(verifier_obj["accept"]),
            bundle_hash=bundle_hash,
        )


def default_config(**overrides):
    return VerifierConfig(**{"script": script_bytes(), **overrides})


def materialize_script(config):
    key = (config.bundle_hash, config.script_hash)
    path = _MATERIALIZED.get(key)
    if path is not None and os.path.isfile(path):
        return path
    directory = tempfile.mkdtemp(prefix=f"cairn-bundle-{config.bundle_hash}-")
    path = os.path.join(directory, "verify.gp")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(fd, "wb") as fh:
        fh.write(config.script)
    os.chmod(path, 0o444)
    _MATERIALIZED[key] = path
    return path


@atexit.register
def _remove_materialized():
    for path in list(_MATERIALIZED.values()):
        shutil.rmtree(os.path.dirname(path), ignore_errors=True)
    _MATERIALIZED.clear()


def _reduce(value, p):
    return value % p if _is_int(value) else value


def _point(value, p):
    if not isinstance(value, (list, tuple)):
        return value
    if p is None:
        return tuple(value)
    return tuple(_reduce(v, p) for v in value)


@dataclass(frozen=True)
class Instance:
    p: object
    a: object
    b: object
    n: object
    P: object
    Q: object

    def __post_init__(self):
        modulus = self.p if _is_int(self.p) and self.p >= 1 else None
        if modulus is not None:
            object.__setattr__(self, "a", _reduce(self.a, modulus))
            object.__setattr__(self, "b", _reduce(self.b, modulus))
        object.__setattr__(self, "P", _point(self.P, modulus))
        object.__setattr__(self, "Q", _point(self.Q, modulus))

    def as_dict(self):
        return {"p": self.p, "a": self.a, "b": self.b, "n": self.n, "P": list(self.P) if isinstance(self.P, tuple) else self.P, "Q": list(self.Q) if isinstance(self.Q, tuple) else self.Q}

    @property
    def instance_hash(self):
        return keys.instance_hash(self.as_dict())

    def fields(self, x):
        out = [self.p, self.a, self.b, self.n]
        for point in (self.P, self.Q):
            if isinstance(point, tuple):
                out.extend(point)
            else:
                out.append(point)
        out.append(x)
        return tuple(out)


@dataclass(frozen=True)
class Submission:
    x: object
    P: object = None
    Q: object = None

    @property
    def names_instance(self):
        return self.P is not None or self.Q is not None


@dataclass(frozen=True)
class VerifierResult:
    instance_hash: str | None
    x: int | None
    accepted: bool
    reason: str | None
    reasons: tuple
    stdout_digest: str | None
    stderr_digest: str | None
    rc: int | None
    wall_s: float

    @property
    def gate_result(self):
        if self.accepted:
            return "pass"
        if self.reason in PRE_SPAWN_REASONS:
            return "refused"
        return "fail"

    def node(self):
        return {
            "instance_hash": self.instance_hash,
            "x": self.x,
            "accepted": self.accepted,
            "reason": self.reason,
            "stdout_digest": self.stdout_digest,
            "stderr_digest": self.stderr_digest,
            "rc": self.rc,
            "wall_s": self.wall_s,
        }


FIELD_RULES = (
    ("p-gt-3", lambda p, a, b, n, Px, Py, Qx, Qy, x: p > 3),
    ("coords-lt-p", lambda p, a, b, n, Px, Py, Qx, Qy, x: a < p and b < p and Px < p and Py < p and Qx < p and Qy < p),
    ("x-lt-n", lambda p, a, b, n, Px, Py, Qx, Qy, x: x < n),
    ("hasse", lambda p, a, b, n, Px, Py, Qx, Qy, x: (n - p - 1) ** 2 <= 4 * p),
)


def validate_fields(fields):
    fields = tuple(fields)
    if len(fields) != ARITY:
        return "bad-arity"
    for value in fields:
        if not _is_int(value) or value < 0:
            return "bad-field"
    for _name, rule in FIELD_RULES:
        if not rule(*fields):
            return "bad-field"
    return None


def render_line(fields):
    return "verify(" + ",".join(str(int(v)) for v in fields) + ")\n"


def fail_codes(stdout):
    if not isinstance(stdout, str):
        return ()
    for line in stdout.splitlines():
        if line.startswith(FAIL_PREFIX):
            seen = []
            for token in CODE_TOKEN.findall(line[len(FAIL_PREFIX):]):
                if token in SCRIPT_REASONS and token not in seen:
                    seen.append(token)
            return tuple(seen)
    return ()


def classify(rc, stdout, stderr, accept=DEFAULT_ACCEPT):
    if accept.holds(rc, stdout, stderr):
        return True, None, ()
    codes = fail_codes(stdout)
    if codes:
        return False, codes[0], codes
    return False, "backend-crash", ("backend-crash",)


def _hash_or_none(instance):
    try:
        return instance.instance_hash
    except (canon.CanonError, AttributeError, TypeError):
        return None


class Verifier:
    def __init__(self, config=None):
        self.config = config if config is not None else default_config()
        if self.config.backend_path != pari.GP_BIN:
            raise VerifierConfigError(f"bundle backend_path {self.config.backend_path!r} is not the installed backend {pari.GP_BIN!r}")
        self._log = log.get("verifier")

    def run(self, instance, x):
        start = time.monotonic()
        submission = x if isinstance(x, Submission) else None
        if submission is not None:
            x = submission.x
        instance_hash = _hash_or_none(instance)
        if submission is not None and submission.names_instance:
            return self._refuse(instance_hash, x, "submitter-named-instance", start)
        try:
            fields = instance.fields(x)
        except AttributeError:
            return self._refuse(instance_hash, x, "bad-field", start)
        return self._run_fields(fields, instance_hash, start)

    def run_fields(self, fields, *, instance_hash=None):
        return self._run_fields(tuple(fields), instance_hash, time.monotonic())

    def crash_selftest(self, instance):
        start = time.monotonic()
        instance_hash = _hash_or_none(instance)
        fields = (instance.p, instance.a, instance.b)
        if any(not _is_int(v) or v < 0 for v in fields) or not (fields[0] > 3 and fields[1] < fields[0] and fields[2] < fields[0]):
            return self._refuse(instance_hash, None, "bad-field", start)
        line = "crash_selftest(" + ",".join(str(v) for v in fields) + ")\n"
        return self._spawn(line, instance_hash, None, start)

    def _run_fields(self, fields, instance_hash, start):
        x = fields[ARITY - 1] if len(fields) == ARITY else None
        reason = validate_fields(fields)
        if reason is not None:
            return self._refuse(instance_hash, x, reason, start)
        return self._spawn(render_line(fields), instance_hash, x, start)

    def _refuse(self, instance_hash, x, reason, start):
        result = VerifierResult(instance_hash, x if _is_int(x) else None, False, reason, (reason,), None, None, None, self._wall(start))
        self._verdict(result)
        return result

    def _spawn(self, line, instance_hash, x, start):
        config = self.config
        path = materialize_script(config)
        argv = [*pari.gp_argv(config.stack_ceiling), path]
        try:
            rc, out, err = pari.run_gp([path], line, timeout_s=config.timeout_s, stack=config.stack_ceiling)
        except pari.GpTimeout:
            result = VerifierResult(instance_hash, x, False, "timeout", ("timeout",), None, None, None, self._wall(start))
            self._log.debug("gp", argv=argv, stdin_digest=_digest(line), stdout_digest=None, stderr_digest=None, timeout_s=config.timeout_s)
            self._verdict(result)
            return result
        accepted, reason, reasons = classify(rc, out, err, config.accept)
        result = VerifierResult(instance_hash, x, accepted, reason, reasons, _digest(out), _digest(err), rc, self._wall(start))
        self._log.debug("gp", argv=argv, stdin_digest=_digest(line), stdout_digest=result.stdout_digest, stderr_digest=result.stderr_digest)
        self._verdict(result)
        return result

    @staticmethod
    def _wall(start):
        return round(time.monotonic() - start, 6)

    def _verdict(self, result):
        self._log.info(
            "verdict",
            instance_hash=result.instance_hash,
            accepted=result.accepted,
            reason=result.reason,
            rc=result.rc,
            wall_ms=round(result.wall_s * 1000, 3),
            gate_result=result.gate_result,
        )
