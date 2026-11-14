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

The repository follows the [Google Fonts project template](https://github.com/googlefonts/googlefonts-project-template).
Fonts are built from the UFO sources in `sources/` with [gftools builder](https://github.com/googlefonts/gftools),
configured in `sources/config.yaml`:

    make build

This creates a Python environment in `venv/`, installs the tools listed in `requirements.in`, and
writes the fonts to `fonts/ttf`. `make test` checks them with
[fontspector](https://github.com/fonttools/fontspector) and `make proof` writes proof pages to
`out/proof`. `scripts/derivation` documents how the sources were derived from Inter.

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
