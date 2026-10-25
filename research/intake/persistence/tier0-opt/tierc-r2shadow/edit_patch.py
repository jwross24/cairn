import sys
p = "src/cport_r2.c"
s = open(p).read()

def sub(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)

sub('''*lpf = NULL, *ptf = NULL, *survf = NULL;
    long maxcases = 5000000; int tierc = 0, no480 = 0;''', '''*lpf = NULL, *ptf = NULL, *survf = NULL, *repf = NULL;
    long maxcases = 5000000; int tierc = 0, no480 = 0;''')
sub('''        else if (!strcmp(argv[i], "--tierc")) tierc = 1;
        else if (!strcmp(argv[i], "--no480"))''', '''        else if (!strcmp(argv[i], "--tierc")) tierc = 1;
        else if (!strcmp(argv[i], "--rep-file")) repf = argv[++i];
        else if (!strcmp(argv[i], "--no480"))''')
sub('(!tierc && (!cases || !only))) die(', '(!tierc && !repf && (!cases || !only))) die(')
sub('    g_dedup = tierc;\n', '    g_dedup = tierc || repf;\n')
block = r'''    if (repf) {
        FILE *fr = fopen(repf, "r"); if (!fr) die("cannot open --rep-file");
        char *line = malloc(1 << 16);
        long nrf = 0, ncl = 0;
        while (fgets(line, 1 << 16, fr)) {
            if (line[0] == '\n' || line[0] == '#') continue;
            char *p = line, *tok; char ysb[512]; int nu, n;
            tok = strsep(&p, " \n"); if (!tok || !*tok) die("bad rep line");
            snprintf(ysb, sizeof ysb, "%s", tok);
            tok = strsep(&p, " \n"); nu = tok ? atoi(tok) : -1;
            tok = strsep(&p, " \n"); n = tok ? atoi(tok) : -1;
            if (nu < 0 || n <= 0 || n > 64) die("bad rep line header");
            Rep rep; memset(&rep, 0, sizeof rep); rep.nu = nu; rep.n = n;
            int cd[64], ce[64];
            for (int i = 0; i < n; i++) {
                tok = strsep(&p, " \n"); if (!tok || sscanf(tok, "%d:%d", &cd[i], &ce[i]) != 2) die("bad rep pair");
            }
            for (int i = 1; i < n; i++) { int xd = cd[i], xe = ce[i], j = i - 1; while (j >= 0 && (cd[j] > xd || (cd[j] == xd && ce[j] > xe))) { cd[j + 1] = cd[j]; ce[j + 1] = ce[j]; j--; } cd[j + 1] = xd; ce[j + 1] = xe; }
            for (int i = 0; i < n; i++) { rep.d[i] = cd[i]; rep.e[i] = ce[i]; }
            mpz_t y, Ub; mpz_init_set_str(y, ysb, 10); mpz_init(Ub);
            int a, b, cc;
            if (!factor237(y, &a, &b, &cc)) die("anchor is not 2^a 3^b 7^c");
            nrf++;
            double tl = cpu_s();
            if (!table_has(n, a)) {
                printf("REPFILE y=%s a=%d b=%d c=%d k=%d nu=%d\n", ysb, a, b, cc, n, nu);
                printf("VERDICT NOTAPPL no U'' row for (k=%d, a=%d) [%.0fs]\n", n, a, cpu_s() - tl);
                fflush(stdout); mpz_clears(y, Ub, NULL); continue;
            }
            mpz_set(Ub, *get_U(n, a)); mpz_set(g_Upp, Ub); mpz_set(g_y, y);
            Co co0; co_init(&co0); co_set(&co0, &g_lam);
            mpz_set_si(co0.v0b, b); mpz_set_si(co0.v0c, cc); co_babai(&co0);
            printf("REPFILE y=%s a=%d b=%d c=%d k=%d nu=%d log10 U''=%.4f\n", ysb, a, b, cc, n, nu, mpz_log10d(Ub));
            R480 rr; r480_init(&rr);
            char lab[700]; snprintf(lab, sizeof lab, "repfile %s nu=%d k=%d", ysb, nu, n);
            run_rep480(lab, 0, &rep, &co0, a, maxcases, &rr);
            char bstr[64]; int closes;
            const char *vd = verdict480(&rr, Ub, bstr, &closes);
            ncl += (!strcmp(vd, "CLOSED-cut") || !strcmp(vd, "CLOSED-sandwich"));
            printf("rep0: wrap=%ld words=%d (notappl=%d taubad=%d) T=%d units=%d space=%.4g |G|=%ld shadow=%d compat(word,child)=%ld notshadow_compat=%ld passchain=%ld windows=%ld alive=%ld wordsalive=%ld notshadow_alive=%ld win_budget=%ld\n",
                   rr.wrap, rr.nwords, rr.nonappl, rr.taubad, rr.nT, rr.nun, rr.space, rr.nG, rr.shadow_ok, rr.compat, rr.notshadow_compat, rr.passchain, rr.nwin, rr.alive, rr.wordsalive, rr.notshadow_alive, rr.win_budget);
            if (rr.have_nn) { char *nns = mpz_get_str(NULL, 10, rr.nn); printf("min nn=%.60s... (%zu digits)\n", nns, strlen(nns)); free(nns); }
            printf("VERDICT %s%s%s log10 U''=%.4f [%.0fs]\n", vd, bstr[0] ? " bound 10^(10^" : "", bstr[0] ? bstr : "", mpz_log10d(Ub), cpu_s() - tl);
            fflush(stdout);
            if (ft) fprintf(ft, "%s\t%d\t%d\t%d\t%d\t%d\t%s\t%s\t%ld\n", ysb, a, n, nu, rr.nwords, rr.nonappl, vd, bstr, rr.alive);
            mpz_clears(y, Ub, rr.nn, NULL); co_clear(&co0);
        }
        printf("\n%ld of %ld representations closed [%.0fs]\n", ncl, nrf, cpu_s() - t0);
        free(line); fclose(fr);
        if (ft) fclose(ft);
        if (g_ptdump) fclose(g_ptdump);
        if (g_surv_out) fclose(g_surv_out);
        return 0;
    }
    KeySet ks = load_keys(only);
    FILE *f = fopen(cases, "r"); if (!f) die("cannot open cases");
    Case c;
    while (read_case(f, &c)) {
        if (!key_wanted(&ks, c.s, c.Mstr, c.a, c.y) || seen_before(c.fullkey))'''
