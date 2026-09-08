import tempfile
from pathlib import Path

from cairn.substrate import Substrate

tmp = Path(tempfile.mkdtemp())
sub = Substrate.open(tmp / "s.sqlite", role="writer")
try:
    with sub._tx():
        try:
            with sub._tx():
                pass
        except Exception as exc:
            print("NESTED_RAISES:", type(exc).__name__, exc)
        else:
            print("NESTED_RAISES: no")
except Exception as exc:
    print("OUTER:", type(exc).__name__, exc)
finally:
    sub.close()
