"""Figure kerning pass. Every pair with a figure on either side is compared with Inter's own
clearance for that pair (times the spacing scale); where the new shapes left it more than a few
percent tighter or looser, the pair gets its own kerning value that restores it. In the italics,
pairs with the rebuilt a, e, f are matched to the finished upright instead."""
import math, sys, json, os, numpy as np
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
import build, spacing

BIG = []
CHARS = [chr(c) for c in list(range(0x21, 0x7F)) + list(range(0xA1, 0x100)) + [0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2026, 0x20AC]]

def _edges(font, glyphs, T):
    gs = font.getGlyphSet(); out = {}
    for g in glyphs:
        rec = RecordingPen(); gs[g].draw(rec)
        L, R = spacing.profile([(c["pts"], c["segs"]) for c in build.shear(build.contours(rec.value), -T)])
        out[g] = (spacing.edge(R), spacing.edge(L))
    return out

def tune(path, inter_path, upright_path=None, tol=0.04):
    font = TTFont(path); inter = TTFont(inter_path); cm = font.getBestCmap()
    T = math.tan(math.radians(-font["post"].italicAngle))
    K = build.widths(build_stem(inter, T), *build_o(inter, T))[0]
    glyphs = sorted({cm[ord(c)] for c in CHARS if ord(c) in cm}); digits = [cm[ord(d)] for d in "0123456789"]
    repl = set(json.load(open(path + ".repl"))) if os.path.exists(path + ".repl") else set()
    en, eo = _edges(font, glyphs, T), _edges(inter, glyphs, T)
    pv_n, pv_o = build._PV(font["GPOS"].table), build._PV(inter["GPOS"].table)
    adv_n, adv_o = font["hmtx"].metrics, inter["hmtx"].metrics
    if upright_path:
        up = TTFont(upright_path); eu = _edges(up, glyphs, 0.0); pv_u = build._PV(up["GPOS"].table); adv_u = up["hmtx"].metrics
    idx = build._pair_index(font["GPOS"].table); n = 0; moved = []
    for d in digits:
        for x in glyphs:
            for a, b in ((d, x), (x, d)) if x != d else ((d, d),):
                vn = pv_n(a, b)
                if upright_path and (a in repl or b in repl):
                    ref = spacing.clearance(*eu[a][0], adv_u[a][0], *eu[b][1], pv_u(a, b)); target = ref
                else:
                    ref = spacing.clearance(*eo[a][0], adv_o[a][0], *eo[b][1], pv_o(a, b)); target = None if ref is None else K * ref
                if ref is None or ref > 320 or ref < 12: continue
                f = lambda v: spacing.clearance(*en[a][0], adv_n[a][0], *en[b][1], v)
                cur = f(vn)
                if cur is None or (abs(cur / target - 1) <= tol or abs(cur - target) <= 5): continue
                lo, hi = vn - 40, vn + 40
                if f(hi) - f(lo) < 0.5 * (hi - lo): continue      # the gap is vertical (a figure over an underscore): moving sideways would not fix it
                if f(hi) <= target: nv = hi
                elif f(lo) >= target: nv = lo
                else:
                    for _ in range(12):
                        mid = (lo + hi) / 2
                        if f(mid) < target: lo = mid
                        else: hi = mid
                    nv = (lo + hi) / 2
                nv = int(round(nv))
                if nv != vn:
                    build._set_pair(font, idx, a, b, vn, nv); n += 1; moved.append(nv - vn); BIG.append((abs(nv - vn), a, b, vn, nv))
    font.save(path)
    return n, (float(np.median(np.abs(moved))) if moved else 0.0), (max(map(abs, moved)) if moved else 0)

def build_stem(f, T):
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.transformPen import TransformPen
    gs = f.getGlyphSet(); bp = BoundsPen(gs); gs["l"].draw(TransformPen(bp, (1, 0, -T, 1, 0, 0))); return bp.bounds[2] - bp.bounds[0]
def build_o(f, T):
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.transformPen import TransformPen
    gs = f.getGlyphSet(); bp = BoundsPen(gs); gs["o"].draw(TransformPen(bp, (1, 0, -T, 1, 0, 0))); return bp.bounds[2] - bp.bounds[0], bp.bounds[3] - bp.bounds[1]

if __name__ == "__main__":
    W=[("ExtraLight","ExtraLight"),("Light","Light"),("Regular","Regular"),("DemiBold","SemiBold"),("Bold","Bold"),("ExtraBold","ExtraBold"),("Black","Black")]
    for it in (False, True):
        for w, sw in W:
            style=(w+"Italic" if it else w).replace("RegularItalic","Italic")
            src="../inter/extras/otf/Inter-"+(("Italic" if sw=="Regular" else sw+"Italic") if it else sw)+".otf"
            r = tune(f"out/DraftGrotesk-{style}.otf", src, f"out/DraftGrotesk-{w}.otf" if it else None)
            print("%-16s figure pairs given their own value: %d (median change %.0f units, largest %d)" % (style, *r), sorted(BIG)[-3:], flush=True); BIG.clear()
