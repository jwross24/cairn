import argparse
import json
import os
import sqlite3
import stat
from pathlib import Path

from cairn import canon, claims, cli, exits, keys, lean, log, verifier
from cairn.canon import STR, List
from cairn.errors import CliError
from cairn.substrate import blob_hash

lg = log.get("bundle")

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SRC = "bundle/"
SCRIPT_KIND = "verifier_script"
PIN_MISMATCH_REASON = "bundle-hash-ne-pin"
SCHEMA = """
CREATE TABLE IF NOT EXISTS objects (
    kind TEXT PRIMARY KEY,
    canonical BLOB NOT NULL
);
"""


class BundleError(Exception):
    pass


class BundlePinMismatch(BundleError):
    def __init__(self, bundle_hash, pin_hash, path, pin_path):
        super().__init__(f"gate bundle {bundle_hash} does not match the pin {pin_hash}")
        self.bundle_hash = bundle_hash
        self.pin_hash = pin_hash
        self.path = str(path)
        self.pin_path = str(pin_path)


class _Json(canon.Type):
    def encode(self, value):
        if value is None:
            return canon.TAG_NONE
        if isinstance(value, bool):
            return canon.BOOL.encode(value)
        if isinstance(value, int):
            return canon.INT.encode(value)
        if isinstance(value, str):
            return canon.STR.encode(value)
        if isinstance(value, (list, tuple)):
            parts = [self.encode(v) for v in value]
            return canon.TAG_LIST + canon.u64le(len(parts)) + b"".join(parts)
        if isinstance(value, dict):
            pairs = sorted((canon.STR.encode(k), self.encode(v)) for k, v in value.items())
            if len({k for k, _ in pairs}) != len(pairs):
                raise canon.CanonError("duplicate key in bundle object after canonicalization")
            return canon.TAG_MAP + canon.u64le(len(pairs)) + b"".join(k + v for k, v in pairs)
        raise canon.CanonError(f"bundle objects admit no {type(value).__name__}")


JSON = _Json()
PAIRS = List(List(STR))


def canonical_bytes(kind, value):
    if kind == SCRIPT_KIND:
        return bytes(value)
    return canon.encode(JSON, value)


def source_objects(src_dir):
    src = Path(src_dir)
    if not src.is_dir():
        raise BundleError(f"bundle source directory {src} does not exist")
    objects = {}
    for path in sorted(src.glob("*.json")):
        objects[path.stem] = json.loads(path.read_text())
    if not objects:
        raise BundleError(f"bundle source directory {src} holds no *.json object")
    objects[SCRIPT_KIND] = verifier.script_bytes()
    if not lean.MANIFEST_PATH.is_file():
        raise BundleError(
            f"lake manifest {lean.MANIFEST_PATH} does not exist; `lake update` in {lean.PROJECT_DIR} writes it"
        )
    objects[lean.MANIFEST_KIND] = lean.manifest_object()
    return objects


def rows_for(objects):
    return [_row(kind, canonical_bytes(kind, objects[kind])) for kind in sorted(objects)]


def _row(kind, canonical):
    return (kind, canonical, blob_hash(canonical))


def bundle_hash(rows):
    pairs = sorted((kind, digest) for kind, _, digest in rows)
    return canon.digest(keys.TAG_GATE_BUNDLE, canon.encode(PAIRS, [[k, h] for k, h in pairs]))


def build(src_dir, out_path):
    rows = rows_for(source_objects(src_dir))
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.chmod(0o644)
        out.unlink()
    conn = sqlite3.connect(str(out))
    try:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT INTO objects (kind, canonical) VALUES (?, ?)", [(kind, canonical) for kind, canonical, _ in rows]
        )
        conn.commit()
    finally:
        conn.close()
    out.chmod(0o444)
    digest = bundle_hash(rows)
    lg.info("build", path=str(out), objects=len(rows), bundle_hash=digest)
    return digest


def read_rows(path):
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [
            _row(r["kind"], bytes(r["canonical"]))
            for r in conn.execute("SELECT kind, canonical FROM objects ORDER BY kind")
        ]
    finally:
        conn.close()


def write_pin(bundle_path, pin_path):
    rows = read_rows(bundle_path)
    digest = bundle_hash(rows)
    pin = Path(pin_path)
    pin.parent.mkdir(parents=True, exist_ok=True)
    if pin.exists():
        pin.chmod(0o644)
    pin.write_text(digest + "\n")
    pin.chmod(0o444)
    Path(bundle_path).chmod(0o444)
    _set_append_only(pin)
    lg.info("pin", bundle=str(bundle_path), pin=str(pin), bundle_hash=digest)
    return digest


def _set_append_only(path):
    if not hasattr(os, "chflags"):
        lg.warning("append_only_unavailable", path=str(path), platform=os.name, effect="the pin carries mode bits only")
        return False
    os.chflags(path, stat.UF_APPEND)
    return True


def read_pin(pin_path):
    return Path(pin_path).read_text().strip()


