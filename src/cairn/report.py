import contextlib
import sqlite3
import sys

from cairn import attest, canon, claims, exits, hunt, keys, ladderplan, laddertable, ledger, repro
from cairn.report_records import (
    ReportRefused,
    _executor_observations,
    _hunt_runs,
    _json,
    _Parser,
    _pre_registration,
    _require_campaign,
    _skeptic_records,
    _spend,
    _statement,
    _withdrawals,
    assertion_line,
)
from cairn.substrate import Substrate, SubstrateError


def render(sub, *, kind, statement_hash=None, ladder_table_hash=None, attest_path=None):
    if kind not in ("run", "campaign") or (statement_hash is None) == (ladder_table_hash is None):
        raise ReportRefused("select exactly one statement or ladder table and a report kind")
    tables = []
    if ladder_table_hash is not None:
        table = laddertable.read(sub, ladder_table_hash)
        if table is None:
            raise ReportRefused("unknown ladder table")
        tables = [table]
        hypothesis = claims.get_hypothesis_object(sub, table.hypothesis_hash)
        if hypothesis is None:
            raise ReportRefused("hypothesis missing")
        statement_hash = hypothesis["claim_statement_hash"]
        hypotheses = [hypothesis]
    else:
        hypotheses = [
            dict(row)
            for row in sub.conn.execute(
                "SELECT * FROM hypothesis_objects WHERE claim_statement_hash = ? ORDER BY rowid", (statement_hash,)
            )
        ]
        for hypothesis in hypotheses:
            for row in sub.conn.execute(
                "SELECT hash FROM ladder_tables WHERE hypothesis_hash = ? ORDER BY rowid", (hypothesis["hash"],)
            ):
                tables.append(laddertable.read(sub, row["hash"]))
    statement = _statement(sub, statement_hash) if statement_hash is not None else None
    history = claims.tag_history_for(sub, statement_hash) if statement_hash is not None else []
    tag = history[-1]["to_tag"] if history else "untagged"
    tag_evidence = history[-1]["evidence_hash"] if history else None
    evidence = claims.evidence_for(sub, statement_hash) if statement_hash is not None else []
    skeptic_records = _skeptic_records(sub, statement_hash) if statement_hash is not None else []
    _require_campaign(kind, statement, skeptic_records)
    runs = _hunt_runs(sub, hypotheses, evidence) if ladder_table_hash is None else []
    completed_runs = [item for item in runs if item[1] is not None]
    if not completed_runs and not tables:
        raise ReportRefused("no finished run")
    default_pointer = tag_evidence or (completed_runs[0][2]["hash"] if completed_runs else None)
    default_pointer = default_pointer or (tables[0].hash if tables else None)
    sections = []

    def section(title, lines):
        sections.append(f"## {title}\n\n" + "\n".join(lines))

    def line(text, pointer=None, line_tag=None):
        return assertion_line(text, statement_hash, tag if line_tag is None else line_tag, pointer or default_pointer)

    if statement is None:
        section("Claim", ["No claim statement is bound to this ladder table; table records are prose."])
    else:
        section(
            "Claim",
            [
                line(f"status: {statement['status']}; statement hash: {statement_hash}"),
                line(
                    f"claim id: {statement['claim_id']}; version: {statement['version']}; informal: {statement['informal']}"
                ),
                line(f"scope: {statement['scope']}"),
                *(
                    line(
                        f"withdrawal reason: {payload['reason']}; hunt run: {payload['hunt_run_hash']}; "
                        f"issued by: {payload['issued_by']} at {payload['at']}; record digest: {digest}; {checked}"
                    )
                    for payload, digest, checked in _withdrawals(sub, statement_hash, attest_path)
                ),
            ],
        )
    hypothesis_lines = []
    for hypothesis in hypotheses:
        document = canon.decode(keys.HYPOTHESIS_OBJECT, hypothesis["canonical"])
        hypothesis_lines.extend(
            [
                line(f"hypothesis object hash and key: {hypothesis['hash']}"),
                line(f"method identity: {_json(document['method_identity'])}"),
                line(f"declared ranges: {_json(document['declared_parameter_ranges'])}"),
                line(f"sampling distribution hash: {document['sampling_distribution']}"),
            ]
        )
    section("Hypothesis key", hypothesis_lines)
    pre = []
    limitations = []
    attempts = set()
    run_lines = []
    for nonce, record, node in runs:
        if record is None:
            run_lines.append(
                line(
                    f"run id: {nonce['run_id']}; verdict: none recorded; unfinished run; nonce drawn_at: {nonce['drawn_at']}"
                )
            )
            limitations.append(
                (f"Run {nonce['run_id']} has a nonce but no hunt record; its outcome is unavailable.", default_pointer)
            )
            continue
        hypothesis = next(h for h in hypotheses if h["hash"] == record.hypothesis_key)
        plan_node = sub.get_node(record.plan_hash)
        if plan_node is None:
            raise ReportRefused("plan missing")
        plan = canon.decode(hunt.PLAN, plan_node["canonical"])
        pointer = node["hash"] if node is not None else record.hash
        pre_lines, limits = _pre_registration(sub, hypothesis, record.plan_hash, nonce, plan)
        pre.extend(line(text, pointer) for text in pre_lines)
        limitations.extend((text, pointer) for text in limits)
        run_lines.append(
            line(f"run id: {nonce['run_id']}; verdict: {record.verdict}; run hash: {record.hash}", pointer)
        )
        run_lines.append(line(f"recorded statement survival standing: {str(record.standing).lower()}", pointer))
        owner_rule = "not evaluated; no KILLED witness"
        if record.verdict == "KILLED":
            try:
                owner_grade, owner_reason = repro.owner_grade(
                    sub, plan["executor_identity"], repro.Verifier(repro.SKILL_VERIFIER, plan["verifier_identity"])
                )
            except repro.ReproError as exc:
                owner_rule = f"unavailable; reason: {exc}"
            else:
                owner_rule = f"{owner_grade}; reason: {owner_reason}"
        run_lines.append(line(f"computed verifier owner rule: {owner_rule}", pointer))
        admissible = (
            str(hunt.attempts_admissible(sub, node)).lower()
            if node is not None
            else "unavailable; hunt evidence absent"
        )
        run_lines.append(line(f"live required hunt attempts admissible: {admissible}", pointer))
        run_lines.append(
            line(
                f"budget: {record.budget_status}; completed trials: {record.completed_trial_count}/{record.declared_trial_count}",
                pointer,
            )
        )
        published = nonce["published_at"] is not None
        run_lines.append(
            line(f"nonce: {record.nonce if published else 'withheld'}; published_at: {nonce['published_at']}", pointer)
        )
        for trial in record.trials:
            seed = trial.seed if published else "withheld"
            run_lines.append(
                line(
                    f"trial: {trial.trial}; point: {_json(dict(trial.point))}; seed: {seed}; outcome: {trial.outcome}; "
                    f"verifier status: {trial.verifier_status or 'not run'}{_executor_observations(sub, trial)}",
                    pointer,
                )
            )
            attempts.update(a for a in (trial.attempt_id, trial.verifier_attempt_id) if a is not None)
        if record.counterexample_trial is not None:
            run_lines.append(
                line(
                    f"counterexample trial: {record.counterexample_trial}; verifier status: {record.trials[record.counterexample_trial].verifier_status}",
                    pointer,
                )
            )
        grade_node = sub.get_node(pointer)
        limitations.append((f"stored evidence replay grade: {grade_node['replay_grade']}", pointer))
        for identity_name in ("executor_identity", "verifier_identity"):
            identity = plan[identity_name]
            certified = sub.get_certificate(identity) is not None
            limitations.append(
                (f"{identity_name}: {identity}; certificate: {'recorded' if certified else 'absent'}", pointer)
            )
            if not certified:
                limitations.append(("uncertified producer; PLAN section 3 grades such a witness AuditOnly.", pointer))
        population = node["population"] if node is not None else _json(plan["family_bounds"])
        limitations.append(
            (
                f"covered population: {population}; statement scope: {statement['scope'] if statement else 'unbound'}",
                pointer,
            )
        )
        if record.verdict == "SURVIVED":
            limitations.append(("Survival under a finite budget has a CONJECTURE ceiling and is not a proof.", pointer))
    table_lines = []
    for table in tables:
        verdict = laddertable.recorded_verdict(sub, table.hash)
        table_lines.append(
            line(
                f"table hash: {table.hash}; run id: {table.run_id}; verdict: {verdict.kind}; predicate: {verdict.predicate}",
                table.hash,
            )
        )
        hypothesis = next(h for h in hypotheses if h["hash"] == table.hypothesis_hash)
        nonce_row = sub.conn.execute("SELECT * FROM instance_nonces WHERE nonce = ?", (table.nonce,)).fetchone()
        pre_lines, limits = _pre_registration(sub, hypothesis, table.plan_hash, nonce_row)
        hypothesis_document = canon.decode(keys.HYPOTHESIS_OBJECT, hypothesis["canonical"])
        pre_lines.append(
            f"recorded trial count: {len(table.trials)}; family bounds: "
            f"{_json(hypothesis_document['declared_parameter_ranges'])}; distribution: "
            f"{hypothesis_document['sampling_distribution']}"
        )
        if sub.get_node(table.plan_hash) is None:
            limits.append(
                "Plan node absent; pre-registration details beyond the recorded table and hypothesis are unavailable."
            )
        pre.extend(line(text, table.hash) for text in pre_lines)
        limitations.extend((text, table.hash) for text in limits)
        for rung in table.rungs:
            table_lines.append(
                line(
                    f"rung: {rung.bits}; role: {rung.role}; trials: {rung.trials}; gate operations: {rung.mean_ops or 'unknown'}; radius: {rung.radius}; band: {rung.model_band}; prediction: {rung.model_prediction}; interval: {rung.claim_ci_low},{rung.claim_ci_high}",
                    table.hash,
                )
            )
            for arm in ladderplan.ARMS:
                trials = [t for t in table.trials if t.bits == rung.bits and t.arm == arm]
                operations = [t.gate_ops.value for t in trials]
                ops = "unknown" if any(v is None for v in operations) or not trials else _json(operations)
                table_lines.append(
                    line(
                        f"arm: {arm}; trials: {len(trials)}; recovered: {sum(t.recovered for t in trials)}; gate operations: {ops}",
                        table.hash,
                    )
                )
        attempts.update(laddertable.attempt_ids_for_table(sub, table.hash))
        limitations.append((f"evidence replay grade: {laddertable.replay_grade(table)}", table.hash))
        document = canon.decode(keys.HYPOTHESIS_OBJECT, hypothesis["canonical"])
        limitations.append(
            (
                f"covered population: {_json(document['declared_parameter_ranges'])}; statement scope: {statement['scope'] if statement else 'unbound'}",
                table.hash,
            )
        )
        if verdict.predicate == "uncounted_backend":
            limitations.append(("The gate held no operation count.", table.hash))
    section("Pre-registration", pre)
    section("Hunt record" if runs else "Ladder table", run_lines + table_lines)
    skeptic_lines = []
    for sent, result, view in skeptic_records:
        skeptic_lines.append(line(f"dispatch: {_json(sent.as_dict())}", sent.hash))
        skeptic_lines.append(
            line(f"result: {_json(result.as_dict())}", result.hash)
            if result is not None
            else line("result: absent", sent.hash)
        )
        if view is not None:
            skeptic_lines.append(line(f"audit observation: {_json(view.as_dict())}", view.result_hash))
            skeptic_lines.append(
                line(
                    f"audit verdict: {view.verdict}; checklist template: {view.role_template_hash}; "
                    f"nodes read: {len(view.read_node_hashes)}",
                    view.result_hash,
                )
            )
            skeptic_lines.extend(
                line(
                    f"checklist item {item.id}: {item.outcome}; answer: {item.answer}; "
                    f"cited: {_json(list(item.cited_node_hashes))}",
                    view.result_hash,
                )
                for item in view.items
            )
            limitations.append(
                (
                    f"Skeptic audit verdict {view.verdict} on dispatch {view.dispatch_id}; the record attests "
                    "the recorded audit response, not approval, truth or a tag.",
                    view.result_hash,
                )
            )
    section("Skeptic record", skeptic_lines or ["absent"])
    calibration = [line(f"latest tag: {tag}; evidence pointer: {tag_evidence or 'none'}", tag_evidence)]
    calibration.extend(
        line(
            f"history seq: {row['seq']}; from: {row['from_tag']}; to: {row['to_tag']}; evidence pointer: {row['evidence_hash'] or 'none'}; justification: {row['justification']}; actor: {row['actor']}; at: {row['at']}",
            row["evidence_hash"],
            row["to_tag"],
        )
        for row in history
    )
    section("Calibration tag", calibration)
    entries = [
        entry
        for hypothesis in hypotheses
        for entry in ledger.entries_for(sub, hypothesis["hash"])
        if entry["decision"] in (ledger.REFUTED, ledger.PARKED)
    ]
    section(
        "Ledger entry",
        [line(f"{entry['decision']}: {_json(entry)}", entry["hash"]) for entry in entries] or [line("none")],
    )
    section("Tier spend", [line(_spend(sub, attempts))])
    if not any(view is not None for _, _, view in skeptic_records):
        limitations.append(("Completed typed Skeptic review absent", default_pointer))
    if statement is not None:
        for review in claims.review_verdicts_for(sub, statement_hash):
            verified = False
            if attest_path is not None:
                with contextlib.suppress(OSError, attest.AttestationError):
                    verified = claims.verdict_matches_file(review, attest_path)
            review_hash = claims._verdict_of(review).hash
            limitations.append(
                (f"human-attested review: {review_hash}; verifies: {str(verified).lower()}", review_hash)
            )
    section("Limitations", [line(text, pointer) for text, pointer in dict.fromkeys(limitations)])
    return "\n\n".join(sections) + "\n"


