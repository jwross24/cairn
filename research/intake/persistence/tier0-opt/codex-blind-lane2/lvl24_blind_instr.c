#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <limits.h>
#include <math.h>

typedef unsigned long long ull;
typedef long long ll;
typedef unsigned __int128 u128;
typedef __int128 i128;

#define MP 3
#define MQ 40
#define MC 24
#define MF 10
#define ML 8
#define HASHMUL 11400714819323198485ULL
#define EMPTY ULLONG_MAX
#define KLIMIT 400000ULL
#define HALFMAX 30000000ULL
#define MAXSETS 6
#define MAXWINDOW 250000

#ifndef MUTANT_WINDOW_SHIFT
#define MUTANT_WINDOW_SHIFT 0
#endif

#ifndef MUTANT_625_SHIFT
#define MUTANT_625_SHIFT 0
#endif

typedef struct {
    ull n, mask;
    ull *key;
    int *r0, *r1;
} Image;

typedef struct {
    ull qe, cof, crt, mask;
    uint32_t *key, *val;
} Factor;

typedef struct {
    int n, pi[MP], family;
    ull mod[MP], offset[MP];
    i128 crt;
    Image image;
} Component;

typedef struct {
    int pi;
    ll g1, g2;
    ull mod, offset;
    i128 crt;
} Linear;

typedef struct {
    int d, r, m, pos, in_a;
    ull v[MQ + 1][MP];
} Slot;

typedef struct {
    int p0, p1;
    ull n;
    uint32_t *x, *y;
    double acceptance;
} KeySet;

typedef struct {
    int ready;
    ull modulus, lam;
    ull *p3, *p7, *p2;
} WindowTable;

typedef struct {
    ull a, b;
} Candidate;

static int amax, q, digit[MQ], np, nc, nl;
static ull prime[MP], generator[MP];
static ll log2_[MP], log3_[MP], log7_[MP];
static ull power10[MP][24], repunit[MP][24];
static int nf[MP], kt[512];
static Factor factor[MP][MF];
static int *log_table[MP];
static uint32_t *exp_table[MP];
static Component component[MC];
static Linear linear_[ML];
static ll uold[2][2];
static i128 modulus_n;
static int i73, i137, ibig, f625, f16, f9;

static KeySet keyset[MAXSETS];
static int nsets;
static Slot slot[MQ];
static int ns;
static ull na, nb;
static ull *half_a, *half_b;
static ll *head, *next_b;
static ull hash_mask;
static unsigned char *a_flags;
static int selected;

static int pidx, a_cur, nu_parent, nu_cur;
static int parent_eps[MQ], child_eps[MQ], digit_count[10];
static i128 parent_b, parent_c;
static ull parent_target[MP], base[MP];
static ll count_children, count_zero, count_dead;
static ll count_tail_dead, count_open, count_exact;

static WindowTable window_table[5];
static uint64_t window_req[MAXWINDOW];
static unsigned char window_flag[MAXWINDOW];
static int window_n;
static int window_k;

static Candidate batch[4];
static int batch_n;

static void die(const char *s)
{
    fprintf(stderr, "%s\n", s);
    exit(2);
}

static void *allocate(size_t n, size_t width)
{
    if (width && n > SIZE_MAX / width)
        die("allocation size overflow");
    void *p = malloc(n * width);
    if (!p && n)
        die("allocation failed");
    return p;
}

static i128 norm(i128 x, i128 m)
{
    x %= m;
    return x < 0 ? x + m : x;
}

static ull gcd_u(ull a, ull b)
{
    while (b) {
        ull t = a % b;
        a = b;
        b = t;
    }
    return a;
}

static i128 gcd_extended(i128 a, i128 b, i128 *x, i128 *y)
{
    if (!b) {
        *x = 1;
        *y = 0;
        return a;
    }
    i128 xx, yy;
    i128 g = gcd_extended(b, a % b, &xx, &yy);
    *x = yy;
    *y = xx - (a / b) * yy;
    return g;
}

static ull inverse(ull a, ull m)
{
    i128 x, y;
    i128 g = gcd_extended((i128)(a % m), (i128)m, &x, &y);
    if (g < 0) {
        g = -g;
        x = -x;
    }
    if (g != 1)
        die("noninvertible value");
    return (ull)norm(x, (i128)m);
}

static ull multiply(ull a, ull b, ull m)
{
    return (ull)((u128)a * b % m);
}

static ull power(ull b, ull e, ull m)
{
    ull r = 1 % m;
    b %= m;
    while (e) {
        if (e & 1)
            r = multiply(r, b, m);
        e >>= 1;
        if (e)
            b = multiply(b, b, m);
    }
    return r;
}

static ull power_signed(ull b, ll e, ull p)
{
    return power(b, (ull)norm((i128)e, (i128)(p - 1)), p);
}

static i128 product_n(i128 x, i128 y)
{
    return norm(norm(x, modulus_n) * norm(y, modulus_n), modulus_n);
}

static i128 parse_integer(const char *s)
{
    int negative = 0;
    if (*s == '-' || *s == '+') {
        negative = *s == '-';
        s++;
    }
    if (*s < '0' || *s > '9')
        die("invalid integer");
    u128 limit = (((u128)1 << 127) - 1) + (unsigned)negative;
    u128 v = 0;
    while (*s >= '0' && *s <= '9') {
        unsigned d = (unsigned)(*s++ - '0');
        if (v > (limit - d) / 10)
            die("integer exceeds signed 128-bit range");
        v = v * 10 + d;
    }
    if (*s)
        die("invalid integer suffix");
    if (!negative)
        return (i128)v;
    if (!v)
        return 0;
    return -(i128)(v - 1) - 1;
}

static i128 read_integer(FILE *f)
{
    char s[128];
    if (fscanf(f, "%127s", s) != 1)
        die("truncated config");
    return parse_integer(s);
}

