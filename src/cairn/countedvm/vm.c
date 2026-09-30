#define _POSIX_C_SOURCE 200809L
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef uint64_t u64;
typedef int64_t i64;
typedef unsigned __int128 u128;

#define REGISTERS 16
#define TABLES 4
#define MAX_TABLE 1048575
#define MAX_LINES 4096
#define MAX_LABELS 256
#define MAX_LINE 256
#define MAX_INDEX 1048575
#define MAX_HEADER_LINES 16
#define MAX_BUDGET UINT64_C(1000000000000)
#define MAX_FIELD_BITS 62
#define MAX_PARTITION_BITS 20

typedef struct {
    u64 x;
    u64 y;
    int inf;
} point;

typedef struct {
    point p;
    u64 s;
    u64 t;
    int used;
} entry;

typedef struct {
    entry *rows;
    u64 size;
} table;

static u64 p, a_coeff, b_coeff, n;
static point P_in, Q_in;
static u64 budget;
static u64 executed;
static u64 group_ops;
static int result_set;
static u64 result_value;
static int solved;

static point preg[REGISTERS];
static u64 sreg[REGISTERS];
static i64 ireg[REGISTERS];
static table tables[TABLES];

static char *lines[MAX_LINES];
static int line_count;
static char *label_names[MAX_LABELS];
static int label_targets[MAX_LABELS];
static int label_count;

static const char *refusal;

static int refuse(const char *reason) {
    if (refusal == NULL) {
        refusal = reason;
    }
    return 0;
}

static u64 mulmod(u64 x, u64 y) {
    return (u64)(((u128)x * (u128)y) % (u128)p);
}

static u64 addmod(u64 x, u64 y, u64 m) {
    u64 sum = x + y;
    return sum >= m ? sum - m : sum;
}

static u64 submod(u64 x, u64 y, u64 m) {
    return x >= y ? x - y : x + m - y;
}

static int invmod(u64 x, u64 m, u64 *out) {
    i64 t = 0, new_t = 1;
    i64 r = (i64)m, new_r = (i64)x;
    while (new_r != 0) {
        i64 q = r / new_r;
        i64 next_t = t - q * new_t;
        i64 next_r = r - q * new_r;
        t = new_t;
        new_t = next_t;
        r = new_r;
        new_r = next_r;
    }
    if (r != 1) {
        return 0;
    }
    if (t < 0) {
        t += (i64)m;
    }
    *out = (u64)t;
    return 1;
}

static u64 powmod(u64 base, u64 exponent) {
    u64 result = 1;
    base %= p;
    while (exponent) {
        if (exponent & 1) {
            result = mulmod(result, base);
        }
        base = mulmod(base, base);
        exponent >>= 1;
    }
    return result;
}

static int is_probable_prime(void) {
    static const u64 bases[] = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37};
    if (p < 2) {
        return 0;
    }
    for (size_t i = 0; i < sizeof bases / sizeof bases[0]; i++) {
        if (p == bases[i]) {
            return 1;
        }
        if (p % bases[i] == 0) {
            return 0;
        }
    }
    u64 d = p - 1;
    int r = 0;
    while ((d & 1) == 0) {
        d >>= 1;
        r += 1;
    }
    for (size_t i = 0; i < sizeof bases / sizeof bases[0]; i++) {
        u64 x = powmod(bases[i], d);
        if (x == 1 || x == p - 1) {
            continue;
        }
        int witness = 1;
        for (int k = 1; k < r; k++) {
            x = mulmod(x, x);
            if (x == p - 1) {
                witness = 0;
                break;
            }
        }
        if (witness) {
            return 0;
        }
    }
    return 1;
}

static int on_curve(point v) {
    if (v.inf) {
        return v.x == 0 && v.y == 0;
    }
    if (v.x >= p || v.y >= p) {
        return 0;
    }
    u64 lhs = mulmod(v.y, v.y);
    u64 rhs = addmod(addmod(mulmod(mulmod(v.x, v.x), v.x), mulmod(a_coeff, v.x), p), b_coeff, p);
    return lhs == rhs;
}

static int count_group_op(void) {
    if (group_ops == UINT64_MAX) {
        return refuse("counter_overflow");
    }
    group_ops += 1;
    return 1;
}

static point infinity(void) {
    point out = {0, 0, 1};
    return out;
}

