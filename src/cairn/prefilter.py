"""The §7 statement pre-filter result a Tier-1 theorem ticket reads.

The filters reject or flag, never pass. A REJECT from any filter denies the ticket. A FLAG is
carried on the record and denies nothing: it is adjudicated by the human statement review that
Tier-2 theorem admission already requires, and collapsing it into a refusal would bar a correct
statement from the cheap tier before the review that resolves it runs. A record satisfies the
Tier-1 predicate only where every filter in the battery carries a verdict and none rejected, so a
filter that did not run is never read as a filter that was quiet.

The record binds the statement hash and the gate-bundle hash it was produced under. Bead
cairn-m1-cqt.5.8 produces these records and conforms to this reader; the verdict spelling below is
the reader's half of that agreement.
"""

from dataclasses import dataclass

from cairn import canon, log
from cairn.canon import NON_EMPTY_STR, STR, Field, List, Map, Struct
from cairn.substrate import SubstrateError, _now

lg = log.get("prefilter")

KIND = "prefilter_result"
PRODUCER = "gate:prefilter"

REJECT = "REJECT"
FLAG = "FLAG"
QUIET = "QUIET"
VERDICTS = (REJECT, FLAG, QUIET)

VACUITY = "vacuity"
EXISTS_IMPLICATION = "exists_implication"
STUB_OR_AXIOM = "stub_or_axiom"
BOUNDED_PROVER = "bounded_prover"
ROUNDTRIP_DIVERGENCE = "roundtrip_divergence"
REQUIRED_FILTERS = (VACUITY, EXISTS_IMPLICATION, STUB_OR_AXIOM, BOUNDED_PROVER, ROUNDTRIP_DIVERGENCE)

RECORD = Struct(
    KIND,
    [
        Field("statement_hash", NON_EMPTY_STR),
        Field("gate_bundle_hash", NON_EMPTY_STR),
        Field("verdicts", Map(STR, STR)),
        Field("flags", List(STR)),
        Field("at", NON_EMPTY_STR),
    ],
)


class PrefilterError(SubstrateError):
    pass


@dataclass(frozen=True)
class PrefilterResult:
    statement_hash: str
    gate_bundle_hash: str
    verdicts: dict
    flags: tuple
    at: str

    @property
    def rejected(self):
        return tuple(sorted(name for name, verdict in self.verdicts.items() if verdict == REJECT))

    @property
    def missing(self):
        return tuple(name for name in REQUIRED_FILTERS if name not in self.verdicts)

    @property
    def flagged(self):
        return tuple(sorted(name for name, verdict in self.verdicts.items() if verdict == FLAG))

    @property
    def passed(self):
        return not self.missing and not self.rejected


def canonical(result):
    return canon.encode(
        RECORD,
        {
            "statement_hash": result.statement_hash,
            "gate_bundle_hash": result.gate_bundle_hash,
            "verdicts": dict(result.verdicts),
            "flags": list(result.flags),
            "at": result.at,
        },
    )


def _validate(statement_hash, gate_bundle_hash, verdicts, flags):
    if not statement_hash or not gate_bundle_hash:
        raise PrefilterError("a pre-filter result names its statement hash and its gate-bundle hash")
    unknown = tuple(sorted(name for name in verdicts if name not in REQUIRED_FILTERS))
    if unknown:
        raise PrefilterError(f"pre-filters {unknown} are not in the battery {REQUIRED_FILTERS}")
    bad = tuple(sorted(f"{name}={verdicts[name]!r}" for name in verdicts if verdicts[name] not in VERDICTS))
    if bad:
        raise PrefilterError(f"verdicts {bad} are not one of {VERDICTS}")
    flagged = {name for name, verdict in verdicts.items() if verdict == FLAG}
    carried = set(flags)
    if not flagged <= carried:
        raise PrefilterError(f"filters {tuple(sorted(flagged - carried))} returned {FLAG} and carry no flag")
    if not carried <= set(verdicts):
        raise PrefilterError(f"flags {tuple(sorted(carried - set(verdicts)))} name no filter that ran")


def record(sub, gate_bundle, *, statement_hash, verdicts, flags=(), at=None):
    _validate(statement_hash, gate_bundle.hash, verdicts, flags)
    result = PrefilterResult(
        statement_hash=statement_hash,
        gate_bundle_hash=gate_bundle.hash,
        verdicts=dict(verdicts),
        flags=tuple(sorted(flags)),
        at=at or _now(),
    )
    digest = sub.put_node(KIND, canonical(result), producer_identity=PRODUCER)
    lg.info(
        "record",
        node=digest,
        statement_hash=statement_hash,
        bundle_hash=gate_bundle.hash,
        rejected=list(result.rejected),
        flagged=list(result.flagged),
        missing=list(result.missing),
        passed=result.passed,
    )
    return digest, result


def result_for(sub, digest):
    row = sub.get_node(digest)
    if row is None or row["kind"] != KIND:
        return None
    return _from_canonical(row["canonical"])


def _from_canonical(blob):
    value = canon.decode(RECORD, blob)
    return PrefilterResult(
        statement_hash=value["statement_hash"],
        gate_bundle_hash=value["gate_bundle_hash"],
        verdicts=dict(value["verdicts"]),
        flags=tuple(value["flags"]),
        at=value["at"],
    )


def read(sub, gate_bundle, statement_hash):
    """The most recent result recorded for the statement under this bundle, or None.

    A result carrying another bundle's hash is not read: the battery is bundle-pinned, so a
    stale-bundle result is an absent one and the ticket re-mints rather than resting on it.
    """
    rows = sub.conn.execute("SELECT canonical FROM nodes WHERE kind = ? ORDER BY rowid", (KIND,)).fetchall()
    found = None
    for row in rows:
        result = _from_canonical(row["canonical"])
        if result.statement_hash == statement_hash and result.gate_bundle_hash == gate_bundle.hash:
            found = result
    return found


def admits_tier_one(sub, gate_bundle, statement_hash):
    result = read(sub, gate_bundle, statement_hash)
    return result is not None and result.passed
