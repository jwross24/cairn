def _schema_objects(conn):
    objects = {}
    for row in conn.execute("SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"):
        kind, name, tbl_name, sql = row[0], row[1], row[2], row[3] or ""
        columns = None
        if kind == "table":
            columns = tuple(
                (c[1], (c[2] or "").upper(), int(c[3]), c[4], int(c[5]))
                for c in conn.execute("SELECT * FROM pragma_table_info(?)", (name,))
            )
        objects[(kind, name)] = (tbl_name, " ".join(sql.split()), columns)
    return objects


def _column_mismatch(name, expected, actual):
    expected_names = [c[0] for c in expected]
    actual_names = [c[0] for c in actual]
    missing = [c for c in expected_names if c not in actual_names]
    unknown = [c for c in actual_names if c not in expected_names]
    parts = []
    if missing:
        parts.append("missing " + ", ".join(missing))
    if unknown:
        parts.append("unknown " + ", ".join(unknown))
    if not parts:
        parts.append("column definitions differ")
    return f"table {name}: " + "; ".join(parts)


def _schema_mismatches(expected, actual):
    """Every object the shipped schema names, present and identical.

    An object the shipped schema does not name is ignored: a live store legitimately
    carries observer tables and triggers a session attached to it, and refusing those
    would refuse a store the shipped schema did create.
    """
    reasons = [f"{kind} {name}: absent from the store" for kind, name in sorted(expected.keys() - actual.keys())]
    for key in sorted(expected.keys() & actual.keys()):
        want, have = expected[key], actual[key]
        if want == have:
            continue
        if key[0] == "table" and want[2] != have[2]:
            reasons.append(_column_mismatch(key[1], want[2], have[2]))
        else:
            reasons.append(f"{key[0]} {key[1]}: definition differs from the shipped schema")
    return reasons
