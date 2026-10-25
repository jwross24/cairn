import os, subprocess, sys

src_dir, dst_dir = sys.argv[1], sys.argv[2]
src = open(os.path.join(src_dir, 'cport.c')).read()


def sub(s, a, b):
    assert s.count(a) == 1, (a, s.count(a))
    return s.replace(a, b)


FIXED_NEW = """        for (int i = 0; i < n; i++) { fixed[i] = 0; fixt[i] = -1; }
        for (int i = 0; i < n; i++) if (sv->t[i] >= 0) { fixed[i] = 1; fixt[i] = sv->t[i]; }
        mpz_set(Lbase, RK);
        for (int i = 0; i < n; i++) {
            if (!fixed[i]) continue;
            mpz_set_si(tmp, s->rep.d[i] - 1); mpz_mul(tmp, tmp, P10[s->rep.e[i] + LMAX * fixt[i]]);
            mpz_add(Lbase, Lbase, tmp);
        }
"""
FIXED_OLD = """        for (int i = 0; i < n; i++) { fixed[i] = 0; fixt[i] = -1; }
        for (int i = 0; i < n; i++) {
            signed char best = -1;
            for (int j = 0; j < n; j++)
                if (sv->t[j] >= 0 && s->rep.d[j] == s->rep.d[i] && s->rep.e[j] == s->rep.e[i] && sv->t[j] > best) best = sv->t[j];
            if (best >= 0) { fixed[i] = 1; fixt[i] = best; }
        }
        mpz_set(Lbase, RK);
        {
            int seen_key[MAXIT]; int ns = 0;
            for (int i = 0; i < n; i++) {
                if (!fixed[i]) continue;
                int dupk = 0;
                for (int q = 0; q < ns; q++) {
                    int j = seen_key[q];
                    if (s->rep.d[j] == s->rep.d[i] && s->rep.e[j] == s->rep.e[i]) { dupk = 1; break; }
                }
                if (dupk) continue;
                seen_key[ns++] = i;
                mpz_set_si(tmp, s->rep.d[i] - 1); mpz_mul(tmp, tmp, P10[s->rep.e[i] + LMAX * fixt[i]]);
                mpz_add(Lbase, Lbase, tmp);
            }
        }
"""

ANCHOR_KEY = """static int seen_before(const char *key) {
"""
ANCHOR_KEY_NEW = """static int seen_before(const char *key0) {
    char key[2700]; { int sp = 0, i = 0; for (; key0[i] && sp < 4; i++) { if (key0[i] == ' ') sp++; key[i] = key0[i]; } key[sp == 4 ? i - 1 : i] = 0; }
"""

M5_SLOW = """            if (mpz_fdiv_ui(L, 5) == 0) { g_n5L++; continue; }
"""
M5_SLOW_NEW = """            if (mpz_fdiv_ui(L, 5) == 0) {
                g_n5L++;
                signed char t5b[MAXIT]; memcpy(t5b, sv->t, MAXIT);
                for (int q = 0; q < nf; q++) if (mask >> q & 1) t5b[fr[q]] = (signed char)(D - 1);
                dc_push(s, &sv->co, t5b, MAXIT);
                continue;
            }
"""

mutants = {
    'm1_dict_bookkeeping': [(FIXED_NEW, FIXED_OLD)],
    'm2_anchor_collapse': [(ANCHOR_KEY, ANCHOR_KEY_NEW)],
    'm3_wrap_range': [('kq < 8 * k + 2', 'kq < 10')],
    'm4_5L_passthrough': [(M5_SLOW, M5_SLOW_NEW), ('int fast = (pre.y5 + 1 <= 8) && a < 64 && !g_break_v2;', 'int fast = 0;')],
}
for name, subs in mutants.items():
    s = src
    for a, b in subs:
        s = sub(s, a, b)
    d = os.path.join(dst_dir, name)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'cport.c'), 'w').write(s)
    r = subprocess.run(['nice', '-n', '10', 'clang', '-O2', '-std=gnu11', '-w', '-I/opt/homebrew/include', '-o', os.path.join(d, 'cport'),
                        os.path.join(d, 'cport.c'), '-L/opt/homebrew/lib', '-lgmp', '-lm'], capture_output=True, text=True)
    print(name, 'build rc', r.returncode, r.stderr[-300:])
