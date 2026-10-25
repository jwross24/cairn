import json,statistics
rows=[json.loads(l) for l in open('gate.jsonl')]
d=[r for r in rows if r['phase']=='diff' and r['level']=='24']
print('diff24 n',len(d),'identical',sum(r['identical'] for r in d),'rc0',sum(r['rc']==[0,0] for r in d))
print('not identical',[(r['eq'],r['A']) for r in d if not r['identical']])
print('count>=1',sum(r['count']>=1 for r in d),'count>=8',sum(r['count']>=8 for r in d))
sp=[r['cpu_ref']/r['cpu_new'] for r in d if r['cpu_new']>0.2]
print('speedup n',len(sp),'median',round(statistics.median(sp),2),'min',round(min(sp),2),'max',round(max(sp),2))
big=[r for r in d if r['cpu_ref']>=5]; print('cpu_ref>=5s n',len(big),'median speedup',round(statistics.median(r['cpu_ref']/r['cpu_new'] for r in big),2) if big else None)
print('total cpu ref',round(sum(r['cpu_ref'] for r in d),1),'new',round(sum(r['cpu_new'] for r in d),1))
for r in d:
    if r['A']>=64: print('A>=64',r['eq'],r['A'],r['identical'],r['lines'],r['sig_ref'],r['sig_new'],r['cpu_ref'],r['cpu_new'])
m=[r for r in rows if r['phase']=='mut']
if m:
    nv=[r for r in m if r['count']>=1]
    print('mut n',len(m),'nonvacuous',len(nv),'m1',sum(r['m1_caught'] for r in nv),'m2',sum(r['m2_caught'] for r in nv))
    print('m1 uncaught',[(r['eq'],r['count']) for r in nv if not r['m1_caught']])
    print('m2 uncaught',[(r['eq'],r['count'],[k for k,v in r['m2_forced'].items() if v]) for r in nv if not r['m2_caught']])
