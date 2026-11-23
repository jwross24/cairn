import json

from cairn import canon, claims, keys, ladderplan, substrate
from cairn.laddertable_rows import (
    ATTEMPT_MEMBERSHIP,
    ATTEMPT_MEMBERSHIP_KIND,
    NODE_KIND,
    RUNGS,
    TABLES,
    TRIALS,
    LadderTableError,
    _rung_fields,
    _table_canonical,
    _trial_fields,
)
from cairn.laddertable_verdict import enqueue_clock_inconclusive, replay_grade, verdict
from cairn.substrate import _now


def _insert_rung(sub, table_hash, row):
    values = {"table_hash": table_hash, **_rung_fields(row)}
    columns = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    sub.conn.execute(f"INSERT OR IGNORE INTO {RUNGS} ({columns}) VALUES ({marks})", tuple(values.values()))


def _insert_trial(sub, table_hash, t):
    values = {"table_hash": table_hash, **_trial_fields(t)}
    values["output_complete"] = int(values["output_complete"])
    values["recovered"] = int(values["recovered"])
    columns = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    sub.conn.execute(f"INSERT OR IGNORE INTO {TRIALS} ({columns}) VALUES ({marks})", tuple(values.values()))


def _members_fields(table_hash, members):
    return {
        "table_hash": table_hash,
        "members": [
            {"arm": arm, "bits": bits, "trial": trial, "attempt_id": attempt_id}
            for arm, bits, trial, attempt_id in members
        ],
    }


def _canonical_members(trial_attempts):
    if not isinstance(trial_attempts, dict):
        raise LadderTableError("trial_attempts must map (arm, bits, trial) to attempt_id")
    members = []
    for key, attempt_id in trial_attempts.items():
        if not isinstance(key, tuple) or len(key) != 3:
            raise LadderTableError("trial_attempts keys must be (arm, bits, trial) tuples")
        arm, bits, trial = key
        if arm not in ladderplan.ARMS:
            raise LadderTableError("trial_attempts keys must name a ladder arm")
        if isinstance(bits, bool) or isinstance(trial, bool) or not isinstance(bits, int) or not isinstance(trial, int):
            raise LadderTableError("trial_attempts keys must contain integer bits and trial")
        if not isinstance(attempt_id, str) or not attempt_id:
            raise LadderTableError("trial_attempts values must be non-empty attempt IDs")
        members.append((arm, bits, trial, attempt_id))
    members.sort()
    if len({attempt_id for _, _, _, attempt_id in members}) != len(members):
        raise LadderTableError("every ladder trial must name a distinct attempt")
    return tuple(members)


def _claimant_dispatch(sub, table):
    rows = sub.conn.execute("SELECT record_json FROM ladder_dispatches ORDER BY rowid").fetchall()
    matches = []
    for row in rows:
        value = json.loads(row["record_json"])
        if (
            value.get("run_id") == table.run_id
            and value.get("nonce") == table.nonce
            and value.get("hypothesis_hash") == table.hypothesis_hash
            and value.get("arm") == ladderplan.ARMS[0]
        ):
            matches.append(value)
    if len(matches) != 1:
        raise LadderTableError(f"table {table.hash} has {len(matches)} claimant dispatches")
    dispatch = matches[0]
    if (
        dispatch.get("method_identity") != table.method_identity
        or dispatch.get("implementation_revision") != table.implementation_revision
        or dispatch.get("gate_bundle_hash") != table.gate_bundle_hash
        or dispatch.get("plan_hash") != table.plan_hash
    ):
        raise LadderTableError(f"claimant dispatch for table {table.hash} disagrees with the table identity")
    return dispatch


def _expected_trial_slots(plan):
    return {
        (arm, rung.bits, trial)
        for rung in plan.rungs
        for arm in ((ladderplan.ARMS[0],) if rung.role == ladderplan.ROLE_HOLD_OUT else ladderplan.ARMS)
        for trial in range(rung.trials)
    }


