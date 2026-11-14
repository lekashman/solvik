"""Final kerning pass. Every pair of basic Latin and Latin-1 characters (letters, figures,
punctuation) is compared with Inter's own clearance for that pair, times the spacing scale; a
pair that ended up more than a few percent tighter or looser gets its own kerning value that
restores it. In the italics, pairs with the rebuilt a, e, f are matched to the finished upright.
Pairs that touch by design in Inter (ff, ft, doubled dashes) are left joined; the one exception
is T followed by 7, which is given a small gap in the weights where Inter lets them touch."""
import math, sys, json, os, numpy as np
from fontTools.ttLib import TTFont
import build, spacing
from figures import CHARS, _edges, build_stem, build_o

MIN_GAP = {("T", "seven"): 0.08}        # minimum clearance as a share of the stem

def tune(path, inter_path, upright_path=None, tol=0.05):
    font = TTFont(path); inter = TTFont(inter_path); cm = font.getBestCmap()
    T = math.tan(math.radians(-font["post"].italicAngle)); stem = build_stem(inter, T)
    K = build.widths(stem, *build_o(inter, T))[0] - 0.055 * max(0.0, (180 - stem) / 90)
    glyphs = sorted({cm[ord(c)] for c in CHARS if ord(c) in cm})
    repl = set(json.load(open(path + ".repl"))) if os.path.exists(path + ".repl") else set()
    en, eo = _edges(font, glyphs, T), _edges(inter, glyphs, T)
    pv_n, pv_o = build._PV(font["GPOS"].table), build._PV(inter["GPOS"].table)
    adv_n, adv_o = font["hmtx"].metrics, inter["hmtx"].metrics
    if upright_path:
        up = TTFont(upright_path); eu = _edges(up, glyphs, 0.0); pv_u = build._PV(up["GPOS"].table); adv_u = up["hmtx"].metrics
    idx = build._pair_index(font["GPOS"].table); moved = []
    for a in glyphs:
        for b in glyphs:
            vn = pv_n(a, b)
            if upright_path and (a in repl or b in repl):
                ref = spacing.clearance(*eu[a][0], adv_u[a][0], *eu[b][1], pv_u(a, b)); target = ref
            else:
                ref = spacing.clearance(*eo[a][0], adv_o[a][0], *eo[b][1], pv_o(a, b)); target = None if ref is None else K * ref
            if ref is None or ref > 320: continue
            floor = MIN_GAP.get((a, b))
            if floor: target = max(target, floor * stem)
            elif ref < 12: continue                       # joined by design
            f = lambda v: spacing.clearance(*en[a][0], adv_n[a][0], *en[b][1], v)
            cur = f(vn)
            if cur is None or abs(cur - target) <= 5 or (abs(cur / target - 1) <= tol if target > 0 else True): continue
            if floor and cur < target - 2:               # a pair that must not touch: open it until the gap appears
                lo, hi = vn, vn + 240
                if f(hi) < target: continue
                for _ in range(14):
                    mid = (lo + hi) / 2
                    if f(mid) < target: lo = mid
                    else: hi = mid
                nv = hi
            else:
                lo, hi = vn - 45, vn + 45
                slope = (f(hi) - f(lo)) / (hi - lo)
                if slope < 0.25: continue                 # the gap is vertical: moving sideways would not fix it
                if slope < 0.5: lo, hi = vn - 30, vn + 30   # mostly diagonal: allow only a small move
                if f(hi) <= target: nv = hi
                elif f(lo) >= target: nv = lo
                else:
                    for _ in range(12):
                        mid = (lo + hi) / 2
                        if f(mid) < target: lo = mid
                        else: hi = mid
                    nv = (lo + hi) / 2
            nv = int(round(nv))
            if nv != vn: build._set_pair(font, idx, a, b, vn, nv); moved.append(nv - vn)
    font.save(path)
    return len(moved), (float(np.median(np.abs(moved))) if moved else 0.0), (max(map(abs, moved)) if moved else 0)


