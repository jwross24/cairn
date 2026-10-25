from math import lgamma, log, log10
def lC(n,k): return (lgamma(n+1)-lgamma(k+1)-lgamma(n-k+1))/log(10)
def lmulti(ms):
    k=sum(ms); return (lgamma(k+1)-sum(lgamma(m+1) for m in ms))/log(10)
def logE(n,ms):
    k=sum(ms)
    return log10(4.1*n*n)+lC(n,k)+lmulti(ms)-(log10(9)+n-1)
for name,ms in [("heavy 2^39 3^3 7^2",[39,3,2]),("k=31 2^23 3^7 7",[23,7,1])]:
    k=sum(ms)
    peak=max(range(k,3000),key=lambda n:logE(n,ms))
    first=[n for n in range(peak,3000) if logE(n,ms)<-3][0]
    tail=lambda n0: log10(sum(10**logE(n,ms) for n in range(n0,3000)))
    print(name,"k=",k,"peak n=",peak,"logE_peak=%.1f"%logE(peak,ms),"E<1e-3 from n=",first,"log10 sum_{n>=300}=%.1f"%tail(300))
