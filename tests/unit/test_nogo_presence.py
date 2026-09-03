import hashlib
import re
import sys
from pathlib import Path

import pytest

from cairn import attest, exits, human_queue, nogo
from cairn.errors import CliError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers

KEY = "a1" * 32
BUNDLE_HASH = "b2" * 32
AT = "2026-09-02T00:00:00.000000+00:00"
EVASIONS = (
    {"no_go": nogo.SHOUP_SQRT_N, "evasion": "exploits the named endomorphism structure, not generic group ops"},
    {"no_go": nogo.ISOGENY_INVARIANCE, "evasion": "never walks the isogeny class; the invariant is not the lever"},
    {"no_go": nogo.PRIME_FIELD_INDEX_CALCULUS, "evasion": "no point decomposition; the field stays F_p with n = 1"},
)


@pytest.fixture
def writer(tmp_path):
    sub = helpers.open_writer(tmp_path)
    yield sub
    sub.close()


@pytest.fixture
def attest_file(tmp_path):
    path = tmp_path / "attest.bin"
    attest.init(str(path), "f" * 64)
    return str(path)


def declaration(evasions=EVASIONS, key=KEY):
    return nogo.Declaration(hypothesis_key=key, evasions=evasions, declared_by="worker-3", at=AT)


def review(verdict=nogo.ACCEPT_FOR_TIERING, declaration_hash="d3" * 32, offset=0, reviewer="human-1"):
    return nogo.Review(
        hypothesis_key=KEY,
        declaration_hash=declaration_hash,
        reviewer=reviewer,
        verdict=verdict,
        gate_bundle_hash=BUNDLE_HASH,
        at=AT,
        file_offset=offset,
    )


def test_a_complete_declaration_addresses_all_three_no_gos_and_hashes_the_same_twice():
    first, second = declaration(), declaration(reversed(EVASIONS))
    assert nogo.missing_no_gos(EVASIONS) == ()
    assert first.hash == second.hash
    a, b = nogo.declaration_canonical(first), nogo.declaration_canonical(second)
    assert (len(a), hashlib.sha256(a).hexdigest()) == (len(b), hashlib.sha256(b).hexdigest())


@pytest.mark.parametrize(
    ("evasions", "problem"),
    [
        (EVASIONS[:2], f"{nogo.PRIME_FIELD_INDEX_CALCULUS} not addressed"),
        ((*EVASIONS[:2], {"no_go": nogo.PRIME_FIELD_INDEX_CALCULUS, "evasion": "   "}), "has an empty evasion"),
        ((*EVASIONS, {"no_go": "weil_descent", "evasion": "x"}), "unknown no-go 'weil_descent'"),
        ((*EVASIONS, EVASIONS[0]), f"{nogo.SHOUP_SQRT_N} named twice"),
        ((), "not addressed"),
    ],
    ids=["one-missing", "blank-evasion", "unknown-name", "duplicate", "empty"],
)
def test_an_incomplete_declaration_is_refused_so_its_absence_stays_the_flag(evasions, problem):
    assert any(problem in p for p in nogo.missing_no_gos(evasions))
    with pytest.raises(nogo.NogoError, match=re.escape(problem)):
        declaration(evasions)


def test_a_review_carries_one_of_the_three_verdicts_and_its_digest_is_the_blob_hash_of_its_canonical():
    r = review()
    assert r.record_digest == attest.blob_hash(nogo.review_canonical(r))
    assert r.hash != r.record_digest
    with pytest.raises(nogo.NogoError, match="verdict must be one of"):
        review(verdict="approve")


def test_a_review_record_is_parsed_from_exactly_its_fields():
    fields = {"hypothesis_key": KEY, "declaration_hash": "d3" * 32, "reviewer": "h", "verdict": "reject", "at": AT}
    parsed = nogo.review_from_fields(fields, BUNDLE_HASH, 40)
    assert (parsed.verdict, parsed.gate_bundle_hash, parsed.file_offset, parsed.supersedes) == (
        "reject",
        BUNDLE_HASH,
        40,
        None,
    )
    with pytest.raises(nogo.NogoError, match="no field checklist_template_hash"):
        nogo.review_from_fields({**fields, "checklist_template_hash": "x"}, BUNDLE_HASH, 0)
    with pytest.raises(nogo.NogoError, match="missing declaration_hash"):
        nogo.review_from_fields({k: v for k, v in fields.items() if k != "declaration_hash"}, BUNDLE_HASH, 0)
    with pytest.raises(CliError) as info:
        attest._nogo_review_from({"bogus": 1}, BUNDLE_HASH, 0)
    assert info.value.code == exits.USER_INPUT


