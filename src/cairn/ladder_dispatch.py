import importlib
import json
from dataclasses import asdict, dataclass
from uuid import uuid4

from cairn import allowlist, bundle, claims, keys, ladderplan, log
from cairn.ladder_commit import _hypothesis, check_order
from cairn.ladder_refusal import (
    ALLOW_LIST_UNBOUND,
    ARM_UNKNOWN,
    BASELINE_REVISION_MISMATCH,
    METHOD_IDENTITY_MISMATCH,
    UNCERTIFIED_REVISION,
    YANKED_REVISION,
    RunRefused,
)
from cairn.substrate import node_hash_for

lg = log.get("ladder")

KIND = "ladder_dispatch"
TABLE = "ladder_dispatches"

CLAIMANT = ladderplan.ARMS[0]
BASELINE = ladderplan.ARMS[1]
BASELINE_AA = ladderplan.ARMS[2]


@dataclass(frozen=True)
class Dispatch:
    run_id: str
    arm: str
    nonce: str
    hypothesis_hash: str
    method_identity: dict
    skill: str
    implementation_revision: str
    identity_bundle: dict
    identity_bundle_hash: str
    allow_list: dict
    allow_list_hash: str
    gate_bundle_hash: str
    plan_hash: str
    at: str

    def __post_init__(self):
        for name in ("method_identity", "identity_bundle", "allow_list"):
            object.__setattr__(self, name, claims.jsonable(getattr(self, name)))

    def as_dict(self):
        return asdict(self)

    @property
    def hash(self):
        return node_hash_for(KIND, bundle.canonical_bytes(KIND, self.as_dict()))

    @property
    def module(self):
        return importlib.import_module(self.skill)


def expected_identity(plan, arm, hypothesis):
    if arm == CLAIMANT:
        return hypothesis["method_identity"]
    if arm in (BASELINE, BASELINE_AA):
        return plan.baseline.method_identity
    raise RunRefused(ARM_UNKNOWN, f"{arm!r} is no arm of {tuple(ladderplan.ARMS)}")


def _allow_list(dispatch):
    data = dispatch.allow_list
    return allowlist.AllowList(
        template_name=data["template_name"],
        template_hash=data["template_hash"],
        bundle_hash=data["bundle_hash"],
        mechanism=data["mechanism"],
        counted_object=data["counted_object"],
        declared_backends=tuple(data["declared_backends"]),
        exec_paths=tuple(data["exec_paths"]),
        network_egress=data["network_egress"],
        writable_root=data["writable_root"],
        profile_hash=data["profile_hash"],
        withheld_roots=tuple(data["withheld_roots"]),
    )


def check_dispatch(sub, gate_bundle, dispatch, plan, *, attest_path=None):
    """Every refusal this dispatch can earn, before a trial spawns anything."""
    hypothesis = _hypothesis(sub, dispatch.hypothesis_hash)
    check_order(sub, hypothesis_hash=dispatch.hypothesis_hash, nonce=dispatch.nonce)
    expected = expected_identity(plan, dispatch.arm, hypothesis)
    if dispatch.method_identity != expected:
        raise RunRefused(
            METHOD_IDENTITY_MISMATCH,
            f"arm {dispatch.arm} dispatches {dispatch.method_identity} against registered {expected}",
        )
    if dispatch.arm != CLAIMANT and dispatch.implementation_revision != plan.baseline.implementation_revision:
        raise RunRefused(
            BASELINE_REVISION_MISMATCH,
            f"arm {dispatch.arm} runs revision {dispatch.implementation_revision[:12]}, "
            f"the plan registers {plan.baseline.implementation_revision[:12]}",
        )
    if dispatch.identity_bundle_hash != keys.identity_bundle_hash(dispatch.identity_bundle):
        raise RunRefused(UNCERTIFIED_REVISION, "the dispatched identity bundle does not hash to its named hash")
    if dispatch.identity_bundle["implementation_revision"] != dispatch.implementation_revision:
        raise RunRefused(UNCERTIFIED_REVISION, "the dispatched identity bundle names another implementation revision")
    if not sub.certified(dispatch.identity_bundle_hash):
        raise RunRefused(
            UNCERTIFIED_REVISION, f"skill identity {dispatch.identity_bundle_hash[:12]} carries no certificate"
        )
    if sub.yanked(dispatch.identity_bundle_hash, attest_path=attest_path):
        raise RunRefused(YANKED_REVISION, f"skill identity {dispatch.identity_bundle_hash[:12]} is yanked")
    if dispatch.allow_list.get("bundle_hash") != gate_bundle.hash:
        raise RunRefused(ALLOW_LIST_UNBOUND, "the instantiated allow-list names another gate bundle")
    if _allow_list(dispatch).hash != dispatch.allow_list_hash:
        raise RunRefused(ALLOW_LIST_UNBOUND, "the instantiated allow-list differs from its recorded hash")
    if not allowlist.check_instantiation(_allow_list(dispatch), gate_bundle):
        raise RunRefused(ALLOW_LIST_UNBOUND, "the instantiated allow-list does not match the bundle template")
    return dispatch


def write_dispatch(sub, value):
    canonical = bundle.canonical_bytes(KIND, value.as_dict())
    with sub._tx():
        sub._put_node(KIND, canonical, value.hash, "Replayable", None)
        sub.conn.execute(
            f"INSERT INTO {TABLE} (dispatch_id, record_hash, run_id, arm, nonce, hypothesis_hash,"
            " implementation_revision, allow_list_hash, gate_bundle_hash, plan_hash, record_json)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid4()),
                value.hash,
                value.run_id,
                value.arm,
                value.nonce,
                value.hypothesis_hash,
                value.implementation_revision,
                value.allow_list_hash,
                value.gate_bundle_hash,
                value.plan_hash,
                json.dumps(value.as_dict(), sort_keys=True, separators=(",", ":")),
            ),
        )
        sub._add_root("ledger_row", value.hash)
    lg.info("dispatch", run_id=value.run_id, arm=value.arm, record=value.hash)
    return value


def dispatches_for(sub, run_id):
    rows = sub.conn.execute(f"SELECT record_json FROM {TABLE} WHERE run_id = ? ORDER BY rowid", (run_id,)).fetchall()
    return {d.arm: d for d in (Dispatch(**json.loads(row["record_json"])) for row in rows)}
