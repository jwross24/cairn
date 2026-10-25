import re, sys, os
py='/private/tmp/persist-cport/py'
os.chdir(py); sys.path.insert(0,py)
import classify_open as C
rx=re.compile(r'^s=(\S+)\s+M=(\S+)\s+a=(\d+)\s+y=(\d+)\s+reps=(\d+)\s+cases=(\d+)\s+(.*)$')
only=[];surv=[]
for l in open('DEEPCUT-run-0545.txt'):
    m=rx.match(l.strip())
    if not m: continue
    s,M,a,y,reps,cases,v=m.groups()
    only.append((s,M,a,y,reps,cases,v))
    if v!='CLOSED': surv.append((s,M,a,y))
W='/private/tmp/persist-cport/'
open(W+'only.txt','w').write(''.join(f"{s} {M} {a} {y}\n" for s,M,a,y,*_ in only))
open(W+'survivors.txt','w').write(''.join(f"{s} {M} {a} {y}\n" for s,M,a,y in surv))
open(W+'ref_deepcut_0545.tsv','w').write(''.join(f"{s}\t{M}\t{a}\t{y}\t{r}\t{c}\t{'CLOSED' if v=='CLOSED' else 'OPEN'}\n" for s,M,a,y,r,c,v in only))
want=set((s,M,a,y) for s,M,a,y,*_ in only)
seen=set();out=[]
for f in ['runall_final.jsonl','trees_c.jsonl','trees_mac.jsonl']:
    for (s,M,a,nu,eps,y,sol) in C.entries(f):
        key=(s,M,a,y)
        if key in seen: continue
        k2=(str(s),''.join(map(str,M)),str(a),str(y))
        if k2 not in want: continue
        seen.add(key)
        if nu is None: out.append(f"{s} {''.join(map(str,M))} {a} {y} - -\n")
        else: out.append(f"{s} {''.join(map(str,M))} {a} {y} {nu} {','.join(map(str,eps))}\n")
open(W+'cases_0545.txt','w').writelines(out)
print(len(only),len(surv),len(want),len(out), sum(1 for o in out if o.split()[4]=='-'))