sub('''    KeySet ks = load_keys(only);
    FILE *f = fopen(cases, "r"); if (!f) die("cannot open cases");
    Case c;
    while (read_case(f, &c)) {
        if (!key_wanted(&ks, c.s, c.Mstr, c.a, c.y) || seen_before(c.fullkey))''', block) if False else None
idx = s.rfind('    KeySet ks = load_keys(only);\n    FILE *f = fopen(cases, "r"); if (!f) die("cannot open cases");\n    Case c;\n    while (read_case(f, &c)) {\n        if (!key_wanted(&ks, c.s, c.Mstr, c.a, c.y) || seen_before(c.fullkey)) { mpz_clear(c.y); continue; }\n        nall++;')
assert idx > 0
old = '    KeySet ks = load_keys(only);\n    FILE *f = fopen(cases, "r"); if (!f) die("cannot open cases");\n    Case c;\n    while (read_case(f, &c)) {\n        if (!key_wanted(&ks, c.s, c.Mstr, c.a, c.y) || seen_before(c.fullkey))'
newb = block
s = s[:idx] + newb + s[idx + len(old):]
sub('static const mpz_t *get_U(int k, int a) {', 'static int table_has(int k, int a) {\n    for (int i = 0; i < g_nu; i++) if (g_u[i].k == k && g_u[i].a == a) return 1;\n    return 0;\n}\n\nstatic const mpz_t *get_U(int k, int a) {')
open(p, "w").write(s)