static int read_int(FILE *f)
{
    i128 v = read_integer(f);
    if (v < INT_MIN || v > INT_MAX)
        die("config integer out of range");
    return (int)v;
}

static ll read_ll(FILE *f)
{
    i128 v = read_integer(f);
    if (v < LLONG_MIN || v > LLONG_MAX)
        die("config signed value out of range");
    return (ll)v;
}

static ull read_ull(FILE *f)
{
    i128 v = read_integer(f);
    if (v < 0 || (u128)v > ULLONG_MAX)
        die("config unsigned value out of range");
    return (ull)v;
}

static void print_integer(i128 v)
{
    char s[64];
    int n = 0;
    if (v < 0)
        die("negative output coefficient");
    do {
        s[n++] = (char)('0' + v % 10);
        v /= 10;
    } while (v);
    while (n)
        putchar(s[--n]);
}

static ull table_size(ull n)
{
    ull size = 1;
    while (size < n) {
        if (size > ULLONG_MAX / 2)
            die("hash size overflow");
        size *= 2;
    }
    return size;
}

static void image_init(Image *h, ull entries)
{
    h->n = 0;
    h->mask = table_size(2 * entries + 1) - 1;
    h->key = allocate((size_t)(h->mask + 1), sizeof *h->key);
    h->r0 = allocate((size_t)(h->mask + 1), sizeof *h->r0);
    h->r1 = allocate((size_t)(h->mask + 1), sizeof *h->r1);
    for (ull j = 0; j <= h->mask; j++)
        h->key[j] = EMPTY;
}

static void image_insert(Image *h, ull key, int r0, int r1)
{
    ull j = key * HASHMUL & h->mask;
    while (h->key[j] != EMPTY && h->key[j] != key)
        j = (j + 1) & h->mask;
    if (h->key[j] == EMPTY)
        h->n++;
    h->key[j] = key;
    h->r0[j] = r0;
    h->r1[j] = r1;
}

static int image_find(const Image *h, ull key, int *r0, int *r1)
{
    ull j = key * HASHMUL & h->mask;
    while (h->key[j] != EMPTY) {
        if (h->key[j] == key) {
            if (h->r0[j] < 0)
                return 0;
            if (r0)
                *r0 = h->r0[j];
            if (r1)
                *r1 = h->r1[j];
            return 1;
        }
        j = (j + 1) & h->mask;
    }
    return 0;
}

static void factor_init(int pi, int fi, ull qe)
{
    Factor *f = &factor[pi][fi];
    ull p = prime[pi], n = p - 1;
    f->qe = qe;
    f->cof = n / qe;
    f->crt = f->cof * inverse(f->cof % qe, qe) % n;
    f->mask = table_size(2 * qe + 1) - 1;
    f->key = allocate((size_t)(f->mask + 1), sizeof *f->key);
    f->val = allocate((size_t)(f->mask + 1), sizeof *f->val);
    memset(f->key, 0, (size_t)(f->mask + 1) * sizeof *f->key);
    ull step = power(generator[pi], f->cof, p);
    ull x = 1;
    for (ull e = 0; e < qe; e++) {
        ull j = x * HASHMUL & f->mask;
        while (f->key[j]) {
            if (f->key[j] == x)
                die("generator has deficient factor order");
            j = (j + 1) & f->mask;
        }
        f->key[j] = (uint32_t)x;
        f->val[j] = (uint32_t)e;
        x = x * step % p;
    }
    if (x != 1)
        die("invalid factor order");
}

static int factor_index(int pi, ull m)
{
    for (int f = 0; f < nf[pi]; f++)
        if (factor[pi][f].qe == m)
            return f;
    die("unsupported component modulus");
    return -1;
}

static ll factor_element_log(int pi, int fi, ull element)
{
    Factor *f = &factor[pi][fi];
    ull j = element * HASHMUL & f->mask;
    while (f->key[j]) {
        if (f->key[j] == element)
            return (ll)f->val[j];
        j = (j + 1) & f->mask;
    }
    die("factor discrete logarithm failed");
    return -1;
}

static ull log_part(int pi, ull m, const ull y[MP],
                    ll cache[MP][MF])
{
    if (log_table[pi]) {
        int x = log_table[pi][y[pi]];
        if (x < 0)
            die("invalid supplied logarithm");
        return (ull)x % m;
    }
    int fi = factor_index(pi, m);
    if (cache[pi][fi] < 0) {
        ull h = power(y[pi], factor[pi][fi].cof, prime[pi]);
        cache[pi][fi] = factor_element_log(pi, fi, h);
    }
    return (ull)cache[pi][fi];
}

static ull full_log(int pi, const ull y[MP], ll cache[MP][MF])
{
    if (log_table[pi]) {
        int x = log_table[pi][y[pi]];
        if (x < 0)
            die("invalid supplied logarithm");
        return (ull)x;
    }
    ull n = prime[pi] - 1;
    ull x = 0;
    for (int f = 0; f < nf[pi]; f++) {
        ull r = log_part(pi, factor[pi][f].qe, y, cache);
        x = (x + r * factor[pi][f].crt) % n;
    }
    if (power(generator[pi], x, prime[pi]) != y[pi])
        die("full discrete logarithm verification failed");
    return x;
}

static int is_power_of(ull m, ull p)
{
    if (m < p)
        return 0;
    while (m % p == 0)
        m /= p;
    return m == 1;
}

static int component_family(const Component *c)
{
    const int choices[3] = {2, 3, 5};
    for (int k = 0; k < 3; k++) {
        int good = 1;
        for (int j = 0; j < c->n; j++)
            if (!is_power_of(c->mod[j], (ull)choices[k]))
                good = 0;
        if (good)
            return choices[k];
    }
    return 0;
}

