import sys
import tempfile
from pathlib import Path

from cairn import attest, claims, disagreement, human_queue, substrate

AT = "2026-09-02T00:00:00+00:00"


def main():
    sys.path.insert(0, "tests")
    import factories

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        log = root / "attestations.log"
        attest.init(log, "f" * 64)
        sub = substrate.Substrate.open(root / "cairn.db", role="writer")
        try:
            statement = factories.claim_statement(seed=1)
            claims.write_claim_statement(sub, statement)
            claims.append_tag_history(
                sub, statement.hash, None, "CONJECTURE", None, claims.to_json({"result": "repro"}), "test", at=AT
            )
            rec = disagreement.record(
                sub,
                statement_hash=statement.hash,
                left_hash="11" * 32,
                right_hash="22" * 32,
                classification=disagreement.STATEMENT_ERROR,
                at=AT,
            )
            frozen = disagreement.freeze_for(sub, statement.hash, log)
            assert frozen is not None, "no freeze to lift; the reproduction never armed"
            try:
                human_queue.close_by_blocker_clear(
                    sub, rec.item_id, attest_path=log, cleared_by="not-a-human-and-nobody-checked"
                )
            except human_queue.ClosingRuleViolation as e:
                still = disagreement.freeze_for(sub, statement.hash, log)
                print("REFUSED: an unattested cleared_by string no longer lifts the freeze")
                print(f"  item     {rec.item_id}")
                print(f"  refusal  {e}")
                print(f"  freeze   {still[0] if still else None} (stands)")
                print(f"  depth    {human_queue.depth(sub, log)}")
                return 1
            print("REPRODUCED: an unattested cleared_by string lifted the freeze")
            return 0
        finally:
            sub.close()


if __name__ == "__main__":
    sys.exit(main())
