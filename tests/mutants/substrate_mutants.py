from contextlib import contextmanager

from cairn import substrate


@contextmanager
def _swap(owner, name, replacement):
    original = getattr(owner, name)
    setattr(owner, name, replacement)
    try:
        yield
    finally:
        setattr(owner, name, original)


@contextmanager
def serve_ignores_disowned():
    with _swap(substrate, "SERVE_SQL", substrate.serve_sql(exclude_disowned=False)):
        yield


@contextmanager
def serve_ignores_missing_blob():
    with _swap(substrate, "SERVE_SQL", substrate.serve_sql(require_blobs=False)):
        yield


ALL = {
    "serve_ignores_disowned": serve_ignores_disowned,
    "serve_ignores_missing_blob": serve_ignores_missing_blob,
}
