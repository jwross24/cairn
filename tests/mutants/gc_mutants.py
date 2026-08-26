from contextlib import contextmanager

from cairn import gc


@contextmanager
def _swap(owner, name, replacement):
    original = getattr(owner, name)
    setattr(owner, name, replacement)
    try:
        yield
    finally:
        setattr(owner, name, original)


@contextmanager
def reachable_from_last_root_only():
    real = gc.reachable

    def broken(roots, edges):
        roots = set(roots)
        if not roots:
            return real(roots, edges)
        return real({max(roots)}, edges)

    with _swap(gc, "reachable", broken):
        yield


@contextmanager
def reachable_cached_by_roots_only():
    real = gc.reachable
    cache = {}

    def cached(roots, edges):
        key = frozenset(roots)
        if key not in cache:
            cache[key] = real(roots, edges)
        return cache[key]

    with _swap(gc, "reachable", cached):
        yield


@contextmanager
def reachable_directed_child_to_parent():
    def broken(roots, edges):
        adjacency = {}
        for child, parent, _kind in edges:
            adjacency.setdefault(child, set()).add(parent)
        seen = set(roots)
        stack = list(seen)
        while stack:
            node = stack.pop()
            for neighbor in adjacency.get(node, ()):
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        return seen

    with _swap(gc, "reachable", broken):
        yield


@contextmanager
def collectable_includes_rooted_blob():
    def broken(roots, edges, blobs):
        return set(blobs) - set(roots)

    with _swap(gc, "collectable", broken):
        yield


@contextmanager
def collect_one_page_only():
    def broken(sub, hashes):
        page = hashes[: gc.PAGE_SIZE]
        if not page:
            return 0
        marks = ", ".join("?" for _ in page)
        cur = sub.conn.execute(f"DELETE FROM blobs WHERE hash IN ({marks})", page)
        return cur.rowcount

    with _swap(gc, "_delete_blobs", broken):
        yield


ALL = {
    "reachable_from_last_root_only": reachable_from_last_root_only,
    "reachable_cached_by_roots_only": reachable_cached_by_roots_only,
    "reachable_directed_child_to_parent": reachable_directed_child_to_parent,
    "collectable_includes_rooted_blob": collectable_includes_rooted_blob,
    "collect_one_page_only": collect_one_page_only,
}
