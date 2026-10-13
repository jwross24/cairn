import base64
import json
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import uuid4

from cairn import bundle, canary, cli, log, roles, skeptic, worker
from cairn.substrate import HashMismatch, UnknownNode, blob_hash, node_hash_for

lg = log.get("dispatch")
ROLE_CONFIG = "worker_roles"
REQUEST_BYTES_UNAVAILABLE = "sdk-query-does-not-expose-provider-bytes"
SKEPTIC_HUNT_TEMPLATE = "skeptic_hunt_checklist"


class DispatchRefused(ValueError):
    pass


@dataclass(frozen=True)
class _Prepared:
    role: str
    node_ids: tuple[str, ...]
    prompt: str
    template: str
    tools: tuple[str, ...]
    model: str
    max_turns: int
    timeout_s: int
    bundle_hash: str
    role_config: bytes
    skeptic_handle: skeptic.Handle | None = None


@dataclass(frozen=True)
class DispatchRecord:
    dispatch_id: str
    role: str
    handed_node_hashes: tuple[str, ...]
    role_template_hash: str
    tool_allow_list: tuple[str, ...]
    prompt_bytes_hash: str
    request_bytes_hash: str | None
    request_bytes_unavailable: str
    bundle_hash: str
    role_config_hash: str
    sdk_version: str
    cli_version: str
    model: str
    at: str

    def as_dict(self):
        return asdict(self)

    @property
    def hash(self):
        return node_hash_for("worker_dispatch", bundle.canonical_bytes("worker_dispatch", self.as_dict()))


@dataclass(frozen=True)
class DispatchResult:
    dispatch_id: str
    status: str
    text: str
    session_id: str
    observed_tools: tuple[str, ...]
    observed_skills: tuple[str, ...]
    observed_plugins: tuple[str, ...]
    cost_usd: str | None
    at: str
    rerun_requests: tuple[dict[str, str], ...] = ()
    read_node_hashes: tuple[str, ...] = ()

    def as_dict(self):
        value = asdict(self)
        if not self.rerun_requests:
            value.pop("rerun_requests")
        if not self.read_node_hashes:
            value.pop("read_node_hashes")
        return value

    @property
    def hash(self):
        return node_hash_for("worker_result", bundle.canonical_bytes("worker_result", self.as_dict()))


