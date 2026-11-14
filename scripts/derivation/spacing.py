"""Spacing and kerning for Draft Grotesk.

Inter's spacing is the reference. For every glyph side we measure the white space between
the edge of the glyph's advance box and its outline (row by row, ignoring anything deeper
than DEPTH so open shapes do not count as empty), then set the new sidebearing so the
reshaped glyph carries the same white, times one scale factor per weight. Straight stems
simply get Inter's sidebearing scaled; rounder, wider bowls get pulled in to compensate
for the extra white at their corners."""
import numpy as np, unicodedata

Y0, STEP, ROWS = -791.5, 16.0, 190          # scan rows cover descender to ascender
DEPTH = 170.0                               # about 15% of x-height

def profile(shapes, steps=10):
    """leftmost and rightmost ink x on each scan row (nan where the row has no ink)"""
    L = np.full(ROWS, np.inf); R = np.full(ROWS, -np.inf)
    for P, S in shapes:
        n = len(P)
        for i in range(n):
            a, b = P[i], P[(i+1) % n]; g = S[i]
            if g is None: pts = [a, b]
            else:
                pts = []
                for k in range(steps+1):
                    t = k/steps; m = 1-t
                    pts.append((m*m*m*a[0]+3*m*m*t*g[0][0]+3*m*t*t*g[1][0]+t*t*t*b[0],
                                m*m*m*a[1]+3*m*m*t*g[0][1]+3*m*t*t*g[1][1]+t*t*t*b[1]))
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                if y0 == y1: continue
                lo, hi = (y0, y1) if y0 < y1 else (y1, y0)
                r0 = int(np.ceil((lo - Y0)/STEP)); r1 = int(np.floor((hi - Y0)/STEP))
                for r in range(max(r0, 0), min(r1, ROWS-1)+1):
                    y = Y0 + r*STEP; x = x0 + (x1-x0)*(y-y0)/(y1-y0)
                    if x < L[r]: L[r] = x
                    if x > R[r]: R[r] = x
    L[~np.isfinite(L)] = np.nan; R[~np.isfinite(R)] = np.nan
    return L, R

def side_bearings(Lo, Ro, adv_o, Ln, Rn, k):
    """returns (dx to shift the new outline, new advance) or None when there is nothing to measure.
    Each side: Inter's sidebearing times k, corrected by how much the edge moved away from the
    glyph's extreme on the rows that carry the shape (rows deeper than DEPTH are open space)."""
    rows = ~np.isnan(Lo) & ~np.isnan(Ln)
    if not rows.any(): return None
    lo, ro, ln, rn = Lo[rows], Ro[rows], Ln[rows], Rn[rows]
    def corr(d_o, d_n):
        use = d_o < DEPTH
        return (k*d_o[use] - np.minimum(d_n[use], k*DEPTH)).mean()
    lsb = k*lo.min() + corr(lo - lo.min(), ln - ln.min())
    rsb = k*(adv_o - ro.max()) + corr(ro.max() - ro, rn.max() - rn)
    dx = lsb - ln.min()
    adv = dx + rn.max() + rsb
    return int(round(dx)), int(round(adv))

def base_of(name, rev, cmap, order_set):
    """glyph an accented letter is built on, e.g. eacute -> e, or None"""
    stem, dot, suffix = name.partition(".")
    cp = rev.get(name) if not dot else rev.get(stem)
    if cp is None or 0xE000 <= cp <= 0xF8FF: return None
    d = unicodedata.normalize("NFD", chr(cp))
    if len(d) < 2: return None
    b = cmap.get(ord(d[0]))
    if b is None: return None
    if dot: b = b + "." + suffix
    return b if b in order_set and b != name else None

def edge(arr):
    """rows that carry ink, as (row index, x)"""
    idx = np.nonzero(~np.isnan(arr))[0]
    return idx.astype(float)*STEP, arr[idx]

def clearance(yr, xr, adv, yl, xl, kern):
    """nearest distance between glyph A's right edge and glyph B's left edge once B sits adv+kern after A"""
    if len(yr) == 0 or len(yl) == 0: return None
    gx = (xl[None, :] + adv + kern) - xr[:, None]
    gy = yl[None, :] - yr[:, None]
    return float(np.hypot(np.maximum(gx, 0), gy).min())

def new_kern(v, k, A_o, B_o, A_n, B_n):
    """Inter's kern value v for the pair, re-expressed for the new shapes: scale it, then move it
    (within limits) until the pair's nearest points are as far apart as Inter's were, times k."""
    base = k*v; lim = 0.25*abs(v) + 10
    d_o = clearance(*A_o, *B_o, v)
    if d_o is None or d_o > 420: return int(round(base))
    target = k*d_o
    f = lambda x: clearance(*A_n, *B_n, x)
    lo, hi = base-lim, base+lim
    flo, fhi = f(lo), f(hi)
    if flo is None or fhi - flo < 1.0: return int(round(base))
    if fhi <= target: return int(round(hi))
    if flo >= target: return int(round(lo))
    for _ in range(14):
        mid = (lo+hi)/2
        if f(mid) < target: lo = mid
        else: hi = mid
    return int(round((lo+hi)/2))
