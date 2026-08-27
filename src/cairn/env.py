import hashlib
import importlib.metadata
import os
import platform
from pathlib import Path

from cairn import pari


def gp_binary_sha256():
    if not Path(pari.GP_BIN).is_file():
        raise pari.GpMissing(pari.GP_BIN)
    with Path(pari.GP_BIN).open("rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def os_text():
    uname = os.uname()
    mac = platform.mac_ver()[0]
    prefix = f"macOS {mac} " if mac else ""
    return f"{prefix}{uname.sysname} {uname.release} {uname.machine}"


def manifest():
    return {
        "os": os_text(),
        "python": platform.python_version(),
        **pari.pari_versions(),
        "blake3": importlib.metadata.version("blake3"),
        "gp_binary_sha256": gp_binary_sha256(),
    }
