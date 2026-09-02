import json
import os
import stat
from pathlib import Path

from cairn import bundle, canon, cli, exits, log
from cairn.canon import NON_EMPTY_STR, Field, Struct
from cairn.errors import CliError
from cairn.substrate import blob_hash

lg = log.get("attest")

LENGTH_BYTES = 8
FIXTURE_WAIVER_EXPIRES = "9999-12-31T23:59:59Z"
KINDS = ("review_verdict", "waiver", "acknowledgment")

WAIVER = Struct(
    "waiver",
    [
        Field("kind", NON_EMPTY_STR),
        Field("target_kind", NON_EMPTY_STR),
        Field("target", NON_EMPTY_STR),
        Field("check", NON_EMPTY_STR),
        Field("reason", NON_EMPTY_STR),
        Field("issued_by", NON_EMPTY_STR),
        Field("expires_at", NON_EMPTY_STR),
    ],
)


class AttestationError(Exception):
    pass


def waiver_canonical(waiver):
    return canon.encode(WAIVER, waiver)


def fixture_waiver(target):
    return {
        "kind": "waiver",
        "target_kind": "hypothesis_key",
        "target": target,
        "check": "tier_gate",
        "reason": "gate-plan fixture",
        "issued_by": "attest init",
        "expires_at": FIXTURE_WAIVER_EXPIRES,
    }


def frame(canonical):
    return canon.length_prefix(bytes(canonical))


def append_record(path, canonical):
    framed = frame(canonical)
    with Path(path).open("ab") as fh:
        offset = fh.tell()
        fh.write(framed)
    lg.info("append", path=str(path), offset=offset, bytes=len(framed), digest=blob_hash(canonical))
    return offset


def read_record(path, offset):
    if isinstance(offset, bool) or not isinstance(offset, int):
        raise AttestationError(f"offset must be an int, got {type(offset).__name__}")
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise AttestationError(f"attestation file {path} is unreadable: {exc.strerror}") from None
    if offset < 0 or offset > len(data) - LENGTH_BYTES:
        return None
    length = int.from_bytes(data[offset : offset + LENGTH_BYTES], "little")
    body = data[offset + LENGTH_BYTES : offset + LENGTH_BYTES + length]
    return body if len(body) == length else None


def _normalize_digest(digest):
    if isinstance(digest, (bytes, bytearray)):
        return bytes(digest).hex()
    if isinstance(digest, str):
        return digest.strip().lower()
    raise AttestationError(f"digest must be bytes or a hex str, got {type(digest).__name__}")


def attestation_record_matches(path, offset, digest):
    wanted = _normalize_digest(digest)
    record = read_record(path, offset)
    if record is None:
        return False
    return blob_hash(record) == wanted


def records(path):
    data = Path(path).read_bytes()
    offset = 0
    while offset + LENGTH_BYTES <= len(data):
        length = int.from_bytes(data[offset : offset + LENGTH_BYTES], "little")
        body = data[offset + LENGTH_BYTES : offset + LENGTH_BYTES + length]
        if len(body) != length:
            return
        yield offset, body
        offset += LENGTH_BYTES + length


def visible_review_verdicts(sub, statement_hash, path):
    from cairn import claims

    return [
        row
        for row in claims.review_verdicts_for(sub, statement_hash)
        if attestation_record_matches(path, row["file_offset"], row["record_digest"])
    ]


def init(path, target):
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    os.close(fd)
    file.chmod(0o644)
    waiver = fixture_waiver(target)
    offset = append_record(file, waiver_canonical(waiver))
    _set_append_only(file)
    lg.info("init", path=str(file), waiver_offset=offset, target=target)
    return offset, waiver


def _set_append_only(path):
    if not hasattr(os, "chflags"):
        lg.warning(
            "append_only_unavailable",
            path=str(path),
            platform=os.name,
            effect="the attestation file carries mode bits only",
        )
        return False
    os.chflags(path, stat.UF_APPEND)
    return True


def _configure(parser):
    subs = parser.add_subparsers(dest="sub", metavar="SUBCOMMAND", required=True)
    parents = [cli.globals_parent(suppress=True), bundle.sub_parent()]
    subs.add_parser(
        "init",
        parents=parents,
        help="create the append-only attestation file and write the gate plan's fixture waiver at record 0",
    )
    append = subs.add_parser(
        "append", parents=parents, help="append one operator record and mirror its digest and offset into the substrate"
    )
    append.add_argument("--kind", required=True, choices=list(KINDS))
    append.add_argument("--record", required=True, metavar="PATH", help="JSON file holding the record's fields")


def _run(ns):
    return {"init": _run_init, "append": _run_append}[ns.sub](ns)


