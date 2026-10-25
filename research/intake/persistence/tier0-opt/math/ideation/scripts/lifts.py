import json, collections, math
base='/Users/jwross/Documents/cairn/research/intake/persistence/tier0/'
S=collections.defaultdict(lambda:[0,0,0,0])
for f in ['trees_mac.jsonl','trees_c.jsonl','runall_final.jsonl']:
    for l in open(base+f):
        try: r=json.loads(l)
        except Exception: continue
        eqs=r.get('eqs',[])
        if not isinstance(eqs,list): continue
        for e in eqs:
            if not isinstance(e,dict): continue
            lv=e.get('levels')
            if not lv or len(lv)<2: continue
            k=len(e['M'])
            S[k][0]+=e['npat']; S[k][1]+=lv[0][2]; S[k][2]+=lv[1][1]; S[k][3]+=lv[1][2]
xs=[];ys=[]
for k in sorted(S):
    n12,o12,ch,s24=S[k]
    if n12<1e8 or o12==0: continue
    print(f"k={k} N12={n12:.2e} open12/N12={o12/n12:.2e} ch24/open12={ch/o12:.1f} tests_per_pattern(ch24/N12)={ch/n12:.3f} s24/N12={s24/n12:.2e}")
    if k>=8: xs.append(k); ys.append(math.log(ch/n12))
# fit log-linear
n=len(xs); mx=sum(xs)/n; my=sum(ys)/n
b=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sum((x-mx)**2 for x in xs); a=my-b*mx
print("growth per k = x%.2f"%math.exp(b))
for k in (20,25,29,36,44): print(k,"tests/pattern ~ %.3g"%math.exp(a+b*k))
