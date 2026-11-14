"""Find every pair of characters that sits closer than a floor (share of the stem), with kerning applied."""
import math, sys, unicodedata, collections
from fontTools.ttLib import TTFont
import numpy as np
import build, spacing, figures
CHARS=[chr(c) for c in list(range(0x21,0x7F))+list(range(0xA1,0x180))+[0x2013,0x2014,0x2018,0x2019,0x201A,0x201C,0x201D,0x201E,0x2022,0x2026,0x2039,0x203A,0x20AC,0x2122]]
JOIN_OK={("f","f"),("f","t"),("t","f"),("t","t")}
def scan(path, inter_path, floor=0.08):
    f=TTFont(path); o=TTFont(inter_path); cm=f.getBestCmap(); T=math.tan(math.radians(-f["post"].italicAngle)); stem=figures.build_stem(o,T)
    chars=[c for c in CHARS if ord(c) in cm]; gl=[cm[ord(c)] for c in chars]
    en=figures._edges(f,sorted(set(gl)),T); pv=build._PV(f["GPOS"].table); hm=f["hmtx"].metrics
    eo=None; out=[]
    for ca,a in zip(chars,gl):
        (yr,xr)=en[a][0]
        if len(yr)==0: continue
        for cb,b in zip(chars,gl):
            (yl,xl)=en[b][1]
            if len(yl)==0: continue
            # cheap reject on same-row gap before the full distance
            d=spacing.clearance(yr,xr,hm[a][0],yl,xl,pv(a,b))
            if d < floor*stem: out.append((round(d),ca+cb,a,b))
    # Inter's value for the flagged pairs only
    if out:
        need=sorted({x[2] for x in out}|{x[3] for x in out}); eo=figures._edges(o,need,T); po=build._PV(o["GPOS"].table); ho=o["hmtx"].metrics
        out=[(d,p,round(spacing.clearance(*eo[a][0],ho[a][0],*eo[b][1],po(a,b)))) for d,p,a,b in out]
    return stem,out
def kind(c):
    k=unicodedata.category(c)
    return "L" if k[0]=="L" else "N" if k[0]=="N" else "P"
if __name__=="__main__":
    for st,src in [x.split("=") for x in sys.argv[1:]]:
        stem,out=scan(f"final2/Solvik-{st}.otf",f"../inter/extras/otf/Inter-{src}.otf")
        by=collections.defaultdict(list)
        for d,p,di in out:
            base=tuple(unicodedata.normalize("NFD",c)[0] for c in p)
            if base in JOIN_OK: by["joined by design"].append((p,d,di)); continue
            by[kind(p[0])+kind(p[1])].append((p,d,di))
        print(st,"stem",round(stem),"floor",round(0.08*stem),"| pairs under the floor:",len(out))
        for k,v in sorted(by.items()):
            worse=[x for x in v if x[1]<x[2]-3]
            print("   %-18s %4d (closer than in Inter: %d)  e.g. %s"%(k,len(v),len(worse)," ".join("%s:%d/%d"%x for x in sorted(v,key=lambda x:x[1])[:14])))
