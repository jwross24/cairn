# ADR 008: Status observation boundary

Status: accepted

## Decision

`cairn status --json` reads the pinned bundle and substrate without invoking command handlers, gate recorders, or writers. Its substrate contract covers unchanged logical rows and byte-for-byte preservation of the main database file. SQLite's `-wal` and `-shm` sidecars are outside that contract; read-only access to a WAL database may require those files to exist or be created. [SQLite WAL read-only behavior](https://www.sqlite.org/wal.html#readonly)

Status uses the ordinary read-only connection for live WAL visibility. SQLite's `immutable=1` mode skips locking and change detection and can return incorrect results when the file changes, so it is unsuitable for this observation. [SQLite immutable URI behavior](https://www.sqlite.org/uri.html#recognized_query_parameters)

An absent substrate or bundle is reported as absent. An existing subsystem with no rows is reported as present with zero counts. Remaining budget is absent because the launch supplies it, and claims with no calibration history remain untagged.

## Evidence and limits

`tests/integration/test_status.py` checks a populated closed store and a committed row in a live WAL. Both checks compare the main database bytes and every logical table row before and after status. A tampered bundle control checks `pin_match: false` and invokes the listed `GateBundle.open` refusal against temporary paths.

The tests establish the status contract for temporary Cairn stores. They do not assert preservation of `-wal` or `-shm` bytes, timestamps, or existence, and they do not claim a general filesystem-level immutability guarantee.
