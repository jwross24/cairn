import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests"))

import _substrate_helpers as helpers
import factories
from cairn import claims, yank


class Injected(RuntimeError):
    pass


def main():
    tmp = Path(tempfile.mkdtemp())
    sub = helpers.open_writer(tmp)
    try:
        revision = sub.put_identity_bundle(helpers.IDENTITY_A)
        sub.put_certificate(revision, helpers.TRANSCRIPT_HASH, helpers.ENV_MANIFEST_HASH, helpers.SELFTEST_SUMMARY)
        key = sub.put_recipe(helpers.recipe(seed=1, skill_identity_hash=revision))
        attempt_id, _ = helpers.launch(sub, key, payloads={"out.json": b'{"x": 1}'})

        run = factories.gate_run(result="refused", reasons=("verifier-mismatch",), seed=5)
        claims.write_gate_run(sub, run)

        def refuse(*_args, **_kwargs):
            raise Injected("injected after the yank row")

        sub.add_salt = refuse
        raised = None
        try:
            yank.record(
                sub,
                yank_id="yank-1",
                skill_identity_hash=revision,
                kind=yank.GATE_VERDICT,
                verdict_ref=run.hash,
                attest_path="unused",
                at="2026-09-05T00:00:00.000000+00:00",
            )
        except Injected as exc:
            raised = exc
        del sub.add_salt

        rows = yank.records_for(sub, revision)
        salt = yank.current_salt(sub, revision)
        yank_row_landed = len(rows) == 1
        print(f"injected_raised={raised is not None}")
        print(f"yank_rows={len(rows)} salt={salt!r} attempt_disowned={sub.get_attempt(attempt_id)['disowned_at']!r}")
        print(f"DEFECT partial_write_survives_a_failure={yank_row_landed}")
        return 0 if yank_row_landed else 1
    finally:
        sub.close()


if __name__ == "__main__":
    raise SystemExit(main())