def _prepare(sub, gate_bundle, *, role, node_ids):
    worker._check_version()
    pinned = bundle.GateBundle.open(gate_bundle.path, gate_bundle.pin_path)
    if pinned.hash != gate_bundle.hash:
        raise DispatchRefused("dispatch bundle differs from the supplied gate bundle")
    registry = pinned.object(ROLE_CONFIG)
    if not isinstance(role, str) or not isinstance(registry, dict) or role not in registry:
        raise DispatchRefused("role is absent from the pinned worker_roles object")
    config = registry[role]
    fields = {"template", "tools", "model", "max_turns", "timeout_s"}
    if not isinstance(config, dict) or set(config) != fields:
        raise DispatchRefused("worker role fields must be template, tools, model, max_turns, timeout_s")
    if not isinstance(config["template"], str) or not config["template"].strip():
        raise DispatchRefused("worker role needs a role-template name")
    try:
        template, _ = roles.load(pinned, config["template"])
    except roles.RoleTemplateError as exc:
        raise DispatchRefused(str(exc)) from None
    tools = config["tools"]
    if not isinstance(tools, list) or any(not isinstance(t, str) or t not in worker.TOOLS for t in tools):
        raise DispatchRefused("worker tool is outside the dispatch tool registry")
    if len(set(tools)) != len(tools):
        raise DispatchRefused("duplicate worker tool")
    if not isinstance(config["model"], str) or not re.fullmatch(r"claude-[a-zA-Z0-9-]+", config["model"]):
        raise DispatchRefused("worker model must be a Claude model identifier")
    for name in ("max_turns", "timeout_s"):
        if type(config[name]) is not int or config[name] <= 0:
            raise DispatchRefused(f"worker {name} must be a positive integer")
    if not isinstance(node_ids, (tuple, list)) or any(not isinstance(n, str) for n in node_ids):
        raise DispatchRefused("node_ids must be a sequence of node hashes")
    handed = []
    for digest in node_ids:
        node = sub.get_node(digest)
        if node is None:
            raise UnknownNode(f"no handed node {digest}")
        raw = bytes(node["canonical"])
        if node_hash_for(node["kind"], raw) != digest:
            raise HashMismatch(f"handed node {digest} does not match its content")
        try:
            content, encoding = raw.decode("utf-8"), "utf-8"
        except UnicodeDecodeError:
            content, encoding = base64.b64encode(raw).decode("ascii"), "base64"
        handed.append({"hash": digest, "kind": node["kind"], "encoding": encoding, "content": content})
    handle = None
    if tools:
        if len(handed) != 1 or handed[0]["kind"] != "claim_statement":
            raise DispatchRefused("scoped tools require exactly one handed claim statement")
        try:
            handle = skeptic.snapshot(sub, pinned, node_ids[0])
        except skeptic.ScopedReadRefused as exc:
            raise DispatchRefused(str(exc)) from None
    return _Prepared(
        role=role,
        node_ids=tuple(node_ids),
        prompt=json.dumps(handed, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
        template=template,
        tools=tuple(tools),
        model=config["model"],
        max_turns=config["max_turns"],
        timeout_s=config["timeout_s"],
        bundle_hash=pinned.hash,
        role_config=pinned.raw(ROLE_CONFIG),
        skeptic_handle=handle,
    )


def _record(sub, prepared):
    prompt_hash = sub.put_blob(prepared.prompt.encode())
    template_hash = sub.put_blob(prepared.template.encode())
    config_hash = sub.put_blob(prepared.role_config)
    record = DispatchRecord(
        dispatch_id=str(uuid4()),
        role=prepared.role,
        handed_node_hashes=prepared.node_ids,
        role_template_hash=template_hash,
        tool_allow_list=prepared.tools,
        prompt_bytes_hash=prompt_hash,
        request_bytes_hash=None,
        request_bytes_unavailable=REQUEST_BYTES_UNAVAILABLE,
        bundle_hash=prepared.bundle_hash,
        role_config_hash=config_hash,
        sdk_version=worker.SDK_VERSION,
        cli_version=worker.CLI_VERSION,
        model=prepared.model,
        at=cli.now_iso(),
    )
    _write(
        sub,
        "worker_dispatch",
        "worker_dispatches",
        record,
        (*prepared.node_ids, prompt_hash, template_hash, config_hash),
    )
    return record


def _write(sub, kind, table, value, parents):
    data = json.dumps(value.as_dict(), sort_keys=True, separators=(",", ":"))
    canonical = bundle.canonical_bytes(kind, value.as_dict())
    with sub._tx():
        sub._put_node(kind, canonical, value.hash, "AuditOnly", None)
        sub.conn.execute(
            f"INSERT INTO {table} (dispatch_id, record_hash, record_json) VALUES (?, ?, ?)",
            (value.dispatch_id, value.hash, data),
        )
        sub._add_root("ledger_row", value.hash)
        for parent in parents:
            sub._add_lineage(value.hash, parent, "input")
    lg.info("write", table=table, dispatch_id=value.dispatch_id, hash=value.hash)


def _read(sub, table, kind, cls, dispatch_id, tuple_fields):
    row = sub.conn.execute(
        f"SELECT record_hash, record_json FROM {table} WHERE dispatch_id = ?", (dispatch_id,)
    ).fetchone()
    if row is None:
        return None
    data = json.loads(row["record_json"])
    for name in tuple_fields:
        if name in data:
            data[name] = tuple(data[name])
    value = cls(**data)
    node = sub.get_node(row["record_hash"])
    expected = bundle.canonical_bytes(kind, value.as_dict())
    if (
        value.dispatch_id != dispatch_id
        or value.hash != row["record_hash"]
        or node is None
        or node["kind"] != kind
        or bytes(node["canonical"]) != expected
    ):
        raise HashMismatch(f"{table} record {dispatch_id} does not match its content address")
    return value


def read(sub, dispatch_id):
    return _read(
        sub,
        "worker_dispatches",
        "worker_dispatch",
        DispatchRecord,
        dispatch_id,
        ("handed_node_hashes", "tool_allow_list"),
    )


def result(sub, dispatch_id):
    return _read(
        sub,
        "worker_results",
        "worker_result",
        DispatchResult,
        dispatch_id,
        ("observed_tools", "observed_skills", "observed_plugins", "rerun_requests", "read_node_hashes"),
    )


@dataclass(frozen=True)
class SkepticItem:
    id: int
    outcome: str
    answer: str
    cited_node_hashes: tuple[str, ...]


@dataclass(frozen=True)
class SkepticRecord:
    statement_hash: str
    dispatch_id: str
    dispatch_hash: str
    result_hash: str
    role_template_hash: str
    verdict: str
    items: tuple[SkepticItem, ...]
    read_node_hashes: tuple[str, ...]
    rerun_requests: tuple[dict[str, str], ...]

    def as_dict(self):
        return asdict(self)


def _closed_json(text):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise DispatchRefused("malformed skeptic_record: duplicate JSON key")
            result[key] = value
        return result

    def constant(_value):
        raise DispatchRefused("malformed skeptic_record: nonfinite JSON value")

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (TypeError, json.JSONDecodeError) as exc:
        raise DispatchRefused("malformed skeptic_record: expected strict JSON") from exc


def _recorded_blob(sub, digest):
    raw = sub.get_blob(digest)
    if raw is None:
        raise DispatchRefused("skeptic_record evidence missing")
    if blob_hash(raw) != digest:
        raise HashMismatch("skeptic_record blob does not match its content address")
    return raw


def skeptic_record(sub, dispatch_id, statement_hash):
    sent = read(sub, dispatch_id)
    if sent is None or sent.role != "skeptic" or sent.handed_node_hashes != (statement_hash,):
        return None
    finished = result(sub, dispatch_id)
    if finished is None or finished.status != "success":
        return None
    if not isinstance(finished.session_id, str) or not finished.session_id.strip():
        raise DispatchRefused("malformed skeptic_record: successful session missing")
    statement = sub.get_node(statement_hash)
    if (
        statement is None
        or statement["kind"] != "claim_statement"
        or node_hash_for(statement["kind"], bytes(statement["canonical"])) != statement_hash
    ):
        raise DispatchRefused("malformed skeptic_record: statement missing or changed")
    if (
        set(finished.observed_tools) != set(sent.tool_allow_list)
        or finished.observed_skills
        or finished.observed_plugins
    ):
        raise DispatchRefused("malformed skeptic_record: observed worker configuration differs")
    config = bundle._decode(_recorded_blob(sub, sent.role_config_hash))
    if not isinstance(config, dict) or not isinstance(config.get("skeptic"), dict):
        raise DispatchRefused("malformed skeptic_record: role configuration")
    selected = config["skeptic"]
    if selected.get("template") != SKEPTIC_HUNT_TEMPLATE:
        return None
    if (
        set(selected) != {"template", "tools", "model", "max_turns", "timeout_s"}
        or selected.get("tools") != list(sent.tool_allow_list)
        or selected.get("model") != sent.model
    ):
        raise DispatchRefused("malformed skeptic_record: dispatch configuration differs")
    template = _recorded_blob(sub, sent.role_template_hash).decode("utf-8")
    ids = tuple(int(value) for value in re.findall(r"^\s*(\d+)\.\s+\S", template, re.MULTILINE))
    if not ids or ids != tuple(range(1, len(ids) + 1)):
        raise DispatchRefused("malformed skeptic_record: numbered template items")
    value = _closed_json(finished.text)
    if not isinstance(value, dict) or set(value) != {"statement_hash", "verdict", "items"}:
        raise DispatchRefused("malformed skeptic_record: response fields")
    if value["statement_hash"] != statement_hash:
        raise DispatchRefused("malformed skeptic_record: response statement differs")
    outcomes = {"clear": 0, "gap": 1, "issue": 2}
    if not isinstance(value["items"], list) or len(value["items"]) != len(ids):
        raise DispatchRefused("malformed skeptic_record: checklist coverage")
    reads = finished.read_node_hashes
    if reads and "mcp__cairn_skeptic__read_node" not in sent.tool_allow_list:
        raise DispatchRefused("malformed skeptic_record: reads without scoped tool")
    for digest in reads:
        node = sub.get_node(digest) if isinstance(digest, str) else None
        raw = sub.get_blob(digest) if isinstance(digest, str) and node is None else None
        if (node is not None and node_hash_for(node["kind"], bytes(node["canonical"])) != digest) or (
            node is None and (raw is None or blob_hash(raw) != digest)
        ):
            raise DispatchRefused("malformed skeptic_record: observed read missing or changed")
    items = []
    for expected, item in zip(ids, value["items"], strict=True):
        if not isinstance(item, dict) or set(item) != {"id", "outcome", "answer", "cited_node_hashes"}:
            raise DispatchRefused("malformed skeptic_record: item fields")
        if type(item["id"]) is not int or item["id"] != expected:
            raise DispatchRefused("malformed skeptic_record: checklist item IDs")
        if not isinstance(item["outcome"], str) or item["outcome"] not in outcomes:
            raise DispatchRefused("malformed skeptic_record: item outcome")
        if not isinstance(item["answer"], str) or not item["answer"].strip():
            raise DispatchRefused("malformed skeptic_record: item answer")
        citations = item["cited_node_hashes"]
        if (
            not isinstance(citations, list)
            or any(not isinstance(digest, str) or digest not in reads for digest in citations)
            or len(set(citations)) != len(citations)
        ):
            raise DispatchRefused("malformed skeptic_record: citation was not observed read")
        items.append(SkepticItem(expected, item["outcome"], item["answer"], tuple(citations)))
    verdict = max((item.outcome for item in items), key=outcomes.__getitem__)
    if value["verdict"] != verdict:
        raise DispatchRefused("malformed skeptic_record: verdict differs from item outcomes")
    return SkepticRecord(
        statement_hash,
        dispatch_id,
        sent.hash,
        finished.hash,
        sent.role_template_hash,
        verdict,
        tuple(items),
        reads,
        finished.rerun_requests,
    )


async def run(sub, gate_bundle, *, role, node_ids):
    prepared = _prepare(sub, gate_bundle, role=role, node_ids=node_ids)
    try:
        canary.require_grounded(sub)
    except canary.CanaryRefused as exc:
        raise DispatchRefused(str(exc)) from None
    record = _record(sub, prepared)
    cwd = Path(tempfile.mkdtemp(prefix="cairn-worker-"))
    try:
        outcome = await worker._execute(prepared, cwd)
    except BaseException as exc:
        failed = DispatchResult(record.dispatch_id, "error", type(exc).__name__, "", (), (), (), None, cli.now_iso())
        _write(sub, "worker_result", "worker_results", failed, (record.hash,))
        raise
    finished = DispatchResult(dispatch_id=record.dispatch_id, at=cli.now_iso(), **outcome)
    _write(sub, "worker_result", "worker_results", finished, (record.hash,))
    return finished