static void read_config(const char *path)
{
    FILE *f = fopen(path, "r");
    if (!f)
        die("cannot open config");
    int old = read_int(f), new_ = read_int(f);
    if (old != 12 || new_ != 24)
        die("this executable supports only level 12 -> 24");
    amax = read_int(f);
    q = read_int(f);
    if (amax < 0 || amax >= 512 || q < 0 || q > MQ)
        die("unsupported config dimensions");
    int seen[10] = {0};
    for (int j = 0; j < q; j++) {
        digit[j] = read_int(f);
        if (digit[j] < 2 || digit[j] > 9)
            die("digits must lie in 2..9");
        if (!j || digit[j] != digit[j - 1]) {
            if (seen[digit[j]])
                die("equal digits must form contiguous groups");
            seen[digit[j]] = 1;
        }
        digit_count[digit[j]]++;
    }
    np = read_int(f);
    if (np != MP)
        die("expected three level-24 primes");
    i73 = i137 = ibig = -1;
    for (int i = 0; i < np; i++) {
        prime[i] = read_ull(f);
        log2_[i] = read_ll(f);
        log3_[i] = read_ll(f);
        log7_[i] = read_ll(f);
        generator[i] = read_ull(f);
        nf[i] = read_int(f);
        if (prime[i] == 73 && i73 < 0)
            i73 = i;
        else if (prime[i] == 137 && i137 < 0)
            i137 = i;
        else if (prime[i] == 99990001 && ibig < 0)
            ibig = i;
        else
            die("unexpected or duplicate prime");
        if (generator[i] < 1 || generator[i] >= prime[i] ||
            nf[i] < 1 || nf[i] > MF)
            die("invalid prime data");
        ull qe[MF], product = 1;
        for (int j = 0; j < nf[i]; j++) {
            ull p = read_ull(f);
            int e = read_int(f);
            if (p < 2 || e < 1)
                die("invalid factorization");
            qe[j] = 1;
            for (int k = 0; k < e; k++) {
                if (qe[j] > (prime[i] - 1) / p)
                    die("factorization overflow");
                qe[j] *= p;
            }
            if (qe[j] > 100000 || product > (prime[i] - 1) / qe[j])
                die("unsupported factorization");
            for (int k = 0; k < j; k++)
                if (gcd_u(qe[k], qe[j]) != 1)
                    die("factor powers must be coprime");
            product *= qe[j];
        }
        if (product != prime[i] - 1)
            die("incomplete factorization");
        for (int k = 0; k < 24; k++) {
            power10[i][k] = read_ull(f);
            if (power10[i][k] >= prime[i])
                die("power-of-ten residue out of range");
        }
        for (int k = 0; k < 24; k++) {
            repunit[i][k] = read_ull(f);
            if (repunit[i][k] >= prime[i])
                die("repunit residue out of range");
        }
        int has = read_int(f);
        if (has) {
            log_table[i] = allocate((size_t)prime[i],
                                    sizeof *log_table[i]);
            for (ull j = 0; j < prime[i]; j++)
                log_table[i][j] = read_int(f);
        }
        for (int j = 0; j < nf[i]; j++)
            factor_init(i, j, qe[j]);
        exp_table[i] = allocate((size_t)(prime[i] - 1),
                                sizeof *exp_table[i]);
        ull x = 1;
        for (ull e = 0; e < prime[i] - 1; e++) {
            exp_table[i][e] = (uint32_t)x;
            x = x * generator[i] % prime[i];
        }
        if (x != 1)
            die("generator exponent table failed");
    }
    nc = read_int(f);
    if (nc < 0 || nc > MC)
        die("too many components");
    for (int c = 0; c < nc; c++) {
        Component *v = &component[c];
        v->n = read_int(f);
        if (v->n < 1 || v->n > MP)
            die("invalid component width");
        for (int j = 0; j < v->n; j++) {
            v->pi[j] = read_int(f);
            if (v->pi[j] < 0 || v->pi[j] >= np)
                die("component prime index out of range");
        }
        ull size = 1;
        for (int j = 0; j < v->n; j++) {
            v->mod[j] = read_ull(f);
            if (v->mod[j] < 2 || size > ULLONG_MAX / v->mod[j])
                die("invalid component modulus");
            factor_index(v->pi[j], v->mod[j]);
            size *= v->mod[j];
        }
        v->crt = read_integer(f);
        ull entries = read_ull(f);
        if (entries > size || entries > 10000000)
            die("unsupported image size");
        image_init(&v->image, entries);
        for (ull h = 0; h < entries; h++) {
            ull key = 0;
            for (int j = 0; j < v->n; j++) {
                ull d = read_ull(f);
                if (d >= v->mod[j])
                    die("component key out of range");
                key = key * v->mod[j] + d;
            }
            int r0 = read_int(f), r1 = read_int(f);
            image_insert(&v->image, key, r0, r1);
        }
        v->family = component_family(v);
    }
    modulus_n = read_integer(f);
    if (modulus_n <= 0 || modulus_n >= ((i128)1 << 62))
        die("unsupported CRT modulus");
    nl = read_int(f);
    if (nl < 0 || nl > ML)
        die("too many linear components");
    for (int j = 0; j < nl; j++) {
        Linear *v = &linear_[j];
        v->pi = read_int(f);
        v->mod = read_ull(f);
        v->g1 = read_ll(f);
        v->g2 = read_ll(f);
        v->crt = read_integer(f);
        if (v->pi < 0 || v->pi >= np || v->mod < 2)
            die("invalid linear component");
        factor_index(v->pi, v->mod);
    }
    for (int row = 0; row < 2; row++)
        for (int col = 0; col < 2; col++)
            uold[row][col] = read_ll(f);
    for (int j = 0; j < 4; j++)
        (void)read_ll(f);
    for (int j = 0; j <= amax; j++)
        kt[j] = read_int(f);
    fclose(f);
    f625 = factor_index(ibig, 625);
    f16 = factor_index(ibig, 16);
    f9 = factor_index(ibig, 9);
}

