import json
from contextlib import contextmanager

from cairn import runner


@contextmanager
def _swap(owner, name, replacement):
    original = getattr(owner, name)
    setattr(owner, name, replacement)
    try:
        yield
    finally:
        setattr(owner, name, original)


@contextmanager
def parser_json_loads_bare():
    def parse(stdout_bytes):
        document = json.loads(stdout_bytes)
        return runner.ParsedOutput.of(document, document.get("status"))

    with _swap(runner, "parse_skill_output", parse):
        yield


@contextmanager
def status_default_ok():
    real = runner.parse_skill_output

    def parse(stdout_bytes):
        parsed = real(stdout_bytes)
        if not parsed.well_formed and "status must be one of" in (parsed.reason or ""):
            return runner.ParsedOutput.of({}, runner.STATUS_OK)
        return parsed

    with _swap(runner, "parse_skill_output", parse):
        yield


@contextmanager
def receipt_trusted():
    with _swap(runner, "HARNESS_ONLY_KEYS", ()):
        yield


ALL = {
    "parser_json_loads_bare": parser_json_loads_bare,
    "status_default_ok": status_default_ok,
    "receipt_trusted": receipt_trusted,
}