def _run_init(ns):
    if Path(ns.attest).exists():
        raise CliError(
            exits.GATE_REFUSED,
            f"the attestation file {ns.attest} exists; the harness never re-creates it and moving it aside is the operator's act",
            where=str(ns.attest),
            next_command=f"cairn attest append --kind review_verdict --record REC.json --attest {ns.attest}",
        )
    gate = bundle.open_or_refuse(ns, command="cairn attest init")
    offset, waiver = init(ns.attest, gate.waiver_target())
    payload = {
        "sub": "init",
        "attest": str(ns.attest),
        "offset": offset,
        "target": waiver["target"],
        "record_digest": blob_hash(waiver_canonical(waiver)),
        "bundle_hash": gate.hash,
    }
    if getattr(ns, "json", False):
        cli.emit_json("attest", payload)
    else:
        print(f"{ns.attest} record {offset} waiver {waiver['target']}")
    return exits.OK


VERDICT_RECORD_FIELDS = ("statement_hash", "reviewer", "verdict", "checklist_template_hash", "at", "supersedes")


def _verdict_from(fields, gate_bundle_hash, file_offset):
    from cairn import claims

    unknown = sorted(set(fields) - set(VERDICT_RECORD_FIELDS))
    if unknown:
        raise CliError(
            exits.USER_INPUT,
            f"the review_verdict record carries fields no verdict has: {', '.join(unknown)}",
            where=", ".join(unknown),
            next_command=f"a review_verdict record carries {', '.join(VERDICT_RECORD_FIELDS)}",
        )
    missing = sorted(f for f in VERDICT_RECORD_FIELDS if f != "supersedes" and f not in fields)
    if missing:
        raise CliError(
            exits.USER_INPUT,
            f"the review_verdict record is missing: {', '.join(missing)}",
            where=", ".join(missing),
            next_command=f"a review_verdict record carries {', '.join(VERDICT_RECORD_FIELDS)}",
        )
    return claims.ReviewVerdict(
        statement_hash=str(fields["statement_hash"]),
        reviewer=str(fields["reviewer"]),
        verdict=str(fields["verdict"]),
        checklist_template_hash=str(fields["checklist_template_hash"]),
        gate_bundle_hash=str(gate_bundle_hash),
        at=str(fields["at"]),
        supersedes=fields.get("supersedes"),
        file_offset=file_offset,
    )


def _acknowledgment_from(fields):
    from cairn import human_queue

    try:
        return human_queue.acknowledgment_from(fields)
    except human_queue.QueueError as exc:
        raise CliError(
            exits.USER_INPUT,
            str(exc),
            where=", ".join(sorted(fields)),
            next_command=f"an acknowledgment record carries {', '.join(human_queue.ACK_RECORD_FIELDS)}",
        ) from None


def _append_acknowledgment(ns, fields):
    from cairn import human_queue, substrate

    ack = _acknowledgment_from(fields)
    canonical = human_queue.acknowledgment_canonical(ack)
    with substrate.Substrate.open(ns.db) as sub:
        try:
            human_queue.acknowledgable(sub, ack["item_id"], ns.attest)
        except human_queue.QueueError as exc:
            raise CliError(
                exits.GATE_REFUSED,
                str(exc),
                where=ack["item_id"],
                next_command="an acknowledgment names an open human-queue item that holds no blocker",
            ) from None
        offset = append_record(ns.attest, canonical)
        row = human_queue.write_acknowledgment(sub, ack, attest_path=ns.attest, file_offset=offset)
    return canonical, offset, row


def _run_append(ns):
    from cairn import claims, substrate

    if not Path(ns.attest).exists():
        raise CliError(
            exits.ENVIRONMENT,
            f"the attestation file {ns.attest} does not exist",
            where=str(ns.attest),
            next_command=f"cairn attest init --attest {ns.attest}",
        )
    gate = bundle.open_or_refuse(ns, command="cairn attest append")
    fields = json.loads(Path(ns.record).read_text())
    if ns.kind == "waiver":
        canonical = waiver_canonical({"kind": "waiver", **fields})
        offset = append_record(ns.attest, canonical)
        row = None
    elif ns.kind == "acknowledgment":
        canonical, offset, row = _append_acknowledgment(ns, fields)
    else:
        canonical = claims.review_verdict_canonical(_verdict_from(fields, gate.hash, 0))
        offset = append_record(ns.attest, canonical)
        placed = _verdict_from(fields, gate.hash, offset)
        with substrate.Substrate.open(ns.db) as sub:
            row = claims.write_review_verdict(sub, placed)
    payload = {
        "sub": "append",
        "attest": str(ns.attest),
        "kind": ns.kind,
        "offset": offset,
        "record_digest": blob_hash(canonical),
        "row_id": row,
        "bundle_hash": gate.hash,
    }
    if getattr(ns, "json", False):
        cli.emit_json("attest", payload)
    else:
        print(f"{ns.attest} record {offset} {ns.kind}")
    return exits.OK


cli.register(
    "attest",
    _configure,
    _run,
    summary="create and append to the operator-owned, append-only attestation file",
    read_only=False,
    json=True,
)