static int build_key_set(int p0, int p1, KeySet *out)
{
    ull mask = table_size(4 * KLIMIT) - 1;
    ull *seen = allocate((size_t)(mask + 1), sizeof *seen);
    for (ull j = 0; j <= mask; j++)
        seen[j] = EMPTY;
    uint32_t *x = allocate((size_t)KLIMIT, sizeof *x);
    uint32_t *y = allocate((size_t)KLIMIT, sizeof *y);
    ull step[2][2];
    for (int row = 0; row < 2; row++) {
        step[row][0] =
            power_signed(3, uold[row][0], prime[p0]) *
            power_signed(7, uold[row][1], prime[p0]) % prime[p0];
        step[row][1] = p1 < 0 ? 0 :
            power_signed(3, uold[row][0], prime[p1]) *
            power_signed(7, uold[row][1], prime[p1]) % prime[p1];
    }
    ull p = p1 < 0 ? 1 : prime[p1];
    x[0] = 1;
    y[0] = p1 < 0 ? 0 : 1;
    ull first = (ull)x[0] * p + y[0];
    seen[first * HASHMUL & mask] = first;
    ull n = 1;
    for (ull h = 0; h < n; h++) {
        for (int row = 0; row < 2; row++) {
            ull xx = (ull)x[h] * step[row][0] % prime[p0];
            ull yy = p1 < 0 ? 0 :
                (ull)y[h] * step[row][1] % prime[p1];
            ull key = xx * p + yy;
            ull j = key * HASHMUL & mask;
            while (seen[j] != EMPTY && seen[j] != key)
                j = (j + 1) & mask;
            if (seen[j] == key)
                continue;
            if (n == KLIMIT) {
                free(seen);
                free(x);
                free(y);
                return 0;
            }
            seen[j] = key;
            x[n] = (uint32_t)xx;
            y[n] = (uint32_t)yy;
            n++;
        }
    }
    free(seen);
    out->p0 = p0;
    out->p1 = p1;
    out->n = n;
    out->x = x;
    out->y = y;
    out->acceptance = (double)n / (double)(prime[p0] - 1);
    if (p1 >= 0)
        out->acceptance /= (double)(prime[p1] - 1);
    return 1;
}

static void setup_key_sets(void)
{
    for (int i = 0; i < np; i++)
        if (build_key_set(i, -1, &keyset[nsets]))
            nsets++;
    for (int i = 0; i < np; i++)
        for (int j = i + 1; j < np; j++)
            if (build_key_set(i, j, &keyset[nsets]))
                nsets++;
    if (!nsets)
        die("no affordable join key set");
}

static void setup_parent(void)
{
    for (int i = 0; i < np; i++) {
        i128 m = (i128)(prime[i] - 1);
        i128 x = norm(
            (i128)a_cur * log2_[i] +
            norm(parent_b, m) * log3_[i] +
            norm(parent_c, m) * log7_[i], m);
        parent_target[i] = exp_table[i][(ull)x];
        for (int c = 0; c < nc; c++)
            for (int j = 0; j < component[c].n; j++)
                if (component[c].pi[j] == i)
                    component[c].offset[j] =
                        (ull)norm(x, (i128)component[c].mod[j]);
        for (int j = 0; j < nl; j++)
            if (linear_[j].pi == i)
                linear_[j].offset =
                    (ull)norm(x, (i128)linear_[j].mod);
    }

    ns = 0;
    int pos = 0;
    for (int start = 0; start < q;) {
        int end = start + 1;
        while (end < q && digit[end] == digit[start])
            end++;
        int rv[MQ], rm[MQ], nr = 0;
        for (int j = start; j < end; j++) {
            int found = -1;
            for (int h = 0; h < nr; h++)
                if (rv[h] == parent_eps[j])
                    found = h;
            if (found < 0) {
                rv[nr] = parent_eps[j];
                rm[nr++] = 1;
            } else {
                rm[found]++;
            }
        }
        for (int j = 0; j < nr; j++) {
            slot[ns].d = digit[start];
            slot[ns].r = rv[j];
            slot[ns].m = rm[j];
            slot[ns].pos = pos;
            pos += rm[j];
            ns++;
        }
        start = end;
    }

    window_k = kt[a_cur];
    if (window_k > 18)
        window_k = 18;
    for (int j = 1; j < ns; j++) {
        int k = j;
        while (k > 0 && slot[k].r < window_k &&
               slot[k - 1].r >= window_k) {
            Slot t = slot[k];
            slot[k] = slot[k - 1];
            slot[k - 1] = t;
            k--;
        }
    }

    for (int s = 0; s < ns; s++) {
        Slot *v = &slot[s];
        for (int i = 0; i < np; i++) {
            ull p = prime[i];
            ull c0 = (ull)(v->d - 1) * power10[i][v->r] % p;
            ull c1 = (ull)(v->d - 1) * power10[i][v->r + 12] % p;
            ull delta = (c1 + p - c0) % p;
            v->v[0][i] = (ull)v->m * c0 % p;
            for (int k = 1; k <= v->m; k++) {
                ull x = v->v[k - 1][i] + delta;
                if (x >= p)
                    x -= p;
                v->v[k][i] = x;
            }
        }
    }
}

static WindowTable *get_window_table(int k)
{
    WindowTable *w = &window_table[k];
    if (w->ready)
        return w;
    w->modulus = 1;
    for (int j = 0; j < k; j++)
        w->modulus *= 10;
    ull l5 = 4;
    for (int j = 1; j < k; j++)
        l5 *= 5;
    ull l2 = k >= 3 ? 1ULL << (k - 2) : 1;
    w->lam = l5 / gcd_u(l5, l2) * l2;
    w->p3 = allocate((size_t)w->lam, sizeof *w->p3);
    w->p7 = allocate((size_t)w->lam, sizeof *w->p7);
    w->p2 = allocate((size_t)(amax + 1), sizeof *w->p2);
    w->p3[0] = w->p7[0] = 1;
    for (ull j = 1; j < w->lam; j++) {
        w->p3[j] = w->p3[j - 1] * 3 % w->modulus;
        w->p7[j] = w->p7[j - 1] * 7 % w->modulus;
    }
    w->p2[0] = 1;
    for (int j = 1; j <= amax; j++)
        w->p2[j] = w->p2[j - 1] * 2 % w->modulus;
    w->ready = 1;
    return w;
}

