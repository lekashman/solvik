"""Add a STAT table to each static font, as Google Fonts expects: one Weight value and one Italic value per font,
with Regular and Roman elidable and style-linked to Bold and Italic."""
import sys
from fontTools.ttLib import TTFont
from fontTools.otlLib.builder import buildStatTable

WEIGHTS = {200: "ExtraLight", 300: "Light", 400: "Regular", 600: "SemiBold", 700: "Bold", 800: "ExtraBold", 900: "Black"}
for path in sys.argv[1:]:
    f = TTFont(path)
    wght = f["OS/2"].usWeightClass
    italic = bool(f["OS/2"].fsSelection & 1)
    weight = dict(value=wght, name=WEIGHTS[wght])
    if wght == 400:
        weight.update(flags=0x2, linkedValue=700)
    ital = dict(value=1, name="Italic") if italic else dict(value=0, name="Roman", flags=0x2, linkedValue=1)
    buildStatTable(f, [dict(tag="wght", name="Weight", values=[weight]), dict(tag="ital", name="Italic", values=[ital])],
                   elidedFallbackName="Regular")
    f.save(path)
