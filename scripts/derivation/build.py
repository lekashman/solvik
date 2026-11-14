"""Draft Grotesk: Inter reshaped toward wider, rounder, more geometric bowls.
  1. widen every glyph horizontally (round letters more than the rest)
  2. take the extra thickness back off the vertical strokes so weight is unchanged
  3. relax curve tension so bowls read as circles instead of rounded rectangles
"""
import sys, math, unicodedata
from fontTools.ttLib import TTFont
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
import terminals, spacing
import numpy as np

FAMILY = "Solvik"
VERSION = "1.030"
TENSION = 0.95
# letters built on a full round bowl: Latin, plus their Cyrillic and Greek twins so scripts match
ROUND = set("ocebdpqgOCGQD" "øØœŒðþÞÐĐƉƊɔƆəƏɵƟɑɡºƍ"
            "оОсСеЕрөӨәӘєЄэЭфФюЮбԁԛ" "οΟθΘσρϱφ")
MID = set("aæª" "а")   # small bowl: halfway between the two widths

def widths(stem, o_w, o_h):
    """Scale factors for this weight. Round letters are sized so the o lands at a set
    width-to-height ratio; the target rises gently with weight, and heavy weights, whose o is
    already nearly round, need little or no extra."""
    k = max(-0.8, min(1.9, (stem - 180) / 120))
    base = 1.045 - 0.015 * k
    ratio = 0.963 + 0.027 * k
    rnd = (ratio * o_h - stem) / (o_w - stem)
    return base, max(base, rnd)
FLAT = True
# In the italics these letters are not taken from Inter's cursive italic shapes (looped e,
# single-storey a, descending f). They are built from the upright letters and slanted, so the
# italic matches the upright the way every other letter does. Cyrillic a and e follow.
ITALIC_FROM_UPRIGHT = set("aef" "\u00e6\u0153\u00aa" "\u0430\u0435")
ITALIC_LOOP = set()

def _rec(gs, name):
    r = RecordingPen(); gs[name].draw(r); return r.value

def contours(rec):
    out, cur = [], None
    for op, a in rec:
        if op == "moveTo": cur = {"pts": [a[0]], "segs": []}
        elif op == "lineTo": cur["segs"].append(None); cur["pts"].append(a[0])
        elif op == "curveTo": cur["segs"].append([a[0], a[1]]); cur["pts"].append(a[2])
        elif op in ("closePath", "endPath"):
            p, s = cur["pts"], cur["segs"]
            if len(p) > 1 and p[-1] == p[0]: p.pop()
            else: s.append(None)
            out.append(cur); cur = None
    return out

def unit(v):
    l = math.hypot(*v); return (v[0]/l, v[1]/l) if l > 1e-6 else None

def reshape(c, s, delta, tension, ital=0.0, vthick=0.0):
    P = [(x*s, y) for x, y in c["pts"]]
    S = [None if g is None else [(g[0][0]*s, g[0][1]), (g[1][0]*s, g[1][1])] for g in c["segs"]]
    n = len(P)
    if n < 2: return P, S
    disp = []
    for i in range(n):
        p, nxt, prv = P[i], P[(i+1) % n], P[i-1]
        so, si = S[i], S[i-1]
        cand_o = ([so[0], so[1]] if so else []) + [nxt]
        cand_i = ([si[1], si[0]] if si else []) + [prv]
        do = next((u for u in (unit((q[0]-p[0], q[1]-p[1])) for q in cand_o) if u), (0, 1))
        di = next((u for u in (unit((p[0]-q[0], p[1]-q[1])) for q in cand_i) if u), (0, 1))
        # ital: where an edge runs level (tops and bottoms of bowls) slide it sideways, outer edge one
        # way and inner edge the other, as Inter does so slanted bowls do not look lopsided
        hi, ho = -delta*di[1] + ital*di[0], -delta*do[1] + ital*do[0]
        # vthick: push level edges outward (up on tops, down on undersides) to thicken horizontal strokes
        vi, vo = -vthick*di[0], -vthick*do[0]
        cross = di[0]*do[1] - di[1]*do[0]
        d = ((hi+ho)/2, (vi+vo)/2)
        if abs(cross) > 0.08:
            t = ((ho-hi)*do[1] - (vo-vi)*do[0])/cross
            m = (hi + t*di[0], vi + t*di[1])
            if math.hypot(*m) <= 2.5*(abs(delta) + abs(ital) + abs(vthick)) + 1e-6: d = m
        disp.append(d)
    NP = [(P[i][0]+disp[i][0], P[i][1]+disp[i][1]) for i in range(n)]
    NS = []
    for i in range(n):
        g = S[i]
        if g is None: NS.append(None); continue
        a, b = NP[i], NP[(i+1) % n]
        da, db = disp[i], disp[(i+1) % n]
        c1 = (g[0][0]+da[0], g[0][1]+da[1]); c2 = (g[1][0]+db[0], g[1][1]+db[1])
        # soften the curve only as far as a true circular arc: bowls drawn squarer than a circle get
        # their handles shortened (by at most 1 - tension); circles, dots and rings are left alone
        h1 = math.hypot(c1[0]-a[0], c1[1]-a[1]); h2 = math.hypot(b[0]-c2[0], b[1]-c2[1]); chord = math.hypot(b[0]-a[0], b[1]-a[1])
        f1 = f2 = 1.0
        if h1 > 1e-6 and h2 > 1e-6 and chord > 1e-6:
            dot = ((c1[0]-a[0])*(b[0]-c2[0]) + (c1[1]-a[1])*(b[1]-c2[1])) / (h1*h2)
            th = math.acos(max(-1.0, min(1.0, dot)))
            hc = chord/3 if th < 0.09 else chord*(2/3)*math.tan(th/4)/math.sin(th/2)
            f1 = max(tension, min(1.0, hc/h1)); f2 = max(tension, min(1.0, hc/h2))
        c1 = (a[0]+(c1[0]-a[0])*f1, a[1]+(c1[1]-a[1])*f1)
        c2 = (b[0]+(c2[0]-b[0])*f2, b[1]+(c2[1]-b[1])*f2)
        NS.append([c1, c2])
    return NP, NS

