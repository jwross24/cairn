"""The ladder-tested method's allow-list: a gate-bundle template, instantiated per dispatch.

The template names what a method under test may reach — the gate-owned counted object, the
uncounted backends its hypothesis object declares, the gate-owned scratch path, and nothing
else. The instantiation binds those names to this host's resolved paths and is the object bead
cairn-m1-cqt.1.3 writes into the ladder dispatch record, so which allow-list a rung ran under is
a ledger fact.

Enforcement is pre-execution and independent of the method: research/grounding/
method-allowlist-macos-sandbox.md measures what the arm confines. Naming a violated clause reads
the child's stderr and is cooperative, so a method that swallows EPERM is confined and unnamed.

`check_instantiation` is what a reader holding only the record can settle: the record against the
bundle template. It cannot see which host paths the launch was entitled to, so `check_binding`
re-derives the allow-list from the gate-owned launch inputs and requires equality; a gate admitting
a launch calls that one.
"""

import os
import re
import sys
from dataclasses import asdict, dataclass
from dataclasses import fields as fields_of
from pathlib import Path
from typing import NoReturn

from cairn import bundle, log
from cairn.bundle import BundleError
from cairn.substrate import blob_hash, node_hash_for

lg = log.get("allowlist")

BUNDLE_KIND = "allow_lists"
RECORD_KIND = "method_allow_list"
LADDER_METHOD = "ladder_method"
SANDBOX_EXEC = "/usr/bin/sandbox-exec"
MECHANISM_SANDBOX_EXEC = "sandbox-exec"
ARMS = {MECHANISM_SANDBOX_EXEC: (("darwin",), SANDBOX_EXEC)}
MECHANISMS = tuple(sorted(ARMS))
DECLARATION_KEY = "uncounted_backends"
SCRATCH_ROOT = "scratch"
SPAWN_POLICY = "declared_backends_only"
TEMPLATE_FIELDS = frozenset(
    {
        "counted_object_slot",
        "backend_catalog",
        "network_egress",
        "process_spawn",
        "writable_roots",
        "readable_roots",
        "mechanisms",
    }
)
CATALOG_FIELDS = frozenset({"counted", "kind"})
BACKEND_KINDS = ("in_process", "process")
BACKEND_NAME = re.compile(r"\A[a-z][a-z0-9_]*\Z")
PROFILE = """(version 1)
(deny default)
(allow process-fork)
(allow process-exec {execs})
(allow sysctl-read)
(allow mach-lookup)
(allow file-read* (subpath "/"))
(allow file-write* (subpath (param "SCRATCH")))
"""
DENIED = re.compile(rb"Operation not permitted")
QUOTED = re.compile(rb"'([^'\n]*)'")
EXEC_MARKERS = (b"_execute_child", b"execvp(", b"Failed to exec")
UNCLASSIFIED = "denied_unclassified"


class AllowListError(BundleError):
    pass


class AllowListRefused(AllowListError):
    pass


def _refuse(message) -> NoReturn:
    raise AllowListRefused(message)


def _catalog(entries):
    if not isinstance(entries, dict) or not entries:
        _refuse("backend_catalog must be a nonempty mapping")
    for name, entry in sorted(entries.items()):
        if not isinstance(name, str) or not BACKEND_NAME.match(name):
            _refuse(f"backend name {name!r} is outside [a-z][a-z0-9_]*")
        if not isinstance(entry, dict) or set(entry) != CATALOG_FIELDS:
            _refuse(f"backend {name!r} must carry exactly {sorted(CATALOG_FIELDS)}")
        if type(entry["counted"]) is not bool:
            _refuse(f"backend {name!r} counted must be a boolean")
        if entry["kind"] not in BACKEND_KINDS:
            _refuse(f"backend {name!r} kind must be one of {BACKEND_KINDS}")
    return entries


def template(gate_bundle, name=LADDER_METHOD):
    obj = gate_bundle.object(BUNDLE_KIND)
    if not isinstance(obj, dict) or set(obj) != {"version", "templates", "provenance"}:
        _refuse(f"the {BUNDLE_KIND} object must carry version, templates and provenance")
    if obj["version"] != 1:
        _refuse(f"the {BUNDLE_KIND} object is version {obj['version']!r}, not 1")
    templates = obj["templates"]
    if not isinstance(templates, dict) or name not in templates:
        _refuse(f"gate bundle {gate_bundle.hash} carries no {BUNDLE_KIND} template {name!r}")
    entry = templates[name]
    if not isinstance(entry, dict) or set(entry) != TEMPLATE_FIELDS:
        _refuse(f"template {name!r} must carry exactly {sorted(TEMPLATE_FIELDS)}")
    catalog = _catalog(entry["backend_catalog"])
    slot = entry["counted_object_slot"]
    counted = sorted(k for k, v in catalog.items() if v["counted"])
    if counted != [slot]:
        _refuse(f"template {name!r} must count exactly its counted_object_slot {slot!r}, counts {counted}")
    if catalog[slot]["kind"] != "process":
        _refuse(f"the counted object {slot!r} must be a process backend")
    if entry["network_egress"] is not False:
        _refuse(f"template {name!r} permits network egress")
    if entry["process_spawn"] != SPAWN_POLICY:
        _refuse(f"template {name!r} must set process_spawn to {SPAWN_POLICY!r}")
    if entry["writable_roots"] != [SCRATCH_ROOT]:
        _refuse(f"template {name!r} must make {SCRATCH_ROOT!r} the only writable root")
    if entry["readable_roots"] != ["any"]:
        _refuse(f"template {name!r} must state its readable roots as ['any']")
    mechanisms = entry["mechanisms"]
    if not isinstance(mechanisms, list) or not mechanisms or any(m not in MECHANISMS for m in mechanisms):
        _refuse(f"template {name!r} names a mechanism outside {MECHANISMS}")
    if sorted(set(mechanisms)) != sorted(mechanisms):
        _refuse(f"template {name!r} repeats a mechanism")
    return entry


