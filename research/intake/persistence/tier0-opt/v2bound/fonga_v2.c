#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define W 4
#define BITS 256

typedef struct { uint64_t w[W]; } u256;

static u256 P10[BITS];
static u256 SP[10][BITS];
static int counts[10];
static int remaining;
static int slack = 0;
static int leading_lo = 1;
static uint64_t nodes = 0;
static uint64_t node_limit = 0;
static int overflow = 0;
static int budget_hit = 0;

static u256 mul_small(u256 x, uint64_t m)
{
    u256 r;
    unsigned __int128 carry = 0;
    for (int i = 0; i < W; i++) {
        unsigned __int128 p = (unsigned __int128)x.w[i] * m + carry;
        r.w[i] = (uint64_t)p;
        carry = p >> 64;
    }
    return r;
}

static inline u256 add(u256 a, u256 b)
{
    u256 r;
    unsigned __int128 carry = 0;
    for (int i = 0; i < W; i++) {
        unsigned __int128 s = (unsigned __int128)a.w[i] + b.w[i] + carry;
        r.w[i] = (uint64_t)s;
        carry = s >> 64;
    }
    return r;
}

static inline int val(const u256 *x)
{
    for (int i = 0; i < W; i++)
        if (x->w[i])
            return 64 * i + __builtin_ctzll(x->w[i]);
    return -1;
}

static int value(int a, u256 T)
{
    if (budget_hit || overflow)
        return 0;
    nodes++;
    if (node_limit && nodes > node_limit) {
        budget_hit = 1;
        return 0;
    }
    int v = val(&T);
    if (v < 0) {
        overflow = 1;
        return 0;
    }
    int top = v + slack;
    if (top >= BITS)
        top = BITS - 1;
    int best = v;
    if (remaining == 0) {
        for (int L = a + leading_lo; L <= top; L++) {
            u256 s = add(T, P10[L]);
            int w = val(&s);
            if (w < 0) {
                overflow = 1;
                return 0;
            }
            if (w > best)
                best = w;
        }
        return best;
    }
    for (int d = 2; d <= 9; d++) {
        if (!counts[d])
            continue;
        counts[d]--;
        remaining--;
        for (int t = a + 1; t <= top; t++) {
            int w = value(t, add(T, SP[d][t]));
            if (w > best)
                best = w;
        }
        counts[d]++;
        remaining++;
    }
    return best;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: fonga_v2 [-s slack] [-l leading_lo] [-n node_limit] digits...\n");
        return 64;
    }
    int i = 1;
    while (i < argc && argv[i][0] == '-' && argv[i][1] && (argv[i][1] < '0' || argv[i][1] > '9')) {
        if (argv[i][1] == 's') slack = atoi(argv[++i]);
        else if (argv[i][1] == 'l') leading_lo = atoi(argv[++i]);
        else if (argv[i][1] == 'n') node_limit = strtoull(argv[++i], 0, 10);
        i++;
    }
    for (; i < argc; i++) {
        int d = atoi(argv[i]);
        if (d < 2 || d > 9) {
            fprintf(stderr, "digit out of range\n");
            return 64;
        }
        counts[d]++;
        remaining++;
    }
    P10[0] = (u256){{1, 0, 0, 0}};
    for (int t = 1; t < BITS; t++)
        P10[t] = mul_small(P10[t - 1], 10);
    for (int d = 2; d <= 9; d++)
        for (int t = 0; t < BITS; t++)
            SP[d][t] = mul_small(P10[t], 9 * (d - 1));
    int best = 0;
    for (int d = 2; d <= 8; d += 2) {
        if (!counts[d])
            continue;
        counts[d]--;
        remaining--;
        u256 T = {{9 * (d - 1) - 1, 0, 0, 0}};
        int w = value(0, T);
        counts[d]++;
        remaining++;
        if (w > best)
            best = w;
    }
    if (overflow) {
        printf("OVERFLOW nodes=%llu\n", (unsigned long long)nodes);
        return 2;
    }
    if (budget_hit) {
        printf("BUDGET nodes=%llu\n", (unsigned long long)nodes);
        return 3;
    }
    printf("%d nodes=%llu\n", best, (unsigned long long)nodes);
    return 0;
}