class GateBundle:
    def __init__(self, path, pin_path, rows, digest, pin_hash):
        self.path = str(path)
        self.pin_path = str(pin_path)
        self.rows = rows
        self.hash = digest
        self.pin_hash = pin_hash
        self._decoded = {}

    @classmethod
    def open(cls, path, pin_path):
        rows = read_rows(path)
        digest = bundle_hash(rows)
        pin_hash = read_pin(pin_path)
        lg.info(
            "open",
            path=str(path),
            pin=str(pin_path),
            bundle_hash=digest,
            pin_hash=pin_hash,
            pin_match=digest == pin_hash,
        )
        if digest != pin_hash:
            raise BundlePinMismatch(digest, pin_hash, path, pin_path)
        return cls(path, pin_path, rows, digest, pin_hash)

    def raw(self, kind):
        for name, canonical, _ in self.rows:
            if name == kind:
                return canonical
        raise BundleError(f"gate bundle {self.hash} carries no {kind!r} object")

    def digest_of(self, kind):
        for name, _, digest in self.rows:
            if name == kind:
                return digest
        raise BundleError(f"gate bundle {self.hash} carries no {kind!r} object")

    def object(self, kind):
        if kind not in self._decoded:
            self._decoded[kind] = _decode(self.raw(kind))
        return self._decoded[kind]

    @property
    def verifier_script(self):
        return self.raw(SCRIPT_KIND)

    @property
    def tiers(self):
        return self.object("tiers")

    @property
    def gate_plan(self):
        return self.object("gate_plan")

    @property
    def waivable_checks(self):
        return self.object("waivable_checks")

    @property
    def ladder_plan(self):
        return self.object("ladder_plan")

    @property
    def lean(self):
        return self.object("lean")

    @property
    def lake_manifest(self):
        return self.object(lean.MANIFEST_KIND)

    def verifier_config(self):
        return verifier.VerifierConfig.from_bundle(self.object("verifier"), self.verifier_script, self.hash)

    def waiver_hypothesis(self):
        plan = self.gate_plan
        fixtures = plan.get("fixtures") if isinstance(plan, dict) else None
        hypothesis = fixtures.get("waiver_hypothesis") if isinstance(fixtures, dict) else None
        if not isinstance(hypothesis, dict):
            raise BundleError(f"gate bundle {self.hash} carries no gate_plan.fixtures.waiver_hypothesis")
        return hypothesis

    def waiver_target(self):
        return keys.hypothesis_key(self.waiver_hypothesis())


def _decode(canonical):
    value, rest = _decode_at(canonical, 0)
    if rest != len(canonical):
        raise canon.CanonError("trailing bytes in a bundle object")
    return value


def _decode_at(data, i):
    tag = data[i : i + 1]
    if tag == canon.TAG_NONE:
        return None, i + 1
    if tag == canon.TAG_BOOL:
        return data[i + 1] == 1, i + 2
    if tag == canon.TAG_INT:
        sign = data[i + 1]
        length = int.from_bytes(data[i + 2 : i + 10], "little")
        body = data[i + 10 : i + 10 + length]
        value = int.from_bytes(body, "big") if body else 0
        return (-value if sign else value), i + 10 + length
    if tag == canon.TAG_STR:
        length = int.from_bytes(data[i + 1 : i + 9], "little")
        return data[i + 9 : i + 9 + length].decode("utf-8"), i + 9 + length
    if tag == canon.TAG_LIST:
        count = int.from_bytes(data[i + 1 : i + 9], "little")
        i += 9
        out = []
        for _ in range(count):
            value, i = _decode_at(data, i)
            out.append(value)
        return out, i
    if tag == canon.TAG_MAP:
        count = int.from_bytes(data[i + 1 : i + 9], "little")
        i += 9
        out = {}
        for _ in range(count):
            key, i = _decode_at(data, i)
            value, i = _decode_at(data, i)
            out[key] = value
        return out, i
    raise canon.CanonError(f"unknown canonical tag {tag!r} in a bundle object")


def record_open_refusal(sub, mismatch):
    run = claims.GateRun(
        gate="bundle_open",
        bundle_hash=mismatch.bundle_hash,
        pin_hash=mismatch.pin_hash,
        result="refused",
        reasons=(PIN_MISMATCH_REASON,),
        at=cli.now_iso(),
    )
    claims.write_gate_run(sub, run)
    lg.info(
        "open_refused",
        path=mismatch.path,
        pin=mismatch.pin_path,
        bundle_hash=mismatch.bundle_hash,
        pin_hash=mismatch.pin_hash,
        run_id=run.hash,
    )
    return run.hash


def open_for_gate(sub, path, pin_path):
    try:
        return GateBundle.open(path, pin_path)
    except BundlePinMismatch as mismatch:
        record_open_refusal(sub, mismatch)
        raise


def repin_sequence(bundle_path, pin_path, src=DEFAULT_SRC):
    return f"chflags nouappnd {pin_path} && cairn bundle build --src {src} --bundle {bundle_path} --force && cairn bundle pin --bundle {bundle_path} --pin {pin_path} --force"


