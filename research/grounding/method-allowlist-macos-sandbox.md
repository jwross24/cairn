# Grounding brief: the ladder-tested method's allow-list and its macOS enforcement arm

Bead `cairn-m1-cqt.1.10` (L10). Probe date 2026-09-08, macOS 26.6 / Darwin 25.6.0 arm64
(`xnu-12377.161.13~4`), 10 cores, 24 GB. Tags as in `linux-container-arms-and-landrun.md`:
**PROVEN-by-probe** = a test asserts the observed output on every run where the arm exists;
**STRONG-EMPIRICAL** = observed here; **CONJECTURE** = stated, not executed here;
**OPEN** = not probed, with the bead that grounds it; **FACT** = documented upstream.

Reproduce with `uv run python research/grounding/probe_method_allowlist.py` and
`uv run python research/grounding/probe_method_allowlist.py --unresolved-scratch`. Both exit 0
when the arm holds; both assert every confined action is denied and that the denied write left no
file, and the first additionally asserts every admitted action succeeds, checks the arithmetic
value on stdout, and reaches 1.1.1.1:80 unsandboxed as the positive control that the network
denial measures the sandbox rather than a dead route.

The script covers the six PROVEN-by-probe rows of §2 and the scratch-resolution row of §3. The
three STRONG-EMPIRICAL rows — `gp` under the profile, DNS, and the exit-71 symlink case — were
run by hand at the shell and are not reachable through either command above, because the script's
child is Python source. Their tag says so; the script is not their evidence.

## 1. The mechanism

`/usr/bin/sandbox-exec` (100 KB, present in the base system) applies a Seatbelt profile to a
process before it execs the target, so confinement precedes the first instruction of the method
under test. The profile the gate renders is deny-default and names six allow forms:

```
(version 1)
(deny default)
(allow process-fork)
(allow process-exec (literal "<backend realpath>") ...)
(allow sysctl-read)
(allow mach-lookup)
(allow file-read* (subpath "/"))
(allow file-write* (subpath (param "SCRATCH")))
```

Parameters reach the profile as `-D KEY=value` and are read with `(param "KEY")`.

## 2. What the arm confines, measured

| Action | Result | Tag |
|---|---|---|
| Arithmetic in the counted object, output on stdout | rc 0 | PROVEN-by-probe |
| Write inside the scratch subpath | rc 0 | PROVEN-by-probe |
| Exec of a declared backend | rc 0 | PROVEN-by-probe |
| Write outside the scratch subpath | `PermissionError: [Errno 1]`, and the file does not exist | PROVEN-by-probe |
| `connect()` to 1.1.1.1:80 | `PermissionError: [Errno 1]` | PROVEN-by-probe |
| Exec of an undeclared `/bin/echo` | `PermissionError: [Errno 1]` | PROVEN-by-probe |
| `gp` (PARI 2.17.4) as the process under the profile, and as a declared backend spawned by the child | rc 0, `2^61-1` printed | STRONG-EMPIRICAL |
| DNS resolution | `gaierror [Errno 8]`, a consequence of the socket denial | STRONG-EMPIRICAL |

## 3. Two path traps, both load-bearing

The profile matches resolved paths, and the two clock sources of §`two-clock-sources` apply
to paths as directly as to instants.

| Trap | Observation | Tag |
|---|---|---|
| Scratch path not resolved | `mktemp -d` hands back `/var/folders/...`; the profile built on that string denies the **honest** scratch write with `PermissionError` while every confinement still holds. The resolved `/private/var/folders/...` admits it. | PROVEN-by-probe (`--unresolved-scratch`) |
| Backend path not resolved | `.venv/bin/python3` is a symlink; `(literal)` on the link path fails before the child starts, at `sandbox-exec` exit **71** with `execvp() of '<path>' failed: Operation not permitted`. The `os.path.realpath` form execs. | STRONG-EMPIRICAL |

An unresolved path is therefore a false green in one direction and a false red in the other, and
neither reports itself as a path bug. `src/cairn/allowlist.py` resolves both before it renders a
profile, and `tests/unit/test_ladder_allowlist.py` asserts the rendered profile carries resolved
paths only.

## 4. Confinement against naming

Confinement is pre-execution and does not depend on the method's cooperation: the write does not
land, the socket does not connect, the undeclared binary does not run. **Naming** the violated
clause is a separate, weaker channel. The child sees `EPERM` and the harness reads it from the
child's stderr, so a method that catches `PermissionError` and exits 0 is confined and unnamed.

| Channel | Strength | Tag |
|---|---|---|
| Confinement (the effect does not occur) | independent of the method | PROVEN-by-probe |
| Naming from the child's stderr | cooperative; a method that swallows `EPERM` defeats it | STRONG-EMPIRICAL |
| Naming from the unified log (`log show`, sandbox violation records) | not probed | OPEN: no bead; the stderr channel carries M1 |

The classes `detect_violation` reports are `undeclared_exec`, `outside_write`, `network_egress`
and `denied_unclassified`. `undeclared_exec` is decided by an exec marker in the trace
(`_execute_child`, `execvp(`, `Failed to exec`), the last two being the mechanism's own wording at
exit 71; `outside_write` by a quoted path that resolves outside the writable root; `network_egress`
by a denial naming no path. A denial whose every quoted path lies inside the writable root is
`denied_unclassified` rather than silently dropped. No class turns on whether the denied path
exists on the auditing host, so the same bytes name the same class on any machine.

## 5. Scope and platform

`sandbox-exec(1)` states "The sandbox-exec command is DEPRECATED" and directs developers to App
Sandbox (FACT, man page on this host). It remains present in the base system and functional, as
§2 measures. It is the only `/usr/bin/sandbox*` binary on this host (STRONG-EMPIRICAL, `ls
/usr/bin/sandbox*` lists `/usr/bin/sandbox-exec` alone). Whether a supported replacement covers
this use is OPEN: App Sandbox is an entitlement on a signed application bundle, not a wrapper for
an arbitrary child process, and no probe here tests it. The gold boundary is the Linux container of bead `cairn-m1-cqt.5.2` with
landrun's Landlock arm, recorded in `linux-container-arms-and-landrun.md`; a green macOS arm
claims nothing about it. On a platform where the mechanism is absent, `allowlist.instantiate`
refuses rather than producing an unenforced instantiation. CI runs macOS only
(`.github/workflows/ci.yml`), so the Linux path of this refusal is unexercised until bead
`cairn-hcl`.

## 6. No-Claim

- The arm is as strong as Seatbelt on this kernel and no stronger; no probe here measures a
  Seatbelt escape, and none is claimed absent.
- Read access is unrestricted by design: the method reads its interpreter, its standard library
  and its declared backends. A read-side channel is out of this bead's scope.
- The counted object slot holds a stand-in. Its binding to the real gate-owned counted object is
  bead `cairn-m1-cqt.1.4`'s assertion, and no rung runs at this bead's close.
- The `INCONCLUSIVE`-at-best cap an uncounted-backend declaration earns is bead
  `cairn-m1-cqt.1.2`'s verdict predicate, not measured here.
- The instantiation's appearance in a dispatch record is bead `cairn-m1-cqt.1.3`'s assertion.
