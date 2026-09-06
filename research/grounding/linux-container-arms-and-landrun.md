# Grounding brief: the gold-tier Linux container, its arms on this Mac, and landrun's sandbox

Bead `cairn-m1-cqt.5.2` (F2). Probe date 2026-09-05, macOS 26.6 / Darwin 25.6.0 arm64, 10 cores,
24 GB; load average 5-20 throughout because a sibling session ran suites, so every wall time is
an upper bound for an idle machine. Tags as in `lean-toolchain-pins-and-mathlib-cost.md`:
**PROVEN-by-probe** = a test asserts the observed output on every run where the arm exists;
**STRONG-EMPIRICAL** = observed here once; **CONJECTURE** = stated, not executed here;
**OPEN** = not probed, with the bead that grounds it; **context** = hand-run, not asserted;
**FACT** = documented upstream (release notes, issue text, kernel.org), not a probe of this machine.

## 1. Identity: input-addressed, with the OCI image id as an artifact

PLAN §16 decision 14. The container identity is `canon.digest("cairn/container-identity/v1",
canonical(bundle/container.json) + bytes(bundle/Containerfile))`. Every input the build fetches
is pinned by digest inside those two files: the base image manifest digest, the Debian snapshot
timestamp, the elan archive, the toolchain archive, the Go toolchain archive and the landrun commit it
builds (the release binary needs glibc 2.38; bookworm ships 2.36), the comparator revision, the
mathlib revision. A rebuild from unchanged inputs has the same identity by
construction; the OCI image id (`docker image inspect --format {{.Id}}`) is recorded in the
gate-run log as an artifact and is NOT the identity, because BuildKit does not produce a
bit-identical layer for the same inputs: §4 records a cached rebuild returning the same id and a
`--no-cache` rebuild from the same two files returning a different one, with every layer after
the base image differing (file mtimes from install time are inside the layer tarballs).
`tests/integration/test_lean_container.py` asserts the identity is a function of exactly those
two byte strings and that the Containerfile `ARG` pins equal the JSON pins.

## 2. Arms on this machine

| Arm | State 2026-09-05 | Kernel inside | Landlock ABI reachable | Tag |
|---|---|---|---|---|
| OrbStack (`docker --context orbstack`) | daemon running, server 29.4.0, seccomp builtin | 7.0.14-orbstack | 8 (TSYNC); no v9 | STRONG-EMPIRICAL (`docker info`) |
| Docker Desktop (`docker --context desktop-linux`) | installed, daemon not running | not probed | not probed | OPEN: start the app to probe; not required for F2 |
| Apple Containerization (`container` 1.3.1, build a9a62e2) | installed by the operator this session, apiserver running, kata kernel | 6.18.35 (lsm=lockdown,capability,landlock,yama,apparmor) | 7 (landrun strict probe, §4.2); no v9 | STRONG-EMPIRICAL (`container run debian:bookworm-slim uname -a`, `/proc/cmdline`) |
| dev tier (`dev-macos-fake-landrun`) | macOS host, comparator's own `scripts/fake-landrun.sh` | none | none | the arm F1/F3 already run on |

Apple's `container run` carries `--user`, `--cap-add`, `--mount`, `--network`, `--read-only`,
`--tmpfs`; it can host the same probes as Docker. It also accepts a custom kernel
(`container system kernel set`), which is the one route on this Mac to a Landlock ABI v9 kernel.

## 3. landrun: maintenance state and the AF_UNIX escape

| Claim | Evidence | Tag |
|---|---|---|
| landrun is maintained | Zouuup/landrun v0.1.17 released 2026-07-22 with `landrun-linux-arm64`; main pushed 2026-07-23, 4 commits ahead of the tag (tests, version bump to 0.1.18) | STRONG-EMPIRICAL (`gh release view`, `gh api`) |
| The escape | issue #43 "Sandbox escape via AF_UNIX sockets": Landlock below ABI v9 does not restrict `connect(2)` to pathname UNIX sockets, so a sandboxed process can drive any daemon socket it can reach (`systemd-run` on a systemd host) | FACT (issue text) |
| The fix | v0.1.17 targets Landlock ABI v9 (go-landlock 0.9.0): pathname UNIX socket connect/sendmsg restricted by default on v9 kernels, `--unix <path>` allows one; abstract sockets and signals scoped by default on ABI v6+ (kernel 6.12+); `--best-effort` degrades to the kernel's best ABI | FACT (release notes) |
| ABI v9 kernel | Linux 7.1+; kernel.org 2026-09-02 lists stable 7.2.3, 7.1.13, longterm 6.18.49 | FACT (`releases.json`) |
| comparator README:53 | "will be fixed in Linux 7.1", committed 2026-05-04 (`5a7df64`), predates both releases; its `systemd-run --property=RestrictAddressFamilies=~AF_UNIX` guard is the host-side compensating control | FACT |
| comparator passes `--best-effort` | `Main.lean:80-86` at rev `5756749` | FACT |

