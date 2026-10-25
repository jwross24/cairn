import re,math,json
rows=[];prev=0
for l in open('/Users/jwross/Documents/cairn/research/intake/persistence/tier0/SANDWICH-run.txt'):
    m=re.search(r's=(\d+)\s+M=(\d+)\s+a=(\d+) y=(\d+)\s+k=(\d+) log10 U=([\d.]+) reps=(\d+) -> (\w+) (.*) \[(\d+)s\]',l)
    if m:
        t=int(m[10]); depths=[int(x) for x in re.findall(r"'CLOSED-(?:sandwich|cut)', (\d+),",m[9])]
        rows.append((int(m[5]),max(depths),max(1,t-prev),int(m[7]))); prev=t
# least squares ln(sec) = a + b k + c D
import itertools
n=len(rows); X=[(1,r[0],r[1]) for r in rows]; y=[math.log(r[2]) for r in rows]
def solve(A,b):
    n=len(A); M=[row[:]+[bb] for row,bb in zip(A,b)]
    for i in range(n):
        p=max(range(i,n),key=lambda r:abs(M[r][i])); M[i],M[p]=M[p],M[i]
        for r in range(n):
            if r!=i:
                f=M[r][i]/M[i][i]; M[r]=[x-f*z for x,z in zip(M[r],M[i])]
    return [M[i][n]/M[i][i] for i in range(n)]
A=[[sum(x[i]*x[j] for x in X) for j in range(3)] for i in range(3)]; b=[sum(x[i]*yy for x,yy in zip(X,y)) for i in range(3)]
co=solve(A,b); res=[yy-sum(c*xx for c,xx in zip(co,x)) for x,yy in zip(X,y)]
print('ln sec = %.3f + %.3f k + %.3f D'%tuple(co),'rmse ln',math.sqrt(sum(r*r for r in res)/n))
json.dump(dict(sandwich_lnsec=co,rmse=math.sqrt(sum(r*r for r in res)/n),n=n,total_s=sum(r[2] for r in rows),
  deepcut=dict(s_per_case=2325/356181,cases_rep_ln_slope=0.40,cases_rep_at_k6=36,reps_per_pat=4.0,pats=679,closed=636)),open('post_fit.json','w'),indent=1)
for k,D in ((8,3),(12,4),(16,6),(20,6),(22,8)): print(k,D,'%.3g s'%math.exp(co[0]+co[1]*k+co[2]*D))
