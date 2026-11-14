"""Find stroke-end cuts that sit a few degrees off axis and square them up
(horizontal or vertical, whichever is nearer), re-cutting the stroke edges
along their own curves so the stroke keeps its shape."""
import math

def _unit(v):
    l = math.hypot(*v); return (v[0]/l, v[1]/l) if l > 1e-6 else None

def _bez(p, t):
    a = [(p[i][0]+(p[i+1][0]-p[i][0])*t, p[i][1]+(p[i+1][1]-p[i][1])*t) for i in range(3)]
    b = [(a[i][0]+(a[i+1][0]-a[i][0])*t, a[i][1]+(a[i+1][1]-a[i][1])*t) for i in range(2)]
    c = (b[0][0]+(b[1][0]-b[0][0])*t, b[0][1]+(b[1][1]-b[0][1])*t)
    return a, b, c

def _solve(p, axis, target, lo, hi, near):
    """parameter t in [lo,hi] closest to `near` where p(t)[axis] == target"""
    best = None; N = 240; prev_t = lo; prev_v = _bez(p, lo)[2][axis] - target
    for k in range(1, N+1):
        t = lo + (hi-lo)*k/N; v = _bez(p, t)[2][axis] - target
        if prev_v == 0 or prev_v*v < 0:
            a, b, fa = prev_t, t, prev_v
            for _ in range(40):
                m = (a+b)/2; fm = _bez(p, m)[2][axis] - target
                if fa*fm <= 0: b = m
                else: a, fa = m, fm
            r = (a+b)/2
            if best is None or abs(r-near) < abs(best-near): best = r
        prev_t, prev_v = t, v
    return best

def _head(p, t):   # sub-curve [0,t]
    a, b, c = _bez(p, t); return [p[0], a[0], b[0], c]
def _tail(p, t):   # sub-curve [t,1]
    a, b, c = _bez(p, t); return [c, b[1], a[2], p[3]]

def find(P, S, stem):
    n = len(P); out = []
    if n < 4: return out
    xs = [p[0] for p in P]; ys = [p[1] for p in P]
    if max(max(xs)-min(xs), max(ys)-min(ys)) < 620: return out   # accents and marks keep their shape
    for i in range(n):
        if S[i] is not None: continue
        a, b = P[i], P[(i+1) % n]
        d = _unit((b[0]-a[0], b[1]-a[1]))
        if not d: continue
        L = math.hypot(b[0]-a[0], b[1]-a[1])
        if not (0.55*stem <= L <= 1.3*stem): continue
        ang = math.degrees(math.atan2(d[1], d[0])) % 180
        offh = min(ang, 180-ang); offv = abs(90-ang)
        off = min(offh, offv)
        if not (2.0 <= off <= 38): continue
        ps, ns = S[i-1], S[(i+1) % n]
        prv, nxt = P[i-1], P[(i+2) % n]
        cand_i = ([ps[1], ps[0]] if ps else []) + [prv]
        cand_o = ([ns[0], ns[1]] if ns else []) + [nxt]
        di = next((u for u in (_unit((a[0]-q[0], a[1]-q[1])) for q in cand_i) if u), None)
        do = next((u for u in (_unit((q[0]-b[0], q[1]-b[1])) for q in cand_o) if u), None)
        if not di or not do: continue
        c1 = di[0]*d[1]-di[1]*d[0]; c2 = d[0]*do[1]-d[1]*do[0]
        if c1 < 0.55 or c2 < 0.55: continue            # two convex, roughly square corners
        if di[0]*do[0]+di[1]*do[1] > -0.45: continue  # edges run back the way they came
        curved = ps is not None or ns is not None
        if not curved:
            # allow a tiny straight nub before the cut if a curve sits right behind it
            lp = math.hypot(a[0]-prv[0], a[1]-prv[1]); ln = math.hypot(nxt[0]-b[0], nxt[1]-b[1])
            curved = (lp < 0.3*stem and S[i-2] is not None) or (ln < 0.3*stem and S[(i+2) % n] is not None)
        if not curved: continue
        out.append((i, 1 if offh <= offv else 0, off))
    return out

