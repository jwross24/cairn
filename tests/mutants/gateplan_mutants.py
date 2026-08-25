from contextlib import contextmanager

from cairn import gateplan


@contextmanager
def _swap(owner, name, replacement):
    original = getattr(owner, name)
    setattr(owner, name, replacement)
    try:
        yield
    finally:
        setattr(owner, name, original)


def _prevalidated(plan_rows):
    return isinstance(plan_rows, list) and bool(plan_rows)


@contextmanager
def loader_skips_unknown_steps():
    original = gateplan.GatePlan.load.__func__

    def load(cls, plan_rows):
        if not _prevalidated(plan_rows):
            return original(cls, plan_rows)
        kept = [row for row in plan_rows if isinstance(row, dict) and row.get("kind") in gateplan.STEP_KINDS]
        return original(cls, kept or plan_rows)

    with _swap(gateplan.GatePlan, "load", classmethod(load)):
        yield


@contextmanager
def loader_runs_valid_prefix():
    def load(cls, plan_rows):
        if not _prevalidated(plan_rows):
            raise gateplan.PlanInvalid("plan-empty")
        prefix = []
        for row in plan_rows:
            try:
                prefix.append(gateplan._step_at(len(prefix), row))
            except gateplan.PlanInvalid:
                break
        return cls(prefix)

    with _swap(gateplan.GatePlan, "load", classmethod(load)):
        yield


@contextmanager
def continue_after_failure():
    def outcomes(steps, observe):
        for step in steps:
            observed, extra, digests = observe(step)
            if observed == step.expect:
                yield step, observed, gateplan.RESULT_PASS, tuple(extra), digests
            else:
                yield step, observed, gateplan.RESULT_FAIL, (gateplan.MISMATCH_REASON, f"observed:{observed}", *tuple(extra)), digests

    with _swap(gateplan, "plan_outcomes", outcomes):
        yield


@contextmanager
def blocks_name_wrong_step():
    def outcomes(steps, observe):
        blocker = None
        for step in steps:
            if blocker is not None:
                yield step, gateplan.RESULT_BLOCKED, gateplan.RESULT_BLOCKED, (f"{gateplan.BLOCKED_PREFIX}{step.step}",), (None, None)
                continue
            observed, extra, digests = observe(step)
            if observed == step.expect:
                yield step, observed, gateplan.RESULT_PASS, tuple(extra), digests
            else:
                yield step, observed, gateplan.RESULT_FAIL, (gateplan.MISMATCH_REASON, f"observed:{observed}", *tuple(extra)), digests
                blocker = step.step

    with _swap(gateplan, "plan_outcomes", outcomes):
        yield




@contextmanager
def tier_gate_skips_recording():
    from cairn import claims

    with _swap(claims, "write_hypothesis_object", lambda sub, obj: obj.hash):
        yield


@contextmanager
def tier_gate_drops_refusal_rows():
    from cairn import claims

    with _swap(claims, "add_tier_refusal", lambda sub, key, declared, ticket, reason: None):
        yield


ALL = {
    "loader_skips_unknown_steps": loader_skips_unknown_steps,
    "loader_runs_valid_prefix": loader_runs_valid_prefix,
    "continue_after_failure": continue_after_failure,
    "blocks_name_wrong_step": blocks_name_wrong_step,
    "tier_gate_skips_recording": tier_gate_skips_recording,
    "tier_gate_drops_refusal_rows": tier_gate_drops_refusal_rows,
}
