from dataclasses import dataclass
from datetime import UTC, datetime

import blake3

from cairn import canon, keys
from cairn.canon import BLOBREF, INT, STR, Field, Map, Struct
from cairn.substrate_errors import SubstrateError

GRADES = ("Replayable", "Verifiable", "AuditOnly")
STATUSES = ("RUNNING", "OK", "FAIL", "DISAGREE", "BUDGET_EXCEEDED", "BLOCKED", "SKILL_YANKED", "INTERRUPTED")
TERMINAL_STATUSES = STATUSES[1:]
ROOT_KINDS = ("recipe", "ledger_row", "certificate", "divergence")
EDGE_OUTPUT_OF = "output_of"
EDGE_INPUT = "input"
EDGE_MEMBER = "member"
EDGE_CERTIFIES = "certifies"

OUTPUT_MANIFEST = Struct("output_manifest", [Field("artifacts", Map(STR, BLOBREF))])
SELFTEST_CERT = keys.SELFTEST_CERT
RECEIPT_FLOAT_FIELDS = ("start_mono", "end_mono", "cpu_user_s", "cpu_sys_s", "wall_s")
RECEIPT_INT_FIELDS = ("peak_rss_bytes", "scratch_bytes_written", "exit_status")
RECEIPT_FIELDS = (
    "gate_bundle_hash",
    "start_mono",
    "end_mono",
    "cpu_user_s",
    "cpu_sys_s",
    "wall_s",
    "peak_rss_bytes",
    "scratch_bytes_written",
    "exit_status",
    "stdout_digest",
    "stderr_digest",
    "tool_digests_hash",
    "measurement_scope",
)
RECEIPT = Struct("receipt", [Field(name, INT if name in RECEIPT_INT_FIELDS else STR) for name in RECEIPT_FIELDS])
KIND_TAGS = {**keys.TAGS_BY_KIND, "skill_certificate": keys.TAG_SELFTEST_CERT}


@dataclass(frozen=True)
class Served:
    attempt_id: str
    output_manifest_hash: str


def _now():
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _hex(digest):
    return digest.hex() if isinstance(digest, (bytes, bytearray)) else str(digest)


def blob_hash(data):
    return blake3.blake3(bytes(data)).hexdigest()


def node_hash_for(kind, canonical):
    tag = KIND_TAGS.get(kind)
    if tag is not None:
        return canon.digest(tag, canonical)
    return keys.node_hash(kind, canonical)


def certificate_canonical(identity_bundle_hash, transcript_hash, env_manifest_hash):
    return canon.encode(
        SELFTEST_CERT,
        {
            "identity_bundle_hash": identity_bundle_hash,
            "transcript_hash": transcript_hash,
            "env_manifest_hash": env_manifest_hash,
        },
    )


def certificate_hash(identity_bundle_hash, transcript_hash, env_manifest_hash):
    return keys.selftest_cert_hash(
        {
            "identity_bundle_hash": identity_bundle_hash,
            "transcript_hash": transcript_hash,
            "env_manifest_hash": env_manifest_hash,
        }
    )


def output_manifest_canonical(artifacts):
    return canon.encode(OUTPUT_MANIFEST, {"artifacts": artifacts})


def output_manifest_hash(artifacts):
    return keys.node_hash("output_manifest", output_manifest_canonical(artifacts))


def receipt_canonical(receipt):
    missing = [f for f in RECEIPT_FIELDS if f not in receipt]
    if missing:
        raise SubstrateError(f"receipt missing field(s) {missing}")
    value = {}
    for name in RECEIPT_FIELDS:
        raw = receipt[name]
        if name in RECEIPT_FLOAT_FIELDS:
            value[name] = repr(float(raw))
        elif name in RECEIPT_INT_FIELDS:
            value[name] = int(raw)
        else:
            value[name] = str(raw)
    return canon.encode(RECEIPT, value)


def receipt_hash(receipt):
    return keys.node_hash("receipt", receipt_canonical(receipt))


def grade_weaker(from_grade, to_grade):
    return GRADES.index(to_grade) > GRADES.index(from_grade)


def attempt_eligible(status, disowned_at, inadmissible, do_not_cache, blobs_present):
    if do_not_cache:
        return "do_not_cache"
    if status != "OK":
        return f"status={status}"
    if disowned_at is not None:
        return "disowned"
    if inadmissible:
        return "inadmissible"
    if not blobs_present:
        return "missing_blob"
    return None


MISSING_BLOB_PREDICATE = (
    "NOT EXISTS (SELECT 1 FROM lineage l WHERE l.parent_hash = a.output_manifest_hash AND l.edge_kind = 'member' "
    "AND NOT EXISTS (SELECT 1 FROM blobs b WHERE b.hash = l.child_hash))"
)


def serve_sql(*, exclude_disowned=True, require_blobs=True, require_ok=True):
    predicates = ["a.recipe_key = ?", "a.inadmissible = 0", "r.do_not_cache = 0", "a.output_manifest_hash IS NOT NULL"]
    if require_ok:
        predicates.append("a.status = 'OK'")
    if exclude_disowned:
        predicates.append("a.disowned_at IS NULL")
    if require_blobs:
        predicates.append(MISSING_BLOB_PREDICATE)
    return (
        "SELECT a.attempt_id, a.output_manifest_hash FROM attempts a JOIN recipes r ON r.recipe_key = a.recipe_key WHERE "
        + " AND ".join(predicates)
        + " ORDER BY a.ended_at DESC, a.rowid DESC LIMIT 1"
    )


SERVE_SQL = serve_sql()