def base_char(font, name, rev):
    b = name.split(".")[0]
    cp = rev.get(b) or rev.get(name)
    if cp is None: return None
    d = unicodedata.normalize("NFD", chr(cp))
    return d[0]

def as_drawn(name, rev):
    """symbols and enclosed characters (circled or squared letters and figures, the copyright sign):
    their circles must stay circles and their insides must not touch the ring, so they keep Inter's
    drawing and only take the family's spacing"""
    b = name.split(".")[0]; cp = rev.get(b) or rev.get(name)
    if ".circled" in name or ".squared" in name: return True
    if cp is None: return False
    return unicodedata.category(chr(cp)) == "So" or 0x2460 <= cp <= 0x24FF or 0x2776 <= cp <= 0x2793 or 0x1F100 <= cp <= 0x1F1FF
NO_ERODE = {"uni0181"}     # B with hook: its hook is a separate overlapping shape that must stay attached
NO_THICKEN = {"uni1DEC"}   # a tiny combining letter whose gap would close
SCALE_ONLY = {"fraction"}  # the fraction bar overlaps its neighbours on purpose: scale its box, do not re-measure

# hooked letters whose hook the terminal rule reshapes in some weights: left as Inter draws them, in every weight
NO_FLAT = {"uni04C4", "uni04C3", "uni04A7", "uni04A6", "uni1EFD", "uni1EFC"}

def flat_ok(name, rev):
    """Square up terminals on letters, figures and currency; leave marks, punctuation and symbols alone."""
    b = name.split(".")[0]
    if b in NO_FLAT: return False
    if b == "section": return True
    cp = rev.get(b) or rev.get(name)
    if cp is None or 0xE000 <= cp <= 0xF8FF: return not name.startswith(("comma", "quote", "ogonek"))
    cat = unicodedata.category(chr(cp))
    return cat[0] in "LN" or cat == "Sc"

def squash(shape, e, xh):
    """after thickening horizontals by e top and bottom, bring heights back: the baseline and the
    x-height stay where they were, and everything above or below simply moves with them"""
    if not e: return shape
    # below the baseline the lift fades out with depth, so tails and hooks thicken evenly both ways
    # and do not creep up toward the letters above them
    def f(y):
        if y >= xh + e: return y - e
        if y > -e: return (y + e) * xh / (xh + 2*e)
        return y + e * max(0.0, min(1.0, (y + 200) / 140))
    P, S = shape
    return ([(x, f(y)) for x, y in P], [None if g is None else [(g[0][0], f(g[0][1])), (g[1][0], f(g[1][1]))] for g in S])

def shear(cons, t):
    for c in cons:
        c["pts"] = [(x + y*t, y) for x, y in c["pts"]]
        c["segs"] = [None if g is None else [(g[0][0] + g[0][1]*t, g[0][1]), (g[1][0] + g[1][1]*t, g[1][1])] for g in c["segs"]]
    return cons

