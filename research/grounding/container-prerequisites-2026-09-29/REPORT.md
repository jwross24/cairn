# Linux container prerequisite reuse probe

This probe measures cold pinned Mathlib dependency preparation, prerequisite archive cost, warm image/cache validation, and private dependency restoration. Its output is observational evidence for a possible CI pilot, not a CI speedup result.

## Reproduction

The measured source checkout was `0f6192c2699b5058f080ea2a75e185eeb14391b3`. The pinned image was `sha256:f27f1c1845ec768cb0f64afd6fe2d30edddfae042414a91b7574fae6169f79bb`, platform `linux/arm64`, Cairn identity `b7a0f1bcf5e5d33c106266ed09534ccac29baa0732294b6e054b1ffed002e375`, cache key `c113c4b0433ed44ee31d0b0e792fcb9a84ca1ef2d15d03ff2a4c9c0a463fbb4b`. The daemon was Docker 29.4.0 on OrbStack; the host was macOS arm64.

Run the cold preparation and planted refusals with:

```bash
uv run python research/grounding/container-prerequisites-2026-09-29/probe.py
```

That path creates retained temporary data, downloads the pinned Mathlib cache into a fresh Cairn cache, exports the image, and performs one image load. It must not be rerun against the measured daemon without accounting for that load. The reproducible refinement uses the retained compressed artifact and does not load an image:

```bash
uv run python research/grounding/container-prerequisites-2026-09-29/probe.py --refine research/grounding/container-prerequisites-2026-09-29/runs/20260929T055912Z-49461/archive-followup-20260929T061809Z-25211.json
```

The default and `--resume` paths reach the strict `data_filter` permission refusal; they do not complete the warm round trip. The `--refine` path restores source permission bits and records the successful positive in `runs/20260929T055912Z-49461/archive-refinement-20260929T064604Z-18878.json`. The mode-restoration helper also passed a retained tiny file/directory/symlink fixture. `uv run ruff check research/grounding/container-prerequisites-2026-09-29/probe.py` passes.

The cold raw record has overall status `failed`: its original archive check compared the OCI image config digest `sha256:e77e93ed12905f5b6e1629a6ad333f1e4234751f440ee226c3c7b15258b1c99e` with Docker's image target ID. Its cold preparation and refusal evidence are populated, but it is not a successful end-to-end run. The corrected archive graph check is recorded in the follow-up JSON.

## Measurements

| Stage | Result |
|---|---|
| Cold Mathlib dependency preparation | 295.464 s; 3,011,858,996-byte cache entry, including inventory; 3,004,447,210 dependency bytes; 41,989 files, 2,491 directories, 3 symlinks |
| Image archive | 1,057,248,256 bytes; tagless OCI index target hashes to the exact inspected image ID; all 14 referenced blobs and eight platform layers validate |
| Python gzip archive | 4,069,107,419 input bytes to 2,353,003,610 bytes (57.83%); compression 356.849 s |
| Refined warm consumer path | 337.392 s, excluding Docker image load; includes payload digest, extraction, source and restored inventory checks, exact mode restoration, pin/cache validation, private restore, and an extra independent copied-tree inventory pass |
| `dependencies.restore` | 197.033 s, including its cache validation, private copy, and internal inventory check; the probe's extra copied-tree inventory pass took 43.694 s |
| Independent BSD tar plus zstd transport | 4,069,107,419 input bytes to 2,321,739,519 bytes; compression 59.267 s, extraction 109.251 s; full dependency inventory had zero differences |
| Independent real warm cache consumer | 157.192 s for validation and private restore; 165.578 s total including an extra output inventory scan; uses the zstd-restored cache and excludes archive extraction and Docker load |

The dependency root contains only the pinned project configuration and `.lake/packages`. Its nine pinned packages contain 4,214 `.olean`/`.ilean` files (549,135,537 bytes) and 31,833 package build files (2,212,791,609 bytes). These are package prerequisites. The root has no candidate, challenge, solution, proof, replay, or verification output. The source and private-copy inventory SHA-256 values both equal `dded153fd25ec2425ad949ce1bbb9ab646b217ff0f7d6e07ba972bf267a73fb7` across 44,483 entries. The mode-repair pass restored permissions on 44,480 files/directories; three symlink targets remained exact.