Consequence for the gate. Neither arm here reaches ABI v9, so Landlock does not close the
pathname-socket escape on this Mac; `--best-effort` lands on ABI 8 (OrbStack) or 7 (Apple)
silently. The gold-tier gate run therefore (a) records the kernel version and the Landlock ABI
landrun enforced, (b) runs the Solution build in a container that exposes no pathname UNIX
socket at all: `--network none`, no daemon, no socket bind-mounts, mathlib mounted read-only,
and (c) states that compensating control in the record. On an ABI v9 host the landrun default
closes the hole and the record says so instead. A follow-up bead can pin a 7.1+ kernel on the
Apple arm; it is outside F2.

## 4. Probes, raw

Image identity `b7a0f1bcf5e5d33c106266ed09534ccac29baa0732294b6e054b1ffed002e375`, tag
`cairn-gate:b7a0f1bcf5e5d33c`. OrbStack rows are the output of
`docker --context orbstack run --rm --network none <image> ...`; the two container tests in
`tests/integration/test_lean_container.py` assert the marked rows on every run where a daemon
answers. The Apple rows are the same Containerfile under `container build` / `container run`.

### 4.1 OrbStack arm (kernel 7.0.14-orbstack, uid 1000, `CapEff 0`, `CapBnd a80425fb`)

| Probe | Result | Tag |
|---|---|---|
| build wall, first / cached second / `--no-cache` third | 246.5 s / 1.5 s / 245.3 s | STRONG-EMPIRICAL |
| OCI image id, cached rebuild | `sha256:c1631b54…bac747` both times; after the `--no-cache` build a further cached rebuild of the same tag resolved to the `--no-cache` id `ed7ed7dc…`, so the id follows BuildKit's newest matching layers and is recorded per run, never pinned | STRONG-EMPIRICAL (the test logs both image ids but asserts only `identity` equality, so the id equality is observed, not asserted) |
| OCI image id, `--no-cache` rebuild | `sha256:ed7ed7dc…457567`; 8 layers, only the base layer `13a56b653580` and the empty final layer shared | STRONG-EMPIRICAL |
| `lean +leanprover/lean4:v4.34.0-rc1 --version` | `Lean (version 4.34.0-rc1, aarch64-unknown-linux-gnu, commit 3447a668783dbce1a8fdb97101dd067687b2b418, Release)` | PROVEN-by-probe |
| `landrun --version` | `landrun version 0.1.17` (built from commit `62823c05`) | PROVEN-by-probe |
| strict `landrun --ro / --rox /usr,/bin,/lib -- /bin/true` | rc 1: `Failed to apply sandbox: … missing kernel Landlock support. Got Landlock ABI v8, wanted {Landlock V9; FS: all; Net: all; Scoped: all}` | PROVEN-by-probe (the ABI is parsed and logged) |
| same with `--best-effort` | rc 0: `Applying Landlock restrictions: {Landlock V9; FS: all; Net: all; Scoped: all (best effort)}` then `Landlock restrictions applied successfully`; the enforced ABI is not printed, only the strict probe reveals it | STRONG-EMPIRICAL |
| `--best-effort --ro / --rox …` then `echo probe > /work/probe` | rc 2: `/bin/sh: 1: cannot create /work/probe: Permission denied` | PROVEN-by-probe |
| same plus `--rw /work` | rc 0, stdout `probe` | PROVEN-by-probe |
| `--ro / --rw /work` with no `--rox`, `/bin/sh -c 'echo x'` | rc 1: `[landrun:error] permission denied`; a "denied" that is really "cannot exec the shell", so every deny probe carries `--rox` and asserts on the shell's own message | STRONG-EMPIRICAL |
| `--ro /` and `/dev/null` | `cannot create /dev/null: Permission denied`; the comparator's own landrun line passes `--rw /dev` for this reason | STRONG-EMPIRICAL |
| pathname UNIX sockets visible inside | `/run` holds only `lock/`; `find / -xdev -type s` lists nothing | STRONG-EMPIRICAL |
| comparator `simple_match` under real landrun | rc 0, `Lean default kernel accepts the solution` / `Your solution is okay!` (11.5 s) | PROVEN-by-probe |
| comparator `simple_mismatch` | rc 1, `uncaught exception: Challenge and solution constant kind don't match: 'comm'` | PROVEN-by-probe |
| comparator `simple_axiom_issue` | rc 1, `uncaught exception: Illegal axiom detected: 'helper'` | STRONG-EMPIRICAL |
| `chattr +a` as uid 1000, default caps | `chattr: Operation not permitted while setting flags on /work/append_only.log`; the file stays `---------------C------` and the later truncate and unlink succeed | PROVEN-by-probe |
| `chattr +a` as root, default caps | identical: `Operation not permitted` (CAP_LINUX_IMMUTABLE is outside the default bounding set) | PROVEN-by-probe |
| `chattr +a` as root with `--cap-add LINUX_IMMUTABLE` | `lsattr` shows `-----a---------C------`; `echo second >>` succeeds; `echo trunc >` fails `Operation not permitted`; `rm -f` fails `cannot remove … Operation not permitted`; `cat` prints `first` `second` | PROVEN-by-probe |
| root sets `+a` on a file it `chown`ed to `cairn`, then `su cairn` | the user appends (`appended-by-user` is in the file), the user's truncate and unlink both fail `Operation not permitted` | STRONG-EMPIRICAL |