def declared_backends(hypothesis, entry):
    claimed = hypothesis.get("claimed") if isinstance(hypothesis, dict) else None
    if not isinstance(claimed, dict):
        _refuse("the hypothesis object carries no claimed map")
    if DECLARATION_KEY not in claimed:
        return ()
    raw = claimed[DECLARATION_KEY]
    if not isinstance(raw, str) or not raw:
        _refuse(f"{DECLARATION_KEY} must be a nonempty string")
    names = raw.split(",")
    if any(not BACKEND_NAME.match(n) for n in names):
        _refuse(f"{DECLARATION_KEY} {raw!r} is not a comma-separated list of backend names")
    if names != sorted(set(names)) or len(names) != len(set(names)):
        _refuse(f"{DECLARATION_KEY} {raw!r} must be strictly sorted with no repeat")
    catalog = entry["backend_catalog"]
    for name in names:
        if name not in catalog:
            _refuse(f"backend {name!r} is outside the template catalog")
        if catalog[name]["counted"]:
            _refuse(f"backend {name!r} is the counted object and is not declarable as uncounted")
    return tuple(names)


def _resolved(label, path):
    text = os.path.realpath(str(path))
    if any(ch in text for ch in ('"', "\\", "\n")):
        _refuse(f"{label} path {text!r} cannot be named in a sandbox profile literal")
    return text


def within(path, root):
    return path == root or path.startswith(root + os.sep)


def _executable(label, path):
    text = _resolved(label, path)
    if not Path(text).is_file() or not os.access(text, os.X_OK):
        _refuse(f"{label} {text!r} is not an executable file")
    return text


def mechanism_for(entry, platform=None):
    plat = sys.platform if platform is None else platform
    for name in entry["mechanisms"]:
        platforms, binary = ARMS[name]
        if plat in platforms and os.access(binary, os.X_OK):
            return name
    _refuse(f"no allow-list enforcement mechanism among {tuple(entry['mechanisms'])} is available on {plat!r}")


@dataclass(frozen=True)
class AllowList:
    template_name: str
    template_hash: str
    bundle_hash: str
    mechanism: str
    counted_object: str
    declared_backends: tuple[str, ...]
    exec_paths: tuple[str, ...]
    network_egress: bool
    writable_root: str
    profile_hash: str

    def as_dict(self):
        return asdict(self)

    @property
    def hash(self):
        return node_hash_for(RECORD_KIND, bundle.canonical_bytes(RECORD_KIND, self.as_dict()))


def profile_bytes(exec_paths):
    execs = " ".join(f'(literal "{path}")' for path in exec_paths)
    return PROFILE.format(execs=execs).encode()


def instantiate(gate_bundle, *, hypothesis, counted_object, scratch_dir, backend_paths=None, name=LADDER_METHOD):
    entry = template(gate_bundle, name)
    mechanism = mechanism_for(entry)
    declared = declared_backends(hypothesis, entry)
    catalog = entry["backend_catalog"]
    supplied = dict(backend_paths or {})
    wanted = {n for n in declared if catalog[n]["kind"] == "process"}
    if set(supplied) != wanted:
        _refuse(f"backend paths {sorted(supplied)} do not match the declared process backends {sorted(wanted)}")
    counted = _executable("counted object", counted_object)
    execs = {counted, *(_executable(f"backend {n}", supplied[n]) for n in sorted(wanted))}
    writable_root = _resolved("scratch", scratch_dir)
    if not Path(writable_root).is_dir():
        _refuse(f"scratch {writable_root!r} is not a directory")
    exec_paths = tuple(sorted(execs))
    value = AllowList(
        template_name=name,
        template_hash=blob_hash(gate_bundle.raw(BUNDLE_KIND)),
        bundle_hash=gate_bundle.hash,
        mechanism=mechanism,
        counted_object=counted,
        declared_backends=declared,
        exec_paths=exec_paths,
        network_egress=entry["network_egress"],
        writable_root=writable_root,
        profile_hash=blob_hash(profile_bytes(exec_paths)),
    )
    lg.info(
        "instantiate",
        bundle_hash=gate_bundle.hash,
        template=name,
        mechanism=mechanism,
        declared=list(declared),
        exec_paths=list(exec_paths),
        allow_list_hash=value.hash,
    )
    return value


