Read this before using `bv`, `cass`, `cm`, `ubs`, `rg`, the bead router, or when a task mentions `slb`, `ntm` or `agent-mail`.

# Tool etiquette detail

- `bv --robot-plan` ranks work by what a completion unblocks. Take the highest-`unblocks` leaf; an epic wins on PageRank by construction and is not workable.
- `ubs $(git diff --name-only --cached)`: exit 0 is safe, exit 3 (nothing scanned) is not a pass, any other nonzero means verify the finding is real, fix the root cause and re-run.
- Prior sessions: `cass search "<question>" --robot --limit 5` before re-solving a problem another session handled. `cm context "<task>" --json` before non-trivial work, with inline `// [cass: helpful <rule-id>] - reason` feedback in the session.
- Search by question shape: `rg` for literals, semantic search for "how does X work".
- `uv run python scripts/route.py <bead-id>` emits the class, path floor, reasons and judge status. Fleet routing owns model assignments.
- `slb`, `ntm` and `agent-mail` are installed but unused: this is a single-agent repository, and no reservation or swarm protocol applies until a second agent works the tree. `rch`, `xf`, `ms`: not installed.
