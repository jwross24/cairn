import json,sys
ok=True
for v in (72,10800,14336):
    a=json.load(open(f'/private/tmp/persist-gpu/logs/gpu_{v}.json')); b=json.load(open(f'/private/tmp/persist-gpu/ref/ref_{v}.json'))
    for x,y in zip(a,b):
        same=x['eq']==y['eq'] and x['sha']==y['sha'] and x['counters']==y['counters'] and x['rc']==0
        ok&=same
        print(v,x['eq'].split('_')[1].ljust(14),x['nlines'],y['nlines'],x['sha'][:16],y['sha'][:16],'SAME' if same else 'DIFF')
print('ALL SAME' if ok else 'MISMATCH')
