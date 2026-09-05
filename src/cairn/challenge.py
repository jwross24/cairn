from dataclasses import dataclass
from pathlib import Path

from cairn import claims, container, lean, log
from cairn.substrate import blob_hash

RENDERER_PATH = Path(__file__)
PRELUDE_PATH = lean.REPO_ROOT / "bundle" / "challenge_prelude.lean"
CHALLENGE_DIR = lean.PROJECT_DIR / "Challenge"
PRELUDE_KIND = "challenge_prelude"
RENDERER_KIND = "challenge_renderer"
GATE = "challenge_render"
MODULE_PREFIX = "Challenge.C_"
HASH_CHARS = 16

lg = log.get("challenge")


class ChallengeError(Exception):
    pass


class NoFormalSource(ChallengeError):
    def __init__(self, statement_hash):
        super().__init__(f"claim statement {statement_hash} carries no formal source to render")
        self.statement_hash = statement_hash


class PathNotGateOwned(ChallengeError):
    def __init__(self, root):
        super().__init__(f"{root} is not the gate-owned Challenge directory {CHALLENGE_DIR}")
        self.root = str(root)


class RenderNotFromBundle(ChallengeError):
    def __init__(self, kind, rendered_hash, bundle_hash):
        super().__init__(
            f"the {kind} the Challenge was rendered under ({rendered_hash}) is not the bundle's ({bundle_hash})"
        )
        self.kind = kind
        self.rendered_hash = rendered_hash
        self.bundle_hash = bundle_hash


class BindingAbsent(ChallengeError):
    def __init__(self, run_hash, why):
        super().__init__(f"gate run {run_hash} carries no claim-to-formal-statement binding: {why}")
        self.run_hash = run_hash
        self.why = why


@dataclass(frozen=True)
class Rendered:
    statement_hash: str
    module: str
    path: str
    source_hash: str
    prelude_hash: str
    renderer_hash: str


@dataclass(frozen=True)
class Submission:
    solution_module: bytes
    formal_statement_hash: str


def prelude_bytes():
    return PRELUDE_PATH.read_bytes()


def renderer_bytes():
    return RENDERER_PATH.read_bytes()


def prelude_hash():
    return blob_hash(prelude_bytes())


def renderer_hash():
    return blob_hash(renderer_bytes())


def _normalize(text):
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


def module_name(statement):
    return f"{MODULE_PREFIX}{statement.hash[:HASH_CHARS]}"


def module_path(statement, root):
    return Path(root) / f"C_{statement.hash[:HASH_CHARS]}.lean"


def render(statement, prelude):
    if not (statement.formal_source or "").strip():
        raise NoFormalSource(statement.hash)
    return (_normalize(prelude.decode()) + "\n" + _normalize(statement.formal_source)).encode()


def write_challenge(statement, prelude, *, root=None):
    target = Path(root) if root is not None else CHALLENGE_DIR
    if target.resolve() != CHALLENGE_DIR.resolve():
        lg.info("path_refused", root=str(target), gate_owned=str(CHALLENGE_DIR))
        raise PathNotGateOwned(target)
    source = render(statement, prelude)
    target.mkdir(parents=True, exist_ok=True)
    path = module_path(statement, target)
    path.write_bytes(source)
    rendered = Rendered(
        statement.hash, module_name(statement), str(path), blob_hash(source), blob_hash(prelude), renderer_hash()
    )
    lg.info("rendered", **rendered.__dict__)
    return rendered


def gate_run(rendered, gate_bundle, at, *, arm, formal_statement_hash=None):
    container.assert_arm(arm)
    for kind, rendered_hash in ((PRELUDE_KIND, rendered.prelude_hash), (RENDERER_KIND, rendered.renderer_hash)):
        pinned = gate_bundle.digest_of(kind)
        if rendered_hash != pinned:
            lg.info("render_not_from_bundle", kind=kind, rendered_hash=rendered_hash, bundle_hash=pinned)
            raise RenderNotFromBundle(kind, rendered_hash, pinned)
    return claims.GateRun(
        gate=GATE,
        bundle_hash=gate_bundle.hash,
        pin_hash=gate_bundle.pin_hash,
        result="pass",
        reasons=(),
        at=at,
        statement_hash=rendered.statement_hash,
        formal_statement_hash=formal_statement_hash,
        renderer_hash=rendered.renderer_hash,
        prelude_hash=rendered.prelude_hash,
        arm=arm,
    )


def binding(run):
    if run.gate != GATE:
        raise BindingAbsent(run.hash, f"gate is {run.gate!r}, not {GATE!r}")
    for name in ("statement_hash", "formal_statement_hash", "renderer_hash", "prelude_hash", "arm"):
        if not getattr(run, name):
            raise BindingAbsent(run.hash, f"{name} is empty")
    return {
        "claim_statement_hash": run.statement_hash,
        "formal_statement_hash": run.formal_statement_hash,
        "bundle_hash": run.bundle_hash,
        "renderer_hash": run.renderer_hash,
        "prelude_hash": run.prelude_hash,
        "arm": run.arm,
    }
