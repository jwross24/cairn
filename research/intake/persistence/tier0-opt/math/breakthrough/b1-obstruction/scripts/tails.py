import sys
caps=(39,3,2)  # twos, threes, sevens
def run(L, caps):
    # states: dict (u, n2,n3,n7) -> count ; u = T_i/2^i
    cur={(0,0,0,0):1}
    res=[]
    for i in range(L):
        nxt={}
        p5=5**i
        for (u,n2,n3,n7),c in cur.items():
            par=u&1
            opts=[]
            if par==1:
                opts.append((1,n2,n3,n7))
                if n3<caps[1]: opts.append((3,n2,n3+1,n7))
                if n7<caps[2]: opts.append((7,n2,n3,n7+1))
            else:
                if n2<caps[0]: opts.append((2,n2+1,n3,n7))
            for d,a,b,e in opts:
                key=((u+d*p5)>>1,a,b,e)
                nxt[key]=nxt.get(key,0)+c
        cur=nxt
        res.append((i+1,sum(cur.values())))
        if len(cur)>3_000_000: print("cap",i+1); break
    return res
for l,c in run(int(sys.argv[1]),caps): 
    if l%10==0 or l<6: print(l,c, "2^l=%.2e"%2.0**l)