Python `tarfile` extraction with `data_filter` changed permissions on 18 pinned-package Git pack/index files from `0444` to `0644`. The strict validator refused that tree with `dependency-cache-content-mismatch`. Restoring permission bits from the source inventory yielded exact equality across all 44,483 entries. The independent BSD tar/zstd transport preserved the inventory directly. Its separate real warm consumer validated the exact image, pinned Lean toolchain, dependency inventory, and private copy using `tests/_linux_dependencies.py` SHA-256 `a81f4f111e9667511027e2b8389acf3d319743ecc5f41e32cbaf99bd8dc89d9c`. The zstd and warm-consumer results are local shared-host evidence using BSD tar and zstd 1.5.7 with two workers; they are not a Linux Actions run.

The pinned `actions/cache@55cc834` save implementation uses POSIX tar with `-P`, then `zstdmt`; restore uses `unzstd` ([save implementation at `55cc8345863c7cc4c66a329aec7e433d2d1c52a9`, SHA-256 `9193aa9dbe5025f2bf39802ae241470af35c5e5737fd4bec6e1d6dbaad153bb4`](https://github.com/actions/cache/blob/55cc8345863c7cc4c66a329aec7e433d2d1c52a9/dist/save/index.js)). The gzip/data-filter timing is exploratory and does not model that transport. The separate tar/zstd probe is closer to its serialization shape, while still differing in host tar, worker settings, cache service transfer, and runner environment. Its raw result is `runs/transport-independent/actions-cache-tar-zstd-result.json`; the tiny permission/symlink result is `runs/transport-independent/actions-cache-tar-zstd-tiny-result.json`; the independent warm-consumer record is `runs/transport-independent/private-cache-restore-result.json`.

One tagless Docker load was performed on the shared daemon. Its elapsed time and before/after named-tag mappings were not retained, and the load was not repeated. The refinement's later literal inspect found the exact ID on `linux/arm64` with no repository tags; `container.assert_pinned` and `dependencies.cached_image` passed. This is same-daemon warm validation, not cold-daemon load evidence. The archive's `RepoTags` is null, and its OCI index descriptor digest equals the inspected ID. In this containerd store, Docker's image inspection ID is the image target digest ([pinned Moby source](https://github.com/moby/moby/blob/daa0cb7f/daemon/containerd/image_inspect.go)); Docker's image-save interface is documented [here](https://docs.docker.com/reference/cli/docker/image/save/).

Planted negatives all exited 42: a missing image record returned `dependency-cache-image-unavailable`; an all-zero wrong image ID was rejected as uninspectable; a corrupted dependency file returned `dependency-cache-content-mismatch`. The raw refusal records are in the cold measurement JSON.

## Limits

The CI context supplied for comparison is run `36524637482` at `7882d17aaaaeff9a652b35092808e32ec53b5ce4`: pytest fixture setup intervals were 66.05 s for image setup, 86.91 s for dependency setup, and 45.18 s for prepared challenge setup. They are not isolated per-function timers, and whole-job variation does not isolate prerequisite reuse. These local measurements ran under shared-host load, exclude cache-service transfer, and do not measure setup-job critical-path overlap. The zstd and gzip paths are separate experiments; their timings are not combined into an end-to-end warm estimate.

No CI speedup, GitHub transfer cost, fresh-daemon load time, or quiet-host timing is established. No candidate, challenge, proof, replay, or verification verdict is cached or reused. A pilot is justified only if measured cache transfer plus setup-job critical-path overhead is below the prerequisite work it removes.

Raw cold measurement SHA-256: `6b5026df00785b21e4b6e64d6c56e03ee3eedf376aee2e1a4d26ae92183d2117`; its probe SHA-256 is `dcabc70bb19b763e566d471b9f3ba4983b5b6d10574d542f8967780953429f1f`. Raw refined-result SHA-256: `01670b5e1d66e9eecec7c1167aad3fa9906def8ee7159d475ea82fb4987aae26`. Refined probe SHA-256: `6d11121a3d286969b3e82d43e3e3aad23e2f62fd94ba79ea6168183ec89e439e`.
