# Solvik

![Solvik sample](documentation/solvik-sample.png)

Solvik is a sans-serif family in seven weights (Extra Light, Light, Regular, SemiBold, Bold,
Extra Bold, Black), each with an italic. It is derived from [Inter](https://github.com/rsms/inter)
by Rasmus Andersson.

## How it differs from Inter

- Round letters are widened so the o is close to a circle in every weight; stroke weight is unchanged.
- Terminals are cut flat.
- Horizontal strokes are held closer to the verticals in SemiBold and heavier.
- Italic a, e and f are the upright letters slanted, not Inter's cursive forms.
- Figures are wider; straight-sided capitals are slightly narrower.
- Spacing and kerning are rebuilt for the new shapes, with a minimum gap between any two Latin
  letters, figures or punctuation marks.

## Building

Fonts are built from the UFO sources in `sources/` with [fontmake](https://github.com/googlefonts/fontmake):

    pip install -r requirements.txt
    sh scripts/build.sh

The built fonts are written to `fonts/ttf`. `scripts/derivation` documents how the sources were
derived from Inter.

## Status

- Static fonts only. There is no variable font yet.
- The fonts are unhinted, with a `gasp` table and smart dropout control set.
- Each font has a STAT table, added by `scripts/add_stat.py` at build time.
- Characters: Latin (including extended), Cyrillic and Greek, as in Inter, plus U+030B.

## License

This Font Software is licensed under the SIL Open Font License, Version 1.1. This license is
available with a FAQ at https://openfontlicense.org. See `OFL.txt`.

## Changelog

**1.040** First release built from UFO sources with fontmake. Weight 600 named SemiBold. Added
U+030B. Private-use codepoints for alternates removed; the alternates remain available through
their OpenType features.
