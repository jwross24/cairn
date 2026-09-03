"""The foundations auditor's transitive query and the downgrade re-derivation walk (PLAN §7).

A claim rests on premises through `justified_by` lineage edges, child = the dependent claim
statement, parent = the premise claim statement. No claim, of any class, may carry such an edge at
any depth to a strictly weaker premise: a PROVEN claim over a CONJECTURE three hops down is the
lattice violation fixture (h) plants. On a node's downgrade every claim transitively justified by
it re-derives through justify, in premise-first order, each capped at its weakest premise's class
with that premise's evidence pointer; a move without an evidence pointer is refused by the
tag_history discipline. One walk serves the yank path, the divergence path and the auditor.
"""

from collections import deque
from dataclasses import dataclass

from cairn import claims, log
from cairn.substrate import SubstrateError

lg = log.get("foundations")

EDGE = "justified_by"
CLASSES = claims.TAGS
SPECULATION, CONJECTURE, STRONG_EMPIRICAL, PROVEN = CLASSES


class FoundationsError(SubstrateError):
    pass


def rank(tag):
    return CLASSES.index(SPECULATION if tag is None else tag)


@dataclass(frozen=True)
class Violation:
    path: tuple
    dependent_tag: str
    premise_tag: str

    @property
    def dependent(self):
        return self.path[-2]

    @property
    def premise(self):
        return self.path[-1]

    @property
    def depth(self):
        return len(self.path) - 1


def premises_of(sub, claim_hash):
    rows = sub.conn.execute(
        "SELECT parent_hash FROM lineage WHERE child_hash = ? AND edge_kind = ? ORDER BY parent_hash",
        (claim_hash, EDGE),
    ).fetchall()
    return [r["parent_hash"] for r in rows]


def dependents_of(sub, claim_hash):
    rows = sub.conn.execute(
        "SELECT child_hash FROM lineage WHERE parent_hash = ? AND edge_kind = ? ORDER BY child_hash",
        (claim_hash, EDGE),
    ).fetchall()
    return [r["child_hash"] for r in rows]


def edges(sub):
    rows = sub.conn.execute("SELECT child_hash, parent_hash FROM lineage WHERE edge_kind = ?", (EDGE,)).fetchall()
    return [(r["child_hash"], r["parent_hash"]) for r in rows]


def current_tag(sub, claim_hash):
    history = claims.tag_history_for(sub, claim_hash)
    return history[-1]["to_tag"] if history else None


def current_evidence(sub, claim_hash):
    """The evidence pointer behind a claim's current tag: the latest history row carrying one."""
    for row in reversed(claims.tag_history_for(sub, claim_hash)):
        if row["evidence_hash"]:
            return row["evidence_hash"]
    return None


def reaches(edge_map, start, target):
    seen = {start}
    stack = [start]
    while stack:
        node = stack.pop()
        if node == target:
            return True
        for parent in edge_map.get(node, ()):
            if parent not in seen:
                seen.add(parent)
                stack.append(parent)
    return False


def add_premise(sub, claim_hash, premise_hash):
    if claim_hash == premise_hash:
        raise FoundationsError(f"claim {claim_hash} cannot rest on itself")
    if claims.get_claim_statement(sub, claim_hash) is None:
        raise claims.UnknownStatement(f"no claim statement {claim_hash}")
    if claims.get_claim_statement(sub, premise_hash) is None:
        raise claims.UnknownStatement(f"no claim statement {premise_hash}")
    edge_map = _edge_map(edges(sub))
    if reaches(edge_map, premise_hash, claim_hash):
        raise FoundationsError(f"premise {premise_hash} already rests on {claim_hash}; the edge would close a cycle")
    sub.add_lineage(claim_hash, premise_hash, EDGE)
    lg.info("premise", claim=claim_hash, premise=premise_hash)


def _edge_map(edge_list):
    edge_map = {}
    for child, parent in edge_list:
        edge_map.setdefault(child, []).append(parent)
    return edge_map


def paths_in(edge_map, root):
    """Every simple path from the root down its premises, breadth first, parents in sorted order."""
    found = []
    queue: deque[tuple] = deque([(root,)])
    while queue:
        path = queue.popleft()
        for parent in sorted(edge_map.get(path[-1], ())):
            if parent in path:
                continue
            extended = (*path, parent)
            found.append(extended)
            queue.append(extended)
    return found


def violations_in(edge_list, tags, root):
    """Every edge on a path from the root whose premise ranks strictly below its dependent."""
    edge_map = _edge_map(edge_list)
    found = []
    for path in paths_in(edge_map, root):
        dependent_tag = tags.get(path[-2])
        premise_tag = tags.get(path[-1])
        if rank(premise_tag) < rank(dependent_tag):
            found.append(Violation(path, dependent_tag or SPECULATION, premise_tag or SPECULATION))
    return found


def closure(sub, claim_hash):
    return paths_in(_edge_map(edges(sub)), claim_hash)


def violations(sub, claim_hash):
    edge_list = edges(sub)
    nodes = {claim_hash, *(n for edge in edge_list for n in edge)}
    tags = {node: current_tag(sub, node) for node in nodes}
    return violations_in(edge_list, tags, claim_hash)


def ceiling_for(sub, claim_hash):
    """The weakest direct premise's tag and the evidence pointer behind it; None with no premises."""
    weakest = None
    for premise in premises_of(sub, claim_hash):
        tag = current_tag(sub, premise) or SPECULATION
        if weakest is None or rank(tag) < rank(weakest[0]):
            weakest = (tag, current_evidence(sub, premise), premise)
    return weakest


def dependents_in_order(sub, claim_hash):
    """Every claim transitively resting on the given one, breadth first from it, each once.

    Each dependent is reached through a direct premise visited before it, and ceiling_for takes
    the weakest direct premise, so one pass leaves no dependent above the downgraded node's tag.
    """
    edge_map = {}
    for child, parent in edges(sub):
        edge_map.setdefault(parent, []).append(child)
    order = []
    seen = set()
    queue = deque(sorted(edge_map.get(claim_hash, ())))
    while queue:
        node = queue.popleft()
        if node in seen:
            continue
        seen.add(node)
        order.append(node)
        queue.extend(sorted(edge_map.get(node, ())))
    return order


def rederive(sub, claim_hash, attest_path, *, actor=None):
    from cairn import justify

    derivations = [
        justify.derive_tag(sub, dependent, attest_path, actor=actor or justify.ACTOR)
        for dependent in dependents_in_order(sub, claim_hash)
    ]
    lg.info("rederive", claim=claim_hash, dependents=[d.statement_hash for d in derivations])
    return tuple(derivations)


def rederive_for_attempts(sub, attempt_ids, attest_path):
    from cairn import justify

    if not attempt_ids:
        return ()
    marks = ",".join("?" for _ in attempt_ids)
    rows = sub.conn.execute(
        f"SELECT DISTINCT target_statement_hash FROM evidence_nodes WHERE attempt_id IN ({marks}) ORDER BY target_statement_hash",
        tuple(attempt_ids),
    ).fetchall()
    rederived = []
    for row in rows:
        statement = row["target_statement_hash"]
        justify.derive_tag(sub, statement, attest_path)
        rederived.append(statement)
        rederived.extend(d.statement_hash for d in rederive(sub, statement, attest_path))
    return tuple(rederived)
