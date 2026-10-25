import subprocess,glob,time
for c in sorted(glob.glob('cfg_*.txt')):
    t0=time.time()
    r=subprocess.run(['nice','-n','10','./lvl12_kr',c,'0','12'],capture_output=True,text=True)
    open(c[:-4]+'.kr','w').write(r.stderr); print(c,round(time.time()-t0,1),flush=True)