def _validate_trial_attempts(sub, table, plan, trial_attempts):
    from cairn import instances

    members = _canonical_members(trial_attempts)
    expected = _expected_trial_slots(plan)
    actual = {(t.arm, t.bits, t.trial) for t in table.trials}
    if actual != expected:
        raise LadderTableError("table trials must match the plan arm topology")
    found = {(arm, bits, trial) for arm, bits, trial, _ in members}
    if found != expected:
        raise LadderTableError("trial_attempts must name every and only table trial")
    trials = {(t.arm, t.bits, t.trial): t for t in table.trials}
    dispatches = {
        value["arm"]: value
        for row in sub.conn.execute("SELECT record_json FROM ladder_dispatches ORDER BY rowid").fetchall()
        if (value := json.loads(row["record_json"])).get("run_id") == table.run_id
    }
    for arm, bits, trial, attempt_id in members:
        attempt = sub.get_attempt(attempt_id)
        if attempt is None:
            raise LadderTableError(f"trial {bits}/{trial} names no attempt {attempt_id}")
        recipe = sub.get_recipe(attempt["recipe_key"])
        dispatch_for_arm = dispatches.get(arm)
        expected_seed = instances.trial_seed(table.nonce, f"{table.hypothesis_hash}/{arm}", bits, trial)
        expected_salt = f"ladder/{table.run_id}/{arm}/{bits}/{trial}"
        if (
            trials[(arm, bits, trial)].seed != expected_seed
            or recipe is None
            or recipe["seed"] != expected_seed
            or recipe["salt"] != expected_salt
            or dispatch_for_arm is None
            or recipe["skill_identity_hash"] != dispatch_for_arm["identity_bundle_hash"]
        ):
            raise LadderTableError(f"attempt {attempt_id} is not the {arm} trial {bits}/{trial} for table {table.hash}")
    return members


def _membership_rows(sub, table_hash):
    rows = sub.conn.execute(
        "SELECT n.hash, n.canonical FROM nodes n JOIN lineage l ON l.child_hash = n.hash "
        "WHERE n.kind = ? AND l.parent_hash = ? AND l.edge_kind = ? ORDER BY n.hash",
        (ATTEMPT_MEMBERSHIP_KIND, table_hash, substrate.EDGE_INPUT),
    ).fetchall()
    memberships = []
    for row in rows:
        value = canon.decode(ATTEMPT_MEMBERSHIP, bytes(row["canonical"]))
        if value["table_hash"] != table_hash:
            raise substrate.HashCollision(f"membership node {row['hash']} names another table")
        members = tuple((m["arm"], m["bits"], m["trial"], m["attempt_id"]) for m in value["members"])
        if tuple(sorted(members)) != members or len({(arm, bits, trial) for arm, bits, trial, _ in members}) != len(
            members
        ):
            raise substrate.HashCollision(f"membership node {row['hash']} is not canonical")
        memberships.append((row["hash"], members))
    return memberships


def membership_for_table(sub, table_hash):
    memberships = _membership_rows(sub, table_hash)
    if not memberships:
        return None
    values = {members for _, members in memberships}
    if len(values) != 1:
        raise substrate.HashCollision(f"table {table_hash} has conflicting attempt memberships")
    return next(iter(values))


def mapped_table_for_attempt(sub, attempt_id):
    tables = set()
    rows = sub.conn.execute(
        "SELECT n.hash, n.canonical, l.parent_hash FROM nodes n JOIN lineage l ON l.child_hash = n.hash "
        "WHERE n.kind = ? AND l.edge_kind = ? ORDER BY n.hash",
        (ATTEMPT_MEMBERSHIP_KIND, substrate.EDGE_INPUT),
    ).fetchall()
    for row in rows:
        value = canon.decode(ATTEMPT_MEMBERSHIP, bytes(row["canonical"]))
        if value["table_hash"] != row["parent_hash"]:
            raise substrate.HashCollision(f"membership node {row['hash']} has a conflicting table lineage")
        if any(member["attempt_id"] == attempt_id for member in value["members"]):
            tables.add(value["table_hash"])
    if len(tables) > 1:
        raise substrate.HashCollision(f"attempt {attempt_id} resolves to multiple ladder memberships")
    return next(iter(tables), None)


def table_for_attempt(sub, attempt_id):
    mapped = mapped_table_for_attempt(sub, attempt_id)
    legacy = {
        row["hash"]
        for row in sub.conn.execute(f"SELECT hash FROM {TABLES} WHERE attempt_id = ?", (attempt_id,)).fetchall()
    }
    all_tables = ({mapped} if mapped is not None else set()) | legacy
    if len(all_tables) > 1:
        raise substrate.HashCollision(f"attempt {attempt_id} resolves to multiple ladder tables")
    return next(iter(all_tables), None)


def attempt_ids_for_table(sub, table_hash):
    members = membership_for_table(sub, table_hash)
    return () if members is None else tuple(attempt_id for _, _, _, attempt_id in members)


