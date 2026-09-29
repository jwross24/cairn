# Linux method allow-list probe results

The standalone Landrun probe exercised 17 cases inside an immutable Linux arm64 image. All 17 unsandboxed controls succeeded. Best-effort Landrun refused outside-scratch path opens and undeclared path execs, while ordinary scratch writes and declared execs succeeded. A preopened writable descriptor still wrote outside scratch. TCP4/TCP6 and abstract Unix attempts delivered no payload; UDP4/UDP6, pathname Unix, and an inherited connected TCP4 socket delivered their exact payloads. Strict mode rejected startup for all 17 cases because the container exposed Landlock ABI 8 while Landrun required ABI 9. These results characterize the probe invocation only.

## Run identity

The driver bound its production source inputs to Git SHA `5b36e29ca6c4bf9b354d2a1ec83cb0b307b6a03f`. The probe was uncommitted at that source SHA; its separate source and binary digests below identify the measured executable. The immutable image ID was `sha256:dac10db1586ef62f44ed6dbd5989504f9e3bc46489cf2f5e622d087873195472` (`linux/arm64`). The container reported kernel `7.0.14-orbstack-00380-ga7e0a2dc9535`, UID/EUID `1000/1000`, Go `go1.27.1`, and Landrun `0.1.17`.

| Artifact | SHA-256 |
|---|---|
| Probe source | `86c6a2b8f93cb181673789b1c63b01c345f50a434514d6d39266c8e6189876cf` |
| Probe, backend, and undeclared executable copies | `d4e174319f2bc96a6ed290820c6d530a294e2f8390db5e525502d62c578ded3a` |
| Landrun binary | `56f7d351cfc5772c3436fd5247e1a8d768e1a5dbb5f49bfdcfab8eb9122e11e1` |
| Host driver | `71f64c3393eca1b174cb365c7e50832c7a2e4d3fe9d678442ddce1a2884374eb` |

The three executable copies had identical bytes and distinct inodes. Source input digests are:

| Source path at the bound Git SHA | SHA-256 |
|---|---|
| `bundle/Containerfile` | `90001aa93a5d8827bf499f2a1413bb3fdaba045420b517823b071f5349015b22` |
| `bundle/container.json` | `fbbe1e24be14108d7bfbbfef10e09019a2dbbafaee4feee2ab0ff0f75972ce5d` |
| `bundle/allow_lists.json` | `f4b3f33e0e13b42d8c4598e0b08a997730b8e4ec0bc8b1d3a3057651f6c673d4` |
| `src/cairn/allowlist.py` | `88c01c466d6ec7171d8433af77c0cd7a23b3e2a8a7337a8ab09515584f4dedc7` |
| `src/cairn/runner.py` | `64a3b7c7c106c3d82ed6b7889c980d3f3f3f34e05b5a4d84fbc9733ce319d0f1` |
| `src/cairn/ladder.py` | `68eb33872137b62a01d4a58c554ce769f381d36a3776331967432c5a1524941d` |

## Commands and receipts

The probe build receipt records this command and environment, with exit code 0. Create a fresh binary directory before building; the recorded paths identify this run's retained scratch:

```bash
GOOS=linux GOARCH=arm64 CGO_ENABLED=0 go build -trimpath -o /tmp/cairn-day-lane3.uMzz8z/probe-binaries/probe /Users/jwross/Documents/cairn/research/grounding/linux-method-allowlist-2026-09-29/probe.go
```

The driver requires three separate executable files. For a shell reproduction, prepare them with:

```bash
mkdir -p /tmp/cairn-day-lane3.uMzz8z/probe-binaries
chmod 755 /tmp/cairn-day-lane3.uMzz8z/probe-binaries
cp /tmp/cairn-day-lane3.uMzz8z/probe-binaries/probe /tmp/cairn-day-lane3.uMzz8z/probe-binaries/backend
cp /tmp/cairn-day-lane3.uMzz8z/probe-binaries/probe /tmp/cairn-day-lane3.uMzz8z/probe-binaries/undeclared
chmod 755 /tmp/cairn-day-lane3.uMzz8z/probe-binaries/probe /tmp/cairn-day-lane3.uMzz8z/probe-binaries/backend /tmp/cairn-day-lane3.uMzz8z/probe-binaries/undeclared
```

The build receipt records the Go build argv; the separate copies were created by the build helper.

The container driver run used the heavy-run lock and memory cap. A rerun requires a fresh output path because the driver refuses to overwrite an existing evidence directory:

```bash
lockf -k /tmp/cairn-heavy.lock uv run --no-project python /Users/jwross/.local/share/cairn-agent-mail/orders/memcap.py 6 uv run --no-project python research/grounding/linux-method-allowlist-2026-09-29/run_probe.py --binary-directory /tmp/cairn-day-lane3.uMzz8z/probe-binaries --image sha256:dac10db1586ef62f44ed6dbd5989504f9e3bc46489cf2f5e622d087873195472 --source-sha 5b36e29ca6c4bf9b354d2a1ec83cb0b307b6a03f --output /tmp/cairn-day-lane3.uMzz8z/probe-run-1 --expect binary-counted:control:action_succeeded=true --expect binary-counted:best_effort:action_succeeded=true --expect exec-undeclared:control:action_succeeded=true --expect exec-undeclared:best_effort:action_succeeded=false --expect write-scratch:best_effort:file_content_matches=true --expect write-outside:best_effort:file_created=false > /tmp/cairn-day-lane3.uMzz8z/probe-run-1.log 2>&1
```