def open_or_refuse(ns, *, command):
    for path, what in ((ns.bundle, "gate bundle"), (ns.pin, "gate-bundle pin")):
        if not Path(path).exists():
            raise CliError(
                exits.ENVIRONMENT,
                f"the {what} {path} does not exist",
                where=str(path),
                next_command=repin_sequence(ns.bundle, ns.pin),
            )
    try:
        return GateBundle.open(ns.bundle, ns.pin)
    except BundlePinMismatch as mismatch:
        raise CliError(
            exits.GATE_REFUSED,
            f"gate bundle hash {mismatch.bundle_hash} differs from the pin {mismatch.pin_hash}; {command} fails closed",
            where=mismatch.pin_path,
            next_command=repin_sequence(ns.bundle, ns.pin),
        ) from None


def sub_parent():
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--force",
        dest="force",
        action="store_true",
        default=argparse.SUPPRESS,
        help="required for the irreversible part of this command",
    )
    parent.add_argument(
        "--json",
        "--robot",
        dest="json",
        action="store_true",
        default=argparse.SUPPRESS,
        help="emit exactly one JSON document on stdout",
    )
    return parent


def _configure(parser):
    subs = parser.add_subparsers(dest="sub", metavar="SUBCOMMAND", required=True)
    parents = [cli.globals_parent(suppress=True), sub_parent()]
    build_parser = subs.add_parser(
        "build", parents=parents, help="compile bundle/*.json plus the verifier script into the gate bundle"
    )
    build_parser.add_argument("--src", default=DEFAULT_SRC, metavar="DIR", help="directory of bundle source objects")
    subs.add_parser("pin", parents=parents, help="record the gate bundle's hash in the operator-owned pin file")
    subs.add_parser("show", parents=parents, help="print the bundle hash, the pin hash and every (kind, hash) row")


def _run(ns):
    return {"build": _run_build, "pin": _run_pin, "show": _run_show}[ns.sub](ns)


def _run_build(ns):
    force = getattr(ns, "force", False)
    cli.refuse_overwrite(ns.bundle, flag="--force", command="cairn bundle build", force=force)
    try:
        digest = build(ns.src, ns.bundle)
    except BundleError as exc:
        raise CliError(
            exits.ENVIRONMENT, str(exc), where=str(ns.src), next_command="cairn bundle build --src bundle/"
        ) from None
    if getattr(ns, "json", False):
        cli.emit_json("bundle", {"sub": "build", "bundle": str(ns.bundle), "src": str(ns.src), "bundle_hash": digest})
    else:
        print(digest)
    return exits.OK


def _run_pin(ns):
    force = getattr(ns, "force", False)
    if not Path(ns.bundle).exists():
        raise CliError(
            exits.ENVIRONMENT,
            f"the gate bundle {ns.bundle} does not exist",
            where=str(ns.bundle),
            next_command=f"cairn bundle build --src {DEFAULT_SRC} --bundle {ns.bundle}",
        )
    cli.refuse_overwrite(ns.pin, flag="--force", command="cairn bundle pin", force=force)
    try:
        digest = write_pin(ns.bundle, ns.pin)
    except PermissionError as exc:
        raise CliError(
            exits.ENVIRONMENT,
            f"the pin {ns.pin} refused the write ({exc.strerror}); clearing its append-only flag is the operator's act",
            where=str(ns.pin),
            next_command=repin_sequence(ns.bundle, ns.pin),
        ) from None
    if getattr(ns, "json", False):
        cli.emit_json("bundle", {"sub": "pin", "bundle": str(ns.bundle), "pin": str(ns.pin), "bundle_hash": digest})
    else:
        print(digest)
    return exits.OK


def _run_show(ns):
    missing = [p for p in (ns.bundle, ns.pin) if not Path(p).exists()]
    if missing:
        raise CliError(
            exits.ENVIRONMENT,
            f"missing gate artifact(s): {', '.join(str(m) for m in missing)}",
            where=str(missing[0]),
            next_command=repin_sequence(ns.bundle, ns.pin),
        )
    rows = read_rows(ns.bundle)
    digest = bundle_hash(rows)
    pin_hash = read_pin(ns.pin)
    match = digest == pin_hash
    payload = {
        "sub": "show",
        "bundle": str(ns.bundle),
        "pin": str(ns.pin),
        "bundle_hash": digest,
        "pin_hash": pin_hash,
        "pin_match": match,
        "objects": [{"kind": kind, "hash": h} for kind, _, h in rows],
    }
    if getattr(ns, "json", False):
        cli.emit_json("bundle", payload)
    else:
        print(f"bundle_hash {digest}")
        print(f"pin_hash    {pin_hash}")
        print(f"pin_match   {str(match).lower()}")
        for kind, _, h in rows:
            print(f"  {kind:<18} {h}")
    if not match:
        raise CliError(
            exits.GATE_REFUSED,
            f"gate bundle hash {digest} differs from the pin {pin_hash}; every gate fails closed until they agree",
            where=str(ns.pin),
            next_command=repin_sequence(ns.bundle, ns.pin),
        )
    return exits.OK


cli.register(
    "bundle",
    _configure,
    _run,
    summary="compile, pin and inspect the content-addressed gate bundle",
    read_only=False,
    json=True,
    dangerous=True,
    gating="--force",
    dry_run_default=True,
)
