import lldb, os, collections, json
CFG=os.environ['KT_CFG']; OUTF=os.environ['KT_OUT']
toks=open(CFG).read().split('\n')
A=int(toks[0].split()[2]); true=[int(x) for x in toks[-2].split()] if toks[-1]=='' else [int(x) for x in toks[-1].split()]
assert len(true)==A+1,(len(true),A)
tally=collections.Counter()
def cb(frame, bp_loc, d):
  try:
    return cb2(frame,bp_loc,d)
  except Exception as e:
    tally[('ERR',repr(e),0)]+=1
    return False
def cb2(frame, bp_loc, d):
    t=frame.GetThread().GetProcess(); tg=t.GetTarget()
    hdr=tg.GetModuleAtIndex(0).GetObjectFileHeaderAddress().GetLoadAddress(tg)
    slide=hdr-0x100000000
    err=lldb.SBError()
    a=t.ReadUnsignedFromMemory(0x1000185ec+slide,4,err)
    k=frame.FindRegister('x14').GetValueAsSigned() & 0xffffffff
    if k>=1<<31: k-=1<<32
    tally[(a,k,true[a] if a<=A else None)]+=1
    return False
def __lldb_init_module(dbg, d):
    pass
def dump(*a):
    json.dump([[list(k),v] for k,v in tally.items()],open(OUTF,'w'))
def arm(debugger, command, result, internal):
    tg=debugger.GetSelectedTarget()
    hdr=tg.GetModuleAtIndex(0).GetObjectFileHeaderAddress().GetLoadAddress(tg)
    slide=hdr-0x100000000
    bp=tg.BreakpointCreateByAddress(0x100005fe0+slide)
    bp.SetScriptCallbackFunction('tally.cb')
    print('slide',hex(slide),'bp resolved',bp.GetNumResolvedLocations())
def snap(debugger, command, result, internal):
    tg=debugger.GetSelectedTarget(); pr=tg.GetProcess()
    hdr=tg.GetModuleAtIndex(0).GetObjectFileHeaderAddress().GetLoadAddress(tg)
    slide=hdr-0x100000000
    err=lldb.SBError()
    vals=[pr.ReadUnsignedFromMemory(0x100019530+slide+4*i,4,err) for i in range(0,A+8)]
    vals=[v-(1<<32) if v>=1<<31 else v for v in vals]
    SNAPS.append((command,vals))
SNAPS=[]
def snapdump(*a):
    json.dump({'A':A,'true':true,'snaps':SNAPS},open(OUTF,'w'))
def ccrt_cb(frame, bp_loc, d):
    pr=frame.GetThread().GetProcess(); err=lldb.SBError()
    w=[pr.ReadUnsignedFromMemory(0x100019530+0x100+4*i,4,err) for i in range(12)]
    CC.append((hex(frame.GetPC()),w)); return False
CC=[]
def armc(debugger, command, result, internal):
    tg=debugger.GetSelectedTarget()
    for a in (0x100002184,0x1000021c8):
        b=tg.BreakpointCreateByAddress(a); b.SetScriptCallbackFunction('tally.ccrt_cb')
def ccdump(*a): json.dump(CC,open(OUTF,'w'))
