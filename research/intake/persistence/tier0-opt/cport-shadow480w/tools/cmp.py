import hashlib, sys
d='/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/'
def rows(p): return open(p).read().split('\n')
def sh(rs): return hashlib.sha256('\n'.join(rs).encode()).hexdigest()
old=[r for r in rows(d+'cport-shadow480/runs/x4_480_1335.tsv') if r]
new=[r for r in rows(d+'cport-shadow480w/runs/x4w_480_1335.tsv') if r]
print(len(old),len(new))
oldc=[r for r in old if r.split('\t')[7]!='NOTAPPL']
keys={r.split('\t')[0] for r in oldc}
newc=[r for r in new if r.split('\t')[0] in keys]
print('closed old',len(oldc),'new filtered',len(newc),sh(oldc)==sh(newc),sh(oldc),sh(newc))
print('order same', [r.split('\t')[0] for r in new if r.split('\t')[0] in keys]==[r.split('\t')[0] for r in oldc])
a=open(d+'cport-shadow480/data/shadow1335.tsv','rb').read(); b=open(d+'cport-shadow480w/runs/reg1335w.tsv','rb').read()
print('shadow384',len(a),len(b),hashlib.sha256(a).hexdigest()==hashlib.sha256(b).hexdigest())
na=[r for r in new if r.split('\t')[0] not in keys]
v={r.split('\t')[0]:r.split('\t') for r in rows(d+'cport-shadow480/data/VERDICTS_1335.tsv') if r}
for r in na:
    f=r.split('\t'); print('NEW',f[0],f[3:],' | old384:',v.get(f[0]))
