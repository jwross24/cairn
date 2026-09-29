# macOS process CPU enforcement probe

**Decision: production adoption is blocked.** The bounded probe stops a live workload in one process group, but `setsid` moves a descendant outside that group while it keeps running. The observations do not establish complete process-tree accounting, a strict CPU ceiling, or a deployable enforcement mechanism.

This artifact is an investigation only. It changes no production enforcement, receipts, schemas, or epistemic rules. CPU usage does not establish operation counts or proof progress.

## Evidence identity

The probe ran on macOS 26.6, kernel 25.6.0, arm64, and Python 3.14.7. The full run records source revision `bb6020f150806e0ba8964bab42c7b40ff38fce47` and SHA-256 hashes of `probe.py` and `src/cairn/runner.py` in each JSON result. The final probe SHA-256 is `8cb2d7778dd7f30ab2173d85befaf81065222c169eff19f9ee108bc5f416283d`; the runner SHA-256 is `64a3b7c7c106c3d82ed6b7889c980d3f3f3f34e05b5a4d84fbc9733ce319d0f1`.

The raw outputs selected for review are `raw/all-cases-final.json`, `raw/calibration-clock-final.json`, `raw/calibration-wrong-clock-final.json`, `raw/live-disabled-final.json`, and `raw/pid-query-error-final.json`. Each includes the machine, kernel, Python, source revision, and source hashes. `raw/SHA256SUMS` covers these outputs and their captured stderr files. The probe retains per-run scratch directories and identifies every spawned PID by `(pid, start_abstime)` before signaling or classifying it.

## Clock and population observations

The probe reads `ri_user_time` and `ri_system_time` from `proc_pid_rusage(RUSAGE_INFO_V1)`, converts Mach ticks with the `mach_timebase_info` numerator and denominator, and checks the converted live usage against a worker blocked at a synchronized CPU-burn barrier. On the dedicated calibration run, the target burn was 0.12 seconds; live usage differed from `time.process_time()` by 0.000548 seconds, and final `wait4` usage differed by 0.005621 seconds. Multiplying the conversion by ten produced a live-sample error of 1.478 seconds and an explicit `REFUSE` (exit 2). These are calibration observations on this host, not a cross-machine guarantee.

Apple's XNU `fill_task_rusage` populates the resource-usage fields from task power information; the task accounting source uses Mach-time values. `mach_timebase_info` supplies the conversion fraction. The local SDK headers define the `libproc` interfaces and `proc_bsdinfo` state fields used by the probe. `proc_pidinfo` maps `ESRCH` to absence; an unexpected error or short record raises, and a planted `EPERM` result refuses with exit 2. In the dedicated calibration run, live usage differed from `time.process_time()` by 0.000548 seconds, and final `wait4` usage differed by 0.005621 seconds. The tenfold conversion planting produced a 1.478-second live-sample error and an explicit `REFUSE` (exit 2).

`proc_listpgrppids` observes members of the requested process group. It is not a descendant-tree query. A sample is a point-in-time list followed by per-PID queries; a process can enter or leave between those operations. The probe keys self-usage samples by PID and process start time, and keeps `ri_child_user_time` / `ri_child_system_time` separate from self usage.

Polled JSON handoffs publish a fully written sibling file with `Path.replace`; the parent reads only the final path. A parse error remains a failure rather than being hidden by retrying the read.

The bounded birth-and-exit control had a 0.480-second interval between snapshots. Its child was absent from both snapshots, while direct `wait4` reported 0.178270 seconds of CPU and the reaped-parent counters reported 0.178215 seconds. This demonstrates that snapshots can miss short-lived children; it does not establish an atomic aggregate counter.

The sampled-then-reaped control recorded 55 live samples of one child, then reaped it. Its last self-usage sample was 0.166220 seconds, its direct `wait4` usage was 0.175033 seconds, and the parent's reaped-child delta was 0.174830 seconds. Adding the last live value to the reaped delta yielded 0.341049 seconds, exceeding direct child `wait4` by 0.166016 seconds. Those counters overlap. The sum is diagnostic only, not an accounting proposal or lower bound.

