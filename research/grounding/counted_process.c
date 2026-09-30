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

static const u64 mont_p_inv_neg = UINT64_C(3689230223249208493);
static const u64 mont_r2 = UINT64_C(277405704032568442);
static const u64 mont_one = UINT64_C(260639425508621833);

static u64 ct_mask(int condition) {
    return (u64)0 - (u64)(condition != 0);
}

static u64 ct_select(u64 mask, u64 when_set, u64 when_clear) {
    return (when_set & mask) | (when_clear & ~mask);
}

static u64 mont_redc(u128 t) {
    u64 m = (u64)t * mont_p_inv_neg;
    u64 u = (u64)((t + (u128)m * (u128)p) >> 64);
    return ct_select(ct_mask(u >= p), u - p, u);
}

static u64 mont_mul(u64 x, u64 y) {
    return mont_redc((u128)x * (u128)y);
}

static u64 to_mont(u64 x) {
    return mont_mul(x, mont_r2);
}

static u64 from_mont(u64 x) {
    return mont_redc((u128)x);
}

static u64 ct_inv_mont(u64 x) {
    const u64 exponent = p - 2;
    u64 result = mont_one;
    for (int bit = 59; bit >= 0; bit--) {
        result = mont_mul(result, result);
        u64 product = mont_mul(result, x);
        result = ct_select(ct_mask((int)((exponent >> bit) & 1)), product, result);
    }
    return result;
}

static u64 field_inverse_mont(u64 x) {
#ifdef CAIRN_VARIABLE_INVERSION
    return to_mont(invmod(from_mont(x)));
#else
    return ct_inv_mont(x);
#endif
}

static point ct_step(point left, point right) {
    u64 left_inf = ct_mask(left.inf);
    u64 right_inf = ct_mask(right.inf);
    u64 both_finite = ~left_inf & ~right_inf;
    u64 same_x = ct_mask(left.x == right.x);
    u64 same_y = ct_mask(left.y == right.y);
    u64 doubling = both_finite & same_x & same_y;
    u64 inverse = both_finite & same_x & ~same_y;
    u64 torsion = doubling & ct_mask(left.y == 0);
#ifdef CAIRN_EARLY_RETURN
    if (left.inf) {
        return right;
    }
    if (right.inf) {
        return left;
    }
    if (inverse || torsion) {
        point out = {0, 0, 1};
        return out;
    }
#endif
    u64 lx = to_mont(left.x);
    u64 ly = to_mont(left.y);
    u64 rx = to_mont(right.x);
    u64 ry = to_mont(right.y);
    u64 dx = submod(rx, lx);
    u64 dy = submod(ry, ly);
    u64 tangent_num = addmod(mont_mul(to_mont(3), mont_mul(lx, lx)), to_mont(a_coeff));
    u64 tangent_den = addmod(ly, ly);
    u64 den = ct_select(doubling, tangent_den, dx);
    u64 num = ct_select(doubling, tangent_num, dy);
    u64 lam = mont_mul(num, field_inverse_mont(den));
    u64 x3 = submod(submod(mont_mul(lam, lam), lx), rx);
    u64 y3 = submod(mont_mul(lam, submod(lx, x3)), ly);
    u64 out_inf = (left_inf & right_inf) | (both_finite & (inverse | torsion));
    point out;
    out.x = ct_select(left_inf, right.x, ct_select(right_inf, left.x, from_mont(x3)));
    out.y = ct_select(left_inf, right.y, ct_select(right_inf, left.y, from_mont(y3)));
    out.x = ct_select(out_inf, 0, out.x);
    out.y = ct_select(out_inf, 0, out.y);
    out.inf = (int)(out_inf & 1);
    return out;
}

static point counted_double(point value) {
    group_calls += 1;
    return ct_step(value, value);
}

static point counted_add(point left, point right) {
    group_calls += 1;
    return ct_step(left, right);
}

static volatile u64 kind_left_x;
static volatile u64 kind_left_y;
static volatile int kind_left_inf;
static volatile u64 kind_right_x;
static volatile u64 kind_right_y;
static volatile int kind_right_inf;
static volatile u64 kind_sink;
static volatile u64 kind_zero;

static u64 kind_carry(void) {
    return kind_sink & kind_zero;
}

static point kind_left(void) {
    u64 carry = kind_carry();
    point out = {kind_left_x ^ carry, kind_left_y ^ carry, kind_left_inf};
    return out;
}

static point kind_right(void) {
    u64 carry = kind_carry();
    point out = {kind_right_x ^ carry, kind_right_y ^ carry, kind_right_inf};
    return out;
}

static void kind_feed(point value) {
    kind_sink = value.x | value.y | (u64)value.inf;
}

static void set_kind_inputs(point left, point right) {
    kind_left_x = left.x;
    kind_left_y = left.y;
    kind_left_inf = left.inf;
    kind_right_x = right.x;
    kind_right_y = right.y;
    kind_right_inf = right.inf;
}

static int run_kind(const char *kind, u64 ops, point *acc) {
    point base = {gx, gy, 0};
    point negated = {gx, p - gy, 0};
    point infinity = {0, 0, 1};
    point torsion = {gx, 0, 0};
    point adjacent = {gx + 1, gy, 0};
    if (strcmp(kind, "kind-add") == 0) {
        *acc = base;
        for (u64 i = 0; i < ops; i++) {
            *acc = counted_add(*acc, base);
        }
        return 1;
    }
    if (strcmp(kind, "kind-double") == 0) {
        *acc = base;
        for (u64 i = 0; i < ops; i++) {
            *acc = counted_double(*acc);
        }
        return 1;
    }
    if (strcmp(kind, "kind-inverse") == 0) {
        set_kind_inputs(base, negated);
    } else if (strcmp(kind, "kind-identity") == 0) {
        set_kind_inputs(infinity, base);
    } else if (strcmp(kind, "kind-torsion") == 0) {
        set_kind_inputs(torsion, torsion);
    } else if (strcmp(kind, "kind-adjacent") == 0) {
        set_kind_inputs(base, adjacent);
    } else {
        return 0;
    }
    *acc = infinity;
    int doubling = strcmp(kind, "kind-torsion") == 0;
    for (u64 i = 0; i < ops; i++) {
        *acc = doubling ? counted_double(kind_left()) : counted_add(kind_left(), kind_right());
        kind_feed(*acc);
    }
    return 1;
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
    int kind = strncmp(mode, "kind-", 5) == 0;
    if (!raw && !counted && !count_only && !zero_work && !serve && !kind) {
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
    } else if (kind) {
        if (!run_kind(mode, ops, &acc)) {
            fprintf(stderr, "unknown kind\n");
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
    if (raw || counted || kind) {
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
