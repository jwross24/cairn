#define _POSIX_C_SOURCE 200809L
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

typedef uint64_t u64;
typedef unsigned __int128 u128;

static const u64 p = UINT64_C(866004983247663323);
static const u64 a_coeff = UINT64_C(645824996691681933);
static const u64 gx = UINT64_C(258236120896152398);
static const u64 gy = UINT64_C(475063108841005863);
static const u64 max_ops = UINT64_C(1000000);
static volatile u64 group_calls;

typedef struct {
    u64 x;
    u64 y;
    int inf;
} point;

static u64 mulmod(u64 x, u64 y) {
    return (u64)(((u128)x * (u128)y) % (u128)p);
}

static u64 addmod(u64 x, u64 y) {
    u64 sum = x + y;
    return sum >= p ? sum - p : sum;
}

static u64 submod(u64 x, u64 y) {
    return x >= y ? x - y : x + p - y;
}

static u64 invmod(u64 x) {
    int64_t t = 0;
    int64_t new_t = 1;
    int64_t r = (int64_t)p;
    int64_t new_r = (int64_t)x;
    while (new_r != 0) {
        int64_t q = r / new_r;
        int64_t next_t = t - q * new_t;
        int64_t next_r = r - q * new_r;
        t = new_t;
        new_t = next_t;
        r = new_r;
        new_r = next_r;
    }
    if (r != 1) {
        return 0;
    }
    if (t < 0) {
        t += (int64_t)p;
    }
    return (u64)t;
}

static point ec_double_impl(point v) {
    point out = {0, 0, 0};
    if (v.inf || v.y == 0) {
        out.inf = 1;
        return out;
    }
    u64 num = addmod(mulmod(3, mulmod(v.x, v.x)), a_coeff);
    u64 lam = mulmod(num, invmod(addmod(v.y, v.y)));
    u64 x3 = submod(mulmod(lam, lam), addmod(v.x, v.x));
    out.x = x3;
    out.y = submod(mulmod(lam, submod(v.x, x3)), v.y);
    return out;
}

static point ec_add_impl(point left, point right) {
    if (left.inf) {
        return right;
    }
    if (right.inf) {
        return left;
    }
    if (left.x == right.x) {
        if (addmod(left.y, right.y) == 0) {
            point out = {0, 0, 1};
            return out;
        }
        return ec_double_impl(left);
    }
    u64 lam = mulmod(submod(right.y, left.y), invmod(submod(right.x, left.x)));
    u64 x3 = submod(submod(mulmod(lam, lam), left.x), right.x);
    point out = {x3, submod(mulmod(lam, submod(left.x, x3)), left.y), 0};
    return out;
}

static point counted_double(point value) {
    group_calls += 1;
    return ec_double_impl(value);
}

static point counted_add(point left, point right) {
    group_calls += 1;
    return ec_add_impl(left, right);
}

static int parse_ops(const char *text, u64 *value) {
    if (text[0] == '\0') {
        return 0;
    }
    u64 parsed = 0;
    for (const char *cursor = text; *cursor != '\0'; cursor++) {
        if (*cursor < '0' || *cursor > '9') {
            return 0;
        }
        u64 digit = (u64)(*cursor - '0');
        if (parsed > (max_ops - digit) / 10) {
            return 0;
        }
        parsed = parsed * 10 + digit;
    }
    *value = parsed;
    return 1;
}

static int parse_coordinate(const char **cursor, u64 *value) {
    const char *text = *cursor;
    while (*text == ' ') {
        text++;
    }
    if (*text < '0' || *text > '9') {
        return 0;
    }
    u64 parsed = 0;
    for (; *text >= '0' && *text <= '9'; text++) {
        u64 digit = (u64)(*text - '0');
        if (parsed > (p - 1 - digit) / 10) {
            return 0;
        }
        parsed = parsed * 10 + digit;
    }
    *cursor = text;
    *value = parsed;
    return 1;
}

static int parse_point(const char **cursor, point *value) {
    u64 x = 0;
    u64 y = 0;
    if (!parse_coordinate(cursor, &x) || !parse_coordinate(cursor, &y)) {
        return 0;
    }
    value->x = x;
    value->y = y;
    value->inf = 0;
    return 1;
}

static int line_ends(const char *cursor) {
    while (*cursor == ' ') {
        cursor++;
    }
    return *cursor == '\n' || *cursor == '\0';
}