def build(src, dst, weight, italic=False, upright_src=None, upright_final=None):
    style = (weight + " Italic" if italic else weight).replace("Regular Italic", "Italic")
    font = TTFont(src); gs = font.getGlyphSet(); order = font.getGlyphOrder()
    cmap = font.getBestCmap(); rev = {}
    for cp, g in cmap.items(): rev.setdefault(g, cp)
    # italics are straightened, processed exactly like the uprights, then slanted back
    T = math.tan(math.radians(-font["post"].italicAngle))
    usrc = TTFont(upright_src) if (T and upright_src) else None
    REPL, OFF, ITAL = set(), 0.0, 0.0
    def upright(name):
        if name in REPL:      # the upright letter, moved to where italics sit in their box
            rec = RecordingPen(); ugs[name].draw(rec); cons = contours(rec.value)
            for c in cons:
                c["pts"] = [(x + OFF, y) for x, y in c["pts"]]
                c["segs"] = [None if g is None else [(g[0][0] + OFF, g[0][1]), (g[1][0] + OFF, g[1][1])] for g in c["segs"]]
            return cons
        rec = RecordingPen(); gs[name].draw(rec); return shear(contours(rec.value), -T)
    def box(name):
        bp = BoundsPen(gs); gs[name].draw(TransformPen(bp, (1, 0, -T, 1, 0, 0)))
        return bp.bounds[2]-bp.bounds[0], bp.bounds[3]-bp.bounds[1]
    stem = box("l")[0]
    S_BASE, S_ROUND = widths(stem, *box("o"))
    # spacing scale for this weight. Below Regular it is eased so the set width never runs wider
    # in a lighter weight than in the next heavier one.
    K = S_BASE - 0.055 * max(0.0, (180 - stem) / 90)
    # proportions set against comparable typefaces: straight-sided lowercase a little wider,
    # straight-sided capitals a little narrower, figures wider
    S_LC = S_BASE + 0.45 * (S_ROUND - S_BASE)
    S_CAP = 1 + 0.5 * (S_BASE - 1)
    S_FIG = S_BASE + 0.75 * (S_ROUND - S_BASE)
    XH = font["OS/2"].sxHeight
    print(style, "stem %d base %.3f round %.3f" % (stem, S_BASE, S_ROUND), flush=True)
    marks = {g for g, c in font["GDEF"].table.GlyphClassDef.classDefs.items() if c == 3}
    if usrc is not None:
        ugs = usrc.getGlyphSet(); uorder = set(usrc.getGlyphOrder())
        bi = BoundsPen(gs); gs["n"].draw(TransformPen(bi, (1, 0, -T, 1, 0, 0))); bu = BoundsPen(ugs); ugs["n"].draw(bu)
        OFF = bi.bounds[0] - bu.bounds[0]
        rec = RecordingPen(); ugs["o"].draw(rec); tops = sorted(max(p[1] for p in c["pts"]) for c in contours(rec.value))
        ITAL = 0.83 * (tops[-1] - tops[0]) * T / 2
        REPL = {n for n in order if n in uorder and n not in marks and base_char(font, n, rev) in ITALIC_FROM_UPRIGHT}
        print("  %s: %d glyphs rebuilt from uprights, origin offset %.0f, extreme correction %.1f" % (style, len(REPL), OFF, ITAL), flush=True)

    # horizontal strokes: Inter's thin out quickly as the weight rises; hold them closer to the verticals
    otops = sorted(max(p[1] for p in c["pts"]) for c in shear(contours(_rec(gs, "o")), -T))
    c0 = (otops[-1] - otops[0]) / (1.017 * stem)
    kk = max(0.0, (stem - 180) / 120)
    cap = 0.07 if kk <= 1 else max(0.03, 0.07 - 0.047 * (kk - 1))     # the heaviest weights get less, or their small counters close up
    VTH = max(0.0, min((0.88 - 0.035 * kk) - c0, cap) * 1.017 * stem / 2) if kk > 0 else 0.0
    print("  %s: horizontal/vertical stroke ratio %.3f, thickening %.1f per edge; lowercase %.3f caps %.3f figures %.3f" % (style, c0, VTH, S_LC, S_CAP, S_FIG), flush=True)

    REVERTED = []
    # 1. reshape every glyph, and record Inter's and the new edge profiles
    shapes, scale, adv_o, prof_o, prof_n = {}, {}, {}, {}, {}
    for name in order:
        bc = base_char(font, name, rev)
        cat = unicodedata.category(bc) if bc else ""
        s = (S_ROUND if bc in ROUND else (S_LC + S_ROUND) / 2 if bc in MID else
             S_LC if cat == "Ll" else S_CAP if cat == "Lu" else S_FIG if cat == "Nd" else S_BASE)
        keepdrawn = as_drawn(name, rev)
        if keepdrawn: s = 1.0
        delta = 0.0 if name in NO_ERODE else (s - 1) * stem / 2
        vth = 0.0 if (keepdrawn or name in NO_THICKEN) else VTH
        cons = upright(name)
        prof_o[name] = spacing.profile([(c["pts"], c["segs"]) for c in cons])
        fo = FLAT and flat_ok(name, rev) and not keepdrawn; raw = []
        for c in cons:
            c["pts"] = list(c["pts"])
            if fo:
                c["segs"] = [None if g is None else list(g) for g in c["segs"]]
                keep = (list(c["pts"]), [None if g is None else list(g) for g in c["segs"]])
                y0 = (min(p[1] for p in c["pts"]), max(p[1] for p in c["pts"]))
                terminals.flatten(c["pts"], c["segs"], stem)
                y1 = (min(p[1] for p in c["pts"]), max(p[1] for p in c["pts"]))
                if abs(y1[0] - y0[0]) > 60 or abs(y1[1] - y0[1]) > 60:      # squaring a terminal must never change a letter's height
                    c["pts"], c["segs"] = keep; REVERTED.append(name)
            raw.append(reshape(c, s, delta, 1.0 if keepdrawn else TENSION, ITAL if name in REPL else 0.0, vth))
        if vth and raw and max(p[1] for c in cons for p in c["pts"]) <= 0.5:
            # a shape hanging from the baseline (the underscore) keeps its top and grows downward
            out = [([(x, y - vth) for x, y in P_], [None if g is None else [(g[0][0], g[0][1] - vth), (g[1][0], g[1][1] - vth)] for g in S_]) for P_, S_ in raw]
        else:
            out = [squash(r, vth, XH) for r in raw]
        shapes[name] = out; scale[name] = s; adv_o[name] = usrc["hmtx"][name][0] if name in REPL else gs[name].width
        prof_n[name] = spacing.profile(out)

    if REVERTED: print("  terminals left as drawn (would have changed height):", sorted(set(REVERTED))[:12], flush=True)
    # 2. sidebearings
    dx, adv = {}, {}
    tab = {n for n in order if ".tf" in n or n.endswith(".tnum")}
    for name in order:
        a0 = adv_o[name]; Lo, Ro = prof_o[name]; Ln, Rn = prof_n[name]
        r = None
        if name in marks or a0 <= 0 or name.endswith("comb"): dx[name], adv[name] = 0, max(0, int(round(a0 * scale[name]))); continue
        if name not in tab and name not in SCALE_ONLY: r = spacing.side_bearings(Lo, Ro, a0, Ln, Rn, K)
        if r is not None and not (0.6 * a0 <= r[1] <= 1.6 * a0):   # odd glyphs (overhanging marks): just scale
            dx[name], adv[name] = 0, max(0, int(round(a0 * scale[name]))); continue
        if r is None:      # empty glyphs and fixed-width figures: scale the box, keep the ink centred as before
            adv[name] = int(round(a0 * (K + scale[name] - S_BASE))); dx[name] = 0
            if np.isnan(Ln).all() and name in rev and unicodedata.category(chr(rev[name])) == "Zs": adv[name] = a0   # word space as Inter has it
            if not np.isnan(Ln).all():
                lo_, ro_ = np.nanmin(Lo), a0 - np.nanmax(Ro); ink = np.nanmax(Rn) - np.nanmin(Ln)
                share = lo_ / (lo_ + ro_) if (lo_ + ro_) else 0.5
                dx[name] = int(round((adv[name] - ink) * share - np.nanmin(Ln)))
        else: dx[name], adv[name] = r
    order_set = set(order)
    for name in order:   # accented letters sit exactly like their base letter
        b = spacing.base_of(name, rev, cmap, order_set)
        if b and adv_o[b] == adv_o[name] and name not in marks and name not in tab:
            dx[name], adv[name] = dx[b], adv[b]

    groups = {}
    for name in order:      # maths signs and other symbols designed on one shared width stay on one shared width
        cp = rev.get(name)
        if cp is not None and unicodedata.category(chr(cp)) in ("Sm", "So") and adv_o[name] > 0 and name not in tab and name not in marks:
            groups.setdefault((unicodedata.category(chr(cp)), adv_o[name]), []).append(name)
    for members in groups.values():
        if len(members) >= 4 and len({adv[m] for m in members}) > 1:
            common = int(round(float(np.median([adv[m] for m in members]))))
            for m in members:
                dx[m] += int(round((common - adv[m]) / 2)); adv[m] = common

    # 3. write outlines
    cff = font["CFF "].cff; top = cff.topDictIndex[0]; cs = top.CharStrings
    new = {}
    for name in order:
        d = dx[name]; pen = T2CharStringPen(adv[name], gs)
        sl = lambda p: (p[0] + d + p[1]*T, p[1])
        for P, S in shapes[name]:
            pen.moveTo(sl(P[0]))
            for i in range(len(P)):
                q = P[(i+1) % len(P)]
                if S[i] is None:
                    if i < len(P)-1: pen.lineTo(sl(q))
                else: pen.curveTo(sl(S[i][0]), sl(S[i][1]), sl(q))
            pen.closePath()
        new[name] = pen.getCharString(private=cs[name].private, globalSubrs=cs[name].globalSubrs)
    for name, c in new.items():
        cs[name].program = c.program; cs[name].bytecode = None
    for priv in ({id(c.private): c.private for c in new.values()}).values():
        priv.nominalWidthX = 0; priv.defaultWidthX = 0
        if hasattr(priv, "Subrs"): priv.Subrs.items = []
    cff.GlobalSubrs.items = []
    gs2 = font.getGlyphSet()
    for name in order:
        bp = BoundsPen(gs2); gs2[name].draw(bp)
        font["hmtx"][name] = (adv[name], int(round(bp.bounds[0])) if bp.bounds else 0)

    # 4. kerning and mark positions
    uanch = _anchors(usrc["GPOS"].table) if usrc is not None else {}
    stats = regpos(font, K, scale, dx, adv, adv_o, prof_o, prof_n, rev, T, REPL, uanch, OFF)
    stats["exceptions"] = exceptions(font, TTFont(src)["GPOS"].table, K, dx, adv, adv_o, prof_o, prof_n, rev, marks)
    if REPL:
        upf = TTFont(upright_final)
        stats["from_upright"] = transplant(font, upf["GPOS"].table, REPL, marks, adv_o)
        stats["retuned"] = tune_swapped(font, upf, usrc, REPL, marks, rev, dx, adv, adv_o, prof_o, prof_n, OFF)
        import json; json.dump(sorted(REPL), open(dst + ".repl", "w"))
    print(" ", style, "kerning:", stats, flush=True)
    finish(font, dst, weight, italic, style)
    import pickle
    core = [g for cp, g in cmap.items() if 0x21 <= cp <= 0x7E]
    pickle.dump(dict(K=K, adv={g: adv[g] for g in core}, adv_o={g: adv_o[g] for g in core},
                     prof_o={g: prof_o[g] for g in core},
                     prof_n={g: (prof_n[g][0] + dx[g], prof_n[g][1] + dx[g]) for g in core}), open(dst + ".prof", "wb"))

