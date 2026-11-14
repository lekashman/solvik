"""Check that the font built from source behaves like the finished font it was derived from."""
import sys, uharfbuzz as hb
from fontTools.ttLib import TTFont
TESTS=[("Hamburgefonstiv AVATAR Tomato Type Wave Yoyo, P. r. 7.1 LT Growth plan",{}),("naïve île maître Fï Hî (j Wï kg Kg 1j T7 wf",{}),("0123456789 1/2 3/4 17:42",{"tnum":True}),("0123456789 1/2 3/4",{"frac":True}),("(H-H) [A:B] ¿Qué?",{"case":True}),("Illegal a g 1 0 6 9",{"ss01":True,"ss02":True,"cv11":True,"zero":True}),("q\u0301 x\u0302 W\u0303 e\u0301\u0323 A\u030A\u0301",{}),("Привет Жизнь щука Αθήνα ψυχή",{}),("fi fl ff -> <- 3x4",{"calt":True,"liga":True,"dlig":True})]
def shape(path,text,feats):
    font=hb.Font(hb.Face(hb.Blob.from_file_path(path))); buf=hb.Buffer(); buf.add_str(text); buf.guess_segment_properties(); hb.shape(font,buf,feats)
    return [(font.glyph_to_string(i.codepoint),p.x_advance,p.x_offset,p.y_offset) for i,p in zip(buf.glyph_infos,buf.glyph_positions)]
def run(a,b):
    bad=0; n=0
    for t,fe in TESTS:
        x,y=shape(a,t,fe),shape(b,t,fe); n+=1
        if len(x)!=len(y) or any(p[0]!=q[0] or abs(p[1]-q[1])>1 or abs(p[2]-q[2])>1 or abs(p[3]-q[3])>1 for p,q in zip(x,y)):
            bad+=1; d=[(p,q) for p,q in zip(x,y) if p!=q][:3]; print("  DIFF",t[:30],fe,d)
    fa,fb=TTFont(a),TTFont(b)
    adv=sum(1 for g in fa.getGlyphOrder() if fa["hmtx"][g][0]!=fb["hmtx"][g][0])
    same_order=fa.getGlyphOrder()==fb.getGlyphOrder(); same_cmap=fa.getBestCmap()==fb.getBestCmap()
    return n,bad,adv,same_order,same_cmap
if __name__=="__main__": print(run(sys.argv[1],sys.argv[2]))