## Enforcement and overrun observations

The same-group positive arm started a root process, child, and grandchild sharing one process group. The CPU workers run without a natural completion condition. At a 0.600-second aggregate self-CPU threshold, the monitor sampled 0.601487 seconds and sent `SIGSTOP`. The next stable sample reported 0.601490 seconds; all three processes reported `SSTOP`. The observed overrun was 0.001490 seconds, the largest observed sampling interval was 0.014100 seconds, and the configured polling interval was 0.005 seconds. Cleanup then killed all three identity-checked processes, observed each as absent, and reaped the direct leader.

With `--disable-enforcement`, the observer reached the same 0.600-second threshold on a live three-process workload (0.603653 seconds), sent no stop signal, and observed all three remain runnable. The probe returned `REFUSE` (exit 2) and cleanup killed every registered identity and reaped the leader. This tests the same liveness predicate with only the enforcement signal omitted.

In the escaped-session arm, the root and child stopped in the measured process group, while a grandchild that called `setsid` remained `SRUN` outside the group with 0.282012 seconds of observed self CPU. The probe returned the expected `COUNTEREXAMPLE` result. Cleanup used the probe's PID/start-time registry to stop that controlled process too; the monitor itself did not contain it.

The separate wall-only sleeper arm used a 0.120-second cap. It exited with signal status -15 after 0.129135 seconds, and cleanup confirmed the sleeper absent and the leader reaped. This is a wall-time control, not evidence of CPU accounting.

The 0.001490-second positive overrun and 0.014100-second largest observed interval are single-run observations, not maxima. Scheduler delay, polling and query latency, signal delivery, startup CPU, short-lived descendants, and descendants outside the group are not bounded by these measurements. The probe does not prove a strict CPU ceiling from observed timings.

## Runner and receipt distinction

The runner uses `start_new_session=True`, polls the process group for other PIDs, and collects the leader's CPU with `wait4`. Its loop enforces yank and wall-cap termination; the CPU classification uses the post-exit `wait4` value. In `status_for`, skill yank outranks CPU overage, which outranks a wall-cap classification.

The controlled post-exit overage receipt has status `BUDGET_EXCEEDED`, exit status 0, 0.535025 seconds CPU against a 0.050000-second ceiling, and `measurement_scope="reaped_descendants"`. The controlled wall-timeout receipt has status `BLOCKED`, exit status -15, 0.013580 seconds CPU, and `measurement_scope="truncated"`. Its measured wall time was 0.060075 seconds for a 0.050000-second cap; interpreter and monitor latency contribute to the overrun.

The receipt schema stores CPU and wall values, exit status, and `measurement_scope`. It does not persist an explicit CPU-stop cause, timeout flag, or yank flag. The candidate CPU stop exists only as probe evidence; there is no production CPU-stop receipt to compare. Status and scope describe the two controlled examples, but a receipt does not independently record the termination cause.

## Conditional implementation contract

This contract applies only after a containment and accounting mechanism passes the evidence hold below. The runner boundary must return final observed CPU, wall elapsed time, measured scope, and a termination cause that distinguishes `cpu_limit`, `wall_timeout`, `yank`, and natural exit. Cause must be set by the event that terminates or completes execution, not inferred from final `wait4` usage. `measurement_scope` continues to describe accounting coverage, independently of that cause. Status classification must preserve CPU-stop refusal even when leader-only or post-reap usage is below the threshold.

Derive the CPU ceiling and wall cap from their existing recipe/profile inputs using `ceiling_for` and `wall_cap_for`. Do not casually persist a second threshold value: a duplicate can diverge from the profile and recipe values that already determine it.