static int required_slots(const int *dg, int length,
                          int exact, uint64_t *requirements)
{
    int have[10] = {0};
    uint64_t req = 0;
    for (int i = 0; i < length; i++) {
        int d = dg[i];
        if (!d)
            return 0;
        if (d == 1)
            continue;
        if (++have[d] > digit_count[d])
            return 0;
        int found = -1;
        int r = i + MUTANT_WINDOW_SHIFT;
        for (int s = 0; s < ns; s++)
            if (slot[s].d == d && slot[s].r == r)
                found = s;
        if (found < 0)
            return 0;
        req |= UINT64_C(1) << found;
    }
    if (exact)
        for (int d = 2; d <= 9; d++)
            if (have[d] != digit_count[d])
                return 0;
    *requirements = req;
    return 1;
}

static void build_window(void)
{
    window_n = -1;
    if (window_k < 1 || window_k > 4)
        return;
    WindowTable *w = get_window_table(window_k);
    ull row[2][2];
    ull period[2];
    for (int r = 0; r < 2; r++) {
        for (int j = 0; j < 2; j++)
            row[r][j] = (ull)norm((i128)uold[r][j],
                                  (i128)w->lam);
        period[r] = w->lam /
            gcd_u(w->lam, gcd_u(row[r][0], row[r][1]));
    }
    if (period[0] * period[1] > MAXWINDOW)
        die("window class capacity exceeded");

    window_n = 0;
    ull b0 = (ull)norm(parent_b, (i128)w->lam);
    ull c0 = (ull)norm(parent_c, (i128)w->lam);
    for (ull t1 = 0; t1 < period[0]; t1++) {
        for (ull t2 = 0; t2 < period[1]; t2++) {
            ull b = (b0 + t1 * row[0][0] +
                     t2 * row[1][0]) % w->lam;
            ull c = (c0 + t1 * row[0][1] +
                     t2 * row[1][1]) % w->lam;
            ull y = w->p2[a_cur] * w->p3[b] % w->modulus;
            y = y * w->p7[c] % w->modulus;
            int dg[4], length = 0;
            ull x = y;
            for (int j = 0; j < window_k; j++) {
                dg[j] = (int)(x % 10);
                x /= 10;
            }
            for (x = y; x; x /= 10)
                length++;
            uint64_t req = 0;
            unsigned char flags = 0;
            if (required_slots(dg, window_k, 0, &req)) {
                flags = 3;
            } else if (y >= 10 &&
                       required_slots(dg, length, 1, &req)) {
                for (int dn = 0; dn < 2; dn++)
                    if (length % 24 == nu_parent + 12 * dn)
                        flags |= (unsigned char)(1U << dn);
            }
            if (flags) {
                window_req[window_n] = req;
                window_flag[window_n] = flags;
                window_n++;
            }
        }
    }
}

static unsigned char window_pass(uint64_t blocked)
{
    if (window_n < 0)
        return 3;
    unsigned char flags = 0;
    for (int j = 0; j < window_n; j++) {
        if (!(window_req[j] & blocked))
            flags |= window_flag[j];
        if (flags == 3)
            break;
    }
    return flags;
}

static void decode_half(int want_a, ull index, int *ks)
{
    for (int s = 0; s < ns; s++) {
        if (slot[s].in_a != want_a)
            continue;
        ull radix = (ull)slot[s].m + 1;
        ks[s] = (int)(index % radix);
        index /= radix;
    }
}

static void decode_child(const int *ks)
{
    for (int s = 0; s < ns; s++)
        for (int j = 0; j < slot[s].m; j++)
            child_eps[slot[s].pos + j] =
                slot[s].r + (j < ks[s] ? 12 : 0);
}

static ull add_replace(ull value, ull new_, ull old, ull p)
{
    ull x = value + new_ + p - old;
    if (x >= p)
        x -= p;
    if (x >= p)
        x -= p;
    return x;
}

static void fill_half(int want_a, ull *out, ull count,
                      unsigned char *flags)
{
    int ids[MQ], nids = 0, ks[MQ] = {0};
    ull value[MP] = {0};
    for (int s = 0; s < ns; s++) {
        if (slot[s].in_a != want_a)
            continue;
        ids[nids++] = s;
        for (int i = 0; i < np; i++)
            value[i] = (value[i] + slot[s].v[0][i]) % prime[i];
    }
    for (ull t = 0; t < count; t++) {
        for (int i = 0; i < np; i++)
            out[t * MP + i] = value[i];
        if (flags) {
            uint64_t blocked = 0;
            for (int j = 0; j < nids; j++) {
                int s = ids[j];
                if (ks[s] == slot[s].m && slot[s].r < window_k)
                    blocked |= UINT64_C(1) << s;
            }
            flags[t] = window_pass(blocked);
        }
        if (t + 1 == count)
            break;
        for (int j = 0; j < nids; j++) {
            int s = ids[j], old = ks[s];
            int new_ = old == slot[s].m ? 0 : old + 1;
            ks[s] = new_;
            for (int i = 0; i < np; i++)
                value[i] = add_replace(value[i],
                    slot[s].v[new_][i], slot[s].v[old][i], prime[i]);
            if (new_)
                break;
        }
    }
}

static void emit(const char *kind, i128 t1, i128 t2, ull y)
{
    printf("%s %d %d %d", kind, pidx, a_cur, nu_cur);
    for (int j = 0; j < q; j++)
        printf(" %d", child_eps[j]);
    putchar(' ');
    print_integer(t1);
    putchar(' ');
    print_integer(t2);
    if (y)
        printf(" %llu", y);
    putchar('\n');
}

