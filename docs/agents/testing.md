Read this before adding a test layer, a fixture that opens the substrate, or a test that writes files.

# Testing detail

- Layout under `tests/`: `unit/`, `integration/`, `e2e/`, `conformance/`, `planted/`, `mutants/`, `hook_contract/`, plus `fixtures/`, `goldens/`, `vectors/`, `fuzz_corpus/`.
- Each layer covers happy path, edge cases and error conditions; integration tests use the real substrate and real PARI, with no mocks of storage or arithmetic.
- `Substrate.open(path, role="writer")` raises `WriterAlreadyOpen` while an earlier writer is unclosed, and a leaked writer fails every later writer-opening test in the run.
- `PariStall` is a `KeyboardInterrupt` subclass raised by cysignals' alarm; after it fires the suite stops at exit 124. `tests/unit/test_pari_module.py` holds the planted loop proving the chain intact.