# ---- crossbar and diagonal neighbours ------------------------------------------------------
# Inter kerns r away from a following t or f so the arm and the crossbar keep a steady distance in
# every weight, but leaves w and k unkerned and v, y, x only partly, so in the heavier weights the
# diagonal ends up almost on the crossbar. Those pairs are raised to the r-t distance. Likewise
# ww, vw, wy and kw close up more than vv does, and are raised to match it.
import unicodedata
def _family(font, bases):
    out = []
    for cp, g in font.getBestCmap().items():
        d = unicodedata.normalize("NFD", chr(cp))
        if d[0] in bases and unicodedata.category(chr(cp)) == "Ll": out.append(g)
    return sorted(set(out))

def floors(path):
    font = TTFont(path); cm = font.getBestCmap(); T = math.tan(math.radians(-font["post"].italicAngle))
    # (letters on the left, letters on the right, the pair whose clearance they are raised to)
    rules = [("vwykx", "tf", ("r", "t")), ("vwyk", "vwy", ("v", "v"))]
    need = set()
    for L, R, ref in rules: need |= set(_family(font, L)) | set(_family(font, R)) | {cm[ord(ref[0])], cm[ord(ref[1])]}
    en = _edges(font, sorted(need), T); pv = build._PV(font["GPOS"].table); hm = font["hmtx"].metrics
    idx = build._pair_index(font["GPOS"].table); n = 0; big = 0
    for L, R, ref in rules:
        ra, rb = cm[ord(ref[0])], cm[ord(ref[1])]
        target = spacing.clearance(*en[ra][0], hm[ra][0], *en[rb][1], pv(ra, rb))
        for a in _family(font, L):
            for b in _family(font, R):
                vn = pv(a, b); f = lambda v: spacing.clearance(*en[a][0], hm[a][0], *en[b][1], v)
                if f(vn) >= target - 2: continue
                lo, hi = vn, vn + 260
                if f(hi) < target: continue
                for _ in range(14):
                    mid = (lo + hi) / 2
                    if f(mid) < target: lo = mid
                    else: hi = mid
                nv = int(round(hi))
                if nv != vn: build._set_pair(font, idx, a, b, vn, nv); n += 1; big = max(big, nv - vn)
    # general floor: no two basic Latin letters, figures or punctuation marks closer than 8% of the stem
    # (wide accents on narrow letters, such as a circumflex i beside a capital, are the usual cause)
    stem = build_stem(font, T); floor = 0.08 * stem
    chars = [c for c in FLOOR_CHARS if ord(c) in cm]; gl = [cm[ord(c)] for c in chars]
    en2 = _edges(font, sorted(set(gl)), T); pv = build._PV(font["GPOS"].table); idx = build._pair_index(font["GPOS"].table); m = 0
    base = {c: unicodedata.normalize("NFD", c)[0] for c in chars}
    for ca, a in zip(chars, gl):
        yr, xr = en2[a][0]
        if len(yr) == 0: continue
        for cb, b in zip(chars, gl):
            yl, xl = en2[b][1]
            if len(yl) == 0: continue
            if (base[ca], base[cb]) in JOINED or (ca in RUNS and cb in RUNS): continue
            vn = pv(a, b); f = lambda v: spacing.clearance(yr, xr, hm[a][0], yl, xl, v)
            if f(vn) >= floor - 1: continue
            lo, hi = vn, vn + 700
            if f(hi) < floor: continue           # one sits above or below the other: sideways movement cannot separate them
            for _ in range(14):
                mid = (lo + hi) / 2
                if f(mid) < floor: lo = mid
                else: hi = mid
            nv = int(round(hi))
            if nv != vn: build._set_pair(font, idx, a, b, vn, nv); m += 1
    font.save(path)
    return n, big, m

FLOOR_CHARS = [chr(c) for c in list(range(0x21, 0x7F)) + list(range(0xA1, 0x180)) + [0x2013, 0x2014, 0x2018, 0x2019, 0x201A, 0x201C, 0x201D, 0x201E, 0x2022, 0x2026, 0x2039, 0x203A, 0x20AC, 0x2122]]
JOINED = {("f", "f"), ("f", "t"), ("t", "f"), ("t", "t")}     # crossbars that join by design
RUNS = set("_-\u2013\u2014=~.\u2026/\\|")                    # marks that are meant to run together when repeated or combined
