import re, sys, os
py='/private/tmp/persist-cport/py'
os.chdir(py); sys.path.insert(0,py)
import classify_open as C
W='/private/tmp/persist-cport/'
rx=re.compile(r'^s=(\S+)\s+M=(\S+)\s+a=(\d+)\s+y=(\d+)\s+reps=(\d+)\s+cases=(\d+)\s+(.*)$')
orig=[]
for l in open('DEEPCUT-run.txt'):
    if l.startswith('depth'): continue
    m=rx.match(l.strip())
    if m: orig.append(m.groups())
open(W+'only_orig.txt','w').write(''.join(f"{g[0]} {g[1]} {g[2]} {g[3]}\n" for g in orig))
open(W+'ref_orig.tsv','w').write('\n'.join(sorted(f"{g[0]}\t{g[1]}\t{g[2]}\t{g[3]}\t{g[4]}\t{g[5]}\t{'CLOSED' if g[6]=='CLOSED' else 'OPEN'}" for g in orig))+'\n')
want=set(tuple(g[:4]) for g in orig)
seen=set(); allc=[]; origc=[]
for f in ['runall_final.jsonl','trees_c.jsonl','trees_mac.jsonl']:
    for (s,M,a,nu,eps,y,sol) in C.entries(f):
        key=(s,M,a,y)
        if key in seen: continue
        seen.add(key)
        Ms=''.join(map(str,M))
        line=f"{s} {Ms} {a} {y} - -\n" if nu is None else f"{s} {Ms} {a} {y} {nu} {','.join(map(str,eps))}\n"
        allc.append(line)
        if (str(s),Ms,str(a),str(y)) in want: origc.append(line)
open(W+'cases_all.txt','w').writelines(allc)
open(W+'cases_orig.txt','w').writelines(origc)
open(W+'only_all.txt','w').write(''.join(l.split()[0]+' '+l.split()[1]+' '+l.split()[2]+' '+l.split()[3]+'\n' for l in allc))
print(len(orig),len(origc),len(allc), sum(int(g[4]) for g in orig))
