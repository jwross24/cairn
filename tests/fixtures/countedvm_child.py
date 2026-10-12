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
#include <sys/mman.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

int main(int argc, char **argv) {
    const char *kind = argc > 3 ? argv[3] : "file";
    int extra_fd = -1;
    if (strcmp(kind, "read_extra") == 0 || strcmp(kind, "write_extra") == 0 ||
        strcmp(kind, "mmap_file") == 0 || strcmp(kind, "mmap_anon_fd") == 0 ||
        strcmp(kind, "write_stdin") == 0 || strcmp(kind, "read_stdout") == 0) {
        extra_fd = open(argv[1], O_RDWR);
        if (extra_fd < 3) {
            return 8;
        }
    }
    if (strcmp(kind, "write_stdin") == 0 && dup2(extra_fd, 0) != 0) {
        return 8;
    }
    if (strcmp(kind, "read_stdout") == 0 && dup2(extra_fd, 1) != 1) {
        return 8;
    }
    if (argc > 2 && strcmp(argv[2], "contain") == 0 && !contain()) {
        return 9;
    }
    if (strcmp(kind, "fork") == 0) {
        pid_t child = fork();
        if (child == 0) {
            _exit(0);
        }
        if (child > 0 && waitpid(child, NULL, 0) != child) {
            return 8;
        }
        printf("fork=%d\\n", (int)child);
        return child < 0 ? 1 : 0;
    }
    if (strcmp(kind, "exec") == 0) {
        execl("/bin/true", "true", (char *)NULL);
        printf("exec=-1\\n");
        return 1;
    }
    if (strcmp(kind, "socket") == 0) {
        int fd = socket(AF_INET, SOCK_STREAM, 0);
        printf("socket=%d\\n", fd);
        return fd < 0 ? 1 : 0;
    }
    if (strcmp(kind, "read_extra") == 0 || strcmp(kind, "write_extra") == 0 ||
        strcmp(kind, "write_stdin") == 0 || strcmp(kind, "read_stdout") == 0 ||
        strcmp(kind, "read_stdin") == 0) {
        char byte = 'x';
        int writing = strcmp(kind, "write_extra") == 0 || strcmp(kind, "write_stdin") == 0;
        int fd = strcmp(kind, "write_stdin") == 0 || strcmp(kind, "read_stdin") == 0 ? 0 :
            (strcmp(kind, "read_stdout") == 0 ? 1 : extra_fd);
        ssize_t got = writing ? write(fd, &byte, 1) : read(fd, &byte, 1);
        printf("io=%zd\\n", got);
        return got == 1 ? 0 : 1;
    }
    if (strcmp(kind, "write_stdio") == 0) {
        ssize_t out = write(1, "x", 1);
        ssize_t err = write(2, "x", 1);
        printf("stdio=%zd\\n", out + err);
        return out == 1 && err == 1 ? 0 : 1;
    }
#ifdef __linux__
    if (strcmp(kind, "read_high_fd") == 0) {
        char byte;
        long rc = syscall(SYS_read, UINT64_C(0x100000000), &byte, 1);
        printf("read=%ld\\n", rc);
        return rc == 1 ? 0 : 1;
    }
    if (strcmp(kind, "clock") == 0) {
        struct timespec stamp;
        long rc = syscall(SYS_clock_gettime, CLOCK_MONOTONIC, &stamp);
        printf("clock=%ld\\n", rc);
        return rc == 0 ? 0 : 1;
    }
    if (strcmp(kind, "stat") == 0) {
        struct stat st;
        int rc = stat(argv[1], &st);
        printf("stat=%d\\n", rc);
        return rc == 0 ? 0 : 1;
    }
    if (strcmp(kind, "mmap_exec") == 0 || strcmp(kind, "mmap_file") == 0 ||
        strcmp(kind, "mmap_anon") == 0 || strcmp(kind, "mmap_anon_fd") == 0 ||
        strcmp(kind, "mmap_extra_flags") == 0) {
        int prot = PROT_READ | PROT_WRITE | (strcmp(kind, "mmap_exec") == 0 ? PROT_EXEC : 0);
        int file = strcmp(kind, "mmap_file") == 0;
        int flags = MAP_PRIVATE | (file ? 0 : MAP_ANONYMOUS) |
            (strcmp(kind, "mmap_extra_flags") == 0 ? MAP_NORESERVE : 0);
        int fd = file || strcmp(kind, "mmap_anon_fd") == 0 ? extra_fd : -1;
        void *mem = mmap(NULL, 4096, prot, flags, fd, 0);
        printf("mapped=%d\\n", mem != MAP_FAILED);
        if (mem != MAP_FAILED) {
            munmap(mem, 4096);
        }
        return mem == MAP_FAILED ? 1 : 0;
    }
#endif
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
    for name in ("uncontained", "contained"):
        completed = subprocess.run(
            [str(binary), str(secret), "contain" if name == "contained" else "none", request.get("kind", "file")],
            input="x",
            capture_output=True,
            text=True,
            check=False,
            timeout=countedvm.RUN_TIMEOUT_S,
        )
        results[name] = {"rc": completed.returncode, "stdout": completed.stdout}
    return results


def main():
    request = json.loads(sys.stdin.read())
    print(json.dumps(globals()["op_" + request["op"]](request)))


if __name__ == "__main__":
    main()
