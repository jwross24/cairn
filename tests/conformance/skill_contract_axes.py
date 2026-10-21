from collections.abc import Mapping

from skill_contract_base import (
    AXES,
    FAIL,
    MUST,
    NA,
    PASS,
    SHOULD,
    Verdict,
    _document,
    _launch,
    certified,
    imported,
)
from skill_contract_checks import _declared_seam, _launch_with_planted_seam

from cairn import profile


def check_axis_declaration(subject, ctx):
    module = imported(subject)
    if hasattr(module, "CROSS_CHECKS"):
        return _check_declared_axes(subject, ctx, module.CROSS_CHECKS)
    axis = getattr(module, "CROSS_CHECK_AXIS", None)
    if axis not in AXES:
        return Verdict("S2-12", MUST, FAIL, f"cross_check.axis {axis!r} is not one of {list(AXES)}")
    declared = getattr(module, "INDEPENDENT_RANGE", None)
    if not isinstance(declared, Mapping) or not declared:
        return Verdict("S2-12", MUST, FAIL, f"independent_range {declared!r} is not an interval record")
    for name, interval in declared.items():
        if name not in subject.inputs:
            return Verdict("S2-12", MUST, FAIL, f"independent_range names {name!r}, which is not an input field")
        if not (isinstance(interval, (list, tuple)) and len(interval) == 2 and interval[0] <= interval[1]):
            return Verdict("S2-12", MUST, FAIL, f"independent_range[{name!r}] = {interval!r} is not an interval")
    outside = _document(ctx, _launch(subject, ctx, inputs=subject.out_of_range_inputs, salt="s2-12"))
    if outside["cross_check"]["result"] != "untested":
        return Verdict(
            "S2-12", MUST, FAIL, f"outside {declared} the cross-check reports {outside['cross_check']['result']!r}"
        )
    summary = certified(subject, ctx)["summary"]["cross_check"]
    if set(summary) != {"axis", "independent_range"}:
        return Verdict("S2-12", MUST, FAIL, f"the ledger's cross_check block claims more than an axis: {summary}")
    seam = _declared_seam(module)
    if seam is None:
        return Verdict(
            "S2-12", MUST, FAIL, "the subject declares no seam, so its in-range result answers to no second opinion"
        )
    inside = _document(ctx, _launch(subject, ctx, salt="s2-12-inside"))["cross_check"]["result"]
    planted = _document(ctx, _launch_with_planted_seam(subject, ctx, "s2-12-seam"))["cross_check"]["result"]
    if planted == inside:
        return Verdict(
            "S2-12",
            MUST,
            FAIL,
            f"in range the cross-check reports {inside!r} whether or not {seam} is planted, "
            "so it compares nothing and S2-12 carries no evidence that a cross-check exists",
        )
    return Verdict(
        "S2-12",
        MUST,
        PASS,
        f"axis {axis}, range {dict(declared)}, untested outside it and in the ledger; "
        f"in range {inside!r} moves to {planted!r} when {seam} is planted, so S2-12 itself "
        "carries the evidence that a comparison runs",
    )


class AxisDeclarationError(ValueError):
    pass


def _axis_records(records, declarations, *, ledger):
    keys_required = {"axis", "independent_range"} if ledger else {"axis", "independent_range", "result"}
    label = "ledger" if ledger else "output"
    if not isinstance(records, list):
        raise AxisDeclarationError(f"{label} cross_check is not a list of per-axis records")
    indexed = {}
    for record in records:
        if not isinstance(record, Mapping):
            raise AxisDeclarationError(f"{label} cross_check contains a non-record: {record!r}")
        axis = record.get("axis")
        if not isinstance(axis, str) or axis not in declarations or axis in indexed:
            raise AxisDeclarationError(f"{label} cross_check axis {axis!r} is undeclared or repeated")
        if set(record) != keys_required:
            raise AxisDeclarationError(
                f"axis {axis}: {label} cross_check has keys {sorted(record)}, expected {sorted(keys_required)}"
            )
        if record["independent_range"] != declarations[axis]["independent_range"]:
            raise AxisDeclarationError(f"axis {axis}: {label} independent_range differs from its declaration")
        indexed[axis] = record
    missing = declarations.keys() - indexed.keys()
    if missing:
        raise AxisDeclarationError(f"{label} cross_check omits axes {sorted(missing)}")
    return indexed


def _axis_probes(subject, axis, declared):
    probes = subject.cross_check_inputs.get(axis)
    if not isinstance(probes, Mapping) or set(probes) != {"inside", "outside"}:
        raise AxisDeclarationError(f"axis {axis}: no complete inside/outside probe pair")
    for kind, inputs in probes.items():
        if not isinstance(inputs, Mapping) or not subject.inputs.keys() <= inputs.keys():
            raise AxisDeclarationError(f"axis {axis}: {kind} probe omits input fields")
        try:
            in_range = all(interval[0] <= inputs[name] <= interval[1] for name, interval in declared.items())
        except TypeError:
            raise AxisDeclarationError(f"axis {axis}: {kind} probe cannot be compared to its intervals") from None
        if in_range != (kind == "inside"):
            raise AxisDeclarationError(f"axis {axis}: {kind} probe is on the wrong side of {dict(declared)}")
        try:
            imported(subject).COST_PROFILE.evaluate(inputs["bits"])
        except profile.ProfileUndeclared:
            raise AxisDeclarationError(
                f"axis {axis}: {kind} probe size {inputs['bits']!r} has no declared cost"
            ) from None
    return probes


