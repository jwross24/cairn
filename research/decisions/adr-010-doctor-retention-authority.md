# ADR-010: Doctor retention authority

## Status

Accepted, 2026-09-29.

## Context

Doctor runs write reports, logs, and reversible action backups under `.doctor/runs/`. The append-only history index is useful after artifacts are collected, and the newest run can be a read-only detection run rather than an undoable action run. Backups preserve source file flags, including `uappnd`, which prevents ordinary directory removal until the flags are cleared.

## Decision

Explicit `cairn doctor gc --before <date> --yes` owns removal of old doctor run directories. A date-only cutoff means midnight UTC. An instant cutoff includes an explicit timezone. Selection uses the UTC creation stamp encoded in a validated run ID and removes only stamps strictly earlier than the cutoff.

Without `--yes`, GC lists the exact selected directories and changes no files. With `--yes`, it holds the doctor lock, validates the full selected batch, refuses the batch if `.doctor/latest` selects a candidate or any path is unsafe, clears file flags without following links, and removes the selected directories. GC reports cleared flags and removed run IDs.

Deletion stays in `src/cairn/doctor_gc.py`, outside the detector and mutation package. The purity scanner covers that module with an explicit deletion allowance and permits only its required `chflags` operation. Every existing doctor module remains subject to the deletion refusal, including `mutate.py`.

The history index remains append-only. `doctor ls` marks artifacts available or unavailable, references to collected reports fail closed, and `doctor undo latest` chooses the newest indexed action run whose artifact directory remains available. `doctor diff [RUN-ID]` compares planned actions with a retained report. `doctor --since=RUN-ID` compares current findings with a retained report.

Artifact-producing doctor runs and collection share `.doctor/lock`, so GC cannot remove an artifact while a current doctor run publishes its report or `latest` link.

## Consequences

Collection bounds only doctor run artifacts and gives up the selected runs' undo backups. It does not collect substrate blobs or change detector verdicts. Retained history rows continue to identify runs whose report artifacts are unavailable.
