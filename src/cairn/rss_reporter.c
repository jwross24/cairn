#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

_Static_assert(F_ADD_SEALS == 1033 && F_GET_SEALS == 1034, "Linux file seal ABI mismatch");
_Static_assert((F_SEAL_WRITE | F_SEAL_GROW | F_SEAL_SHRINK | F_SEAL_SEAL) == 15, "Linux seal mask ABI mismatch");
_Static_assert(SCM_CREDENTIALS == 2 && SO_PASSCRED == 16, "Linux credential ABI mismatch");

static volatile sig_atomic_t canceled;

struct exec_error {
    int stage;
    int error;
};

static void cancel(int sig) {
    (void)sig;
    canceled = 1;
}

static void fail_child(int fd, int stage) {
    struct exec_error error = {stage, errno};
    ssize_t result;
    do { result = write(fd, &error, sizeof(error)); } while (result < 0 && errno == EINTR);
    _exit(127);
}

static void signal_worker(pid_t pid, int sig) {
    if (kill(-pid, sig) < 0) kill(pid, sig);
}

static void kill_worker(pid_t pid) {
    signal_worker(pid, SIGKILL);
}

static int send_packet(int fd, const char *text) {
    size_t length = strlen(text);
    ssize_t result;
    do { result = send(fd, text, length, MSG_NOSIGNAL | MSG_DONTWAIT); } while (result < 0 && errno == EINTR);
    return result == (ssize_t)length;
}

static double monotonic(void) {
    struct timespec value;
    if (clock_gettime(CLOCK_MONOTONIC, &value) < 0) return -1;
    return value.tv_sec + value.tv_nsec / 1000000000.0;
}

int main(int argc, char **argv) {
    if (argc < 4) return 64;
    int fd = atoi(argv[1]);
    close(atoi(argv[2]));
    struct ucred parent;
    socklen_t parent_size = sizeof(parent);
    if (getsockopt(fd, SOL_SOCKET, SO_PEERCRED, &parent, &parent_size) < 0 || parent_size != sizeof(parent)) return 65;
    struct sigaction action = {.sa_handler = cancel};
    if (sigemptyset(&action.sa_mask) < 0 || sigaction(SIGTERM, &action, NULL) < 0 ||
        sigaction(SIGINT, &action, NULL) < 0 || prctl(PR_SET_DUMPABLE, 0L) < 0 ||
        prctl(PR_SET_PDEATHSIG, SIGTERM) < 0 || getppid() != parent.pid ||
        fcntl(fd, F_SETFD, FD_CLOEXEC) < 0) return 65;
    int errors[2];
    if (pipe2(errors, O_CLOEXEC | O_NONBLOCK) < 0) return 66;
    pid_t reporter = getpid();
    pid_t worker = fork();
    if (worker < 0) return 67;
    if (worker == 0) {
        close(errors[0]);
        close(fd);
        action.sa_handler = SIG_DFL;
        if (sigaction(SIGTERM, &action, NULL) < 0 || sigaction(SIGINT, &action, NULL) < 0 ||
            setsid() < 0 || prctl(PR_SET_PDEATHSIG, SIGKILL) < 0 || getppid() != reporter ||
            prctl(PR_SET_NO_NEW_PRIVS, 1L, 0L, 0L, 0L) < 0) fail_child(errors[1], 1);
        execvp(argv[3], argv + 3);
        fail_child(errors[1], 2);
    }
    close(errors[1]);
    char text[256];
    snprintf(text, sizeof(text), "START %ld", (long)worker);
    int failed = !send_packet(fd, text);
    struct exec_error error = {0, 0};
    size_t total = 0;
    int exec_reported = 0;
    struct rusage usage;
    int status = 0;
    int reaped = 0;
    int exited = 0;
    double exited_at = 0;
    while (!reaped) {
        char control[4];
        ssize_t control_size = recv(fd, control, sizeof(control), MSG_DONTWAIT);
        int acknowledged = control_size == 3 && memcmp(control, "ACK", 3) == 0 && exited;
        int term = control_size == 4 && memcmp(control, "TERM", 4) == 0;
        int force = control_size == 4 && memcmp(control, "KILL", 4) == 0;
        if (term) signal_worker(worker, SIGTERM);
        if (force || acknowledged) kill_worker(worker);
        if (canceled || control_size == 0 || (control_size > 0 && !acknowledged && !term && !force) ||
            (control_size < 0 && errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR)) failed = 1;
        if (exited && monotonic() - exited_at > 5.0) failed = 1;
        if (failed) kill_worker(worker);
        if (!exec_reported) {
            ssize_t result = read(errors[0], (char *)&error + total, sizeof(error) - total);
            if (result > 0) total += (size_t)result;
            if (result == 0 || total == sizeof(error)) {
                if (total != 0 && total != sizeof(error)) failed = 1;
                snprintf(text, sizeof(text), "EXEC %d %d", error.stage, error.error);
                if (!failed && !send_packet(fd, text)) failed = 1;
                exec_reported = 1;
            } else if (result < 0 && errno != EAGAIN && errno != EINTR) failed = 1;
        }
        if (!exited) {
            siginfo_t info = {0};
            int result = waitid(P_PID, worker, &info, WEXITED | WNOHANG | WNOWAIT);
            if (result < 0 && errno != EINTR) { failed = 1; break; }
            if (result == 0 && info.si_pid == worker && exec_reported) {
                exited = 1;
                exited_at = monotonic();
                snprintf(text, sizeof(text), "EXIT %ld", (long)worker);
                if (!send_packet(fd, text)) failed = 1;
            }
        }
        if (acknowledged || failed) {
            pid_t result;
            do { result = wait4(worker, &status, 0, &usage); } while (result < 0 && errno == EINTR);
            if (result == worker) reaped = 1;
            else return 68;
        }
        if (!reaped) {
            struct pollfd watch = {.fd = fd, .events = POLLIN | POLLRDHUP};
            if (poll(&watch, 1, 5) < 0 && errno != EINTR) failed = 1;
        }
    }
    close(errors[0]);
    if (!reaped) {
        kill_worker(worker);
        pid_t result;
        do { result = wait4(worker, &status, 0, &usage); } while (result < 0 && errno == EINTR);
        if (result != worker) return 68;
    }
    if (!exec_reported || failed) {
        return 69;
    }
    long long user_us = (long long)usage.ru_utime.tv_sec * 1000000 + usage.ru_utime.tv_usec;
    long long sys_us = (long long)usage.ru_stime.tv_sec * 1000000 + usage.ru_stime.tv_usec;
    snprintf(text, sizeof(text), "FINAL %ld %d %ld %lld %lld", (long)worker, status, usage.ru_maxrss,
             user_us, sys_us);
    return send_packet(fd, text) ? 0 : 70;
}
