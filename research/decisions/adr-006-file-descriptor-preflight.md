# ADR 006: File-descriptor capacity before commit gates

Status: accepted

## Decision

The pre-commit hook reads kernel-wide descriptor usage before staged-path resolution
or content gates. Python owns parsing, classification and logging. A snapshot with
less than 20 percent of capacity free refuses the commit; exactly 20 percent passes.
The integer predicate is `(maximum - used) * 5 < maximum`.

The probe invokes `sysctl -n kern.num_files kern.maxfiles` with a five-second timeout.
A missing provider, malformed response, nonzero exit, stderr output or unavailable
log denies. Each invocation leaves an `FD-CLEAR`, `FD-CEILING`,
`FD-INFRA-DENY` or `FD-BYPASS` record in `.check.log`. A nonzero helper exit also
produces `FD-PREFLIGHT-DENY` in the hook. If the log cannot be written, stderr reports the failure
and the commit remains refused.

`CAIRN_FD_CEILING_SKIP` requires a nonblank single-line reason and logs its use.
The content-gate bypass does not bypass this preflight. Hosts without the kernel
counters need that explicit, attributable exception rather than a silent skip.

## Evidence and rationale

Historical commit output contains `Too many open files in system` followed by
misleading audit refusals. Nearby kernel readings are 162,749 / 184,320 and
165,638 / 184,320. A ten-percent reserve would admit both readings. Twenty percent
is a conservative policy that refuses both, not a measured sufficient reserve.

The personal-MBP sample is 16,596 / 245,760, with no live exhaustion established.
Raising a per-process `ulimit` does not address this kernel-wide measurement.

`tests/hook_contract/test_fd_ceiling_contract.py` exercises the real hook against
controlled external readings, including a refusal before any content gate starts.
`tests/unit/test_fd_ceiling_gate.py` checks parsing, classification and exact boundary behavior.

## Limits

A snapshot does not reserve capacity. Usage may increase while a long audit runs,
and process creation can fail before the probe starts. The guard classifies observed
pressure; it does not guarantee that every later resource failure is prevented.
No kernel limits, epistemic gates or CI pass criteria are altered.

## Verification fixture boundary

The runner tree-scope fixture uses its existing `BURNER_BUDGET` for the no-descendant
arm, with `wall_cap_multiplier=1.0` and `wall_cap_floor_s=0.0`. Its wall cap is
120.077 seconds. Status and measurement-scope assertions remain independent of the
toy-curve performance calibration. This is a test fixture, not a production budget.
