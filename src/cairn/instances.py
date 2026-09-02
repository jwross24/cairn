"""Gate-side half of the instance-maker: nonce lifecycle, seed derivation, trial launch.

A ladder run draws one fresh nonce after its hypothesis object is recorded,
from entropy the hypothesis object never enters. The nonce is withheld
(published_at is null) until the run completes, then published together with
every trial's seed so each instance replays. A caller that hands back a nonce
already recorded for the same hypothesis object is refused: a rung re-run after
INCONCLUSIVE sees fresh instances because the first run's table published its
seeds. The append-order check between hypothesis object and nonce is the run
engine's; this module records what it is handed.
"""

import secrets
from dataclasses import dataclass

from cairn import cli, keys, log, runner, substrate, tiergate
from cairn.skills import instance_maker

LOG_STEP = "instances"
NONCE_BYTES = 32
NONCE_REUSED = "nonce-reused"
RUN_HAS_NONCE = "run-has-nonce"
UNKNOWN_NONCE = "unknown-nonce"
NONCE_PUBLISHED = "nonce-published"
TRIAL_RECORDED = "trial-recorded"
TRIAL_REFUSED = "trial-refused"
SEED_MODULUS = 1 << 63
DECLARED_TIER = 0


class InstanceError(substrate.SubstrateError):
    def __init__(self, reason, detail):
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}")


class NonceReused(InstanceError):
    def __init__(self, detail):
        super().__init__(NONCE_REUSED, detail)


class RunHasNonce(InstanceError):
    def __init__(self, detail):
        super().__init__(RUN_HAS_NONCE, detail)


class UnknownNonce(InstanceError):
    def __init__(self, detail):
        super().__init__(UNKNOWN_NONCE, detail)


class NoncePublished(InstanceError):
    def __init__(self, detail):
        super().__init__(NONCE_PUBLISHED, detail)


class TrialRecorded(InstanceError):
    def __init__(self, detail):
        super().__init__(TRIAL_RECORDED, detail)


class TrialRefused(InstanceError):
    def __init__(self, reasons):
        self.reasons = tuple(reasons)
        super().__init__(TRIAL_REFUSED, f"the tier gate refused the maker: {', '.join(self.reasons)}")


@dataclass(frozen=True)
class NonceRecord:
    nonce: str
    hypothesis_key: str
    run_id: str
    drawn_at: str
    published_at: str | None

    @property
    def withheld(self):
        return self.published_at is None


def trial_seed(nonce, hypothesis_key, bits, trial):
    """Seed of trial i at size s: H(nonce || hypothesis hash || s || i), domain-separated and typed."""
    digest = keys.trial_seed_hash({"nonce": nonce, "hypothesis_key": hypothesis_key, "bits": bits, "trial": trial})
    return int.from_bytes(bytes.fromhex(digest)[:8], "big") % SEED_MODULUS or 1


def fresh_nonce():
    return secrets.token_bytes(NONCE_BYTES).hex()


def _record(row):
    return NonceRecord(row["nonce"], row["hypothesis_key"], row["run_id"], row["drawn_at"], row["published_at"])


def get_nonce(sub, nonce):
    row = sub.conn.execute("SELECT * FROM instance_nonces WHERE nonce = ?", (nonce,)).fetchone()
    return None if row is None else _record(row)


def nonces_for(sub, hypothesis_key):
    rows = sub.conn.execute(
        "SELECT * FROM instance_nonces WHERE hypothesis_key = ? ORDER BY rowid", (hypothesis_key,)
    ).fetchall()
    return [_record(row) for row in rows]


def commit_nonce(sub, hypothesis_key, run_id, nonce, *, at=None):
    lg = log.get(LOG_STEP)
    if not isinstance(nonce, str) or len(nonce) != 2 * NONCE_BYTES or set(nonce) - set("0123456789abcdef"):
        raise InstanceError("bad-nonce", f"a nonce is {NONCE_BYTES} bytes of lowercase hex, got {nonce!r}")
    with sub._tx():
        prior = sub.conn.execute(
            "SELECT run_id, hypothesis_key FROM instance_nonces WHERE nonce = ?", (nonce,)
        ).fetchone()
        if prior is not None:
            lg.info("refuse", reason=NONCE_REUSED, hypothesis_key=hypothesis_key, run_id=run_id, prior=prior[0])
            raise NonceReused(f"nonce {nonce[:12]} is recorded for hypothesis {prior[1][:12]} by run {prior[0]}")
        held = sub.conn.execute("SELECT nonce FROM instance_nonces WHERE run_id = ?", (run_id,)).fetchone()
        if held is not None:
            lg.info("refuse", reason=RUN_HAS_NONCE, hypothesis_key=hypothesis_key, run_id=run_id)
            raise RunHasNonce(f"run {run_id} holds nonce {held[0][:12]}; a run draws exactly one")
        drawn_at = at or cli.now_iso()
        sub.conn.execute(
            "INSERT INTO instance_nonces (nonce, hypothesis_key, run_id, drawn_at, published_at) VALUES (?, ?, ?, ?, NULL)",
            (nonce, hypothesis_key, run_id, drawn_at),
        )
    lg.info("write", table="instance_nonces", hypothesis_key=hypothesis_key, run_id=run_id, status="inserted")
    return NonceRecord(nonce, hypothesis_key, run_id, drawn_at, None)


def draw_nonce(sub, hypothesis_key, run_id, *, at=None):
    return commit_nonce(sub, hypothesis_key, run_id, fresh_nonce(), at=at)