def test_the_flag_is_the_absence_of_a_declaration_and_writing_one_enqueues_the_review(writer, attest_file):
    before = nogo.flag(writer, KEY)
    assert (before.declared, before.accepted, before.flagged) == (False, False, True)
    digest, item_id = nogo.write_declaration(writer, declaration(), attest_path=attest_file)
    after = nogo.flag(writer, KEY)
    assert (after.declaration_hash, after.declared, after.accepted, after.flagged) == (digest, True, False, False)
    item = human_queue.get_item(writer, item_id)
    assert (item["class"], item["target_kind"], item["target"], item["blocker"]) == (
        human_queue.NOGO_REVIEW,
        human_queue.BRANCH,
        KEY,
        human_queue.NOGO_REVIEW,
    )
    assert nogo.write_declaration(writer, declaration(), attest_path=attest_file) == (digest, None)
    assert writer.get_node(digest)["kind"] == nogo.DECLARATION_KIND
    with pytest.raises(nogo.NogoError, match="needs the attestation path"):
        nogo.write_declaration(writer, declaration(reversed(EVASIONS)))


def test_a_review_is_visible_only_when_its_re_derived_digest_is_the_record_at_its_offset(writer, attest_file):
    path = Path(attest_file)
    digest, _ = nogo.write_declaration(writer, declaration(), attest_path=attest_file)
    accepted = review(declaration_hash=digest)
    offset = attest.append_record(str(path), nogo.review_canonical(accepted))
    placed = review(declaration_hash=digest, offset=offset)
    nogo.write_review(writer, placed)
    assert [r["verdict"] for r in nogo.visible_reviews(writer, KEY, str(path))] == [nogo.ACCEPT_FOR_TIERING]
    assert nogo.flag(writer, KEY, str(path)).accepted
    assert nogo.mirrored(writer, KEY, placed.record_digest, offset)

    unattested = review(verdict=nogo.REJECT, declaration_hash=digest, offset=offset + 1000)
    nogo.write_review(writer, unattested)
    forged = review(verdict=nogo.REJECT, declaration_hash=digest, offset=offset)
    writer.conn.execute(
        f"INSERT INTO {nogo.REVIEWS} (hypothesis_key, declaration_hash, reviewer, verdict, gate_bundle_hash, at, supersedes, record_digest, file_offset) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (KEY, digest, forged.reviewer, forged.verdict, BUNDLE_HASH, AT, None, placed.record_digest, offset),
    )
    writer.conn.commit()
    corrupt = review(verdict=nogo.REJECT, declaration_hash=digest, offset=offset, reviewer="human-2")
    corrupt_offset = attest.append_record(str(path), nogo.review_canonical(corrupt))
    writer.conn.execute(
        f"INSERT INTO {nogo.REVIEWS} (hypothesis_key, declaration_hash, reviewer, verdict, gate_bundle_hash, at, supersedes, record_digest, file_offset) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (KEY, digest, "human-2", nogo.REJECT, BUNDLE_HASH, AT, None, "0" * 64, corrupt_offset),
    )
    writer.conn.commit()
    rows = nogo.reviews_for(writer, KEY)
    assert [r["verdict"] for r in rows] == [nogo.ACCEPT_FOR_TIERING, nogo.REJECT, nogo.REJECT, nogo.REJECT]
    assert attest.attestation_record_matches(str(path), corrupt_offset, nogo._review_of(rows[3]).record_digest)
    assert [r["row_id"] for r in nogo.visible_reviews(writer, KEY, str(path))] == [rows[0]["row_id"]]
    assert nogo.flag(writer, KEY, str(path)).accepted
    assert not nogo.mirrored(writer, KEY, placed.record_digest, offset + 1000)


def test_a_review_of_a_superseded_declaration_neither_accepts_nor_closes_for_the_current_one(writer, attest_file):
    path = Path(attest_file)
    old, item_id = nogo.write_declaration(writer, declaration(), attest_path=attest_file)
    placed = review(
        declaration_hash=old,
        offset=attest.append_record(str(path), nogo.review_canonical(review(declaration_hash=old))),
    )
    nogo.write_review(writer, placed)
    assert nogo.flag(writer, KEY, str(path)).accepted
    assert nogo.mirrored(writer, KEY, placed.record_digest, placed.file_offset)
    revised = tuple({**e, "evasion": e["evasion"] + " (revised)"} for e in EVASIONS)
    new, same_item = nogo.write_declaration(writer, declaration(revised), attest_path=attest_file)
    assert same_item == item_id
    flag = nogo.flag(writer, KEY, str(path))
    assert (flag.declaration_hash, flag.declared, flag.accepted) == (new, True, False)
    assert not nogo.mirrored(writer, KEY, placed.record_digest, placed.file_offset)
    with pytest.raises(human_queue.ClosingRuleViolation, match="is mirrored"):
        human_queue.close_by_attestation(
            writer, item_id, attest_path=attest_file, file_offset=placed.file_offset, record_digest=placed.record_digest
        )
    assert nogo.open_review_item(writer, KEY, attest_file) == item_id


def test_the_kind_and_verdict_checks_are_in_the_schema(writer):
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        writer.conn.execute(
            f"INSERT INTO {nogo.REVIEWS} (hypothesis_key, declaration_hash, reviewer, verdict, gate_bundle_hash, at, supersedes, record_digest, file_offset) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (KEY, "d3" * 32, "h", "approve", BUNDLE_HASH, AT, None, "0" * 64, 0),
        )
    nogo.write_declaration(writer, declaration(), enqueue=False)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        writer.conn.execute(f"DELETE FROM {nogo.DECLARATIONS}")