static int serve_requests(u64 max_requests) {
    char line[128];
    u64 served = 0;
    while (fgets(line, sizeof line, stdin) != NULL) {
        if (strchr(line, '\n') == NULL) {
            fprintf(stderr, "request line must end with a newline\n");
            return 0;
        }
        if (strcmp(line, "q\n") == 0) {
            return 1;
        }
        if (served >= max_requests) {
            fprintf(stderr, "request count exceeds OPS\n");
            return 0;
        }
        const char *cursor = line + 1;
        point out = {0, 0, 0};
        if (line[0] == 'd') {
            point value = {0, 0, 0};
            if (!parse_point(&cursor, &value) || !line_ends(cursor)) {
                fprintf(stderr, "malformed double request\n");
                return 0;
            }
            out = counted_double(value);
        } else if (line[0] == 'a') {
            point left = {0, 0, 0};
            point right = {0, 0, 0};
            if (!parse_point(&cursor, &left) || !parse_point(&cursor, &right) || !line_ends(cursor)) {
                fprintf(stderr, "malformed add request\n");
                return 0;
            }
            out = counted_add(left, right);
        } else {
            fprintf(stderr, "unknown request\n");
            return 0;
        }
        served++;
        if (out.inf) {
            fputs("inf\n", stdout);
        } else {
            printf("%" PRIu64 " %" PRIu64 "\n", out.x, out.y);
        }
        if (fflush(stdout) != 0) {
            return 0;
        }
    }
    fprintf(stderr, "input ended without q\n");
    return 0;
}

static int elapsed_ns(struct timespec start, struct timespec end, u64 *value) {
    int64_t seconds = (int64_t)end.tv_sec - (int64_t)start.tv_sec;
    int64_t nanoseconds = (int64_t)end.tv_nsec - (int64_t)start.tv_nsec;
    if (nanoseconds < 0) {
        seconds -= 1;
        nanoseconds += INT64_C(1000000000);
    }
    if (seconds < 0 || (u64)seconds > (UINT64_MAX - (u64)nanoseconds) / UINT64_C(1000000000)) {
        return 0;
    }
    *value = (u64)seconds * UINT64_C(1000000000) + (u64)nanoseconds;
    return 1;
}

int main(int argc, char **argv) {
    if (argc != 4) {
        fprintf(stderr, "expected MODE OPS timed|untimed\n");
        return 2;
    }

    const char *mode = argv[1];
    int raw = strcmp(mode, "raw") == 0;
    int counted = strcmp(mode, "counted") == 0;
    int count_only = strcmp(mode, "count-only") == 0;
    int zero_work = strcmp(mode, "zero-work") == 0;
    int serve = strcmp(mode, "serve") == 0;
    if (!raw && !counted && !count_only && !zero_work && !serve) {
        fprintf(stderr, "unknown mode\n");
        return 2;
    }

    u64 ops = 0;
    if (!parse_ops(argv[2], &ops)) {
        fprintf(stderr, "OPS must be decimal digits from 0 through 1000000\n");
        return 2;
    }

    int timed = strcmp(argv[3], "timed") == 0;
    if (!timed && strcmp(argv[3], "untimed") != 0) {
        fprintf(stderr, "timing mode must be timed or untimed\n");
        return 2;
    }

    point base = {gx, gy, 0};
    point acc = base;
    u64 count = 0;
    int has_count = !raw;
    u64 child_cpu_ns = 0;
    struct timespec start = {0, 0};
    struct timespec end = {0, 0};

    if (timed && clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &start) != 0) {
        fprintf(stderr, "could not read process CPU clock\n");
        return 1;
    }

    if (raw) {
        for (u64 i = 0; i < ops; i++) {
            acc = i % 2 == 0 ? ec_double_impl(acc) : ec_add_impl(acc, base);
        }
    } else if (counted) {
        for (u64 i = 0; i < ops; i++) {
            acc = i % 2 == 0 ? counted_double(acc) : counted_add(acc, base);
        }
        count = group_calls;
    } else if (count_only) {
        for (u64 i = 0; i < ops; i++) {
            group_calls += 1;
        }
        count = group_calls;
    } else if (serve) {
        if (!serve_requests(ops)) {
            return 2;
        }
        count = group_calls;
    }

    if (timed) {
        if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &end) != 0 || !elapsed_ns(start, end, &child_cpu_ns)) {
            fprintf(stderr, "could not read process CPU duration\n");
            return 1;
        }
    }

    printf("{\"mode\":\"%s\",\"requested_ops\":%" PRIu64 ",\"count\":", mode, ops);
    if (has_count) {
        printf("%" PRIu64, count);
    } else {
        printf("null");
    }
    printf(",\"point\":");
    if (raw || counted) {
        if (acc.inf) {
            printf("null");
        } else {
            printf("[%" PRIu64 ",%" PRIu64 "]", acc.x, acc.y);
        }
    } else {
        printf("null");
    }
    printf(",\"child_cpu_ns\":");
    if (timed) {
        printf("%" PRIu64, child_cpu_ns);
    } else {
        printf("null");
    }
    printf("}\n");
    return ferror(stdout) ? 1 : 0;
}