def _walk_anchors(gpos):
    """yield (key, glyph, anchor) for every mark-positioning anchor, keyed so two fonts can be matched"""
    for li, lk in enumerate(gpos.LookupList.Lookup):
        for si, sub in enumerate(lk.SubTable):
            t = sub.ExtSubTable if lk.LookupType == 9 else sub; kind = type(t).__name__
            if kind == "MarkBasePos":
                for g, mr in zip(t.MarkCoverage.glyphs, t.MarkArray.MarkRecord): yield (li, si, "m", g, 0), g, mr.MarkAnchor
                for g, br in zip(t.BaseCoverage.glyphs, t.BaseArray.BaseRecord):
                    for j, an in enumerate(br.BaseAnchor): yield (li, si, "b", g, j), g, an
            elif kind == "MarkMarkPos":
                for g, mr in zip(t.Mark1Coverage.glyphs, t.Mark1Array.MarkRecord): yield (li, si, "m", g, 0), g, mr.MarkAnchor
                for g, br in zip(t.Mark2Coverage.glyphs, t.Mark2Array.Mark2Record):
                    for j, an in enumerate(br.Mark2Anchor): yield (li, si, "b", g, j), g, an

def _anchors(gpos):
    return {k: (an.XCoordinate, an.YCoordinate) for k, g, an in _walk_anchors(gpos) if an is not None}

