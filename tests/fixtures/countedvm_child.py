import dataclasses
import json
import subprocess
import sys
from pathlib import Path

from cairn import countedvm
from cairn.countedvm import Instance, LaunchRefused

PROBE_MAIN = """
#define main vm_main
#include "vm.c"
#undef main
#include <fcntl.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc > 2 && strcmp(argv[2], "contain") == 0 && !contain()) {
        return 9;
    }
    int fd = open(argv[1], O_RDONLY);
    char byte = 0;
    ssize_t got = fd < 0 ? -1 : read(fd, &byte, 1);
    printf("open=%d read=%zd\\n", fd, got);
    return fd >= 0 && got == 1 ? 0 : 1;
}
"""


def _compile(source, binary, *flags):
    completed = subprocess.run(
        [str(countedvm.CC), *flags, "-o", str(binary), str(source)], capture_output=True, text=True, check=False
    )
    assert completed.returncode == 0, completed.stderr


def op_build(request):
    binary = countedvm.build(scratch=request["scratch"])
    return {"binary": str(binary), "digest": countedvm.file_digest(binary)}


def op_mutant(request):
    source = countedvm.SOURCE.read_text()
    assert source.count(request["old"]) == 1
    root = Path(request["scratch"])
    root.mkdir(parents=True, exist_ok=True)
    mutated = root / "vm.c"
    mutated.write_text(source.replace(request["old"], request["new"]))
    binary = root / "vm"
    _compile(mutated, binary, *countedvm.CFLAGS)
    return {"binary": str(binary), "digest": countedvm.file_digest(binary)}


def op_launch(request):
    instance = Instance(*request["instance"][:4], *[None if p is None else tuple(p) for p in request["instance"][4:]])
    try:
        run = countedvm.launch(
            request["binary"],
            request["digest"],
            instance,
            request["program"],
            request["budget"],
            attempt_id=request["attempt_id"],
            scratch_dir=request["scratch"],
            wall_cap_s=request.get("wall_cap_s"),
        )
    except LaunchRefused as refused:
        return {"refused": refused.reason}
    return dataclasses.asdict(run)


def op_probe(request):
    root = Path(request["scratch"])
    root.mkdir(parents=True, exist_ok=True)
    source = root / "probe.c"
    source.write_text(PROBE_MAIN)
    binary = root / "probe"
    _compile(source, binary, "-std=c11", "-Wno-unused-function", f"-I{countedvm.SOURCE.parent}")
    secret = root / "answer.txt"
    secret.write_text("x")
    results = {}
    for name, extra in (("uncontained", []), ("contained", ["contain"])):
        completed = subprocess.run([str(binary), str(secret), *extra], capture_output=True, text=True, check=False)
        results[name] = {"rc": completed.returncode, "stdout": completed.stdout}
    return results


def main():
    request = json.loads(sys.stdin.read())
    print(json.dumps(globals()["op_" + request["op"]](request)))


if __name__ == "__main__":
    main()