static point ec_double_raw(point v) {
    if (v.inf || v.y == 0) {
        return infinity();
    }
    u64 inv;
    if (!invmod(addmod(v.y, v.y, p), p, &inv)) {
        refuse("zero_denominator");
        return infinity();
    }
    u64 num = addmod(mulmod(3, mulmod(v.x, v.x)), a_coeff, p);
    u64 lam = mulmod(num, inv);
    u64 x3 = submod(mulmod(lam, lam), addmod(v.x, v.x, p), p);
    point out = {x3, submod(mulmod(lam, submod(v.x, x3, p)), v.y, p), 0};
    return out;
}

static point ec_add_raw(point l, point r) {
    if (l.inf) {
        return r;
    }
    if (r.inf) {
        return l;
    }
    if (l.x == r.x) {
        if (addmod(l.y, r.y, p) == 0) {
            return infinity();
        }
        return ec_double_raw(l);
    }
    u64 inv;
    if (!invmod(submod(r.x, l.x, p), p, &inv)) {
        refuse("zero_denominator");
        return infinity();
    }
    u64 lam = mulmod(submod(r.y, l.y, p), inv);
    u64 x3 = submod(submod(mulmod(lam, lam), l.x, p), r.x, p);
    point out = {x3, submod(mulmod(lam, submod(l.x, x3, p)), l.y, p), 0};
    return out;
}

static point counted_add(point l, point r) {
    count_group_op();
    return ec_add_raw(l, r);
}

static point counted_double(point v) {
    count_group_op();
    return ec_double_raw(v);
}

static point counted_mul(point base, u64 k) {
    point acc = infinity();
    int started = 0;
    for (int bit = 63; bit >= 0; bit--) {
        if (started) {
            acc = counted_double(acc);
        }
        if ((k >> bit) & 1) {
            acc = started ? counted_add(acc, base) : base;
            started = 1;
        }
        if (refusal != NULL) {
            return infinity();
        }
    }
    return acc;
}

static point negate(point v) {
    if (v.inf) {
        return v;
    }
    point out = {v.x, v.y == 0 ? 0 : p - v.y, 0};
    return out;
}

static int parse_u64(const char *text, u64 limit, u64 *value) {
    if (text == NULL || *text == '\0') {
        return 0;
    }
    u64 parsed = 0;
    for (const char *c = text; *c != '\0'; c++) {
        if (*c < '0' || *c > '9') {
            return 0;
        }
        u64 digit = (u64)(*c - '0');
        if (digit > limit || parsed > (limit - digit) / 10) {
            return 0;
        }
        parsed = parsed * 10 + digit;
    }
    *value = parsed;
    return 1;
}

static int parse_register(const char *text, char kind, int *index) {
    if (text == NULL || text[0] != kind) {
        return 0;
    }
    u64 value;
    if (!parse_u64(text + 1, REGISTERS - 1, &value)) {
        return 0;
    }
    *index = (int)value;
    return 1;
}

static int parse_table(const char *text, int *index) {
    if (text == NULL || text[0] != 't') {
        return 0;
    }
    u64 value;
    if (!parse_u64(text + 1, TABLES - 1, &value)) {
        return 0;
    }
    *index = (int)value;
    return 1;
}

static int find_label(const char *name) {
    for (int i = 0; i < label_count; i++) {
        if (strcmp(label_names[i], name) == 0) {
            return label_targets[i];
        }
    }
    return -1;
}

static int parse_point_line(char *rest, point *out) {
    if (rest == NULL) {
        return 0;
    }
    char *save = NULL;
    char *first = strtok_r(rest, " ", &save);
    if (first == NULL) {
        return 0;
    }
    if (strcmp(first, "inf") == 0) {
        if (strtok_r(NULL, " ", &save) != NULL) {
            return 0;
        }
        *out = infinity();
        return 1;
    }
    char *second = strtok_r(NULL, " ", &save);
    if (second == NULL || strtok_r(NULL, " ", &save) != NULL) {
        return 0;
    }
    u64 x, y;
    if (!parse_u64(first, UINT64_MAX, &x) || !parse_u64(second, UINT64_MAX, &y)) {
        return 0;
    }
    point value = {x, y, 0};
    *out = value;
    return 1;
}

