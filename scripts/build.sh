#!/bin/sh
# Build the 14 static TTFs from the UFO sources with fontmake, as Google Fonts requires.
set -e
cd "$(dirname "$0")/.."
rm -rf fonts/ttf && mkdir -p fonts/ttf
for ufo in sources/*.ufo; do
  fontmake -u "$ufo" -o ttf --output-dir fonts/ttf --feature-writer None --no-production-names --keep-overlaps
done
python3 scripts/fix_nonhinting.py fonts/ttf/*.ttf
python3 scripts/add_stat.py fonts/ttf/*.ttf
