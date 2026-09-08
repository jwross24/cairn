"""The §7 statement pre-filter battery: it produces the records `cairn.prefilter` reads.

The battery lives outside `cairn.prefilter` because `cairn.tiergate` imports that reader, and a
Tier-0 admission predicate must not pull the Lean toolchain into its import graph.

Four filters run. `roundtrip_divergence` is deliberately not among them: it is carried by
`cairn-ii6`, and a filter that did not run is absent from the verdicts rather than QUIET, so
`PrefilterResult.passed` is False and Tier-1 theorem admission stays shut until that bead lands.

The `exists_implication` and `stub_or_axiom` filters are formal-conjectures' `ExistsImplicationLinter`
and `StubLinter`, vendored under `lean/vendor/formal_conjectures/` and carried in the gate bundle as
raw objects, so the pinned revision is what runs whatever upstream does later. Their measured
limitation is that the binder-predicate and conjunction-nested forms of the `exists`-implication trap
pass silently; the Skeptic's checklist carries it and `tests/unit/test_statement_prefilters.py` pins it.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from cairn import lean, log, prefilter

lg = log.get("statement_prefilters")

VENDOR_DIR = lean.REPO_ROOT / "lean" / "vendor" / "formal_conjectures"
VENDOR_REPO = "https://github.com/google-deepmind/formal-conjectures"
VENDOR_REV = "e13dd7284e72012a1616806d09cb6b8025e387af"

PROVENANCE_KIND = "prefilter_linters"
LINTER_SOURCES = {
    "linter_exists_implication": "FormalConjecturesUtil/Linters/ExistsImplicationLinter.lean",
    "linter_infotree_util": "FormalConjecturesForMathlib/Lean/Elab/InfoTree/Util.lean",
    "linter_stub": "FormalConjecturesUtil/Linters/StubLinter.lean",
    "linter_term": "FormalConjecturesForMathlib/Tactic/Linter/Term.lean",
}
LINTER_KINDS = tuple(sorted(LINTER_SOURCES))
LINTER_IMPORTS = (
    "FormalConjecturesUtil.Linters.ExistsImplicationLinter",
    "FormalConjecturesUtil.Linters.StubLinter",
)

LAKEFILE = """name = "cairn_prefilter"

[[lean_lib]]
name = "FormalConjecturesForMathlib"
globs = ["FormalConjecturesForMathlib.+"]

[[lean_lib]]
name = "FormalConjecturesUtil"
globs = ["FormalConjecturesUtil.+"]