def withheld(sub, nonce):
    record = get_nonce(sub, nonce)
    if record is None:
        raise UnknownNonce(f"no nonce {nonce[:12]} is recorded")
    return record.withheld


def publish_nonce(sub, nonce, *, at=None):
    lg = log.get(LOG_STEP)
    with sub._tx():
        record = get_nonce(sub, nonce)
        if record is None:
            raise UnknownNonce(f"no nonce {nonce[:12]} is recorded")
        if record.published_at is not None:
            raise NoncePublished(f"nonce {nonce[:12]} is published at {record.published_at}")
        published_at = at or cli.now_iso()
        sub.conn.execute("UPDATE instance_nonces SET published_at = ? WHERE nonce = ?", (published_at, nonce))
    lg.info("write", table="instance_nonces", nonce=nonce, status="published")
    return NonceRecord(record.nonce, record.hypothesis_key, record.run_id, record.drawn_at, published_at)


def record_trial(sub, nonce, bits, trial, seed, instance_hash, x, attempt_id):
    lg = log.get(LOG_STEP)
    with sub._tx():
        if get_nonce(sub, nonce) is None:
            raise UnknownNonce(f"no nonce {nonce[:12]} is recorded")
        held = sub.conn.execute(
            "SELECT seed FROM instance_trials WHERE nonce = ? AND bits = ? AND trial = ?", (nonce, bits, trial)
        ).fetchone()
        if held is not None:
            raise TrialRecorded(f"trial {trial} at {bits} bits under nonce {nonce[:12]} holds seed {held[0]}")
        sub.conn.execute(
            "INSERT INTO instance_trials (nonce, bits, trial, seed, instance_hash, x, attempt_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (nonce, bits, trial, seed, instance_hash, str(x), attempt_id),
        )
    lg.info("write", table="instance_trials", nonce=nonce, bits=bits, trial=trial, seed=seed, status="inserted")


def trials_for(sub, nonce):
    rows = sub.conn.execute("SELECT * FROM instance_trials WHERE nonce = ? ORDER BY bits, trial", (nonce,)).fetchall()
    return [dict(row) for row in rows]


def maker_recipe(seed, salt):
    identity = instance_maker.identity_bundle()
    return {
        "skill_identity_hash": keys.identity_bundle_hash(identity),
        "inputs": {},
        "seed": seed,
        "tool_versions": {
            "cypari2": identity["tool_digests"]["cypari2"],
            "libpari": identity["tool_digests"]["libpari"],
        },
        "container_digest": identity["container_digest"],
        "salt": salt,
    }


def admit(sub, gate_bundle, *, hypothesis_key, method_identity, bits, seed, budget_remaining):
    launch = tiergate.Launch(
        cost_profile=instance_maker.COST_PROFILE,
        inputs={"bits": bits, "seed": seed},
        budget_remaining=budget_remaining,
        hypothesis_key=hypothesis_key,
        method_identity=method_identity,
        skill_identity_hash=instance_maker.skill_identity_hash(),
        declared_tier=DECLARED_TIER,
    )
    decision = tiergate.TierGate(sub, gate_bundle).admit(launch)
    if isinstance(decision, tiergate.TierRefused):
        raise TrialRefused(decision.reasons)
    return decision


def launch_trial(
    sub,
    gate_bundle,
    *,
    nonce,
    bits,
    trial,
    scratch_root,
    method_identity,
    budget_remaining,
    ceiling_multiplier=None,
):
    record = get_nonce(sub, nonce)
    if record is None:
        raise UnknownNonce(f"no nonce {nonce[:12]} is recorded")
    seed = trial_seed(nonce, record.hypothesis_key, bits, trial)
    admit(
        sub,
        gate_bundle,
        hypothesis_key=record.hypothesis_key,
        method_identity=method_identity,
        bits=bits,
        seed=seed,
        budget_remaining=budget_remaining,
    )
    tiers = gate_bundle.tiers
    attempt = runner.launch(
        sub,
        "cairn.skills.instance_maker",
        maker_recipe(seed, f"trial/{nonce}/{bits}/{trial}"),
        stdin_document={"bits": bits, "seed": seed},
        bundle_hash=gate_bundle.hash,
        evaluation=instance_maker.COST_PROFILE.evaluate(bits),
        ceiling_multiplier=tiers["ceiling_multiplier"] if ceiling_multiplier is None else ceiling_multiplier,
        wall_cap_multiplier=tiers["wall_cap_multiplier"],
        wall_cap_floor_s=tiers["wall_cap_floor_s"],
        tool_digests=instance_maker.identity_bundle()["tool_digests"],
        scratch_root=scratch_root,
        replay=instance_maker.REPLAY_GRADE,
        skip_cache_lookup=True,
        do_not_cache=instance_maker.DO_NOT_CACHE,
    )
    if attempt.status != runner.STATUS_OK or attempt.parsed is None or attempt.parsed.document is None:
        return attempt, None
    out = instance_maker.InstanceOutput.from_dict(_from_wire(attempt.parsed.document))
    record_trial(sub, nonce, bits, trial, seed, out.instance_hash, out.x, attempt.attempt_id)
    return attempt, out


def _from_wire(document):
    doc = dict(document)
    for name in instance_maker.BIG_FIELDS:
        doc[name] = int(doc[name])
    for name in instance_maker.POINT_FIELDS:
        doc[name] = [int(c) for c in doc[name]]
    if doc.get("transcripts") is not None:
        doc["transcripts"] = [
            {**t, "curve": [int(c) for c in t["curve"]], "result": int(t["result"])} for t in doc["transcripts"]
        ]
    return doc
