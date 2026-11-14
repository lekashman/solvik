"""Last steps for every font: hinting, then family-wide metadata.
  - CFF standard stems set from each font's own l and o, then autohinted (AFDKO otfautohint)
  - Windows clipping heights raised to the tallest and deepest glyph in the family (line spacing is
    unaffected: the fonts use the typographic metrics for that)
  - one underline thickness and position across the family (Regular's)
  - a STAT table naming each font's weight and whether it is italic"""
import glob, os, math, subprocess, shutil
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.otlLib.builder import buildStatTable
import build
WNAME = {200: "ExtraLight", 300: "Light", 400: "Regular", 600: "DemiBold", 700: "Bold", 800: "ExtraBold", 900: "Black"}
def run(src="out", dst="final2"):
    shutil.rmtree("hin", ignore_errors=True); shutil.rmtree(dst, ignore_errors=True); os.makedirs("hin"); os.makedirs(dst)
    for p in sorted(glob.glob(f"{src}/Solvik-*.otf")):
        f = TTFont(p); gs = f.getGlyphSet(); T = math.tan(math.radians(-f["post"].italicAngle))
        bp = BoundsPen(gs); gs["l"].draw(TransformPen(bp, (1, 0, -T, 1, 0, 0))); vw = round(bp.bounds[2]-bp.bounds[0])
        tops = sorted(max(q[1] for q in c["pts"]) for c in build.contours(build._rec(gs, "o"))); hw = round(tops[-1]-tops[0])
        priv = f["CFF "].cff.topDictIndex[0].Private; priv.StdVW = vw; priv.StdHW = hw; priv.StemSnapV = [vw]; priv.StemSnapH = [hw]
        f.save("hin/"+os.path.basename(p))
        r = subprocess.run(["otfautohint", "-o", f"{dst}/{os.path.basename(p)}", "hin/"+os.path.basename(p)], capture_output=True)
        if r.returncode: raise SystemExit("hinting failed: "+p)
    fonts = {p: TTFont(p) for p in sorted(glob.glob(f"{dst}/Solvik-*.otf"))}
    ymax = max(f["head"].yMax for f in fonts.values()); ymin = min(f["head"].yMin for f in fonts.values())
    reg = fonts[f"{dst}/Solvik-Regular.otf"]; ut, up = reg["post"].underlineThickness, reg["post"].underlinePosition
    for p, f in fonts.items():
        f["OS/2"].usWinAscent = ymax; f["OS/2"].usWinDescent = -ymin
        f["post"].underlineThickness = ut; f["post"].underlinePosition = up
        w = f["OS/2"].usWeightClass; it = 1 if f["post"].italicAngle else 0
        wv = dict(value=w, name=WNAME[w]); 
        if w == 400: wv.update(flags=0x2, linkedValue=700)
        iv = dict(value=it, name="Italic" if it else "Roman")
        if not it: iv.update(flags=0x2, linkedValue=1)
        buildStatTable(f, [dict(tag="wght", name="Weight", ordering=0, values=[wv]), dict(tag="ital", name="Italic", ordering=1, values=[iv])], elidedFallbackName="Regular", macNames=False)
        f["head"].fontRevision = float(str(f["name"].getDebugName(5)).split()[-1])
        f.save(p)
    for p in glob.glob(f"{src}/Solvik-*.otf"):
        b = os.path.basename(p); shutil.copy(p+".prof", f"{dst}/{b}.prof")
        if os.path.exists(p+".repl"): shutil.copy(p+".repl", f"{dst}/{b}.repl")
    return ymax, ymin, ut, up
if __name__ == "__main__":
    print("family yMax %d yMin %d, underline %d at %d" % run())
