# Grounding brief: the stack facts M0 stands on

Bead `cairn-m0-e0s.2`. Every row below is copied from the `test.log.jsonl` records the listed tests emit through `cairn.log` at INFO; the tests are the executable record and re-run forever, this file is the human-readable ledger with tags.

Tags: **PROVEN-by-probe** = the exact command ran on this machine and the test asserts the observed output on every run; **STRONG-EMPIRICAL** = observed on this machine, asserted, but on one input or one timing window; **CONJECTURE** = stated, not executed here; **OPEN** = not probed, with the milestone that grounds it; **context (not asserted)** = taken from a command run by hand or from a logged field; no test asserts it.

## Environment (one machine, one OS user)

| Item | Value |
|---|---|
| Date | 2026-08-21 |
| `sw_vers` | ProductName: macOS, ProductVersion: 26.6, BuildVersion: 25G72 |
| `uname -a` | `Darwin ALC00648 25.6.0 Darwin Kernel Version 25.6.0: Sat Jul 11 15:26:29 PDT 2026; root:xnu-12377.161.13~4/RELEASE_ARM64_T8132 arm64` (context, not asserted; the fs tests log `platform.system() mac_ver() release() machine()`) |
| Filesystem | APFS (`diskutil info /System/Volumes/Data` → `File System Personality: APFS`; pytest's `tmp_path` lives under `/private/var/folders/.../T`, on that volume) (context, not asserted) |
| OS user | uid 502 (`jr843u`), not root; the only user in play (operator decision 8) |
| Interpreter | `uv run python -c "import sqlite3,sys; print(sys.version, sqlite3.sqlite_version)"` → `3.14.0 (main, Oct 31 2025, 23:20:55) [Clang 21.1.4 ] 3.50.4` (uv-managed CPython at `~/Library/Application Support/uv/python/cpython-3.14-macos-aarch64-none`) |
| gp | `/opt/homebrew/bin/gp` — `GP/PARI CALCULATOR Version 2.17.4 (released)`, arm64 darwin, GMP 6.3.0. `tests/integration/test_grounding_gp.py::test_gp_version_short_is_2_17` runs `/opt/homebrew/bin/gp --version-short` (rc 0, stdout `2.17.4\n`, logged) and asserts stdout starts with `2.17`: PROVEN-by-probe for the major.minor; the patch level, arm64 and GMP cells are context (not asserted) |
| libpari / cypari2 | `cairn.pari.pari_versions()` → `{'libpari': '2.17.2', 'cypari2': '2.2.4'}` (logged by the PRNG and version tests, not asserted) |

Run command (all four files):

```
uv run pytest tests/integration/test_grounding_sqlite.py tests/integration/test_grounding_fs.py tests/integration/test_grounding_gp.py tests/integration/test_grounding_subprocess.py -q -p no:randomly
```

Result on 2026-08-21: `68 passed in 2.25s`. Mutation check on the 66-row run of the same date (scratch copies with ten expectations flipped to the opposite outcome: pin append OK, attest unlink OK, attest rename OK, DELETE-EXCLUSIVE reads, busy_timeout=0 waits, 8M ellcard60 prints n, 40-bit ellcard consumes PRNG in both backends, wait4 raises ValueError, proc.wait() returns 3): exactly those 10 failed, the other 56 passed — the tables bite. Mutation check on the 68-row run (seven flips: pin/attest truncate-after-clear swapped, chmod-EPERM mode check set to 0600, rename-EPERM `.moved` check inverted, PRNG baseline draw off by one, 40-bit ellsea treated draw off by one, `f3(1,2,3)` expected `1 2 0`, gp version prefix `2.18`): each flip fails exactly the rows it touches (2, 2, 2, 8, 2, 1, 1) and nothing else.

## 1. SQLite: readers against an uncommitted writer, by journal mode and BEGIN kind

Test: `tests/integration/test_grounding_sqlite.py::test_reader_against_uncommitted_writer_by_journal_mode_and_begin_kind`. File DB under `tmp_path`; the writer connection (`sqlite3.connect(path, autocommit=True)`) runs `PRAGMA journal_mode=<mode>` (the pragma returns `wal` / `delete`, asserted), `BEGIN <kind>`, one `INSERT`, and holds; a second connection with `timeout=0.5` runs `SELECT count(*)`. CPython 3.14.0, SQLite 3.50.4.

| id | journal_mode | BEGIN kind | Reader outcome | wait_ms | Tag |
|---|---|---|---|---|---|
| `WAL-DEFERRED-reads` | WAL | DEFERRED | reads, count 0 | 0.1 | PROVEN-by-probe |
| `WAL-IMMEDIATE-reads` | WAL | IMMEDIATE | reads, count 0 | 0.1 | PROVEN-by-probe |
| `WAL-EXCLUSIVE-reads` | WAL | EXCLUSIVE | reads, count 0 | 0.1 | PROVEN-by-probe |
| `DELETE-DEFERRED-reads` | DELETE | DEFERRED | reads, count 0 | 0.0 | PROVEN-by-probe |
| `DELETE-IMMEDIATE-reads` | DELETE | IMMEDIATE | reads, count 0 | 0.0 | PROVEN-by-probe |
| `DELETE-EXCLUSIVE-locked` | DELETE | EXCLUSIVE | `OperationalError: database is locked` | 539.3 | PROVEN-by-probe |

Facts: under WAL a reader never waits on a writer, whatever BEGIN kind the writer holds. Under rollback-journal (DELETE) mode only `BEGIN EXCLUSIVE` blocks readers; `BEGIN` and `BEGIN IMMEDIATE` leave the reader free (the lock-state mechanism, writer holds RESERVED while readers still take SHARED, is context from the SQLite locking documentation, not asserted; the rows assert only the reader outcome). That is why the probe's writer holds `BEGIN EXCLUSIVE`: with a plain `BEGIN` the control (DELETE) arm would agree with the treatment (WAL) arm and the probe would fail by its own control-vs-treatment rule. The single-writer contract (PLAN §3) stands on the WAL rows; the DELETE-EXCLUSIVE row is the planted negative.

## 2. SQLite: busy timeout between two writers (WAL)

Test: `tests/integration/test_grounding_sqlite.py::test_second_writer_busy_timeout_under_wal`. A: `BEGIN IMMEDIATE; INSERT` and holds; B (a thread, own connection, `timeout=<busy_timeout>`): `INSERT`.

| id | B busy_timeout | A commits after | B outcome | B wait_ms | Tag |
|---|---|---|---|---|---|
| `timeout500-commitNone-locked` | 500 ms | never (A rolls back at the end) | `database is locked` | 547.7 | STRONG-EMPIRICAL (timing window; asserted 450–1500 ms) |
| `timeout0-commitNone-locked` | 0 ms (control: no timeout) | never | `database is locked` | 0.2 | STRONG-EMPIRICAL (asserted < 100 ms) |
| `timeout500-commit200-ok` | 500 ms | 200 ms | inserted; table holds 2 rows | 248.1 | STRONG-EMPIRICAL (asserted 150–1500 ms) |

Facts: the busy handler waits about the configured timeout and then raises; without a timeout the second writer fails at once; when the first writer commits inside the window the second writer succeeds after roughly the commit delay. Measured waits are on this machine on 2026-08-21; the assertions use windows of about three times the timeout (upper bound 1500 ms for the 500 ms rows), the observed values are the row. Every connection is closed at the end of its row (`contextlib.closing`).

## 3. macOS `uappnd` (UF_APPEND) on APFS: mode × flag × operation, by the owning user

Test: `tests/integration/test_grounding_fs.py::test_mode_x_uappnd_x_op_by_owner` (skips with a reason when `sys.platform != "darwin"`). Each row: fresh file under `tmp_path` holding `seed\n`, `os.chmod(path, mode)`, `os.chflags(path, stat.UF_APPEND)` when flagged (asserted via `st_flags`), one operation, then the fixture clears the flag (`os.chflags(path, 0)`) and restores 0644 on every path it created, so pytest's basetemp cleanup is never blocked. Success rows also assert the effect (append grew the file, `w` replaced it, truncate emptied it, chmod changed the mode, unlink/rename moved it); refused write rows assert the file still holds `seed\n`, refused chmod rows assert `S_IMODE` is unchanged, refused rename rows assert no `.moved` path exists. Roles in the ids: `attest` = 0644+uappnd (the attestation file shape), `pin` = 0444+uappnd (the pin shape), `readonly` = 0444 without the flag, `control` = 0644 without the flag. All rows PROVEN-by-probe on macOS 26.6 / Darwin 25.6.0 / APFS, uid 502.

| op | attest 0644+uappnd | pin 0444+uappnd | readonly 0444 | control 0644 |
|---|---|---|---|---|
| `open(p,'a')` + write | OK | EACCES | EACCES | OK |
| `os.open(O_WRONLY\|O_APPEND)` + write | OK | EACCES | EACCES | OK |
| `open(p,'w')` | EPERM | EPERM | EACCES | OK |
| `open(p,'r+')` | EPERM | EPERM | EACCES | OK |
| `os.truncate(p, 0)` | EPERM | EPERM | EACCES | OK |
| `os.chmod(p, 0o600)` by the owner | EPERM | EPERM | OK | OK |
| `os.unlink(p)` | EPERM | EPERM | OK | OK |
| `os.rename(p, p+'.moved')` | EPERM | EPERM | OK | OK |

Observed strings (context, not asserted; the rows assert the errno): EPERM rows raise `PermissionError: [Errno 1] Operation not permitted`; EACCES rows raise `PermissionError: [Errno 13] Permission denied`. Test ids follow `<role>-<mode>-<uappnd|noflag>-<op>-<OK|EPERM|EACCES>`, e.g. `pin-0444-uappnd-append-EACCES`, `attest-0644-uappnd-unlink-EPERM`, `readonly-0444-noflag-chmod-OK`, `control-0644-noflag-open_w-OK`.

Consequences for the write boundary (PLAN §4):
- Attestation file = 0644 + `uappnd`: appendable, not overwritable, not truncatable, not re-modable, not unlinkable, not renameable while the flag stands.
- Pin = 0444 + `uappnd`: nothing writes it (append is EACCES from the mode, overwrite/truncate are EPERM from the flag), nothing re-modes, unlinks or renames it while the flag stands — so the pin cannot be replaced by rename while flagged.
- The mode is consulted before the flag: on 0444 the append is EACCES, the flag is never reached. The 0444+uappnd append row is a planted negative: if it ever succeeds the attestation-file mode rule in `cairn-m0-e0s.10` is wrong and the test fails.

## 4. The recorded gap: one OS user can clear the flag

Test: `tests/integration/test_grounding_fs.py::test_owner_clears_uappnd_then_chmod_truncate_rename_unlink_succeed` (ids `pin-0444-truncate-EACCES-until-chmod`, `attest-0644-truncate-OK`). Same uid sets `uappnd` (`st_flags` 4), calls `os.chflags(path, 0)` (`st_flags` 0), then `os.truncate(path, 0)`: on the pin (0444) it is refused with EACCES and the file keeps its 5 bytes, on the attest file (0644) it succeeds and the size is 0; then `chmod 0644`, `truncate`, `rename`, `unlink` — all succeed on both. PROVEN-by-probe. The pin's mode is a second refusal independent of the flag, and it falls to one `chmod` by the owner.

Honest statement of what M0 has: with ONE OS user (operator decision 8) the flag refuses truncation, overwrite, re-mode, unlink and rename by the harness process, but does not bind against a process that clears the flag first; `chflags nouappnd` by the owner is one call. At M0 "the orchestrator cannot write the pin" means cannot overwrite / truncate / re-mode / unlink / rename it; an append to the attestation file by the harness process is not refused until the two-user shape — the digest/offset rule of `cairn-m0-e0s.12` is what makes a harness-appended forgery useless, and `cairn-m0-e0s.10` tests that.

| Fact | Tag | Grounded by |
|---|---|---|
| A second OS user (orchestrator process user ≠ pin/attestation owner) cannot clear `uappnd` on a file it does not own | OPEN | M3 introduces the second OS user; probe then |
| Linux `chattr +a` (immutable-append) gives the same table | OPEN | M1 container bead; `chattr` needs CAP_LINUX_IMMUTABLE to set and clear, which is a different (stronger) shape than macOS `uappnd` — do not assume the table transfers |
| Behavior on a non-APFS filesystem (HFS+, NFS, tmpfs) | OPEN | not needed for M0; note it if a `var/` path ever moves off the boot volume |

## 5. gp facts: exit status, arity, stack, small p

Test: `tests/integration/test_grounding_gp.py::test_gp_exit_arity_stack_and_small_p_facts`. Every row runs `cairn.pari.run_gp([<absolute path of tests/integration/gp/probe.gp>], <stdin line>, stack=<stack>)`, i.e. `gp -q -f -s <stack> /…/tests/integration/gp/probe.gp` fed one stdin line; the log record carries the argv as passed. The 60-bit curve comes from the `load_vector` fixture in `tests/conftest.py`. `probe.gp` defines `f3(a,b,c)=print(a," ",b," ",c)`, `ok()=print("OK");quit(0)`, `fail()=print("FAIL [\"x\"]");quit(1)` and nothing else; it reads no file another bead owns. Expected stdout is matched exactly; an empty expected stderr is asserted as exactly empty; a non-empty expected stderr is a fragment. gp 2.17.4.

| id | stack | stdin | rc | stdout | stderr (fragment) | Tag |
|---|---|---|---|---|---|---|
| `64M-div-by-zero-rc0-stderr` | 64M | `1/0` | 0 | `` | `  ***   at top-level: 1/0` … `  *** _/_: impossible inverse in gdiv: 0.` | PROVEN-by-probe |
| `64M-f3-two-args-zero-filled` | 64M | `f3(1,2)` | 0 | `1 2 0\n` | `` | PROVEN-by-probe |
| `64M-f3-three-args-control` | 64M | `f3(1,2,3)` | 0 | `1 2 3\n` | `` | PROVEN-by-probe (control: the trailing 0 in the row above is a fill, not an echo) |
| `64M-ok-rc0-empty-stderr` | 64M | `ok()` | 0 | `OK\n` | `` (0 bytes) | PROVEN-by-probe |
| `64M-fail-rc1-stdout-empty-stderr` | 64M | `fail()` | 1 | `FAIL ["x"]\n` | `` (0 bytes) | PROVEN-by-probe |
| `8M-ellcard60-overflow-rc0-stderr` | 8M | `print(ellcard(ellinit([218370429096749092,332004879195750802],866004983247663323)))` | 0 | `` | `  *** ellcard: the PARI stack overflows !` + `current stack size: 8000000 (7.629 Mbytes)` | PROVEN-by-probe (planted negative: a success here means the stack facts moved and `cairn-m0-e0s.8`'s crash-fixture premise must be re-grounded) |
| `64M-ellcard60-prints-n` | 64M | same line | 0 | `866004985024698433\n` | `` | PROVEN-by-probe (control for the row above) |
| `2M-startup-overflow-rc1` | 2M | `ok()` | 1 | `### Errors on startup, exiting...\n\n\n` | `  ***   the PARI stack overflows !` + `current stack size: 2000000 (1.907 Mbytes)` | PROVEN-by-probe |
| `1M-startup-overflow-rc1` | 1M | `ok()` | 1 | same | same with `1000000 (0.954 Mbytes)` | PROVEN-by-probe |
| `3M-startup-fits-ok` | 3M | `ok()` | 0 | `OK\n` | `` | PROVEN-by-probe (control: startup fits at 3M) |
| `64M-ellinit-p2-returns-empty` | 64M | `print(ellinit([0,1],2))` | 0 | `[]\n` | `` | PROVEN-by-probe |
| `64M-ellisoncurve-p2-fatal-rc0` | 64M | `print(ellisoncurve(ellinit([0,1],2),[0,1]))` | 0 | `` | `  *** ellisoncurve: incorrect type in checkell (t_VEC).` | PROVEN-by-probe |
| `64M-ellinit-p3-returns-empty` | 64M | `print(ellinit([0,1],3))` | 0 | `[]\n` | `` | PROVEN-by-probe |
| `64M-ellisoncurve-p5-control` | 64M | `print(ellisoncurve(ellinit([0,1],5),[0,1]))` | 0 | `1\n` | `` | PROVEN-by-probe (control: p = 5 initializes and the point test answers) |

Facts the rows pin:
- gp exits 0 on a fatal error (`1/0`, the 8M overflow, the p = 2 `checkell` failure) with the message on stderr and nothing on stdout: never trust rc alone; the verifier's accept predicate is `rc == 0 and stdout == "OK" and stderr == ""`, and the `ok()` row shows that predicate is satisfiable (0 bytes on stderr).
- gp zero-fills missing arguments (`f3(1,2)` prints `1 2 0`, `f3(1,2,3)` prints `1 2 3`): arity is the driver's job.
- `fail()` gives rc 1 with the `FAIL [...]` line on stdout and empty stderr; `quit(n)` is the only way a script sets rc.
- gp's own startup needs more than 2 MB of stack: `-s 2M` and `-s 1M` exit 1 with `### Errors on startup, exiting...` on stdout and the overflow message on stderr without reading stdin (the `ok()` line never ran); `-s 3M` is enough for startup.
- `ellinit([0,1],2)` and `ellinit([0,1],3)` return `[]` (characteristic 2 and 3 are not short-Weierstrass curves), and any `ellisoncurve` on that `[]` dies with a fatal `incorrect type in checkell (t_VEC)` at rc 0 with empty stdout — the fact behind the verifier driver's `p > 3` pre-spawn rule (`cairn-m0-e0s.8`).
- The 60-bit `ellcard` on `tests/vectors/curve60_seed1.json` overflows at `-s 8M` and answers `866004985024698433` at `-s 64M`. The same 8M overflow is also asserted by bead .1's `tests/integration/test_smoke.py::test_curve60_ellcard_under_8mb_default_stack_overflows_with_rc0`; this table carries it because it is this bead's planted negative.

### 5a. `verify()`-OK-at-3M/8M/64M (reserved for `cairn-m0-e0s.8`)

Row to be added at that bead's close by `tests/integration/test_verifier.py` on the bundle script: the verifier script never calls `ellcard`, so an 8 MB ceiling does not crash `verify()`; the forced-crash fixture is its `crash_selftest(p,a,b)` entry (a 60-bit `ellcard`). Not claimed here.

## 6. PARI PRNG consumption by point-counting calls

Test: `tests/integration/test_grounding_gp.py::test_prng_consumption_of_point_counting_calls`, rows `(bits, call, state_changes)` × backend `{gp, cypari2}`. Sequence per cell: `E = ellinit([a,b],p)` (built before the seed is set), `setrand(1)`, two prefix draws `random(2^64)`, the call under test, then `random(2^64)`; compared against the same sequence without the call. gp rows spawn `gp -q -f -s 64M` twice; cypari2 rows run in-process on libpari 2.17.2. 40-bit curve: `p = 617956103213, a = 574238428165, b = 529421460422` (pinned as constants; the derivation `setrand(7); p=randomprime([2^39,2^40]); a=random(p); b=random(p)` and the factorization `ellcard` = 617955427618 = 2 · 342179 · 902971 are context, not asserted). 60-bit curve: `tests/vectors/curve60_seed1.json` (prime order).

| id (× `-gp`, `-cypari2`) | bits | call | baseline final draw | treated final draw | state changes | Tag |
|---|---|---|---|---|---|---|
| `40bit-ellcard-leaves-prng` | 40 | `ellcard(E)` | 14991082624209354397 | 14991082624209354397 | no | STRONG-EMPIRICAL (this curve) |
| `40bit-ellsea-consumes-prng` | 40 | `ellsea(E)` | 14991082624209354397 | 11721172991787151380 | yes | STRONG-EMPIRICAL (this curve) |
| `60bit-ellcard-consumes-prng` | 60 | `ellcard(E)` | 14991082624209354397 | 12458736420605239190 | yes | STRONG-EMPIRICAL (this curve) |
| `60bit-ellsea1-consumes-prng` | 60 | `ellsea(E,1)` | 14991082624209354397 | 12458736420605239190 | yes | STRONG-EMPIRICAL (this curve) |

Every cell asserts the baseline draw `14991082624209354397` (module constant) and the treated draw listed in its row, in both backends, so gp and cypari2 agree cell for cell including the draw values by assertion (same libpari PRNG). Observation outside the asserted table, recorded for `cairn-m0-e0s.6`: on the 40-bit curve `ellsea(E,1)` left the final draw at 14991082624209354397 (no consumption) — its order is even, so the early-abort path returns at ℓ = 2 without reaching the randomized stage; that cell is curve-dependent and is not a row. The asserted facts are what the toy-curve skill pins its call sequence on: at 40 bits `ellcard` is PRNG-neutral and `ellsea` is not; at 60 bits both `ellcard` and `ellsea(E,1)` consume.

### 6a. Tries table (reserved for `cairn-m0-e0s.6`)

The tries-per-bit-size table for the toy-curve search under the pinned call sequence is written by that bead at its close; `tests/vectors/curve60_seed1.json` carries `tries: 45` for 60 bits, seed 1. Not claimed here.

## 7. CPython reap order: `communicate()` reaps

Tests: `tests/integration/test_grounding_subprocess.py`. Child: `[sys.executable, "-c", "import sys; sys.exit(3)"]`; `sys.executable` = `.venv/bin/python3` (CPython 3.14.0 under uv); `subprocess.py` at `~/Library/Application Support/uv/python/cpython-3.14-macos-aarch64-none/lib/python3.14/subprocess.py`.

| Test | Command | Observed | Tag |
|---|---|---|---|
| `test_communicate_reaps_so_wait4_raises_and_returncode_is_3` | `Popen(child, stdout=PIPE, stderr=PIPE); communicate(); os.wait4(pid, 0)` | `communicate()` → `(b'', b'')`, `proc.returncode == 3`; `os.wait4(pid, 0)` raises `ChildProcessError: [Errno 10] No child processes` (asserted as `errno.ECHILD` and the message match) | PROVEN-by-probe (planted negative: if `wait4` returns, the runner's reap rule in `cairn-m0-e0s.9` is moot and the test fails) |
| `test_wait4_before_any_wait_returns_status_and_rusage_then_proc_wait_reports_0` | `Popen(child, stdout=file, stderr=file); os.wait4(pid, 0); proc.wait()` | `proc.returncode` is `None` until waited; `wait4` → `(pid, 768, struct_rusage)` (asserted `isinstance(rusage, resource.struct_rusage)`), `os.waitstatus_to_exitcode(768) == 3`; `proc.wait()` then returns `0` and `proc.returncode == 0` | PROVEN-by-probe |

Source the rows rest on (read 2026-08-21, that file): `communicate()` calls `self.wait()` on its single-pipe path (line 1212) and `self.wait(timeout=...)` on the multi-pipe path (1239) and inside `_communicate` (2152); `_try_wait` (2019–2029) catches `ChildProcessError` and returns `(pid, 0)`, which `_wait` turns into `returncode = 0` — the path that records every crash as exit 0 when something else reaped the child first. The runner that wants rusage must call `os.wait4` itself and never let `communicate()`/`wait()` run first.

## 8. OPEN, stated plainly

- Second OS user: nothing here shows that a process under another uid is refused by `uappnd`; only that the owner is refused until the owner clears the flag. M3.
- Linux `chattr +a`: not probed; the M1 container bead owns it.
- Non-APFS filesystems: not probed.
- Timing rows (§2) are this machine's numbers; a loaded CI box will move them inside the asserted windows.
- Rho at 60 bits: reserved for `cairn-m0-e0s.15` (§9 below).

## 9. Rho at 60 bits (reserved for `cairn-m0-e0s.15`)

Section written by that bead at its close. Not claimed here.