def check_instantiation(value, gate_bundle, name=LADDER_METHOD):
    entry = template(gate_bundle, name)
    catalog = entry["backend_catalog"]
    if value.template_name != name:
        _refuse(f"allow-list names template {value.template_name!r}, not {name!r}")
    if value.template_hash != blob_hash(gate_bundle.raw(BUNDLE_KIND)):
        _refuse("allow-list template hash differs from the bundle template it names")
    if value.bundle_hash != gate_bundle.hash:
        _refuse("allow-list bundle hash differs from the gate bundle")
    if value.network_egress != entry["network_egress"]:
        _refuse("allow-list network egress differs from the template")
    if value.mechanism not in entry["mechanisms"]:
        _refuse(f"allow-list mechanism {value.mechanism!r} is outside the template")
    if any(n not in catalog or catalog[n]["counted"] for n in value.declared_backends):
        _refuse("allow-list declares a backend the template catalog does not offer as uncounted")
    if value.profile_hash != blob_hash(profile_bytes(value.exec_paths)):
        _refuse("allow-list profile hash does not address its own exec paths")
    permitted = 1 + sum(1 for n in value.declared_backends if catalog[n]["kind"] == "process")
    if len(value.exec_paths) > permitted or value.counted_object not in value.exec_paths:
        _refuse(f"allow-list permits {len(value.exec_paths)} executables against {permitted} the template allows")
    for label, path in (("counted object", value.counted_object), ("scratch", value.writable_root)):
        if path != os.path.realpath(path):
            _refuse(f"{label} path {path!r} is unresolved")
    if value.writable_root == os.sep or Path(value.writable_root).parent == Path(value.writable_root):
        _refuse(f"allow-list makes the filesystem root {value.writable_root!r} writable")
    for path in value.exec_paths:
        if within(path, value.writable_root):
            _refuse(f"allow-list makes its own executable {path!r} writable")
    return True


def check_binding(
    value, gate_bundle, *, hypothesis, counted_object, scratch_dir, backend_paths=None, name=LADDER_METHOD
):
    check_instantiation(value, gate_bundle, name)
    expected = instantiate(
        gate_bundle,
        hypothesis=hypothesis,
        counted_object=counted_object,
        scratch_dir=scratch_dir,
        backend_paths=backend_paths,
        name=name,
    )
    if value != expected:
        differing = sorted(k for k, v in expected.as_dict().items() if value.as_dict()[k] != v)
        _refuse(f"allow-list differs from the one the gate derives for this launch: {differing}")
    return True


def write_profile(value, path):
    data = profile_bytes(value.exec_paths)
    if blob_hash(data) != value.profile_hash:
        _refuse("the rendered profile does not match the allow-list profile hash")
    path.write_bytes(data)
    path.chmod(0o444)
    return path


def argv_for(value, profile_path, argv):
    if value.mechanism != MECHANISM_SANDBOX_EXEC:
        _refuse(f"no argv form for mechanism {value.mechanism!r}")
    if not argv or _resolved("argv0", argv[0]) not in value.exec_paths:
        _refuse(f"argv0 {argv[0]!r} is outside the allow-list exec paths")
    return [SANDBOX_EXEC, "-D", f"SCRATCH={value.writable_root}", "-f", str(profile_path), *argv]


def detect_violation(exit_status, stderr_bytes, value):
    text = bytes(stderr_bytes)
    if exit_status == 0 or not DENIED.search(text):
        return None
    if any(marker in text for marker in EXEC_MARKERS):
        return "undeclared_exec"
    paths = [os.path.realpath(os.fsdecode(p)) for p in QUOTED.findall(text) if p.startswith(b"/")]
    if any(not within(p, value.writable_root) for p in paths):
        return "outside_write"
    return UNCLASSIFIED if paths else "network_egress"


def record(sub, value):
    digest = sub.put_node(RECORD_KIND, bundle.canonical_bytes(RECORD_KIND, value.as_dict()), replay_grade="AuditOnly")
    lg.info("record", allow_list_hash=digest, declared=list(value.declared_backends))
    return digest


def read(sub, digest):
    node = sub.get_node(digest)
    if node is None or node["kind"] != RECORD_KIND:
        _refuse(f"no {RECORD_KIND} node {digest}")
    fields = bundle._decode(bytes(node["canonical"]))
    if not isinstance(fields, dict) or set(fields) != {f.name for f in fields_of(AllowList)}:
        _refuse(f"{RECORD_KIND} node {digest} does not carry the allow-list fields")
    value = AllowList(
        template_name=fields["template_name"],
        template_hash=fields["template_hash"],
        bundle_hash=fields["bundle_hash"],
        mechanism=fields["mechanism"],
        counted_object=fields["counted_object"],
        declared_backends=tuple(fields["declared_backends"]),
        exec_paths=tuple(fields["exec_paths"]),
        network_egress=fields["network_egress"],
        writable_root=fields["writable_root"],
        profile_hash=fields["profile_hash"],
    )
    if value.hash != digest:
        _refuse(f"{RECORD_KIND} node {digest} does not match its content address")
    return value