The comparator projects ship without a `lakefile.toml`, so every comparator row copies the project
under `/work`, adds the comparator's `lean-toolchain` and a two-library lakefile, and runs
`lake env $COMPARATOR_BIN config.json` there.

### 4.2 Apple Containerization arm

Kernel `6.18.35 #1 SMP Mon Jun 15 12:55:27 UTC 2026 aarch64` (kata), `container run` default uid 0
with `CapEff a80425fb` (the Docker default set), so the `--user cairn` of the Containerfile is the
only thing that drops root.

| Probe | Result | Tag |
|---|---|---|
| `container build --file bundle/Containerfile --tag cairn-gate-apple:f2 bundle/` | rc 1 after 68 s at the apt step: `Cannot initiate the connection to snapshot.debian.org:80 (2a04:4e42:61::644). - connect (101: Network is unreachable) Could not connect to snapshot.debian.org:80 (199.232.134.132), connection timed out` then `E: Package 'ca-certificates' has no installation candidate`; the base-image pull from the registry succeeded | STRONG-EMPIRICAL |
| egress from a plain `debian:bookworm-slim` on this arm | `/etc/resolv.conf` is `nameserver 192.168.64.1` and `getent hosts snapshot.debian.org` resolves; `</dev/tcp/199.232.134.132/80` and `</dev/tcp/1.1.1.1/443` both fail, so DNS answers and outbound TCP does not; the same fetches succeed from OrbStack's VM on the same Mac at the same minute | STRONG-EMPIRICAL |
| strict landrun, the OrbStack-built static binary bind-mounted into `debian:bookworm-slim` | rc 1: `Got Landlock ABI v7, wanted {Landlock V9; FS: all; Net: all; Scoped: all}` | STRONG-EMPIRICAL |
| same with `--best-effort` | rc 0: `{Landlock V9; FS: all; Net: all; Scoped: all (best effort)}` then `Landlock restrictions applied successfully` | STRONG-EMPIRICAL |
| gold image on this arm, comparator under landrun, chattr | OPEN until the arm has a route to the pinned mirrors; the follow-up bead that pins a 7.1+ kernel here owns it | |

Raw files for every row above sit beside the OrbStack ones in the session scratchpad and are
pasted into the bead's close comment.

### 4.3 Docker Desktop arm

Not probed: the daemon was not running and F2 needs one Linux arm, not two.

## 5. No-Claim

A green container test proves the pinned image builds, the checker runs under landrun inside
it, and the recorded probes hold on the arm named in the record. It does not prove the sandbox
is escape-free on a kernel below ABI v9; that is the compensating control in §3, stated per run.
