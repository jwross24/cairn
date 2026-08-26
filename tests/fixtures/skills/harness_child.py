import importlib
import json
import os
import sys

SUBJECT_ENV = "CAIRN_HARNESS_SUBJECT"
MODE_ENV = "CAIRN_HARNESS_MODE"
MODE_SEAM = "seam"
MODE_ENV_DUMP = "env-dump"
SEAM_OFFSET = 2


def _plant_seam(seam):
    module_path, _, attr = seam.rpartition(".")
    module = importlib.import_module(module_path)
    real = getattr(module, attr)

    def planted(*args, **kwargs):
        return real(*args, **kwargs) + SEAM_OFFSET

    setattr(module, attr, planted)


def _dump_environment(stderr):
    stderr.write(
        json.dumps(
            {"environ": dict(os.environ), "argv": list(sys.argv[1:])},
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    stderr.flush()


def main(stderr=None):
    stderr = sys.stderr if stderr is None else stderr
    subject = importlib.import_module(os.environ[SUBJECT_ENV])
    mode = os.environ.get(MODE_ENV, "")
    if mode == MODE_SEAM:
        _plant_seam(subject.SEAM)
    elif mode == MODE_ENV_DUMP:
        _dump_environment(stderr)
    return subject.main()


if __name__ == "__main__":
    sys.exit(main())
