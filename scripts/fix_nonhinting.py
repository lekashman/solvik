"""What gftools fix-nonhinting does for an unhinted TrueType font: a gasp table asking for smooth rendering at
every size, and a prep program that turns on smart dropout control."""
import sys
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import ttProgram
for path in sys.argv[1:]:
    f = TTFont(path)
    gasp = newTable("gasp"); gasp.gaspRange = {0xFFFF: 15}; gasp.version = 1; f["gasp"] = gasp
    prep = newTable("prep"); prep.program = ttProgram.Program(); prep.program.fromBytecode(b"\xb8\x01\xff\x85\xb0\x04\x8d"); f["prep"] = prep
    f["head"].flags |= 1 << 3
    f.save(path)