def _curl(P, S, i, axis, lim):
    """A cut far off axis means the stroke has not turned enough to be cut square. Instead of
    shearing it, carry the trailing edge on along its own curve until it is level with the
    leading edge, then turn the leading edge's last handle parallel to it. The stroke ends up
    heading almost straight into the cut, like the arms of c and e."""
    n = len(P); j = (i+1) % n; k = (j+1) % n
    a, b = P[i], P[j]; ps, ns = S[i-1], S[j]
    if ps is None or ns is None: return False
    di = _unit((a[0]-ps[1][0], a[1]-ps[1][1])); do = _unit((ns[0][0]-b[0], ns[0][1]-b[1]))
    if not di or not do: return False
    fwd = 1 if (di[axis]-do[axis]) > 0 else -1
    L0 = math.hypot(b[0]-a[0], b[1]-a[1])
    if fwd*b[axis] < fwd*a[axis]:            # b trails: extend the edge leaving b
        p = [b, ns[0], ns[1], P[k]]; t = _solve(p, axis, a[axis], -0.9, 0.65, 0.0)
        if t is None: return False
        tl = _tail(p, t); nb = tl[0]; u = _unit((tl[1][0]-nb[0], tl[1][1]-nb[1]))
        if not u or math.hypot(nb[0]-b[0], nb[1]-b[1]) > lim: return False
        if (-u[0])*di[0] + (-u[1])*di[1] < 0.8: return False          # no more than ~35 degrees of turn
        L = math.hypot(nb[0]-a[0], nb[1]-a[1])
        if not (0.85*L0 <= L <= 1.25*L0): return False
        h = math.hypot(a[0]-ps[1][0], a[1]-ps[1][1])
        S[i-1] = [ps[0], (a[0]+u[0]*h, a[1]+u[1]*h)]
        P[j] = nb; S[j] = [tl[1], tl[2]]
    else:                                     # a trails: extend the edge arriving at a
        p = [P[i-1], ps[0], ps[1], a]; t = _solve(p, axis, b[axis], 0.35, 1.9, 1.0)
        if t is None: return False
        hd = _head(p, t); na = hd[3]; u = _unit((na[0]-hd[2][0], na[1]-hd[2][1]))
        if not u or math.hypot(na[0]-a[0], na[1]-a[1]) > lim: return False
        if (-u[0])*do[0] + (-u[1])*do[1] < 0.8: return False
        L = math.hypot(na[0]-b[0], na[1]-b[1])
        if not (0.85*L0 <= L <= 1.25*L0): return False
        h = math.hypot(ns[0][0]-b[0], ns[0][1]-b[1])
        S[j] = [(b[0]-u[0]*h, b[1]-u[1]*h), ns[1]]
        P[i] = na; S[i-1] = [hd[1], hd[2]]
    return True

def flatten(P, S, stem):
    """P: on-curve points, S[i]: None (line) or [c1,c2] for the segment P[i]->P[i+1]. Edits in place."""
    n = len(P); done = []
    for i, axis, off in find(P, S, stem):
        j = (i+1) % n; a, b = P[i], P[j]
        target = (a[axis]+b[axis])/2
        lim = 0.7*stem
        if off > 22 and _curl(P, S, i, axis, lim):
            done.append((i, axis, off)); continue
        # edge arriving at a
        ps = S[i-1]; na = None
        if ps is not None:
            p = [P[i-1], ps[0], ps[1], a]; t = _solve(p, axis, target, 0.35, 1.9, 1.0)
            if t is not None:
                h = _head(p, t); na = h[3]; newps = [h[1], h[2]]
        else:
            q = P[i-1]; den = a[axis]-q[axis]
            if abs(den) > 1e-6:
                t = (target-q[axis])/den
                if 0.2 < t < 6: na = (q[0]+(a[0]-q[0])*t, q[1]+(a[1]-q[1])*t); newps = None
        # edge leaving b
        ns = S[j]; nb = None; k = (j+1) % n
        if ns is not None:
            p = [b, ns[0], ns[1], P[k]]; t = _solve(p, axis, target, -0.9, 0.65, 0.0)
            if t is not None:
                tl = _tail(p, t); nb = tl[0]; newns = [tl[1], tl[2]]
        else:
            q = P[k]; den = b[axis]-q[axis]
            if abs(den) > 1e-6:
                t = (target-q[axis])/den
                if 0.2 < t < 6: nb = (q[0]+(b[0]-q[0])*t, q[1]+(b[1]-q[1])*t); newns = None
        if na is None or nb is None: continue
        if math.hypot(na[0]-a[0], na[1]-a[1]) > lim or math.hypot(nb[0]-b[0], nb[1]-b[1]) > lim: continue
        P[i], P[j] = na, nb
        if ps is not None: S[i-1] = newps
        if ns is not None: S[j] = newns
        done.append((i, axis, off))
    return done
