# GIANTS campaign inputs

These are AuditOnly historical configurations for the October 13, 2026 two-grumpy-giants
experiments. The three specifications preserve their statements, distributions, program
identities, tool versions, and declared budgets. Only `module_dir` points to this repository.
The eleven files in `modules/` preserve the original basenames and bytes, including the
evaluators, six adapters, and formula dependencies.

Run from the repository root with Python 3.14 and the project's uv dependencies:

```bash
uv run python -m cairn.campaign --spec examples/giants/campaign1.json --plan-only
uv run python -m cairn.campaign --spec examples/giants/campaign2.json --plan-only
uv run python -m cairn.campaign --spec examples/giants/campaign3.json --plan-only
```

`--plan-only` checks the program digests and prints the statement and plan commitments.
It does not run trials or preregister a campaign. Each executor and verifier declares
`expected_wall_s: 120.0`; configured trial ceilings are 198, 115, and 52 respectively.

Preserving identities does not certify the evaluators or their results. These inputs do
not include historical outputs, substrates, nonces, or raw receipts. A rerun is not a
historical replay or a fresh preregistration. Campaign 3's `1e-10` ambiguity band and
post-run scoring rules are not fully enforced by the campaign runner. A runner result
alone does not establish the complete historical score or mathematical proof.

Deployment and verification setup is in [development.md](../../docs/development.md).