static int tail_digits_ok(const int *dg, int length, int exact,
                          int pattern[10][24])
{
    int have[10] = {0};
    int used[10][24] = {{0}};
    for (int j = 0; j < length; j++) {
        int d = dg[j];
        if (!d)
            return 0;
        if (d == 1)
            continue;
        if (++have[d] > digit_count[d])
            return 0;
        if (++used[d][j % 24] > pattern[d][j % 24])
            return 0;
    }
    if (exact)
        for (int d = 2; d <= 9; d++)
            if (have[d] != digit_count[d])
                return 0;
    return 1;
}

static void tail_test(i128 t1, i128 t2)
{
    int k = window_k;
    if (k < 1) {
        emit("OPEN", t1, t2, 0);
        count_open++;
        return;
    }
    ull m = 1, l5 = 4;
    for (int j = 0; j < k; j++)
        m *= 10;
    for (int j = 1; j < k; j++)
        l5 *= 5;
    ull l2 = k >= 3 ? 1ULL << (k - 2) : 1;
    ull lam = l5 / gcd_u(l5, l2) * l2;
    i128 b = norm(norm(parent_b, (i128)lam) +
                  norm(t1, (i128)lam) *
                      norm((i128)uold[0][0], (i128)lam) +
                  norm(t2, (i128)lam) *
                      norm((i128)uold[1][0], (i128)lam),
                  (i128)lam);
    i128 c = norm(norm(parent_c, (i128)lam) +
                  norm(t1, (i128)lam) *
                      norm((i128)uold[0][1], (i128)lam) +
                  norm(t2, (i128)lam) *
                      norm((i128)uold[1][1], (i128)lam),
                  (i128)lam);
    ull y = multiply(power(2, (ull)a_cur, m),
                     power(3, (ull)b, m), m);
    y = multiply(y, power(7, (ull)c, m), m);
    int dg[18], length = 0;
    ull x = y;
    for (int j = 0; j < k; j++) {
        dg[j] = (int)(x % 10);
        x /= 10;
    }
    for (x = y; x; x /= 10)
        length++;
    int pattern[10][24] = {{0}};
    for (int j = 0; j < q; j++)
        pattern[digit[j]][child_eps[j]]++;
    int exact = y >= 10 && length % 24 == nu_cur % 24 &&
        tail_digits_ok(dg, length, 1, pattern);
    int open = tail_digits_ok(dg, k, 0, pattern);
    if (exact) {
        emit("EXACT", t1, t2, y);
        count_exact++;
    }
    if (open) {
        emit("OPEN", t1, t2, 0);
        count_open++;
    }
    if (!exact && !open)
        count_tail_dead++;
}

static int lookup_component(int c, const ull y[MP],
                            ll cache[MP][MF], int shift625,
                            int *r0, int *r1)
{
    Component *v = &component[c];
    ull key = 0;
    for (int j = 0; j < v->n; j++) {
        ull m = v->mod[j];
        ull lg = log_part(v->pi[j], m, y, cache);
        if (shift625 && v->pi[j] == ibig && m == 625)
            lg = (lg + (ull)shift625) % m;
        ull d = (lg + m - v->offset[j]) % m;
        key = key * m + d;
    }
    return image_find(&v->image, key, r0, r1);
}

static int check_family(int family, const ull y[MP],
                        ll cache[MP][MF], int shift625)
{
    for (int c = 0; c < nc; c++)
        if (component[c].family == family &&
            !lookup_component(c, y, cache, shift625, NULL, NULL))
            return 0;
    return 1;
}

static void finish_candidate(const ull y[MP], ull z,
                             ull ia, ull ib, const int *plain_ks)
{
    ll cache[MP][MF];
    for (int i = 0; i < MP; i++)
        for (int f = 0; f < MF; f++)
            cache[i][f] = -1;

    cache[ibig][f625] = factor_element_log(
        ibig, f625, power(z, 144, prime[ibig]));
    if (!check_family(5, y, cache, MUTANT_625_SHIFT)) {
        count_dead++;
        return;
    }

    cache[ibig][f16] = factor_element_log(
        ibig, f16, power(z, 5625, prime[ibig]));
    if (!check_family(2, y, cache, 0)) {
        count_dead++;
        return;
    }

    cache[ibig][f9] = factor_element_log(
        ibig, f9, power(z, 10000, prime[ibig]));
    if (!check_family(3, y, cache, 0)) {
        count_dead++;
        return;
    }

    i128 t1 = 0, t2 = 0;
    for (int c = 0; c < nc; c++) {
        int r0, r1;
        if (!lookup_component(c, y, cache, 0, &r0, &r1)) {
            count_dead++;
            return;
        }
        t1 = norm(t1 + product_n(component[c].crt, r0), modulus_n);
        t2 = norm(t2 + product_n(component[c].crt, r1), modulus_n);
    }
    for (int j = 0; j < nl; j++) {
        Linear *v = &linear_[j];
        ull lg = log_part(v->pi, v->mod, y, cache);
        i128 key = (i128)((lg + v->mod - v->offset) % v->mod);
        i128 x1, x2;
        i128 g = gcd_extended(v->g1, v->g2, &x1, &x2);
        if (g < 0) {
            g = -g;
            x1 = -x1;
            x2 = -x2;
        }
        ull d = gcd_u((ull)g, v->mod);
        if (key % d) {
            count_dead++;
            return;
        }
        ull mm = v->mod / d;
        ull s = 0;
        if (mm > 1) {
            ull gi = (ull)norm(g / d, (i128)mm);
            s = (ull)(key / d) * inverse(gi, mm) % mm;
        }
        t1 = norm(t1 + product_n(v->crt, x1 * s), modulus_n);
        t2 = norm(t2 + product_n(v->crt, x2 * s), modulus_n);
    }

    for (int i = 0; i < np; i++)
        if (!log_table[i])
            (void)full_log(i, y, cache);

    if (plain_ks) {
        decode_child(plain_ks);
    } else {
        int ks[MQ] = {0};
        decode_half(1, ia, ks);
        decode_half(0, ib, ks);
        decode_child(ks);
    }
    tail_test(t1, t2);
}

