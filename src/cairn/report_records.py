import argparse
import json
from decimal import Decimal

from cairn import claims, dispatch, hunt, ladder


class ReportRefused(ValueError):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ReportRefused(message)


def assertion_line(text, statement_hash=None, tag="untagged", evidence_hash=None):
    text = " ".join(str(text).splitlines())
    if statement_hash is None:
        return text
    pointer = evidence_hash[:12] if evidence_hash else "none"
    return f"{text} [statement={statement_hash[:12]} tag={tag} evidence={pointer}]"


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _statement(sub, digest):
    row = claims.get_claim_statement(sub, digest)
    if row is None:
        named = [
            match["hash"]
            for match in sub.conn.execute(
                "SELECT hash FROM claim_statements WHERE claim_id = ? ORDER BY rowid", (digest,)
            )
        ]
        if named:
            raise ReportRefused(
                f"unknown statement; --statement takes a statement hash, "
                f"and claim id {digest!r} names {', '.join(named)}"
            )
        raise ReportRefused("unknown statement")
    return row


def _require_blob(sub, digest):
    if digest is not None and sub.get_blob(digest) is None:
        raise ReportRefused("evidence missing")


def _validate_trial_evidence(sub, record):
    for trial in record.trials:
        for digest in (trial.execution_evidence, trial.verifier_evidence):
            _require_blob(sub, digest)
            payload = sub.get_blob(digest) if digest is not None else None
            if payload is None:
                continue
            document = json.loads(payload)
            for stream in document.get("stream_blobs", {}).values():
                _require_blob(sub, stream)
            for value in document.get("recipe", {}).get("inputs", {}).values():
                _require_blob(sub, value[0])


def _executor_observations(sub, trial):
    if trial.execution_evidence is None:
        return ""
    evidence = json.loads(sub.get_blob(trial.execution_evidence))
    stdout = evidence.get("stream_blobs", {}).get("stdout")
    if stdout is None:
        return ""
    try:
        output = json.loads(sub.get_blob(stdout))
    except TypeError, ValueError:
        return ""
    if not isinstance(output, dict):
        return ""
    observations = [
        f"{label}: {output[field]}"
        for field, label in (("l", "prime"), ("weight", "weight"))
        if type(output.get(field)) is int
    ]
    return "; executor observations: " + "; ".join(observations) if observations else ""


def _skeptic_records(sub, statement_hash):
    records = []
    for row in sub.conn.execute("SELECT dispatch_id FROM worker_dispatches ORDER BY rowid"):
        sent = dispatch.read(sub, row["dispatch_id"])
        if sent.role != "skeptic" or statement_hash not in sent.handed_node_hashes:
            continue
        view = dispatch.skeptic_record(sub, sent.dispatch_id, statement_hash)
        records.append((sent, dispatch.result(sub, sent.dispatch_id), view))
    return records


def _require_campaign(kind, statement, skeptic_records):
    if kind != "campaign":
        return
    if not any(view is not None for _, _, view in skeptic_records):
        raise ReportRefused("missing skeptic_record")
    if statement is None or statement["status"] == "open":
        raise ReportRefused("statement not terminal")


def _hunt_runs(sub, hypotheses, evidence):
    runs_by_nonce = {}
    for row in sub.conn.execute("SELECT hash FROM nodes WHERE kind = 'hunt_run' ORDER BY rowid"):
        record = hunt.record_for(sub, row["hash"])
        runs_by_nonce[record.nonce] = record
    evidence_by_run = {}
    for node in evidence:
        if node["kind"] != hunt.KIND:
            continue
        for edge in sub.lineage_of(node["hash"]):
            if edge["edge_kind"] == "input":
                evidence_by_run[edge["parent_hash"]] = node
    runs = []
    for hypothesis in hypotheses:
        nonces = sub.conn.execute(
            "SELECT n.rowid AS append_position, n.* FROM instance_nonces n WHERE hypothesis_key = ? "
            "AND NOT EXISTS (SELECT 1 FROM ladder_tables t WHERE t.nonce = n.nonce "
            "AND t.hypothesis_hash = n.hypothesis_key AND t.run_id = n.run_id) ORDER BY n.rowid",
            (hypothesis["hash"],),
        ).fetchall()
        for nonce in nonces:
            record = runs_by_nonce.get(nonce["nonce"])
            if record is None:
                runs.append((dict(nonce), None, None))
                continue
            _validate_trial_evidence(sub, record)
            linked_evidence = evidence_by_run.get(record.hash)
            if linked_evidence is None:
                raise ReportRefused("evidence missing")
            runs.append((dict(nonce), record, linked_evidence))
    runs.sort(key=lambda item: (item[0]["drawn_at"], item[0]["append_position"]))
    return runs


def _pre_registration(sub, hypothesis, plan_hash, nonce, plan_document=None):
    position = ladder.sequence_position(sub, hypothesis["hash"])
    plan_position = ladder.sequence_position(sub, plan_hash)
    lines = [
        f"plan hash: {plan_hash}; hypothesis append position: {position}; plan append position: {plan_position}",
    ]
    if plan_document is not None:
        lines.append(
            f"trial count: {plan_document['trial_count']}; family bounds: {_json(plan_document['family_bounds'])}; "
            f"distribution: {plan_document['distribution_hash']}"
        )
    if nonce is None:
        lines.append("nonce drawn_at: none recorded")
        lines.append("entropy commitment: none recorded")
        return lines, ["entropy commitment: none recorded"]
    lines.append(f"run id: {nonce['run_id']}; nonce drawn_at: {nonce['drawn_at']}")
    committed_position, commitment = ladder.commitment_for(sub, nonce["nonce"])
    if commitment is None:
        lines.append("entropy commitment: none recorded")
        return lines, ["entropy commitment: none recorded"]
    if position is None or position >= committed_position:
        raise ReportRefused("hypothesis after entropy")
    if commitment.hypothesis_hash != hypothesis["hash"]:
        raise ReportRefused("entropy hypothesis mismatch")
    lines.append(f"entropy commitment: {commitment.hash}; append position: {committed_position}")
    return lines, []


def _spend(sub, attempt_ids):
    cpu = Decimal(0)
    wall = Decimal(0)
    for attempt_id in sorted(attempt_ids):
        attempt = sub.get_attempt(attempt_id)
        if attempt is None:
            raise ReportRefused("attempt missing")
        receipt = sub.get_receipt(attempt["receipt_hash"])
        if receipt is None:
            raise ReportRefused("receipt missing")
        cpu += Decimal(str(receipt["cpu_user_s"])) + Decimal(str(receipt["cpu_sys_s"]))
        wall += Decimal(str(receipt["wall_s"]))
    return f"attempts: {len(attempt_ids)}; CPU-seconds: {cpu}; wall-seconds: {wall}"
