# ADR 009: Doctor detector test boundaries

Status: accepted

## Decision

`detectors.Context.vectors` defaults to `kat.DEFAULT_VECTORS`, and `d_kat` passes that path to `kat.run`. A doctor fixture can therefore supply a temporary corrupt vector file and reach `D-kat/mismatch` through real canonicalization and hashing. The named fixture seams are `Context.vectors` and the existing `pari.GP_BIN` module global; the latter drives real `gp` subprocesses from temporary shell fixtures.

The three `D-pari-inprocess` findings remain untested under the supported real libpari build: `stack` needs a reported stack smaller than 64,000,000 bytes, `ellcard` needs disagreement with the vendored corpus, and `libpari-version` needs a version outside 2.17.x. These conditions are not introduced by a supported doctor fixture. No arithmetic mock or second libpari build is added, and no passing result is claimed for those findings.

## Evidence and limits

`tests/integration/test_doctor.py::test_kat_detector_uses_context_vectors_with_a_real_corrupt_vector_file` checks a clean control, a corrupt temporary vector file, the `D-kat/mismatch` finding, its temporary path, and the repository vector file's length and SHA-256 before and after the run. The fixture lives at `tests/doctor_fixtures/kat_mismatch/__init__.py` and uses the fixture loader's Context-only path so existing CLI fixture discovery remains intact.

The test establishes that the doctor reports a mismatch for supplied corrupt vectors. It does not establish canonicalizer correctness or coverage of the three in-process PARI findings. `src/cairn/doctor/testing.md` is the inventory and coverage report for these boundaries.