def regpos(font, K, scale, dx, adv, adv_o, prof_o, prof_n, rev, T, REPL=frozenset(), uanch={}, OFF=0.0):
    gpos = font["GPOS"].table; st_count = {"pairs": 0, "moved_from_scaled": 0, "anchors": 0}
    cache = {}
    def edges(g):
        if g not in cache:
            cache[g] = (spacing.edge(prof_o[g][1]), spacing.edge(prof_o[g][0]),
                        spacing.edge(prof_n[g][1] + dx[g]), spacing.edge(prof_n[g][0] + dx[g]))
        return cache[g]
    def rep(glyphs):   # the letter that stands for a kerning class; never one whose shape was swapped
        return min(glyphs, key=lambda g: (g in REPL, rev.get(g, 0x110000), len(g), g))
    def fix(vr, a, b):
        if vr is None: return
        if getattr(vr, "XPlacement", 0): vr.XPlacement = int(round(K * vr.XPlacement))
        v = getattr(vr, "XAdvance", 0)
        if v:
            if a and b:
                ea, eb = edges(a), edges(b)
                nv = spacing.new_kern(v, K, (*ea[0], adv_o[a]), eb[1], (*ea[2], adv[a]), eb[3])
            else: nv = int(round(K * v))
            st_count["pairs"] += 1; st_count["moved_from_scaled"] += nv != int(round(K * v)); vr.XAdvance = nv
    for lk in gpos.LookupList.Lookup:
        for sub in lk.SubTable:
            t = sub.ExtSubTable if lk.LookupType == 9 else sub; kind = type(t).__name__
            if kind == "PairPos" and t.Format == 1:
                for g1, ps in zip(t.Coverage.glyphs, t.PairSet):
                    for pv in ps.PairValueRecord: fix(pv.Value1, g1, pv.SecondGlyph)
            elif kind == "PairPos" and t.Format == 2:
                c1 = {}; c2 = {}
                for g in t.Coverage.glyphs: c1.setdefault(t.ClassDef1.classDefs.get(g, 0), []).append(g)
                for g, c in t.ClassDef2.classDefs.items(): c2.setdefault(c, []).append(g)
                r1 = {c: rep(v) for c, v in c1.items()}; r2 = {c: rep(v) for c, v in c2.items()}
                for i, rec1 in enumerate(t.Class1Record):
                    for j, rec2 in enumerate(rec1.Class2Record):
                        fix(rec2.Value1, r1.get(i), r2.get(j))
            elif kind == "SinglePos":
                vals = [t.Value] if t.Format == 1 else t.Value
                for vr in vals:
                    for f in ("XPlacement", "XAdvance"):
                        if getattr(vr, f, 0): setattr(vr, f, int(round(K * getattr(vr, f))))
    for key, g, an in _walk_anchors(gpos):
        if an is None: continue
        if g in REPL and key in uanch:      # anchor of the upright letter, carried through the same moves
            xu, yu = uanch[key]
            an.XCoordinate = int(round(scale[g] * (xu + OFF) + dx[g] + yu * T)); an.YCoordinate = yu
        else:
            an.XCoordinate = int(round(scale[g] * an.XCoordinate + dx[g] + (1 - scale[g]) * an.YCoordinate * T))
        st_count["anchors"] += 1
    return st_count

def _pair_index(gpos):
    idx = []
    for li, lk in enumerate(gpos.LookupList.Lookup):
        subs = []
        for sub in lk.SubTable:
            t = sub.ExtSubTable if lk.LookupType == 9 else sub
            if type(t).__name__ != "PairPos": continue
            cov = {g: i for i, g in enumerate(t.Coverage.glyphs)}
            subs.append((t, cov))
        if subs: idx.append((li, subs))
    return idx

def _pair_value(idx, a, b, only=None):
    total = 0
    for li, subs in idx:
        if only is not None and li != only: continue
        for t, cov in subs:
            i = cov.get(a)
            if i is None: continue
            if t.Format == 1:
                hit = next((p for p in t.PairSet[i].PairValueRecord if p.SecondGlyph == b), None)
                if hit is None: continue
                total += (hit.Value1.XAdvance or 0) if hit.Value1 else 0; break
            v = t.Class1Record[t.ClassDef1.classDefs.get(a, 0)].Class2Record[t.ClassDef2.classDefs.get(b, 0)].Value1
            total += (getattr(v, "XAdvance", 0) or 0) if v else 0; break
    return total

