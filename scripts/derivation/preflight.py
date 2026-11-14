"""Pre-flight checks for the Draft Grotesk family. Prints PASS/WARN/FAIL lines."""
import sys, glob, os, math, collections
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.boundsPen import BoundsPen
import uharfbuzz as hb
from PIL import ImageFont
W = [("ExtraLight","ExtraLight",200),("Light","Light",300),("Regular","Regular",400),("DemiBold","SemiBold",600),("Bold","Bold",700),("ExtraBold","ExtraBold",800),("Black","Black",900)]
res = collections.defaultdict(list)
def note(level, check, msg): res[(level, check)].append(msg)
fam = {}
for w, sw, num in W:
    for it in (0, 1):
        style = (w + "Italic" if it else w).replace("RegularItalic", "Italic")
        src = "../inter/extras/otf/Inter-" + (("Italic" if sw == "Regular" else sw + "Italic") if it else sw) + ".otf"
        path = f"final2/Solvik-{style}.otf"
        f = TTFont(path); o = TTFont(src); fam[style] = f
        nm = {n.nameID: str(n) for n in f["name"].names if n.platformID == 3}
        # --- opens everywhere
        try:
            hb.Font(hb.Face(hb.Blob.from_file_path(path))); ImageFont.truetype(path, 40).getlength("Hamburgefonstiv")
        except Exception as e: note("FAIL", "opens in shaping and rendering engines", f"{style}: {e}")
        # --- coverage
        if f.getGlyphOrder() != o.getGlyphOrder(): note("FAIL", "same glyph set as Inter", style)
        if f.getBestCmap() != o.getBestCmap(): note("FAIL", "same character map as Inter", style)
        # --- names
        full = "Solvik " + ((w + (" Italic" if it else "")).replace("Regular Italic", "Italic"))
        ribbi = w in ("Regular", "Bold")
        exp = {1: "Solvik" if ribbi else f"Solvik {w}", 4: full, 6: "Solvik-" + style}
        exp[2] = (("Bold " if w == "Bold" else "") + ("Italic" if it else "")).strip() or "Regular" if ribbi else ("Italic" if it else "Regular")
        for k, v in exp.items():
            if nm.get(k) != v: note("FAIL", "name table", f"{style}: name {k} is {nm.get(k)!r}, expected {v!r}")
        if not ribbi and (nm.get(16) != "Solvik" or nm.get(17) != full.replace("Solvik ", "")): note("FAIL", "name table", f"{style}: typographic family/style {nm.get(16)!r}/{nm.get(17)!r}")
        for k, v in nm.items():
            if k not in (0, 8, 10, 11, 12, 13, 14) and "Inter" in v: note("FAIL", "no leftover Inter naming", f"{style}: name {k} = {v}")
        if "STAT" not in f: note("FAIL", "STAT table present", style)
        if f["OS/2"].usWinAscent < f["head"].yMax or f["OS/2"].usWinDescent < -f["head"].yMin: note("FAIL", "Windows clipping heights cover every glyph", style)
        fam[style].ul = (f["post"].underlineThickness, f["post"].underlinePosition)
        if "Open Font License" not in nm.get(13, ""): note("FAIL", "license text in font", style)
        if "Inter Project Authors" not in nm.get(0, ""): note("FAIL", "original copyright kept", style)
        if nm.get(5) != "Version 1.030": note("FAIL", "version string", f"{style}: {nm.get(5)}")
        if len(nm.get(6, "")) > 63 or len(nm.get(4, "")) > 63: note("FAIL", "name lengths", style)
        note("INFO", "credits", f"manufacturer={nm.get(8)!r} designer={nm.get(9)!r} vendor={f['OS/2'].achVendID!r} description={nm.get(10)!r}") if style == "Regular" else None
        cffn = f["CFF "].cff; top = cffn.topDictIndex[0]
        if cffn.fontNames[0] != nm.get(6): note("FAIL", "CFF name matches PostScript name", f"{style}: {cffn.fontNames[0]}")
        # --- style bits
        os2 = f["OS/2"]; fs = os2.fsSelection
        if os2.usWeightClass != num: note("FAIL", "weight class", f"{style}: {os2.usWeightClass}")
        if bool(fs & 1) != bool(it): note("FAIL", "italic flag", style)
        if bool(fs & 32) != (w == "Bold"): note("FAIL", "bold flag", style)
        if bool(fs & 64) != (w != "Bold" and not it): note("FAIL", "regular flag", f"{style}: fsSelection {bin(fs)}")
        if bool(f["head"].macStyle & 2) != bool(it) or bool(f["head"].macStyle & 1) != (w == "Bold"): note("FAIL", "macStyle", style)
        if (f["post"].italicAngle != 0) != bool(it): note("FAIL", "italic angle", style)
        if os2.fsType != 0: note("WARN", "embedding permissions", f"{style}: fsType {os2.fsType}")
        fam[style].vm = (f["hhea"].ascent, f["hhea"].descent, f["hhea"].lineGap, os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap, os2.usWinAscent, os2.usWinDescent, os2.sxHeight, os2.sCapHeight, f["head"].unitsPerEm)
        # --- metrics
        hm = f["hmtx"].metrics
        if any(a < 0 for a, _ in hm.values()): note("FAIL", "no negative advances", style)
        if f["hhea"].advanceWidthMax != max(a for a, _ in hm.values()): note("FAIL", "hhea max advance up to date", f"{style}: {f['hhea'].advanceWidthMax} vs {max(a for a,_ in hm.values())}")
        avg = round(sum(a for a, _ in hm.values() if a > 0) / max(1, sum(1 for a, _ in hm.values() if a > 0)))
        if abs(os2.xAvgCharWidth - avg) > 2: note("FAIL", "OS/2 average width up to date", f"{style}: {os2.xAvgCharWidth} vs {avg}")
        tf = {hm[g][0] for g in f.getGlyphOrder() if g.endswith(".tf") and g.split(".")[0] in ("zero","one","two","three","four","five","six","seven","eight","nine")}
        if len(tf) != 1: note("FAIL", "tabular figures share one width", f"{style}: {sorted(tf)}")
        cm = f.getBestCmap()
        import unicodedata
        bad = []
        for cp, g in cm.items():
            d = unicodedata.normalize("NFD", chr(cp))
            if len(d) > 1 and ord(d[0]) in cm and o["hmtx"][g][0] == o["hmtx"][cm[ord(d[0])]][0] and hm[g][0] != hm[cm[ord(d[0])]][0]: bad.append(g)
        if bad: note("FAIL", "accented letters match their base width", f"{style}: {bad[:8]}")
        # --- outlines
        gs, go = f.getGlyphSet(), o.getGlyphSet(); T = math.tan(math.radians(-f["post"].italicAngle))
        import json
        repl = set(json.load(open(path + ".repl"))) if it and os.path.exists(path + ".repl") else set()
        if it and len(repl) < 80: note("FAIL", "italic a, e, f rebuilt from uprights", f"{style}: {len(repl)} glyphs")
        gu = TTFont(src.replace("Italic.otf", ".otf").replace("Inter-.otf", "Inter-Regular.otf")).getGlyphSet() if it else None
        n_contour = n_dir = n_area = n_y = 0; ex = []
        for g in f.getGlyphOrder():
            ref = gu if g in repl else go
            ra, rb = RecordingPen(), RecordingPen(); gs[g].draw(ra); ref[g].draw(rb)
            ca = sum(1 for op, _ in ra.value if op == "moveTo"); cb = sum(1 for op, _ in rb.value if op == "moveTo")
            if ca != cb: n_contour += 1; ex.append(g); continue
            for op, a in ra.value:
                for p in a:
                    if not (math.isfinite(p[0]) and math.isfinite(p[1])): note("FAIL", "finite coordinates", f"{style}: {g}")
            pa, pb = AreaPen(gs), AreaPen(ref); gs[g].draw(pa); ref[g].draw(pb)
            if pb.value and (pa.value > 0) != (pb.value > 0): n_dir += 1; ex.append(g)
            if abs(pb.value) > 2000:
                r = pa.value / pb.value
                if not (0.9 < r < 1.3): n_area += 1; ex.append(f"{g}:{r:.2f}")
            ba, bb = BoundsPen(gs), BoundsPen(ref); gs[g].draw(ba); ref[g].draw(bb)
            if ba.bounds and (abs(ba.bounds[1] - bb.bounds[1]) > 60 or abs(ba.bounds[3] - bb.bounds[3]) > 60): n_y += 1; ex.append(g + ":height")
        if n_contour: note("FAIL", "contour counts match Inter", f"{style}: {n_contour} glyphs {ex[:6]}")
        if n_dir: note("FAIL", "contour direction preserved", f"{style}: {n_dir} {ex[:6]}")
        if n_area: note("WARN", "ink area within expected range of Inter", f"{style}: {n_area} glyphs {ex[:10]}")
        if n_y: note("WARN", "glyph heights unchanged", f"{style}: {n_y} glyphs {ex[:8]}")
        # --- layout tables
        fo = sorted({fr.FeatureTag for fr in o["GSUB"].table.FeatureList.FeatureRecord} | {fr.FeatureTag for fr in o["GPOS"].table.FeatureList.FeatureRecord})
        fn = sorted({fr.FeatureTag for fr in f["GSUB"].table.FeatureList.FeatureRecord} | {fr.FeatureTag for fr in f["GPOS"].table.FeatureList.FeatureRecord})
        if fo != fn: note("FAIL", "OpenType features intact", style)
        font = hb.Font(hb.Face(hb.Blob.from_file_path(path)))
        def adv(t, feats):
            buf = hb.Buffer(); buf.add_str(t); buf.guess_segment_properties(); hb.shape(font, buf, feats); return sum(p.x_advance for p in buf.glyph_positions), len(buf.glyph_infos)
        if adv("AV", {"kern": True})[0] >= adv("AV", {"kern": False})[0]: note("FAIL", "kerning active", style)
        if adv("11", {"tnum": True})[0] == adv("11", {"tnum": False})[0]: note("WARN", "tabular figures feature active", style)
        if adv("1/2", {"frac": True})[1] > 3: pass
        fam[style].stem = None
        fam[style].nadv = hm["n"][0]
# --- family-level
if len({f.ul for f in fam.values()}) != 1: note("FAIL", "one underline across the family", str({s: f.ul for s, f in fam.items()}))
vms = {s: f.vm for s, f in fam.items()}
if len(set(vms.values())) != 1: note("FAIL", "vertical metrics identical across the family", str({s: v for s, v in vms.items()}))
ps = [str(f["name"].getDebugName(6)) for f in fam.values()]
if len(set(ps)) != len(ps): note("FAIL", "PostScript names unique", str(ps))
for it in ("", "Italic"):
    seq = [fam[(w + it).replace("RegularItalic", "Italic")].nadv for w, _, _ in W]
    if seq != sorted(seq): note("WARN", "advance of n grows with weight", f"{it or 'upright'}: {seq}")
order = ["FAIL", "WARN", "INFO"]
for (lvl, chk), msgs in sorted(res.items(), key=lambda kv: order.index(kv[0][0])):
    print(lvl, "|", chk, "|", len(msgs)); [print("     ", m) for m in msgs[:6]]
print("checked", len(fam), "fonts;", sum(1 for k in res if k[0] == "FAIL"), "failing checks,", sum(1 for k in res if k[0] == "WARN"), "warnings")
