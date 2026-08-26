import os
import uuid
from datetime import UTC, datetime

from cairn import cli, exits, log, substrate
from cairn.errors import CliError

lg = log.get("gc")

PAGE_SIZE = 100


def _now():
    return datetime.now(UTC).isoformat(timespec="microseconds")


def reachable(roots, edges):
    adjacency = {}
    for child, parent, _kind in edges:
        adjacency.setdefault(child, set()).add(parent)
        adjacency.setdefault(parent, set()).add(child)
    seen = set(roots)
    stack = list(seen)
    while stack:
        node = stack.pop()
        for neighbor in adjacency.get(node, ()):
            if neighbor not in seen:
                seen.add(neighbor)
                stack.append(neighbor)
    return seen


def collectable(roots, edges, blobs):
    return set(blobs) - reachable(roots, edges)


def _load(sub):
    roots = {row["node_hash"] for row in sub.conn.execute("SELECT node_hash FROM roots")}
    edges = [
        (row["child_hash"], row["parent_hash"], row["edge_kind"])
        for row in sub.conn.execute("SELECT child_hash, parent_hash, edge_kind FROM lineage")
    ]
    sizes = {row["hash"]: row["size"] for row in sub.conn.execute("SELECT hash, size FROM blobs")}
    return roots, edges, sizes


def plan(sub):
    roots, edges, sizes = _load(sub)
    reach = reachable(roots, edges)
    candidate_hashes = sorted(collectable(roots, edges, set(sizes)))
    candidates = [{"hash": h, "size": sizes[h]} for h in candidate_hashes]
    return {
        "roots": len(roots),
        "reachable": len(reach),
        "candidates": candidates,
        "bytes": sum(c["size"] for c in candidates),
    }


def _delete_blobs(sub, hashes):
    deleted = 0
    for start in range(0, len(hashes), PAGE_SIZE):
        page = hashes[start : start + PAGE_SIZE]
        marks = ", ".join("?" for _ in page)
        cur = sub.conn.execute(f"DELETE FROM blobs WHERE hash IN ({marks})", page)
        deleted += cur.rowcount
    return deleted


def collect(sub, *, dry_run=True, at=None):
    p = plan(sub)
    hashes = [c["hash"] for c in p["candidates"]]
    run_id = uuid.uuid4().hex
    deleted = 0
    with sub._tx():
        if not dry_run:
            deleted = _delete_blobs(sub, hashes)
        sub.conn.execute(
            "INSERT INTO gc_runs (run_id, dry_run, roots, reachable, candidates, count, bytes, at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, int(dry_run), p["roots"], p["reachable"], len(hashes), deleted, p["bytes"], at or _now()),
        )
    lg.info(
        "collect",
        roots=p["roots"],
        reachable=p["reachable"],
        candidates=len(hashes),
        bytes=p["bytes"],
        dry_run=dry_run,
        deleted=deleted,
        run_id=run_id,
    )
    lg.debug("candidates", hashes=hashes)
    return {**p, "dry_run": dry_run, "deleted": deleted, "run_id": run_id}


def _configure(parser):
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list collectable blobs and change nothing; this is the default without --yes, spelled explicitly",
    )


def _run(ns):
    if not os.path.exists(ns.db):
        raise CliError(
            exits.ENVIRONMENT,
            f"the substrate {ns.db} does not exist; a substrate is created by the first command that writes to it",
            where=str(ns.db),
            next_command=f"cairn selftest toy-curve --db {ns.db}",
        )
    yes = getattr(ns, "yes", False)
    try:
        with substrate.Substrate.open(ns.db) as sub:
            if yes:
                preview = plan(sub)
                cli.require_yes(
                    yes,
                    plan=f"delete {len(preview['candidates'])} blob(s), {preview['bytes']} byte(s)",
                    command="cairn gc",
                )
            result = collect(sub, dry_run=not yes)
    except substrate.WriterAlreadyOpen as exc:
        raise CliError(
            exits.CONFLICT,
            f"another writer already holds {ns.db}: {exc}",
            where=str(ns.db),
            next_command=f"cairn gc --db {ns.db}",
        ) from None
    payload = {k: result[k] for k in ("dry_run", "roots", "reachable", "candidates", "bytes", "deleted")}
    if getattr(ns, "json", False):
        cli.emit_json("gc", payload)
    else:
        print(
            f"roots={payload['roots']} reachable={payload['reachable']} "
            f"candidates={len(payload['candidates'])} bytes={payload['bytes']} "
            f"dry_run={payload['dry_run']} deleted={payload['deleted']}"
        )
        for c in payload["candidates"]:
            print(f"  {c['hash']} {c['size']}")
    return exits.OK


cli.register(
    "gc",
    _configure,
    _run,
    summary="collect blobs unreachable from any root over lineage; --yes to delete, otherwise list only",
    read_only=False,
    json=True,
    dangerous=True,
    gating="--yes",
    dry_run_default=True,
)