class _PV:
    """fast pair-value lookup over a font's kerning"""
    def __init__(self, gpos):
        self.lk = []
        for lk in gpos.LookupList.Lookup:
            subs = []
            for sub in lk.SubTable:
                t = sub.ExtSubTable if lk.LookupType == 9 else sub
                if type(t).__name__ != "PairPos": continue
                cov = {g: i for i, g in enumerate(t.Coverage.glyphs)}
                if t.Format == 1:
                    subs.append((1, cov, [{p.SecondGlyph: ((p.Value1.XAdvance or 0) if p.Value1 else 0) for p in ps.PairValueRecord} for ps in t.PairSet]))
                else:
                    m = [[((getattr(c2.Value1, "XAdvance", 0) or 0) if c2.Value1 else 0) for c2 in c1.Class2Record] for c1 in t.Class1Record]
                    subs.append((2, cov, t.ClassDef1.classDefs, t.ClassDef2.classDefs, m))
            if subs: self.lk.append(subs)
    def __call__(self, a, b):
        tot = 0
        for subs in self.lk:
            for s in subs:
                i = s[1].get(a)
                if i is None: continue
                if s[0] == 1:
                    v = s[2][i].get(b)
                    if v is None: continue
                    tot += v; break
                tot += s[4][s[2].get(a, 0)][s[3].get(b, 0)]; break
        return tot

def transplant(font, gpos_up, REPL, marks, adv_o):
    """The swapped italic letters are our upright letters, so they take the upright's finished kerning.
    Added as one extra kerning lookup holding the difference between what the italic's own tables
    give for each pair and what the upright gives."""
    from fontTools.otlLib.builder import buildLookup, buildPairPosClassesSubtable, buildValue
    gpos = font["GPOS"].table; it, up = _PV(gpos), _PV(gpos_up)
    G = [g for g in font.getGlyphOrder() if g not in marks and adv_o.get(g, 0) > 0]
    R = sorted(REPL); rest = [g for g in G if g not in REPL]
    def classes(rows, cols):
        D = {r: tuple(up(r, c) - it(r, c) for c in cols) for r in rows}
        rc = {}
        for r, sig in D.items():
            if any(sig): rc.setdefault(sig, []).append(r)
        pairs = {}; n = 0
        if not rc: return pairs, 0
        sigs = list(rc); cc = {}
        for j, c in enumerate(cols):
            col = tuple(s[j] for s in sigs)
            if any(col): cc.setdefault(col, []).append(c)
        for col, cg in cc.items():
            for k, sig in enumerate(sigs):
                if col[k]:
                    pairs[(tuple(rc[sig]), tuple(cg))] = (buildValue({"XAdvance": col[k]}), None); n += len(rc[sig]) * len(cg)
        return pairs, n
    gm = font.getReverseGlyphMap(); subs = []; total = 0
    for rows, cols in ((R, G), (rest, R)):
        pairs, n = classes(rows, cols); total += n
        if pairs: subs.append(buildPairPosClassesSubtable(pairs, gm))
    if not subs: return 0
    main = next(lk for lk in gpos.LookupList.Lookup if lk.LookupType in (2, 9) and any(type(getattr(s, "ExtSubTable", s)).__name__ == "PairPos" for s in lk.SubTable))
    lk = buildLookup(subs, flags=main.LookupFlag, markFilterSet=getattr(main, "MarkFilteringSet", None))
    gpos.LookupList.Lookup.append(lk); gpos.LookupList.LookupCount = len(gpos.LookupList.Lookup)
    idx = len(gpos.LookupList.Lookup) - 1
    for fr in gpos.FeatureList.FeatureRecord:
        if fr.FeatureTag == "kern":
            fr.Feature.LookupListIndex.append(idx); fr.Feature.LookupCount = len(fr.Feature.LookupListIndex)
    return total

def _set_pair(font, idx, a, b, total_now, total_new):
    """give the pair a b its own kerning value, as a specific pair ahead of the class tables"""
    from fontTools.ttLib.tables import otTables as ot
    from fontTools.ttLib.tables.otBase import ValueRecord
    gid = font.getGlyphID
    f1 = [(li, subs) for li, subs in idx if subs[0][0].Format == 1]
    li = next((li for li, subs in f1 if any(a in cov for _, cov in subs)), f1[0][0])
    subs = dict(idx)[li]; t = subs[0][0]
    vr = ValueRecord(); vr.XAdvance = _pair_value(idx, a, b, only=li) + (total_new - total_now)
    rec = ot.PairValueRecord(); rec.SecondGlyph = b; rec.Value1 = vr; rec.Value2 = None
    cov = t.Coverage.glyphs
    if a not in cov:
        pos = sum(1 for g in cov if gid(g) < gid(a))
        cov.insert(pos, a); ps = ot.PairSet(); ps.PairValueRecord = []; t.PairSet.insert(pos, ps)
        subs[0] = (t, {g: i for i, g in enumerate(cov)})
    ps = t.PairSet[cov.index(a)]
    ps.PairValueRecord = [p for p in ps.PairValueRecord if p.SecondGlyph != b] + [rec]
    ps.PairValueRecord.sort(key=lambda p: gid(p.SecondGlyph)); ps.PairValueCount = len(ps.PairValueRecord)
    t.PairSetCount = len(t.PairSet)

