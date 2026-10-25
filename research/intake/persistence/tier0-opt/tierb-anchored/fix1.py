import re
p = "enum_surv.c"
s = open(p).read()
i = s.index("static void set_target")
j = s.index("    ya = (int)a;")
new = '''static void set_target(const char *ys)
{
    int len = (int)strlen(ys);
    long long a = 0;
    char buf[256];
    strcpy(buf, ys);
    for (;;) {
        int bl = (int)strlen(buf);
        if (((buf[bl - 1] - '0') & 1) || !strcmp(buf, "0")) break;
        int r = 0, on = 0;
        char out[256];
        for (int i = 0; i < bl; i++) {
            int x = r * 10 + (buf[i] - '0');
            int q = x / 2;
            r = x % 2;
            if (on || q) out[on++] = (char)('0' + q);
        }
        out[on] = 0;
        strcpy(buf, on ? out : "0");
        a++;
    }
'''
s = s[:i] + new + s[j:]
s = s.replace('''static void flush_pattern(int upto)
{
    int n = 0;
    for (int e = 0; e < upto; e++)
        for (int t = 0; t < 7; t++)
            for (int j = 0; j < stk[e][t]; j++) { dd_[n] = DD[t]; ee_[n] = e; n++; }
    (void)n;
}

''', '')
s = s.replace('''    static int cnt[MAXM + 1][1];
    (void)cnt;
''', '')
s = s.replace('''    int cnt[NPOS + 1];
    memset(cnt, 0, sizeof cnt);
    ncls = 0;''', '    ncls = 0;')
open(p, "w").write(s)