Adding a cause to a receipt requires coordinated review of `src/cairn/runner.py`, `src/cairn/substrate.py` (`RECEIPT_FIELDS`, typed `RECEIPT`, canonicalization, hashing, and `put_receipt`), and `src/cairn/schema.sql` (required columns and append-only constraints). Review receipt hash consumers and golden artifacts for the changed canonical receipt; these files are not in the repository's source identity lists. Contract tests must cover canonical bytes/hash, missing or invalid cause refusal, and append-only writes. Runtime tests must plant four distinct outcomes: CPU stop while final `wait4` is below the ceiling, wall timeout below the CPU ceiling, natural exit with post-exit overage, and yank. The first outcome must remain a refusal even when killed descendants are absent from the leader's `wait4` result.

The production hold remains open until the same runtime scope accounts for and terminates forked, exec'd, `setsid`-escaped, reparented, and short-lived descendants with a documented termination bound. The probe does not select the mechanism or establish that bound.

## Adoption boundary

The candidate process-group sampler is insufficient for production enforcement. The observed `setsid` counterexample disproves the claim that its population equals the hostile process tree, and the sampled/reaped transition disproves adding those counters without a deduplication rule. The probe selects no deployable mechanism.

Production adoption requires evidence for a runtime-enforced containment scope that includes fork, exec, `setsid`, reparenting, and short-lived descendants; aggregate CPU accounting over that same scope; and a termination guarantee with a documented bound that satisfies the configured CPU ceiling. The evidence must include planted escapes and accounting-transition cases. A persisted termination cause must distinguish CPU stop, wall timeout, yank, and post-exit CPU overage independently of final `wait4` usage. No enforcement or receipt change is implemented by this research artifact.

## Reproduction

From the repository root:

```bash
uv run python research/grounding/process-tree-cpu-2026-09-29/probe.py all
uv run python research/grounding/process-tree-cpu-2026-09-29/probe.py calibrate
uv run python research/grounding/process-tree-cpu-2026-09-29/probe.py calibrate --misconvert-clock
uv run python research/grounding/process-tree-cpu-2026-09-29/probe.py live --disable-enforcement
uv run python research/grounding/process-tree-cpu-2026-09-29/probe.py pid-query-error
uv run ruff check research/grounding/process-tree-cpu-2026-09-29/probe.py
uv run codespell --builtin clear,rare,en-GB_to_en-US research/grounding/process-tree-cpu-2026-09-29/probe.py research/grounding/process-tree-cpu-2026-09-29/implementation-spec.md
```

Expected exits are 0 for `all` and calibrated `calibrate`, and 2 for the misconverted clock, disabled enforcement, and planted API-error arms. A zero from `all` means every bounded arm reached its declared outcome, no registered process was observed executing, and the direct leaders were reaped. The final full-run record lists all registered processes as absent; the cleanup predicate also accepts zombies, so exit 0 alone does not prove absence. It does not mean process-tree enforcement is complete.

## Sources

- Python 3.14 [`os.wait4`](https://docs.python.org/3.14/library/os.html#os.wait4), [`os.killpg`](https://docs.python.org/3.14/library/os.html#os.killpg), [`pathlib.Path.replace`](https://docs.python.org/3.14/library/pathlib.html#pathlib.Path.replace), [`subprocess.Popen`](https://docs.python.org/3.14/library/subprocess.html#subprocess.Popen), and [`resource.getrusage`](https://docs.python.org/3.14/library/resource.html#resource.getrusage).
- Apple XNU [`libproc.c`](https://github.com/apple-oss-distributions/xnu/blob/main/libsyscall/wrappers/libproc/libproc.c), [`bsd_kern.c`](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/kern/bsd_kern.c), [`task.c`](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/kern/task.c), and [`kern_resource.c`](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_resource.c).
- Apple [`mach_absolute_time` and timebase conversion](https://developer.apple.com/documentation/kernel/1462446-mach_absolute_time?language=occ).
- Local SDK declarations: `/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include/libproc.h`, `/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include/sys/proc_info.h`, and `/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include/sys/proc.h`.