static int read_input(void) {
    char line[MAX_LINE + 2];
    int have_p = 0, have_a = 0, have_b = 0, have_n = 0, have_P = 0, have_Q = 0, have_budget = 0, in_program = 0;
    int have_end = 0;
    int header_lines = 0;
    while (fgets(line, sizeof line, stdin) != NULL) {
        size_t len = strlen(line);
        if (len == 0 || line[len - 1] != '\n') {
            return refuse("line_too_long_or_unterminated");
        }
        line[len - 1] = '\0';
        if (have_end) {
            return refuse("trailing_input");
        }
        if (in_program) {
            if (strcmp(line, "end") == 0) {
                in_program = 0;
                have_end = 1;
                continue;
            }
            if (line_count >= MAX_LINES) {
                return refuse("program_too_long");
            }
            lines[line_count] = strdup(line);
            if (lines[line_count] == NULL) {
                return refuse("out_of_memory");
            }
            line_count += 1;
            continue;
        }
        if (++header_lines > MAX_HEADER_LINES) {
            return refuse("too_many_header_lines");
        }
        char *save = NULL;
        char *copy = strdup(line);
        if (copy == NULL) {
            return refuse("out_of_memory");
        }
        char *key = strtok_r(copy, " ", &save);
        if (key == NULL) {
            free(copy);
            return refuse("empty_header_line");
        }
        char *rest = save == NULL ? copy + strlen(copy) : save;
        if (strcmp(key, "program") == 0) {
            if (have_end || rest[0] != '\0') {
                free(copy);
                return refuse("program_header_malformed");
            }
            in_program = 1;
        } else if (strcmp(key, "P") == 0 || strcmp(key, "Q") == 0) {
            point value;
            if (!parse_point_line(rest, &value)) {
                free(copy);
                return refuse("point_malformed");
            }
            if (key[0] == 'P') {
                P_in = value;
                have_P = 1;
            } else {
                Q_in = value;
                have_Q = 1;
            }
        } else {
            char *value_text = strtok_r(NULL, " ", &save);
            if (value_text == NULL || strtok_r(NULL, " ", &save) != NULL) {
                free(copy);
                return refuse("header_malformed");
            }
            u64 value;
            if (!parse_u64(value_text, UINT64_MAX, &value)) {
                free(copy);
                return refuse("header_not_a_number");
            }
            if (strcmp(key, "p") == 0) {
                p = value;
                have_p = 1;
            } else if (strcmp(key, "a") == 0) {
                a_coeff = value;
                have_a = 1;
            } else if (strcmp(key, "b") == 0) {
                b_coeff = value;
                have_b = 1;
            } else if (strcmp(key, "n") == 0) {
                n = value;
                have_n = 1;
            } else if (strcmp(key, "budget") == 0) {
                budget = value;
                have_budget = 1;
            } else {
                free(copy);
                return refuse("unknown_header");
            }
        }
        free(copy);
    }
    if (in_program || !have_end) {
        return refuse("program_unterminated");
    }
    if (!have_p || !have_a || !have_b || !have_n || !have_P || !have_Q || !have_budget) {
        return refuse("header_incomplete");
    }
    return 1;
}

static int validate_domain(void) {
    if (p < 3 || (p & 1) == 0 || p >> MAX_FIELD_BITS) {
        return refuse("field_not_odd_or_too_wide");
    }
    if (!is_probable_prime()) {
        return refuse("field_not_prime");
    }
    if (a_coeff >= p || b_coeff >= p) {
        return refuse("coefficient_outside_field");
    }
    if (n == 0 || n >> MAX_FIELD_BITS) {
        return refuse("order_out_of_range");
    }
    if (n == p) {
        return refuse("order_equals_field");
    }
    if (budget == 0 || budget > MAX_BUDGET) {
        return refuse("budget_out_of_range");
    }
    u64 four_a3 = mulmod(4, mulmod(mulmod(a_coeff, a_coeff), a_coeff));
    u64 twenty_seven_b2 = mulmod(27, mulmod(b_coeff, b_coeff));
    if (addmod(four_a3, twenty_seven_b2, p) == 0) {
        return refuse("curve_singular");
    }
    if (!on_curve(P_in) || !on_curve(Q_in)) {
        return refuse("point_not_on_curve");
    }
    return 1;
}

static int collect_labels(void) {
    for (int i = 0; i < line_count; i++) {
        size_t len = strlen(lines[i]);
        if (len >= 2 && lines[i][len - 1] == ':' && strchr(lines[i], ' ') == NULL) {
            if (label_count >= MAX_LABELS) {
                return refuse("too_many_labels");
            }
            lines[i][len - 1] = '\0';
            if (find_label(lines[i]) >= 0) {
                return refuse("duplicate_label");
            }
            label_names[label_count] = lines[i];
            label_targets[label_count] = i;
            label_count += 1;
        }
    }
    return 1;
}

