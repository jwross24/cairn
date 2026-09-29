# Doctor detector test boundaries

## Named fixture seams

- `detectors.Context.vectors` defaults to `kat.DEFAULT_VECTORS`; `d_kat` passes the path to `kat.run` and includes it in mismatch evidence. `tests/doctor_fixtures/kat_mismatch` supplies a real corrupt JSON file under the test's temporary checkout.
- `pari.GP_BIN` is the module-level executable path read by the doctor detectors. The `gp` integration fixtures replace that path with temporary shell scripts and still exercise the real subprocess boundary.

## Coverage limits

- `D-pari-inprocess/stack` is **UNTESTED** under the supported real libpari build. The finding requires `pari.pari.stacksize()` to report less than 64,000,000 bytes; this test boundary does not alter the library result.
- `D-pari-inprocess/ellcard` is **UNTESTED** under the supported real libpari build. The finding requires `pari.ellcard` to disagree with the first vendored corpus case; this test boundary does not alter arithmetic results.
- `D-pari-inprocess/libpari-version` is **UNTESTED** under the supported real libpari build. The finding requires the library version to fall outside 2.17.x; this test boundary does not substitute version data.

These findings have no passing fixture. No arithmetic mock or second libpari build is part of the detector test surface. The KAT fixture demonstrates that the doctor reports a mismatch from the vector file it receives; it does not establish canonicalizer correctness or exercise the three in-process PARI findings.
