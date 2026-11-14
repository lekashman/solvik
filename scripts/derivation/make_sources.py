"""Turn a finished Solvik font into an editable UFO source with its feature code, ready for fontmake."""
import sys, os, re, shutil, subprocess
import extractor, ufoLib2
from fontTools.ttLib import TTFont
# Google Fonts wants the repository URL in the copyright string: set REPO once the repository exists
REPO = "https://github.com/lekashman/solvik"
COPYRIGHT = "Copyright 2026 The Solvik Project Authors" + (f" ({REPO})" if REPO else "")
GFNAME = {"DemiBold": "SemiBold"}       # Google Fonts requires the standard weight name for 600
def style_names(st):
    it = st.endswith("Italic"); w = st[:-6] if it else st
    w = w or "Regular"; w = GFNAME.get(w, w)
    return w, it
def make(otf, outdir):
    st = os.path.basename(otf)[len("Solvik-"):-4]; w, it = style_names(st)
    style = (w + " Italic" if it else w).replace("Regular Italic", "Italic")
    ufo_path = f"{outdir}/Solvik-{style.replace(' ', '')}.ufo"
    f = TTFont(otf); ufo = ufoLib2.Font()
    extractor.extractUFO(otf, ufo, doKerning=False)
    ufo.kerning.clear(); ufo.groups.clear()
    # feature code decompiled from the finished font: substitutions, kerning, mark positioning
    fea = subprocess.run(["otf2fea", otf], capture_output=True, text=True).stdout
    cd = f["GDEF"].table.GlyphClassDef.classDefs; cls = {1: [], 2: [], 3: [], 4: []}
    for g in f.getGlyphOrder():
        if g in cd: cls[cd[g]].append(g)
    gdef = "table GDEF {\n    GlyphClassDef [%s], [%s], [%s], [%s];\n} GDEF;" % tuple(" ".join(cls[i]) for i in (1, 2, 3, 4))
    fea, n = re.subn(r"table GDEF \{.*?\} GDEF;", lambda m: gdef, fea, count=1, flags=re.S); assert n == 1
    # inside "feature aalt" the decompiler repeats script and language lines that the syntax forbids there
    fea = re.sub(r"feature aalt \{.*?\} aalt;", lambda m: re.sub(r"^\s*(script|language)\s+[^;]+;\s*\n", "", m.group(0), flags=re.M), fea, flags=re.S)
    # names of the stylistic sets and character variants (the decompiler drops them)
    nm = {n.nameID: str(n) for n in f["name"].names if n.platformID == 3}
    for fr in f["GSUB"].table.FeatureList.FeatureRecord:
        p = fr.Feature.FeatureParams; tag = fr.FeatureTag
        if p is None or f"NAMED {tag}" in fea: continue
        if tag.startswith("ss") and getattr(p, "UINameID", None) in nm:
            block = '    # NAMED %s\n    featureNames {\n        name "%s";\n    };\n' % (tag, nm[p.UINameID])
        elif tag.startswith("cv") and getattr(p, "FeatUILabelNameID", None) in nm:
            block = '    # NAMED %s\n    cvParameters {\n        FeatUILabelNameID {\n            name "%s";\n        };\n    };\n' % (tag, nm[p.FeatUILabelNameID])
        else: continue
        k = fea.find("feature %s {\n" % tag)
        if k >= 0: k += len("feature %s {\n" % tag); fea = fea[:k] + block + fea[k:]
    # U+030B combining double acute, required by Google Fonts' Latin Core set and absent from Inter:
    # the spacing double acute, placed and attached the way the combining acute is
    def box(name):
        xs = [p.x for c in ufo[name] for p in c]; return (min(xs) + max(xs)) / 2
    if "uni030B" not in ufo and "hungarumlaut" in ufo and "acutecomb" in ufo and "acute" in ufo:
        shift = box("acutecomb") - box("acute"); g = ufo.newGlyph("uni030B"); src = ufo["hungarumlaut"]
        g.width = 0; g.unicodes = [0x030B]
        pen = g.getPointPen()
        for c in src:
            pen.beginPath()
            for p in c: pen.addPoint((p.x + shift, p.y), segmentType=p.type, smooth=p.smooth)
            pen.endPath()
        d = int(round(box("uni030B") - box("acutecomb")))
        fea = re.sub(r"(    markClass (?:\[[^\]]*\bacutecomb\b[^\]]*\]|acutecomb) <anchor (-?\d+) (-?\d+)> (@\w+);\n)",
                     lambda m: m.group(1) + "    markClass uni030B <anchor %d %s> %s;\n" % (int(m.group(2)) + d, m.group(3), m.group(4)), fea)
        fea = fea.replace("GlyphClassDef [", "GlyphClassDef [", 1)
        k = fea.index("GlyphClassDef"); parts = fea[k:fea.index(";", k)].split("], [")
        parts[2] = parts[2] + " uni030B"; fea = fea[:k] + "], [".join(parts) + fea[fea.index(";", k):]
        order = list(ufo.lib.get("public.glyphOrder", [])); order.append("uni030B"); ufo.lib["public.glyphOrder"] = order
    ufo.features.text = fea
    # private-use codepoints for alternate letters exist only in the uprights; Google Fonts wants every
    # style to cover the same characters, and the alternates stay reachable through their features
    for g in ufo:
        g.unicodes = [u for u in g.unicodes if not (0xE000 <= u <= 0xF8FF)]
    # straight stems and bars that drifted off true by a unit in rounding are squared up
    for g in ufo:
        for c in g:
            pts = list(c); n = len(pts)
            for a in range(n):
                p, q = pts[a], pts[(a + 1) % n]
                if p.type is None or q.type != "line": continue
                if not it and abs(q.x - p.x) == 1 and abs(q.y - p.y) >= 30: q.x = p.x
                if abs(q.y - p.y) == 1 and abs(q.x - p.x) >= 30: q.y = p.y
    i = ufo.info
    ribbi = w in ("Regular", "Bold")
    i.familyName = "Solvik"; i.styleName = style
    i.styleMapFamilyName = "Solvik" if ribbi else f"Solvik {w}"
    i.styleMapStyleName = (("bold " if w == "Bold" else "") + ("italic" if it else "")).strip() or "regular"
    i.versionMajor, i.versionMinor = 1, 40
    i.copyright = COPYRIGHT
    i.openTypeNameVersion = "Version 1.040"
    i.openTypeNameUniqueID = f"1.040;NONE;Solvik-{style.replace(' ', '')}"
    i.postscriptFontName = f"Solvik-{style.replace(' ', '')}"; i.postscriptFullName = f"Solvik {style}"
    i.openTypeNamePreferredFamilyName = None if ribbi else "Solvik"
    i.openTypeNamePreferredSubfamilyName = None if ribbi else style
    i.openTypeNameWWSFamilyName = None; i.openTypeNameWWSSubfamilyName = None
    i.openTypeNameManufacturer = "The Solvik Project Authors"; i.openTypeNameManufacturerURL = REPO
    i.openTypeNameDesigner = "The Solvik Project Authors, based on Inter by Rasmus Andersson"; i.openTypeNameDesignerURL = REPO
    i.openTypeNameDescription = "Solvik is a sans-serif family derived from Inter (https://github.com/rsms/inter): wider, rounder bowls, flat terminals, upright-shaped italics, and spacing and kerning redone to match."
    i.openTypeNameLicense = "This Font Software is licensed under the SIL Open Font License, Version 1.1. This license is available with a FAQ at: https://openfontlicense.org"
    i.openTypeNameLicenseURL = "https://openfontlicense.org"
    i.openTypeOS2VendorID = "NONE"; i.openTypeOS2Type = []
    i.openTypeOS2Selection = [7]            # line spacing from the typographic metrics
    i.trademark = None
    i.openTypeNameRecords = []
    if os.path.exists(ufo_path): shutil.rmtree(ufo_path)
    ufo.save(ufo_path)
    return ufo_path, style
if __name__ == "__main__":
    print(make(sys.argv[1], sys.argv[2]))