static int is_label_line(int i) {
    for (int k = 0; k < label_count; k++) {
        if (label_targets[k] == i) {
            return 1;
        }
    }
    return 0;
}

static int need_index(i64 value, u64 size, u64 *out) {
    if (value < 0 || (u64)value >= size) {
        return refuse("index_out_of_bounds");
    }
    *out = (u64)value;
    return 1;
}

static int tick(void) {
    if (executed >= budget) {
        return refuse("budget_exhausted");
    }
    executed += 1;
    return 1;
}

static int set_index(int reg, i64 value) {
    if (value < 0 || value > MAX_INDEX) {
        return refuse("index_out_of_range");
    }
    ireg[reg] = value;
    return 1;
}

static int execute(void) {
    int pc = 0;
    char *argv[8];
    while (pc < line_count) {
        if (is_label_line(pc)) {
            pc += 1;
            continue;
        }
        if (!tick()) {
            return 0;
        }
        char *copy = strdup(lines[pc]);
        if (copy == NULL) {
            return refuse("out_of_memory");
        }
        char *save = NULL;
        int argc = 0;
        for (char *tok = strtok_r(copy, " ", &save); tok != NULL; tok = strtok_r(NULL, " ", &save)) {
            if (argc >= 8) {
                free(copy);
                return refuse("instruction_too_long");
            }
            argv[argc++] = tok;
        }
        if (argc == 0) {
            free(copy);
            return refuse("empty_instruction");
        }
        const char *op = argv[0];
        int ok = 0;
        int next = pc + 1;
        int d, x, y, z, w;
        u64 value, idx;
        if (solved && strcmp(op, "halt") != 0 && strcmp(op, "result") != 0) {
            free(copy);
            return refuse("solve_not_final");
        }
        if (strcmp(op, "halt") == 0 && argc == 1) {
            free(copy);
            return 1;
        } else if (strcmp(op, "addp") == 0 && argc == 4) {
            if (parse_register(argv[1], 'p', &d) && parse_register(argv[2], 'p', &x) && parse_register(argv[3], 'p', &y)) {
                preg[d] = counted_add(preg[x], preg[y]);
                ok = 1;
            }
        } else if (strcmp(op, "dblp") == 0 && argc == 3) {
            if (parse_register(argv[1], 'p', &d) && parse_register(argv[2], 'p', &x)) {
                preg[d] = counted_double(preg[x]);
                ok = 1;
            }
        } else if (strcmp(op, "negp") == 0 && argc == 3) {
            if (parse_register(argv[1], 'p', &d) && parse_register(argv[2], 'p', &x)) {
                preg[d] = negate(preg[x]);
                ok = 1;
            }
        } else if (strcmp(op, "mulp") == 0 && argc == 4) {
            if (parse_register(argv[1], 'p', &d) && parse_register(argv[2], 'p', &x) && parse_register(argv[3], 's', &y)) {
                preg[d] = counted_mul(preg[x], sreg[y]);
                ok = 1;
            }
        } else if (strcmp(op, "setp") == 0 && argc == 3) {
            if (parse_register(argv[1], 'p', &d)) {
                if (strcmp(argv[2], "P") == 0) {
                    preg[d] = P_in;
                    ok = 1;
                } else if (strcmp(argv[2], "Q") == 0) {
                    preg[d] = Q_in;
                    ok = 1;
                } else if (strcmp(argv[2], "inf") == 0) {
                    preg[d] = infinity();
                    ok = 1;
                }
            }
        } else if (strcmp(op, "eqp") == 0 && argc == 4) {
            if (parse_register(argv[1], 'i', &d) && parse_register(argv[2], 'p', &x) && parse_register(argv[3], 'p', &y)) {
                point l = preg[x], r = preg[y];
                int equal = (l.inf && r.inf) || (!l.inf && !r.inf && l.x == r.x && l.y == r.y);
                ok = set_index(d, equal);
            }
        } else if (strcmp(op, "isinf") == 0 && argc == 3) {
            if (parse_register(argv[1], 'i', &d) && parse_register(argv[2], 'p', &x)) {
                ok = set_index(d, preg[x].inf);
            }
        } else if (strcmp(op, "sadd") == 0 && argc == 4) {
            if (parse_register(argv[1], 's', &d) && parse_register(argv[2], 's', &x) && parse_register(argv[3], 's', &y)) {
                sreg[d] = addmod(sreg[x], sreg[y], n);
                ok = 1;
            }
        } else if (strcmp(op, "ssub") == 0 && argc == 4) {
            if (parse_register(argv[1], 's', &d) && parse_register(argv[2], 's', &x) && parse_register(argv[3], 's', &y)) {
                sreg[d] = submod(sreg[x], sreg[y], n);
                ok = 1;
            }
        } else if (strcmp(op, "sneg") == 0 && argc == 3) {
            if (parse_register(argv[1], 's', &d) && parse_register(argv[2], 's', &x)) {
                sreg[d] = sreg[x] == 0 ? 0 : n - sreg[x];
                ok = 1;
            }
        } else if (strcmp(op, "sset") == 0 && argc == 3) {
            if (parse_register(argv[1], 's', &d) && parse_u64(argv[2], UINT64_MAX, &value)) {
                if (value >= n) {
                    free(copy);
                    return refuse("scalar_out_of_range");
                }
                sreg[d] = value;
                ok = 1;
            }
        } else if (strcmp(op, "seq") == 0 && argc == 4) {
            if (parse_register(argv[1], 'i', &d) && parse_register(argv[2], 's', &x) && parse_register(argv[3], 's', &y)) {
                ok = set_index(d, sreg[x] == sreg[y]);
            }
        } else if (strcmp(op, "iset") == 0 && argc == 3) {
            if (parse_register(argv[1], 'i', &d) && parse_u64(argv[2], MAX_INDEX, &value)) {
                ok = set_index(d, (i64)value);
            }
        } else if ((strcmp(op, "iadd") == 0 || strcmp(op, "isub") == 0) && argc == 4) {
            if (parse_register(argv[1], 'i', &d) && parse_register(argv[2], 'i', &x) && parse_u64(argv[3], MAX_INDEX, &value)) {
                i64 delta = op[1] == 'a' ? (i64)value : -(i64)value;
                ok = set_index(d, ireg[x] + delta);
            }
        } else if ((strcmp(op, "ieq") == 0 || strcmp(op, "ilt") == 0) && argc == 4) {
            if (parse_register(argv[1], 'i', &d) && parse_register(argv[2], 'i', &x) && parse_register(argv[3], 'i', &y)) {
                ok = set_index(d, op[1] == 'e' ? ireg[x] == ireg[y] : ireg[x] < ireg[y]);
            }
        } else if (strcmp(op, "partition") == 0 && argc == 4) {
            if (parse_register(argv[1], 'i', &d) && parse_register(argv[2], 'p', &x) && parse_u64(argv[3], MAX_PARTITION_BITS, &value) && value >= 1) {
                point v = preg[x];
                u64 mask = (UINT64_C(1) << value) - 1;
                ok = set_index(d, v.inf ? 0 : (i64)(v.x & mask));
            }
        } else if (strcmp(op, "table") == 0 && argc == 3) {
            if (parse_table(argv[1], &d) && parse_u64(argv[2], MAX_TABLE, &value) && value >= 1) {
                if (tables[d].rows != NULL) {
                    free(copy);
                    return refuse("table_already_allocated");
                }
                tables[d].rows = calloc((size_t)value, sizeof(entry));
                if (tables[d].rows == NULL) {
                    free(copy);
                    return refuse("out_of_memory");
                }
                tables[d].size = value;
                ok = 1;
            }
        } else if (strcmp(op, "tstore") == 0 && argc == 6) {
            if (parse_table(argv[1], &d) && parse_register(argv[2], 'i', &x) && parse_register(argv[3], 'p', &y) && parse_register(argv[4], 's', &z) && parse_register(argv[5], 's', &w)) {
                if (tables[d].rows == NULL) {
                    free(copy);
                    return refuse("table_unallocated");
                }
                if (!need_index(ireg[x], tables[d].size, &idx)) {
                    free(copy);
                    return 0;
                }
                entry row = {preg[y], sreg[z], sreg[w], 1};
                tables[d].rows[idx] = row;
                ok = 1;
            }
        } else if (strcmp(op, "tload") == 0 && argc == 6) {
            if (parse_register(argv[1], 'p', &d) && parse_register(argv[2], 's', &x) && parse_register(argv[3], 's', &y) && parse_table(argv[4], &z) && parse_register(argv[5], 'i', &w)) {
                if (tables[z].rows == NULL) {
                    free(copy);
                    return refuse("table_unallocated");
                }
                if (!need_index(ireg[w], tables[z].size, &idx)) {
                    free(copy);
                    return 0;
                }
                if (!tables[z].rows[idx].used) {
                    free(copy);
                    return refuse("table_entry_unset");
                }
                preg[d] = tables[z].rows[idx].p;
                sreg[x] = tables[z].rows[idx].s;
                sreg[y] = tables[z].rows[idx].t;
                ok = 1;
            }
        } else if (strcmp(op, "tfind") == 0 && argc == 4) {
            if (parse_register(argv[1], 'i', &d) && parse_table(argv[2], &x) && parse_register(argv[3], 'p', &y)) {
                if (tables[x].rows == NULL) {
                    free(copy);
                    return refuse("table_unallocated");
                }
                i64 found = -1;
                point target = preg[y];
                for (u64 k = 0; k < tables[x].size; k++) {
                    if (executed >= budget) {
                        free(copy);
                        return refuse("budget_exhausted");
                    }
                    executed += 1;
                    entry row = tables[x].rows[k];
                    int both_inf = row.p.inf && target.inf;
                    int same_finite = !row.p.inf && !target.inf && row.p.x == target.x && row.p.y == target.y;
                    if (row.used && (both_inf || same_finite)) {
                        found = (i64)k;
                        break;
                    }
                }
                ok = set_index(d, found < 0 ? 0 : found + 1);
            }
        } else if (strcmp(op, "jmp") == 0 && argc == 2) {
            next = find_label(argv[1]);
            ok = next >= 0;
        } else if ((strcmp(op, "jz") == 0 || strcmp(op, "jnz") == 0) && argc == 3) {
            if (parse_register(argv[1], 'i', &x)) {
                int target = find_label(argv[2]);
                if (target >= 0) {
                    int taken = op[1] == 'z' ? ireg[x] == 0 : ireg[x] != 0;
                    next = taken ? target : pc + 1;
                    ok = 1;
                }
            }
        } else if (strcmp(op, "solve") == 0 && argc == 6) {
            if (parse_register(argv[1], 's', &d) && parse_register(argv[2], 's', &x) && parse_register(argv[3], 's', &y) && parse_register(argv[4], 's', &z) && parse_register(argv[5], 's', &w)) {
                u64 den = submod(sreg[w], sreg[z], n);
                u64 inv;
                if (den == 0 || !invmod(den, n, &inv)) {
                    free(copy);
                    return refuse("zero_denominator");
                }
                sreg[d] = (u64)(((u128)submod(sreg[x], sreg[y], n) * (u128)inv) % (u128)n);
                solved = 1;
                ok = 1;
            }
        } else if (strcmp(op, "result") == 0 && argc == 2) {
            if (parse_register(argv[1], 's', &x)) {
                result_value = sreg[x];
                result_set = 1;
                ok = 1;
            }
        }
        free(copy);
        if (!ok) {
            return refusal != NULL ? 0 : refuse("instruction_malformed");
        }
        if (refusal != NULL) {
            return 0;
        }
        pc = next;
    }
    return refuse("no_halt");
}

int main(void) {
    for (int i = 0; i < REGISTERS; i++) {
        preg[i] = infinity();
    }
    if (!read_input() || !validate_domain() || !collect_labels()) {
        printf("{\"status\":\"REFUSED\",\"reason\":\"%s\"}\n", refusal);
        return 2;
    }
    int finished = execute();
    if (!finished || refusal != NULL) {
        printf("{\"status\":\"REFUSED\",\"reason\":\"%s\",\"count\":%" PRIu64 ",\"executed\":%" PRIu64 "}\n",
               refusal == NULL ? "unfinished" : refusal, group_ops, executed);
        return 3;
    }
    printf("{\"status\":\"OK\",\"count\":%" PRIu64 ",\"executed\":%" PRIu64 ",\"result\":", group_ops, executed);
    if (result_set) {
        printf("%" PRIu64, result_value);
    } else {
        printf("null");
    }
    printf(",\"p0\":");
    if (preg[0].inf) {
        printf("null");
    } else {
        printf("[%" PRIu64 ",%" PRIu64 "]", preg[0].x, preg[0].y);
    }
    printf(",\"i0\":%" PRId64 "}\n", ireg[0]);
    return ferror(stdout) ? 1 : 0;
}
