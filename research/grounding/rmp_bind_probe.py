"""A gate admission binding refuses every ticket hash a Tier-0 admission could supply.

`BINDING.ticket_hash` is non-empty, so the adapter writes a binding only where the gate selected a
ticket: the alternative is a record asserting an admission under a ticket that was never granted.
"""

from cairn import canon
from cairn.ticketlattice import BINDING

BASE = {
    "attempt_id": "att-1",
    "hypothesis_key": "a" * 64,
    "method_identity": '{"interface_version":"toy/1"}',
    "tier": 0,
    "bundle_hash": "b" * 64,
    "at": "2026-09-08T00:00:00.000000+00:00",
}
CASES = [
    (None, "Tier-0 admission (ticket_hash None)"),
    ("", "empty string"),
    ("c" * 64, "a real ticket hash"),
]

for ticket_hash, label in CASES:
    try:
        canon.encode(BINDING, {**BASE, "ticket_hash": ticket_hash})
        print(f"OK      {label}")
    except Exception as error:
        print(f"REFUSED {label}: {type(error).__name__}: {error}")