def _store_membership(sub, table, members):
    existing = membership_for_table(sub, table.hash)
    if existing is not None and existing != members:
        raise substrate.HashCollision(f"table {table.hash} exists with different trial_attempts")
    canonical = canon.encode(ATTEMPT_MEMBERSHIP, _members_fields(table.hash, members))
    digest = keys.node_hash(ATTEMPT_MEMBERSHIP_KIND, canonical)
    sub._put_node(ATTEMPT_MEMBERSHIP_KIND, canonical, digest, "Replayable", None)
    sub._add_lineage(digest, table.hash, substrate.EDGE_INPUT)
    return digest


def _binding_table_hashes(sub, node_hash):
    rows = sub.conn.execute(
        "SELECT l.parent_hash FROM lineage l JOIN nodes n ON n.hash = l.parent_hash "
        "WHERE l.child_hash = ? AND l.edge_kind = ? AND n.kind = ?",
        (node_hash, substrate.EDGE_INPUT, NODE_KIND),
    ).fetchall()
    return {row["parent_hash"] for row in rows}


def _validate_evidence_node(sub, table, node):
    if node.kind != NODE_KIND:
        raise LadderTableError("a ladder table can bind only ladder_table evidence")
    members = membership_for_table(sub, table.hash)
    claimant_ids = {attempt_id for arm, _, _, attempt_id in members or () if arm == ladderplan.ARMS[0]}
    if members is None or node.attempt_id not in claimant_ids:
        raise LadderTableError(f"evidence attempt {node.attempt_id} is not a claimant member of table {table.hash}")
    hypothesis = claims.get_hypothesis_object(sub, table.hypothesis_hash)
    statement_hash = None if hypothesis is None else hypothesis["claim_statement_hash"]
    if statement_hash is None or node.target_statement_hash != statement_hash:
        raise LadderTableError(
            f"evidence target {node.target_statement_hash} is not table {table.hash}'s bound statement"
        )
    if claims.get_claim_statement(sub, statement_hash) is None:
        raise LadderTableError(f"table {table.hash} names missing claim statement {statement_hash}")
    dispatch = _claimant_dispatch(sub, table)
    if node.producer_tag != "skill" or node.producer_identity != dispatch["identity_bundle_hash"]:
        raise LadderTableError(f"evidence producer is not table {table.hash}'s claimant skill")


def write_evidence_node(sub, table, node):
    if membership_for_table(sub, table.hash) is None:
        raise LadderTableError(f"table {table.hash} has no claimant membership")
    _validate_evidence_node(sub, table, node)
    with sub._tx():
        bindings = _binding_table_hashes(sub, node.hash)
        if bindings and bindings != {table.hash}:
            raise substrate.HashCollision(f"evidence {node.hash} is already bound to another ladder table")
        claims.write_evidence_node(sub, node)
        sub._add_lineage(node.hash, table.hash, substrate.EDGE_INPUT)
    return node.hash


def write(sub, table, plan, *, at=None, attempt_id=None, trial_attempts=None, evidence_nodes=()):
    v = verdict(table, plan)
    grade = replay_grade(table)
    canonical = _table_canonical(table)
    created_at = table.created_at or at or _now()
    members = None if trial_attempts is None else _validate_trial_attempts(sub, table, plan, trial_attempts)
    with sub._tx():
        sub._put_node(NODE_KIND, canonical, table.hash, grade, None)
        inserted = claims._insert_once(
            sub,
            TABLES,
            "hash",
            {
                "hash": table.hash,
                "run_id": table.run_id,
                "nonce": table.nonce,
                "hypothesis_hash": table.hypothesis_hash,
                "method_identity": claims.to_json(table.method_identity),
                "implementation_revision": table.implementation_revision,
                "gate_bundle_hash": table.gate_bundle_hash,
                "plan_hash": table.plan_hash,
                "uncounted_backend": table.uncounted_backend,
                "attempt_id": attempt_id,
                "verdict": v.kind,
                "verdict_predicate": v.predicate,
                "refutation_kind": v.refutation_kind,
                "verdict_rung": v.rung_bits,
                "replay_grade": grade,
                "created_at": created_at,
            },
            table.hash,
        )
        if inserted:
            for row in table.rungs:
                _insert_rung(sub, table.hash, row)
            for t in table.trials:
                _insert_trial(sub, table.hash, t)
        if members is not None:
            _store_membership(sub, table, members)
        for node in evidence_nodes:
            write_evidence_node(sub, table, node)
        if inserted:
            enqueue_clock_inconclusive(sub, table, plan, v, at=created_at)
    return table.hash