def _check_declared_axes(subject, ctx, records):
    try:
        if not isinstance(records, (list, tuple)) or not records:
            raise AxisDeclarationError("CROSS_CHECKS is not a nonempty list or tuple of declarations")
        declarations = {}
        for record in records:
            if not isinstance(record, Mapping) or set(record) != {"axis", "independent_range", "seam"}:
                raise AxisDeclarationError(
                    f"cross-check declaration is not exactly axis, independent_range and seam: {record!r}"
                )
            axis = record["axis"]
            if not isinstance(axis, str) or axis not in AXES:
                raise AxisDeclarationError(f"cross_check.axis {axis!r} is not one of {list(AXES)}")
            if axis in declarations:
                raise AxisDeclarationError(f"axis {axis}: repeated declaration")
            declared = record["independent_range"]
            if not isinstance(declared, Mapping) or not declared:
                raise AxisDeclarationError(f"axis {axis}: independent_range {declared!r} is not an interval record")
            for name, interval in declared.items():
                if name not in subject.inputs:
                    raise AxisDeclarationError(
                        f"axis {axis}: independent_range names {name!r}, which is not an input field"
                    )
                valid = isinstance(interval, (list, tuple)) and len(interval) == 2
                try:
                    valid = valid and interval[0] <= interval[1]
                except TypeError:
                    valid = False
                if not valid:
                    raise AxisDeclarationError(
                        f"axis {axis}: independent_range[{name!r}] = {interval!r} is not an interval"
                    )
            declarations[axis] = dict(
                record, independent_range={name: list(interval) for name, interval in declared.items()}
            )
        evidence = []
        for axis, record in declarations.items():
            declared = record["independent_range"]
            probes = _axis_probes(subject, axis, declared)
            outside = _document(ctx, _launch(subject, ctx, inputs=probes["outside"], salt=f"s2-12-{axis}-outside"))
            result = _axis_records(outside.get("cross_check"), declarations, ledger=False)[axis]["result"]
            if result != "untested":
                raise AxisDeclarationError(f"axis {axis}: outside {declared} the cross-check reports {result!r}")
            summary = certified(subject, ctx)["summary"].get("cross_check")
            _axis_records(summary, declarations, ledger=True)
            seam = record["seam"]
            if not isinstance(seam, str) or "." not in seam:
                raise AxisDeclarationError(f"axis {axis}: the subject declares no seam for its in-range result")
            inside_doc = _document(ctx, _launch(subject, ctx, inputs=probes["inside"], salt=f"s2-12-{axis}-inside"))
            inside = _axis_records(inside_doc.get("cross_check"), declarations, ledger=False)[axis]["result"]
            planted_doc = _document(
                ctx,
                _launch(
                    subject,
                    ctx,
                    module="skills.harness_child",
                    inputs=probes["inside"],
                    salt=f"s2-12-{axis}-seam",
                    env_extra={
                        "CAIRN_HARNESS_SUBJECT": subject.module,
                        "CAIRN_HARNESS_MODE": "seam",
                        "CAIRN_HARNESS_AXIS": axis,
                    },
                ),
            )
            planted = _axis_records(planted_doc.get("cross_check"), declarations, ledger=False)[axis]["result"]
            if planted == inside:
                raise AxisDeclarationError(
                    f"axis {axis}: in range the cross-check reports {inside!r} whether or not {seam} is planted, "
                    "so it compares nothing and S2-12 carries no evidence that a cross-check exists"
                )
            evidence.append(
                f"axis {axis}, range {dict(declared)}, {inside!r} moves to {planted!r} when {seam} is planted"
            )
    except AxisDeclarationError as exc:
        return Verdict("S2-12", MUST, FAIL, str(exc))
    return Verdict(
        "S2-12", MUST, PASS, "; ".join(evidence) + "; every axis untested outside its range and exact in the ledger"
    )


def check_numeric_profile(subject, ctx):
    module = imported(subject)
    numeric = module.identity_bundle()["numeric_profile"]
    document = _document(ctx, _launch(subject, ctx, salt="s2-13"))
    if not _emits_float(document):
        if numeric is None:
            return Verdict("S2-13", SHOULD, NA, "the subject emits no floats, so no numeric profile is owed")
        return Verdict("S2-13", SHOULD, PASS, f"numeric_profile {numeric!r} declared although no float is emitted")
    if numeric is None:
        return Verdict("S2-13", SHOULD, FAIL, "the subject emits floats and declares no numeric profile")
    return Verdict("S2-13", SHOULD, PASS, f"numeric_profile {numeric!r} declared for a float-emitting subject")


def _emits_float(value):
    if isinstance(value, float):
        return True
    if isinstance(value, Mapping):
        return any(_emits_float(v) for v in value.values())
    if isinstance(value, list):
        return any(_emits_float(v) for v in value)
    return False


def check_postcondition_arm(subject, ctx):
    tier = imported(subject).COST_PROFILE.tier
    if tier != 0:
        return Verdict("S2-14", SHOULD, NA, f"tier {tier} is not the Tier-0 arithmetic case")
    if subject.postcondition is None:
        return Verdict("S2-14", SHOULD, FAIL, "a Tier-0 subject declares no postcondition arm")
    held, refused = subject.postcondition(subject, ctx)
    if not held:
        return Verdict("S2-14", SHOULD, FAIL, "the postcondition refused the subject's own answer")
    if not refused:
        return Verdict("S2-14", SHOULD, FAIL, "the postcondition accepted a planted wrong answer")
    return Verdict("S2-14", SHOULD, PASS, "the postcondition holds on the real answer and refuses a planted one")
