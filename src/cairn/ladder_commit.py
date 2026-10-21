from dataclasses import asdict, dataclass

from cairn import bundle, canon, cli, instances, keys, log
from cairn.ladder_refusal import (
    COMMITMENT_ABSENT,
    HYPOTHESIS_ABSENT,
    HYPOTHESIS_AFTER_ENTROPY,
    NONCE_ABSENT,
    NONCE_FOREIGN,
    NONCE_PUBLISHED,
    RunRefused,
)
from cairn.substrate import node_hash_for

lg = log.get("ladder")

COMMITMENT_KIND = "ladder_entropy_commitment"
COMMITMENT_SCHEMA = canon.Map(canon.STR, canon.STR)


def method_seed(nonce, hypothesis_key, arm, bits, trial):
    return instances.trial_seed(nonce, f"{hypothesis_key}/{arm}", bits, trial)


def sequence_position(sub, node_hash):
    row = sub.conn.execute("SELECT rowid FROM nodes WHERE hash = ?", (node_hash,)).fetchone()
    return None if row is None else row["rowid"]


@dataclass(frozen=True)
class Commitment:
    run_id: str
    hypothesis_hash: str
    nonce: str
    at: str

    def as_dict(self):
        return asdict(self)

    @property
    def hash(self):
        return node_hash_for(COMMITMENT_KIND, bundle.canonical_bytes(COMMITMENT_KIND, self.as_dict()))


def commit_entropy(sub, *, hypothesis_hash, run_id, nonce=None, at=None):
    """Write the run's entropy commitment, then draw the nonce it names."""
    value = Commitment(
        run_id=run_id,
        hypothesis_hash=hypothesis_hash,
        nonce=instances.fresh_nonce() if nonce is None else nonce,
        at=cli.now_iso() if at is None else at,
    )
    canonical = bundle.canonical_bytes(COMMITMENT_KIND, value.as_dict())
    with sub._tx():
        sub._put_node(COMMITMENT_KIND, canonical, value.hash, "Replayable", None)
    record = instances.commit_nonce(sub, hypothesis_hash, run_id, value.nonce, at=value.at)
    lg.info("commit_entropy", run_id=run_id, hypothesis_hash=hypothesis_hash, commitment=value.hash)
    return value, record


def commitment_for(sub, nonce):
    rows = sub.conn.execute(
        "SELECT rowid, canonical FROM nodes WHERE kind = ? ORDER BY rowid", (COMMITMENT_KIND,)
    ).fetchall()
    for row in rows:
        data = canon.decode(COMMITMENT_SCHEMA, bytes(row["canonical"]))
        if data["nonce"] == nonce:
            return row["rowid"], Commitment(**data)
    return None, None


def _hypothesis(sub, hypothesis_hash):
    row = sub.get_node(hypothesis_hash)
    if row is None or row["kind"] != "hypothesis_object":
        raise RunRefused(HYPOTHESIS_ABSENT, f"no hypothesis object {hypothesis_hash[:12]} is recorded")
    return canon.decode(keys.HYPOTHESIS_OBJECT, bytes(row["canonical"]))


def check_order(sub, *, hypothesis_hash, nonce):
    """The hypothesis object precedes the run's entropy commitment in the substrate's append order."""
    _hypothesis(sub, hypothesis_hash)
    position = sequence_position(sub, hypothesis_hash)
    committed_at, commitment = commitment_for(sub, nonce)
    if commitment is None:
        raise RunRefused(COMMITMENT_ABSENT, f"nonce {nonce[:12]} carries no entropy commitment record")
    if commitment.hypothesis_hash != hypothesis_hash:
        raise RunRefused(NONCE_FOREIGN, f"nonce {nonce[:12]} commits hypothesis {commitment.hypothesis_hash[:12]}")
    if position >= committed_at:
        raise RunRefused(
            HYPOTHESIS_AFTER_ENTROPY,
            f"hypothesis {hypothesis_hash[:12]} sits at record {position}, the commitment at {committed_at}",
        )
    record = instances.get_nonce(sub, nonce)
    if record is None:
        raise RunRefused(NONCE_ABSENT, f"no nonce {nonce[:12]} is recorded")
    if record.hypothesis_key != hypothesis_hash:
        raise RunRefused(NONCE_FOREIGN, f"nonce {nonce[:12]} is drawn for {record.hypothesis_key[:12]}")
    if not record.withheld:
        raise RunRefused(NONCE_PUBLISHED, f"nonce {nonce[:12]} is published at {record.published_at}")
    return commitment