The driver ran Docker `29.4.0` with `--network=none`, `--memory=6g`, `--memory-swap=6g`, and the three read-only binaries mounted at `/probe`. [raw/manifest.json](raw/manifest.json) records each source path, uncompressed byte length, and SHA-256. It links the [build receipt](raw/probe-build-receipt.json.gz), primary [driver log](raw/probe-run-1.log.gz), [container receipt](raw/probe-run-1--receipt.json.gz), [result](raw/probe-run-1--result.json.gz), [stdout](raw/probe-run-1--probe.stdout.gz), and [stderr](raw/probe-run-1--probe.stderr.gz), plus the [planted-negative log](raw/probe-negative.log.gz), [container receipt](raw/probe-negative--receipt.json.gz), [result](raw/probe-negative--result.json.gz), [stdout](raw/probe-negative--probe.stdout.gz), and [stderr](raw/probe-negative--probe.stderr.gz). The driver tag refusal is recorded in [driver-tag-refusal.log.gz](raw/driver-tag-refusal.log.gz).

Each candidate command used `/usr/local/bin/landrun --best-effort --ro / --rox /probe/probe,/probe/backend --rw /work/scratch -- /probe/probe child ...`; strict commands omitted `--best-effort`. The probe kept the exact argv, exit code, stdout, stderr, process IDs, child reports, and file or local-listener receipts for each case.

## Observations

Every unsandboxed control succeeded. The file controls verified exact contents, and each local network control received its exact fixed payload.

| Case | Best-effort observation |
|---|---|
| Counted binary | Probe child started and reported its executable. |
| Declared backend exec | `/probe/backend` exec and identity receipt succeeded. |
| Undeclared binary exec | Exec returned permission denied; no target identity receipt. |
| Counted binary self reexec | Reexec and identity receipt succeeded. |
| Symlink to declared backend | Exec through the symlink and identity receipt succeeded. |
| Symlink to undeclared binary | Exec returned permission denied; no target identity receipt. |
| Scratch write | File was created with the exact payload. |
| Outside-scratch write | Open returned permission denied; no file was created. |
| Preopened writable file descriptor | Write succeeded; the outside-scratch file held the exact payload. |
| Preopened undeclared executable descriptor | Exec through `/proc/self/fd/3` returned permission denied. |
| TCP4 loopback | Dial returned permission denied; listener received no payload. |
| TCP6 loopback | Dial returned permission denied; listener received no payload. |
| UDP4 loopback | Listener received the exact payload. |
| UDP6 loopback | Listener received the exact payload. |
| Pathname Unix stream socket | Listener received the exact payload. |
| Abstract Unix stream socket | Dial returned operation not permitted; listener received no payload. |
| Inherited connected TCP4 socket | Write through inherited fd 3 succeeded; listener received the exact payload. |

All 17 strict invocations returned code 1 before the child started. Landrun reported: `Failed to apply Landlock restrictions: missing kernel Landlock support. Got Landlock ABI v8, wanted {Landlock V9; FS: all; Net: all; Scoped: all}`. This is a strict startup refusal, not evidence that any individual operation was denied under strict mode.

## Limits

The local listeners and inherited socket were inside the private container network namespace. UDP, pathname Unix socket, and inherited-socket receipts show local payload delivery in this setup; they do not establish host egress, external reachability, or a reachable production escape. The inherited fd 3 was deliberately supplied through `ExtraFiles`; this premise does not establish the production runner's descriptor-passing behavior.

The self-reexec case used a static Go probe binary. It does not test Python framework interpreter reexecution or the production method launch path. DNS is unmeasured, and fork without exec is unimplemented. No complete Linux method enforcement mechanism is selected, no production allow-list policy is changed, and no PROVEN claim follows.

The planted negative expected `network-udp4:best_effort:exact_payload_received=false`. The measured value was `true`, so the assertion reported `passed=false`; the driver and memcap both returned 1, with a 0.05 GiB peak. The result, receipt, stdout, stderr, and log are linked above.

```bash
lockf -k /tmp/cairn-heavy.lock uv run --no-project python /Users/jwross/.local/share/cairn-agent-mail/orders/memcap.py 6 uv run --no-project python research/grounding/linux-method-allowlist-2026-09-29/run_probe.py --binary-directory /tmp/cairn-day-lane3.uMzz8z/probe-binaries --image sha256:dac10db1586ef62f44ed6dbd5989504f9e3bc46489cf2f5e622d087873195472 --source-sha 5b36e29ca6c4bf9b354d2a1ec83cb0b307b6a03f --output /tmp/cairn-day-lane3.uMzz8z/probe-negative --expect network-udp4:best_effort:exact_payload_received=false > /tmp/cairn-day-lane3.uMzz8z/probe-negative.log 2>&1
```

The scoped repository fast check covers spelling but excludes these research Python/Go files from its format, lint, type, and test scopes. Direct Ruff lint/format checks, Go formatting inspection, Linux arm64 cross-compilation, and `go vet` pass. These developer checks do not add Linux authority evidence beyond the actual probe runs above.

UBS exits 0 with eight resource-ownership warnings and no critical findings. The executable file is assigned to `controlFile` and closed by its deferred call; the seven listener factories return their `Close` functions to callers that defer `control.close()`. The inherited socket helper also closes its original client after obtaining the duplicate descriptor. The source review resolves these reported ownership paths, not every possible resource defect.