def tune_swapped(font, upf, usrc, REPL, marks, rev, dx, adv, adv_o, prof_o, prof_n, OFF):
    """The upright's kerning suits a swapped letter next to any neighbour whose italic is just the
    upright slanted. A few neighbours are drawn differently in the italic (the ampersand, the hash
    sign, some symbols). For those pairs, set the value that gives the same clearance the pair has
    in the upright."""
    ugs, fgs = usrc.getGlyphSet(), upf.getGlyphSet()
    def prof(gs, g):
        rec = RecordingPen(); gs[g].draw(rec); return spacing.profile([(c["pts"], c["segs"]) for c in contours(rec.value)])
    def differs(g):      # Inter's italic of g, slant removed, against Inter's upright g
        Lu, Ru = prof(ugs, g); Li, Ri = prof_o[g]
        rows = ~np.isnan(Lu) & ~np.isnan(Li)
        if rows.sum() < 4: return (~np.isnan(Lu)).sum() != (~np.isnan(Li)).sum()
        dl = (Li[rows] - np.nanmin(Li[rows])) - (Lu[rows] - np.nanmin(Lu[rows]))
        dr = (np.nanmax(Ri[rows]) - Ri[rows]) - (np.nanmax(Ru[rows]) - Ru[rows])
        return (max(np.abs(dl).mean(), np.abs(dr).mean()) > 5 or max(np.percentile(np.abs(dl), 90), np.percentile(np.abs(dr), 90)) > 12
                or abs((~np.isnan(Lu)).sum() - (~np.isnan(Li)).sum()) > 3)
    uorder = set(usrc.getGlyphOrder())
    sym = lambda g: rev[g] < 0x250 and unicodedata.category(chr(rev[g]))[0] in "PS"      # common punctuation and symbols: always checked
    cand = [g for g in rev if g not in REPL and g not in marks and adv_o.get(g, 0) > 0 and g in uorder and (sym(g) or differs(g))]
    R = sorted(g for g in REPL if g in rev)
    eu = {}
    for g in set(cand) | set(R):
        L, Rr = prof(fgs, g); eu[g] = (spacing.edge(Rr), spacing.edge(L))
    en = {g: (spacing.edge(prof_n[g][1] + dx[g]), spacing.edge(prof_n[g][0] + dx[g])) for g in set(cand) | set(R)}
    uadv = upf["hmtx"].metrics
    pv_up = _PV(upf["GPOS"].table); pv_it = _PV(font["GPOS"].table); idx = _pair_index(font["GPOS"].table); n = 0
    for r in R:
        for x in cand:
            for a, b in ((r, x), (x, r)):
                vu, vi = pv_up(a, b), pv_it(a, b)
                d_up = spacing.clearance(*eu[a][0], uadv[a][0], *eu[b][1], vu)
                if d_up is None or d_up > 320 or d_up < 20: continue
                f = lambda v: spacing.clearance(*en[a][0], adv[a], *en[b][1], v)
                d_it = f(vi)
                if d_it is None or 0.9 <= d_it / d_up <= 1.1: continue
                lo, hi = vi - 160, vi + 160
                if f(hi) - f(lo) < 1: continue
                if f(hi) <= d_up: nv = hi
                elif f(lo) >= d_up: nv = lo
                else:
                    for _ in range(12):
                        mid = (lo + hi) / 2
                        if f(mid) < d_up: lo = mid
                        else: hi = mid
                    nv = (lo + hi) / 2
                _set_pair(font, idx, a, b, vi, int(round(nv))); n += 1
    print("    neighbours drawn differently in the italic: %d (%s ...)" % (len(cand), " ".join(chr(rev[g]) for g in cand[:40])), flush=True)
    return n

TAILED = set("gyj") | set("ɡǥ")     # letters whose descending tails now reach closer to the letter before them      # letters whose reshaped tail reaches further left than Inter's

