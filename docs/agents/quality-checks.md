Read this before deciding how much of the check suite to run for a change, or when a gate reports a bypass or exclusion.

# Quality check detail

- The fast form of `scripts/check.sh` is the first five gates; the full form adds pytest under a session deadline.
- Choose tests from the changed behavior and its callers, including a positive case and a refusal where applicable.
- If the affected scope is unclear, run the relevant CI lane locally. CI supplies broad regression coverage on the pushed commit; a full local `scripts/check.sh` is for a named cross-suite risk or investigation.
- Run local-only checks when CI cannot exercise the affected behavior. Edits invalidate evidence for the behavior they change, not unrelated results.