def document(*, db_path, kind, statement_hash=None, ladder_table_hash=None, attest_path=None):
    with Substrate.open(db_path, role="reader") as sub:
        sub.conn.execute("BEGIN")
        return render(
            sub, kind=kind, statement_hash=statement_hash, ladder_table_hash=ladder_table_hash, attest_path=attest_path
        )


def main(argv=None):
    parser = _Parser(prog="python -m cairn.report")
    parser.add_argument("--db", required=True)
    parser.add_argument("--kind", required=True, choices=("run", "campaign"))
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--statement", help="claim statement hash (statement_hash in the campaign output)")
    selector.add_argument("--ladder-table", help="ladder table hash")
    parser.add_argument("--attest")
    try:
        args = parser.parse_args(argv)
        output = document(
            db_path=args.db,
            kind=args.kind,
            statement_hash=args.statement,
            ladder_table_hash=args.ladder_table,
            attest_path=args.attest,
        )
    except (ReportRefused, SubstrateError, sqlite3.Error, OSError, ValueError, KeyError) as exc:
        print(f"refused: {' '.join(str(exc).splitlines())}", file=sys.stderr)
        return exits.GATE_REFUSED
    print(output, end="")
    return exits.OK


if __name__ == "__main__":
    raise SystemExit(main())