def exceptions(font, gpos_o, K, dx, adv, adv_o, prof_o, prof_n, rev, marks):
    """Pair-specific fixes. The g's new tail curls further toward the letter before it, and g shares
    its kerning class with c, d, e, o and q, so the class value cannot account for it. Wherever a
    letter followed by g ends up clearly closer than Inter's clearance (scaled), give that pair its
    own value that restores the clearance."""
    from fontTools.ttLib.tables import otTables as ot
    from fontTools.ttLib.tables.otBase import ValueRecord
    gpos = font["GPOS"].table
    io, inw = _pair_index(gpos_o), _pair_index(gpos)
    def e_o(g): return spacing.edge(prof_o[g][1]), spacing.edge(prof_o[g][0])
    def e_n(g): return spacing.edge(prof_n[g][1] + dx[g]), spacing.edge(prof_n[g][0] + dx[g])
    rights = [g for g, cp in rev.items() if unicodedata.normalize("NFD", chr(cp))[0] in TAILED and "." not in g]
    lefts = [g for g in rev if g not in marks and adv_o[g] > 0]
    eo = {g: e_o(g) for g in set(lefts + rights)}; en = {g: e_n(g) for g in set(lefts + rights)}
    todo = []
    for b in rights:
        for a in lefts:
            v_o, v_n = _pair_value(io, a, b), _pair_value(inw, a, b)
            d_o = spacing.clearance(*eo[a][0], adv_o[a], *eo[b][1], v_o)
            if d_o is None or d_o > 320 or d_o < 30: continue
            d_n = spacing.clearance(*en[a][0], adv[a], *en[b][1], v_n)
            if d_n >= 0.87 * K * d_o - 4: continue
            target = 0.97 * K * d_o; lo, hi = v_n, v_n + 130
            if spacing.clearance(*en[a][0], adv[a], *en[b][1], hi) < target: nv = hi
            else:
                for _ in range(12):
                    mid = (lo + hi) / 2
                    if spacing.clearance(*en[a][0], adv[a], *en[b][1], mid) < target: lo = mid
                    else: hi = mid
                nv = hi
            todo.append((a, b, int(round(nv)), v_n))
    gid = font.getGlyphID
    for a, b, nv, v_n in todo:
        li = next((li for li, subs in inw if any(a in cov for _, cov in subs)), inw[0][0])
        subs = dict(inw)[li]; t = subs[0][0]
        assert t.Format == 1
        cur = _pair_value(inw, a, b, only=li)
        vr = ValueRecord(); vr.XAdvance = cur + (nv - v_n)
        rec = ot.PairValueRecord(); rec.SecondGlyph = b; rec.Value1 = vr; rec.Value2 = None
        cov = t.Coverage.glyphs
        if a not in cov:
            pos = sum(1 for g in cov if gid(g) < gid(a))
            cov.insert(pos, a); ps = ot.PairSet(); ps.PairValueRecord = []; t.PairSet.insert(pos, ps)
            subs[0] = (t, {g: i for i, g in enumerate(cov)})
        ps = t.PairSet[cov.index(a)]
        ps.PairValueRecord = [p for p in ps.PairValueRecord if p.SecondGlyph != b] + [rec]
        ps.PairValueRecord.sort(key=lambda p: gid(p.SecondGlyph)); ps.PairValueCount = len(ps.PairValueRecord)
        t.PairSetCount = len(t.PairSet)
    return len(todo)

def finish(font, dst, weight, italic, style):
    cff = font["CFF "].cff; top = cff.topDictIndex[0]
    ribbi = weight in ("Regular", "Bold")
    ps = FAMILY.replace(" ", "") + "-" + style.replace(" ", "")
    sub = (style if ribbi else ("Italic" if italic else "Regular"))
    vals = {0: None, 1: FAMILY if ribbi else f"{FAMILY} {weight}", 2: sub,
            3: f"{VERSION};{ps}", 4: f"{FAMILY} {style}", 5: f"Version {VERSION}",
            6: ps, 16: FAMILY, 17: style}
    for nrec in font["name"].names:
        if nrec.nameID == 0: nrec.string = str(nrec) + ". Solvik modifications 2026."
        elif vals.get(nrec.nameID) is not None: nrec.string = vals[nrec.nameID]
    font["name"].names = [x for x in font["name"].names if x.nameID not in (7, 21, 22, 25)]
    cff.fontNames = [ps]; top.FullName = f"{FAMILY} {style}"; top.FamilyName = FAMILY
    credit(font)
    font.save(dst)

DESCRIPTION = ("Solvik is a modified version of Inter (https://rsms.me/inter): wider, rounder bowls, "
               "flat terminals, and respaced and rekerned to match. Inter is by The Inter Project Authors and is "
               "licensed under the SIL Open Font License 1.1, as is this font.")

def credit(font):
    """metadata that has to describe this font and not Inter: maker, description, vendor code, average width"""
    name = font["name"]
    for n in list(name.names):
        if n.nameID == 8: n.string = "Modified from Inter (rsms)"
    for plat, enc, lang in {(n.platformID, n.platEncID, n.langID) for n in name.names}:
        name.setName(DESCRIPTION, 10, plat, enc, lang)
    font["OS/2"].achVendID = "NONE"
    adv = [a for a, _ in font["hmtx"].metrics.values() if a > 0]
    font["OS/2"].xAvgCharWidth = int(round(sum(adv) / len(adv)))

WEIGHTS = [("ExtraLight", "ExtraLight"), ("Light", "Light"), ("Regular", "Regular"), ("DemiBold", "SemiBold"),
           ("Bold", "Bold"), ("ExtraBold", "ExtraBold"), ("Black", "Black")]

if __name__ == "__main__":
    weight, italic = sys.argv[1], len(sys.argv) > 2 and sys.argv[2] == "Italic"
    srcw = dict(WEIGHTS)[weight]
    src = "../inter/extras/otf/Inter-" + (("Italic" if srcw == "Regular" else srcw + "Italic") if italic else srcw) + ".otf"
    style = (weight + "Italic" if italic else weight).replace("RegularItalic", "Italic")
    build(src, f"out/Solvik-{style}.otf", weight, italic,
          upright_src=f"../inter/extras/otf/Inter-{srcw}.otf" if italic else None,
          upright_final=f"out/Solvik-{weight}.otf" if italic else None)
    import polish       # final kerning pass over every basic pair (run uprights before italics)
    print("  pairs retuned in the final pass:", polish.tune(f"out/Solvik-{style}.otf", src, f"out/Solvik-{weight}.otf" if italic else None)[0], flush=True)
    print("  crossbar and diagonal pairs opened:", polish.floors(f"out/Solvik-{style}.otf"), flush=True)
