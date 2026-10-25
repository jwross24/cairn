import sys, glob, os, json
def parse(path):
    tk=open(path).read().split(); i=0
    def nx():
        nonlocal i; v=tk[i]; i+=1; return v
    Lo,Ln,A,q=(int(nx()) for _ in range(4)); i+=q
    np_=int(nx())
    for _ in range(np_):
        p=int(nx()); i+=3; i+=1; nf=int(nx()); i+=2*nf
        i+=2*Ln; has=int(nx())
        if has: i+=p
    nc=int(nx()); comps=[]
    for _ in range(nc):
        cn=int(nx()); idx=[int(nx()) for _ in range(cn)]; mods=[int(nx()) for _ in range(cn)]
        crt=int(nx()); hs=int(nx()); ent=[]
        for _ in range(hs):
            key=[int(nx()) for _ in range(cn)]; r0=int(nx()); r1=int(nx()); ent.append((r0,r1))
        comps.append((crt,ent))
    N=int(nx()); nlin=int(nx()); i+=5*nlin; i+=8
    K=[int(nx()) for _ in range(A+1)]
    assert i==len(tk),(i,len(tk))
    return A,N,comps,K
def corrupt(comps,K,A):
    c=[x[0] for x in comps]
    out=list(c)
    for ci in range(len(c)):
        v=c[ci]&((1<<128)-1)
        for w in range(4):
            idx=64+4*ci+w
            if idx<=A:
                v&=~(0xffffffff<<(32*w)); v|=(K[idx]&0xffffffff)<<(32*w)
        if v>=1<<127: v-=1<<128
        out[ci]=v
    return out
if __name__=='__main__':
    rows=[]
    for p in sorted(glob.glob('cfgs/*.txt')):
        A,N,comps,K=parse(p)
        cc=corrupt(comps,K,A)
        det=[]
        for ci,(crt,ent) in enumerate(comps):
            d=(cc[ci]-crt)%N
            if d==0 and cc[ci]==crt: det.append((ci,0,len(ent))); continue
            bad=sum(1 for r0,r1 in ent if (d*r0)%N or (d*r1)%N)
            det.append((ci,bad,len(ent)))
        print(os.path.basename(p),'A',A,'nc',len(comps),'N bits',N.bit_length(),'comp0 delta==0 mod N:',(cc[0]-comps[0][0])%N==0,'(comp,#entries shifted,#entries):',[d for d in det if d[1]>0 or d[0]==0][:4],flush=True)
