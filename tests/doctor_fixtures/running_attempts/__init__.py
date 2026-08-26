from cairn import substrate

FIXABLE = False
ONLY = None
FINDINGS = ("D-substrate/running-attempts",)


def corrupt(shape):
    with substrate.Substrate.open(shape.db) as sub:
        sub.conn.execute(
            "INSERT INTO attempts (attempt_id, recipe_key, status, replay_grade, skip_cache_lookup, started_at)"
            " VALUES ('a' * 64, 'r' * 64, 'RUNNING', 'Replayable', 0, '2026-01-01T00:00:00Z')"
        )
