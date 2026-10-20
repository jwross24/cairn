"""The human act that withdraws an open claim statement whose hunt survived (PLAN section 4).

Withdrawal is terminal and reason-bearing, the act of the branch's worker or of the human and never
of the orchestrator, and it erases no gate outcome. It concludes one SURVIVED hunt of the statement
on the strength of a typed Skeptic record, refuses a statement any hunt killed, and moves no tag.
"""

from cairn import canon, claims, dispatch, human_authority, hunt, log, report_records

lg = log.get("withdrawal")


class WithdrawalRefused(ValueError):
    pass


def _hunt_record(sub, digest):
    try:
        return hunt.record_for(sub, digest)
    except canon.CanonError, ValueError, TypeError:
        return None


def _killed(sub, statement_hash):
    for row in sub.conn.execute("SELECT hash FROM nodes WHERE kind = 'hunt_run'").fetchall():
        record = _hunt_record(sub, row["hash"])
        if record is not None and record.statement_hash == statement_hash and record.verdict == "KILLED":
            return True
    return False


def check(sub, fields, *, gate_bundle_hash):
    try:
        human_authority.canonical(human_authority.STATEMENT_WITHDRAWAL, fields, gate_bundle_hash=gate_bundle_hash)
    except human_authority.HumanAuthorityError as exc:
        raise WithdrawalRefused(str(exc)) from None
    statement_hash = fields["statement_hash"]
    statement = claims.get_claim_statement(sub, statement_hash)
    if statement is None or statement["status"] != "open":
        raise WithdrawalRefused("statement is not open")
    record = _hunt_record(sub, fields["hunt_run_hash"])
    if (
        record is None
        or record.hash != fields["hunt_run_hash"]
        or record.statement_hash != statement_hash
        or record.verdict != "SURVIVED"
    ):
        raise WithdrawalRefused("withdrawal must conclude a SURVIVED hunt of this statement")
    if _killed(sub, statement_hash):
        raise WithdrawalRefused("a KILLED hunt refutes this statement; it cannot be withdrawn")
    try:
        skeptic = dispatch.skeptic_record(sub, fields["skeptic_dispatch_id"], statement_hash)
    except dispatch.DispatchRefused as exc:
        raise WithdrawalRefused(str(exc)) from None
    if skeptic is None:
        raise WithdrawalRefused("missing skeptic_record")
    try:
        report_records._skeptic_records(sub, statement_hash)
    except (report_records.ReportRefused, dispatch.DispatchRefused) as exc:
        raise WithdrawalRefused(str(exc)) from None


def attested(sub, attest_path, statement_hash):
    return [
        record
        for record in human_authority.visible_records(sub, human_authority.STATEMENT_WITHDRAWAL, attest_path)
        if record["statement_hash"] == statement_hash
    ]


def withdraw(sub, attest_path, fields, *, gate_bundle_hash):
    check(sub, fields, gate_bundle_hash=gate_bundle_hash)
    earlier = attested(sub, attest_path, fields["statement_hash"])
    row = (
        earlier[0]
        if earlier
        else human_authority.append(
            sub, attest_path, human_authority.STATEMENT_WITHDRAWAL, fields, gate_bundle_hash=gate_bundle_hash
        )
    )
    claims.transition_status(sub, fields["statement_hash"], "withdrawn")
    lg.info("withdraw", statement_hash=fields["statement_hash"], record_digest=row["record_digest"])
    return row
