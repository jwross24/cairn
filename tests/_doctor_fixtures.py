import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent / "doctor_fixtures"


def names():
    return sorted(p.name for p in HERE.iterdir() if p.is_dir() and (p / "__init__.py").is_file())


def load(name):
    module_name = f"doctor_fixture_{name}"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, HERE / name / "__init__.py")
    assert spec is not None and spec.loader is not None, f"no fixture module at {HERE / name}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