static ull bitmap137[3];

static int cheap_accept(const ull y[MP])
{
    for (int i = 0; i < np; i++) {
        if (!y[i]) {
            count_zero++;
            return 0;
        }
    }
    ull r = y[i137];
    if (!(bitmap137[r / 64] & (1ULL << (r % 64)))) {
        count_dead++;
        return 0;
    }
    return 1;
}

static void candidate_residues(ull ia, ull ib, ull y[MP])
{
    for (int i = 0; i < np; i++) {
        ull x = base[i] + half_a[ia * MP + i] +
                half_b[ib * MP + i];
        if (x >= prime[i])
            x -= prime[i];
        if (x >= prime[i])
            x -= prime[i];
        y[i] = x;
    }
}

static long INSTR_hist[5], INSTR_plain;
static void flush_batch(void)
{
    if (!batch_n)
        return;
    INSTR_hist[batch_n]++;
    ull y[4][MP], x[4], z[4];
    ull p = prime[ibig];
    for (int j = 0; j < batch_n; j++) {
        candidate_residues(batch[j].a, batch[j].b, y[j]);
        x[j] = y[j][ibig];
        z[j] = 1;
    }
    ull e = 1111;
    while (e) {
        if (e & 1)
            for (int j = 0; j < batch_n; j++)
                z[j] = z[j] * x[j] % p;
        e >>= 1;
        if (e)
            for (int j = 0; j < batch_n; j++)
                x[j] = x[j] * x[j] % p;
    }
    for (int j = 0; j < batch_n; j++)
        finish_candidate(y[j], z[j], batch[j].a, batch[j].b, NULL);
    batch_n = 0;
}

static void enqueue_candidate(ull ia, ull ib)
{
    ull y[MP];
    candidate_residues(ia, ib, y);
    if (!cheap_accept(y))
        return;
    batch[batch_n].a = ia;
    batch[batch_n].b = ib;
    if (++batch_n == 4)
        flush_batch();
}

static void build_bitmap(void)
{
    memset(bitmap137, 0, sizeof bitmap137);
    KeySet *set = NULL;
    for (int j = 0; j < nsets; j++)
        if (keyset[j].p0 == i137 && keyset[j].p1 < 0)
            set = &keyset[j];
    if (!set)
        die("missing 137 key image");
    for (ull j = 0; j < set->n; j++) {
        ull r = parent_target[i137] * set->x[j] % 137;
        bitmap137[r / 64] |= 1ULL << (r % 64);
    }
}

static void plain_recurse(int s, int *ks, ull acc[MP])
{
    if (s == ns) {
        uint64_t blocked = 0;
        for (int j = 0; j < ns; j++)
            if (ks[j] == slot[j].m && slot[j].r < window_k)
                blocked |= UINT64_C(1) << j;
        int dn = (nu_cur - nu_parent) / 12;
        if (!(window_pass(blocked) & (1U << dn)))
            return;
        ull y[MP];
        for (int i = 0; i < np; i++) {
            y[i] = base[i] + acc[i];
            if (y[i] >= prime[i])
                y[i] -= prime[i];
        }
        if (cheap_accept(y))
            finish_candidate(y, power(y[ibig], 1111, prime[ibig]),
                             0, 0, ks);
        return;
    }
    for (int k = 0; k <= slot[s].m; k++) {
        ull next[MP];
        ks[s] = k;
        for (int i = 0; i < np; i++) {
            next[i] = acc[i] + slot[s].v[k][i];
            if (next[i] >= prime[i])
                next[i] -= prime[i];
        }
        plain_recurse(s + 1, ks, next);
    }
}

static void plain_parent(void)
{
    for (int dn = 0; dn < 2; dn++) {
        nu_cur = nu_parent + 12 * dn;
        for (int i = 0; i < np; i++)
            base[i] = repunit[i][nu_cur];
        int ks[MQ] = {0};
        ull acc[MP] = {0};
        plain_recurse(0, ks, acc);
    }
}

static void key_name(const KeySet *set, char out[64])
{
    if (set->p1 < 0) {
        snprintf(out, 64, "%llu", prime[set->p0]);
    } else {
        ull x = prime[set->p0], y = prime[set->p1];
        if (x > y) {
            ull t = x;
            x = y;
            y = t;
        }
        snprintf(out, 64, "%llu,%llu", x, y);
    }
}

static void choose_key(ull combinations)
{
    double best = HUGE_VAL;
    selected = -1;
    for (int j = 0; j < nsets; j++) {
        double c = (double)combinations;
        double k = (double)keyset[j].n;
        double a = sqrt(c / k);
        if (a < 1)
            a = 1;
        double cost = 20 * a * k +
                      10 * (a + c / a) +
                      40 * c * keyset[j].acceptance;
        if (cost < best) {
            best = cost;
            selected = j;
        }
    }
    const char *forced = getenv("BLIND_FORCE_KEY");
    if (forced && *forced) {
        selected = -1;
        for (int j = 0; j < nsets; j++) {
            char name[64];
            key_name(&keyset[j], name);
            if (!strcmp(name, forced))
                selected = j;
        }
        if (selected < 0)
            die("requested join key set is unavailable");
    }
    if (getenv("INSTR_KEY")) { char nm[64]; key_name(&keyset[selected], nm); fprintf(stderr, "INSTR key %s\n", nm); }
}