[[lean_lib]]
name = "Prefilter"
globs = ["Prefilter.+"]
"""

PRODUCED_FILTERS = (
    prefilter.VACUITY,
    prefilter.EXISTS_IMPLICATION,
    prefilter.STUB_OR_AXIOM,
    prefilter.BOUNDED_PROVER,
)

MODULE_PREFIX = "Prefilter.P_"
HASH_CHARS = 16
BOUNDED_TACTICS = ("rfl", "decide", "omega", "trivial", "simp_all")

EXISTS_WARNING = "Declaration contains the pattern"
STUB_WARNING = "Placeholder definitions"
AXIOM_WARNING = "New axioms"
SORRY_WARNING = "declaration uses `sorry`"
WARNING = re.compile(r"^warning: (?P<path>[^:]+):(?P<line>\d+):(?P<col>\d+): (?P<text>.*)$")

THEOREM = "theorem"
AXIOM = "axiom"
OPAQUE = "opaque"
DEFINITION = "def"
DECLARATION_KINDS = (THEOREM, AXIOM, OPAQUE, DEFINITION)

STUB = "stub"
NEW_AXIOM = "new_axiom"
PROVABLE = "provable"
REFUTABLE = "refutable"


class PrefilterBatteryError(Exception):
    pass


@dataclass(frozen=True)
class Statement:
    name: str
    conclusion: str
    binders: str = ""
    hypotheses: tuple = ()
    proof: str = "by sorry"
    imports: tuple = ()
    kind: str = THEOREM

    def __post_init__(self):
        if self.kind not in DECLARATION_KINDS:
            raise PrefilterBatteryError(f"declaration kind {self.kind!r} is not one of {DECLARATION_KINDS}")

    @property
    def proposition_valued(self):
        return self.kind in (THEOREM, AXIOM)

    @property
    def declaration(self):
        if self.kind == AXIOM:
            return f"axiom {self.name} : {self.proposition}", None
        if self.kind == OPAQUE:
            return f"opaque {self.name} : {self.conclusion}", None
        if self.kind == DEFINITION:
            return f"def {self.name} : {self.conclusion}", "  sorry"
        return f"theorem {self.name} : {self.proposition}", f"  {self.proof}"

    @property
    def proposition(self):
        quantified = f"∀ {self.binders}, " if self.binders else ""
        implied = "".join(f"({h}) → " for h in self.hypotheses)
        return f"{quantified}{implied}({self.conclusion})"

    @property
    def premise(self):
        quantified = f"∀ {self.binders}, " if self.binders else ""
        implied = "".join(f"({h}) → " for h in self.hypotheses)
        return f"{quantified}{implied}False"


@dataclass(frozen=True)
class Battery:
    statement_hash: str
    verdicts: dict
    flags: tuple
    detail: dict


def linter_objects():
    objects = {}
    for kind, relative in LINTER_SOURCES.items():
        path = VENDOR_DIR / relative
        if not path.is_file():
            raise PrefilterBatteryError(f"vendored linter source {path} does not exist")
        objects[kind] = path.read_bytes()
    return objects


def provenance():
    return {
        "repo": VENDOR_REPO,
        "rev": VENDOR_REV,
        "files": {kind: LINTER_SOURCES[kind] for kind in LINTER_KINDS},
        "edits": [
            "FormalConjecturesForMathlib/Tactic/Linter/Term.lean: add `public import Lean.Linter.Basic`",
            "FormalConjecturesUtil/Linters/StubLinter.lean: `public import Mathlib.Tactic.Linter.Header`"
            " becomes `public meta import Lean.Linter.Basic`",
        ],
        "imports": list(LINTER_IMPORTS),
        "silent_forms": [
            "∃ n, n > 0 ∧ (n ≠ 1 → False)",
            "∃ n, (n ≠ 0 → False) ∧ True",
        ],
    }


def module_name(statement_hash):
    return f"{MODULE_PREFIX}{statement_hash[:HASH_CHARS]}"


def module_path(statement_hash, project_dir):
    return Path(project_dir) / "Prefilter" / f"P_{statement_hash[:HASH_CHARS]}.lean"


def _tactic_block():
    attempts = " | ".join(f"({tactic}; done)" for tactic in BOUNDED_TACTICS)
    return f"  by intros; first | {attempts} | sorry"


def render(statement):
    lines = [f"import {name}" for name in (*LINTER_IMPORTS, *statement.imports)]
    lines += ["", "set_option linter.style.stubs true", ""]
    anchors = {}

    def declare(anchor, text, proof):
        anchors[anchor] = len(lines) + 1
        lines.append(text if proof is None else f"{text} :=")
        if proof is not None:
            lines.extend(proof.rstrip("\n").split("\n"))
        lines.append("")

    declare("statement", *statement.declaration)
    declare("vacuity", f"theorem cairn_vacuity : {statement.premise}", _tactic_block())
    if statement.proposition_valued:
        declare("provable", f"theorem cairn_provable : {statement.proposition}", _tactic_block())
        declare("refutable", f"theorem cairn_refutable : ¬ ({statement.proposition})", _tactic_block())
    return "\n".join(lines), anchors


def warnings_for(stdout, stderr, path_suffix):
    found = []
    for line in f"{stdout}\n{stderr}".split("\n"):
        match = WARNING.match(line.strip())
        if match and match["path"].endswith(path_suffix):
            found.append((int(match["line"]), match["text"]))
    return tuple(found)


def _proved(found, anchors, anchor):
    line = anchors[anchor]
    return not any(at == line and SORRY_WARNING in text for at, text in found)


def classify(found, anchors):
    statement_line = anchors["statement"]
    on_statement = tuple(text for at, text in found if at == statement_line)
    detail = {"stub_or_axiom": [], "bounded_prover": []}

    trapped = any(EXISTS_WARNING in text for text in on_statement)
    if any(STUB_WARNING in text for text in on_statement):
        detail["stub_or_axiom"].append(STUB)
    if any(AXIOM_WARNING in text for text in on_statement):
        detail["stub_or_axiom"].append(NEW_AXIOM)

    vacuous = _proved(found, anchors, "vacuity")
    if "provable" in anchors and _proved(found, anchors, "provable"):
        detail["bounded_prover"].append(PROVABLE)
    if "refutable" in anchors and _proved(found, anchors, "refutable"):
        detail["bounded_prover"].append(REFUTABLE)

    verdicts = {
        prefilter.VACUITY: prefilter.REJECT if vacuous else prefilter.QUIET,
        prefilter.EXISTS_IMPLICATION: prefilter.FLAG if trapped else prefilter.QUIET,
        prefilter.STUB_OR_AXIOM: prefilter.FLAG if detail["stub_or_axiom"] else prefilter.QUIET,
    }
    if "provable" in anchors:
        verdicts[prefilter.BOUNDED_PROVER] = prefilter.FLAG if detail["bounded_prover"] else prefilter.QUIET
    else:
        detail["bounded_prover"] = "not-run: the declaration is not proposition-valued"
    flags = tuple(sorted(name for name, verdict in verdicts.items() if verdict == prefilter.FLAG))
    return verdicts, flags, detail


def write_linters(gate, project_dir):
    written = {}
    for kind in LINTER_KINDS:
        target = Path(project_dir) / LINTER_SOURCES[kind]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(gate.raw(kind))
        written[kind] = gate.digest_of(kind)
    return written


def scratch_project(gate, work_dir):
    root = Path(work_dir)
    root.mkdir(parents=True, exist_ok=True)
    (root / "lean-toolchain").write_text(gate.lean["toolchain"] + "\n")
    (root / "lakefile.toml").write_text(LAKEFILE)
    (root / "Prefilter").mkdir(exist_ok=True)
    write_linters(gate, root)
    return root


def run(gate, statement, *, statement_hash, project_dir=None, timeout_s=lean.DEFAULT_TIMEOUT_S):
    pins = gate.lean
    lean.assert_pinned(pins)
    root = Path(project_dir) if project_dir is not None else lean.PROJECT_DIR
    linters = write_linters(gate, root)
    source, anchors = render(statement)
    path = module_path(statement_hash, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source + "\n")
    module = module_name(statement_hash)
    result = lean.run_argv(lean.command(pins, "build", module=module), cwd=root, timeout_s=timeout_s)
    if result.rc != 0:
        raise PrefilterBatteryError(f"pre-filter build rc={result.rc}: {result.stdout}{result.stderr}")
    found = warnings_for(result.stdout, result.stderr, path.name)
    verdicts, flags, detail = classify(found, anchors)
    battery = Battery(
        statement_hash=statement_hash,
        verdicts=verdicts,
        flags=flags,
        detail={
            **detail,
            "module": module,
            "linters": linters,
            "vendor_rev": VENDOR_REV,
            "roundtrip_divergence": "not-run: cairn-ii6",
        },
    )
    lg.info("battery", statement_hash=statement_hash, verdicts=verdicts, flags=list(flags), detail=battery.detail)
    return battery


def record(sub, gate, battery, *, at=None):
    return prefilter.record(
        sub, gate, statement_hash=battery.statement_hash, verdicts=battery.verdicts, flags=battery.flags, at=at
    )