static void run_parent(void)
{
    setup_parent();
    build_window();
    ull combinations = 1;
    for (int s = 0; s < ns; s++)
        combinations *= (ull)slot[s].m + 1;
    if (combinations > (ull)(LLONG_MAX - count_children) / 2)
        die("child counter overflow");
    count_children += (ll)(2 * combinations);
    if (!window_n)
        return;

    build_bitmap();
    choose_key(combinations);
    KeySet *set = &keyset[selected];
    double target = sqrt((double)combinations / (double)set->n);
    if (target < 1)
        target = 1;
    na = nb = 1;
    for (int s = 0; s < ns; s++) {
        ull radix = (ull)slot[s].m + 1;
        slot[s].in_a = (double)(na * radix) <= target * 1.5;
        if (slot[s].in_a)
            na *= radix;
        else
            nb *= radix;
    }
    if (na > HALFMAX || nb > HALFMAX) {
        INSTR_plain++;
        plain_parent();
        return;
    }

    half_a = allocate((size_t)na * MP, sizeof *half_a);
    a_flags = allocate((size_t)na, sizeof *a_flags);
    fill_half(1, half_a, na, a_flags);
    unsigned char any = 0;
    for (ull j = 0; j < na; j++)
        any |= a_flags[j];
    if (!any) {
        free(a_flags);
        free(half_a);
        return;
    }

    half_b = allocate((size_t)nb * MP, sizeof *half_b);
    fill_half(0, half_b, nb, NULL);
    hash_mask = table_size(2 * nb) - 1;
    head = allocate((size_t)(hash_mask + 1), sizeof *head);
    next_b = allocate((size_t)nb, sizeof *next_b);
    for (ull j = 0; j <= hash_mask; j++)
        head[j] = -1;
    ull p0 = prime[set->p0];
    ull p1 = set->p1 < 0 ? 1 : prime[set->p1];
    for (ull j = 0; j < nb; j++) {
        ull key = half_b[j * MP + set->p0] * p1;
        if (set->p1 >= 0)
            key += half_b[j * MP + set->p1];
        ull h = key * HASHMUL & hash_mask;
        next_b[j] = head[h];
        head[h] = (ll)j;
    }

    ull *tx = allocate((size_t)set->n, sizeof *tx);
    ull *ty = allocate((size_t)set->n, sizeof *ty);
    for (ull j = 0; j < set->n; j++) {
        tx[j] = parent_target[set->p0] * set->x[j] % p0;
        ty[j] = set->p1 < 0 ? 0 :
            parent_target[set->p1] * set->y[j] % p1;
    }

    for (int dn = 0; dn < 2; dn++) {
        nu_cur = nu_parent + 12 * dn;
        for (int i = 0; i < np; i++)
            base[i] = repunit[i][nu_cur];
        for (ull ia = 0; ia < na; ia++) {
            if (!(a_flags[ia] & (1U << dn)))
                continue;
            for (ull j = 0; j < set->n; j++) {
                ull x = tx[j] + 2 * p0 -
                        base[set->p0] - half_a[ia * MP + set->p0];
                if (x >= p0)
                    x -= p0;
                if (x >= p0)
                    x -= p0;
                ull y = 0;
                if (set->p1 >= 0) {
                    y = ty[j] + 2 * p1 -
                        base[set->p1] - half_a[ia * MP + set->p1];
                    if (y >= p1)
                        y -= p1;
                    if (y >= p1)
                        y -= p1;
                }
                ull key = x * p1 + y;
                ull h = key * HASHMUL & hash_mask;
                for (ll ib = head[h]; ib >= 0; ib = next_b[ib]) {
                    if (half_b[(ull)ib * MP + set->p0] != x)
                        continue;
                    if (set->p1 >= 0 &&
                        half_b[(ull)ib * MP + set->p1] != y)
                        continue;
                    enqueue_candidate(ia, (ull)ib);
                }
            }
        }
        flush_batch();
    }

    free(tx);
    free(ty);
    free(head);
    free(next_b);
    free(half_b);
    free(a_flags);
    free(half_a);
}

static char *next_parent_token(void)
{
    char *s = strtok(NULL, " \t\r\n");
    if (!s)
        die("truncated parent line");
    return s;
}

static int parent_int(const char *s)
{
    i128 x = parse_integer(s);
    if (x < INT_MIN || x > INT_MAX)
        die("parent integer out of range");
    return (int)x;
}

int main(int argc, char **argv)
{
    if (argc != 3) {
        fprintf(stderr, "usage: lvlN cfg parents\n");
        return 1;
    }
    read_config(argv[1]);
    setup_key_sets();
    FILE *f = fopen(argv[2], "r");
    if (!f)
        die("cannot open parents");
    char line[4096];
    while (fgets(line, sizeof line, f)) {
        int a, nu;
        if (sscanf(line, "%d %d", &a, &nu) != 2)
            continue;
        if (!strchr(line, '\n') && !feof(f))
            die("parent line exceeds buffer");
        char *s = strtok(line, " \t\r\n");
        a_cur = parent_int(s);
        nu_parent = parent_int(next_parent_token());
        if (a_cur < 0 || a_cur > amax ||
            nu_parent < 0 || nu_parent >= 12)
            die("parent header out of range");
        for (int j = 0; j < q; j++) {
            parent_eps[j] = parent_int(next_parent_token());
            if (parent_eps[j] < 0 || parent_eps[j] >= 12)
                die("parent residue out of range");
        }
        parent_b = parse_integer(next_parent_token());
        parent_c = parse_integer(next_parent_token());
        run_parent();
        if (pidx == INT_MAX)
            die("parent index overflow");
        pidx++;
    }
    if (ferror(f))
        die("parent read failed");
    fclose(f);
    fprintf(stderr, "INSTR plain_parents %ld\n", INSTR_plain); fprintf(stderr, "INSTR batch1 %ld batch2 %ld batch3 %ld batch4 %ld\n", INSTR_hist[1], INSTR_hist[2], INSTR_hist[3], INSTR_hist[4]);
    fprintf(stderr,
        "parents %d children %lld zero %lld dead %lld "
        "tail-dead %lld open %lld exact %lld\n",
        pidx, count_children, count_zero, count_dead,
        count_tail_dead, count_open, count_exact);
    if (fflush(stdout) == EOF || ferror(stdout))
        die("stdout write failed");
    return 0;
}
