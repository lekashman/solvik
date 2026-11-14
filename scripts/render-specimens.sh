#!/bin/sh
# Render the specimen pages in documentation/specimens to PNG images in documentation/,
# at 3200 x 2000 pixels (the card at 1520 x 1012, twice the 760 x 506 Google Fonts asks for), with headless Chrome. Run `make build` first so fonts/ttf exists.
# Set CHROME to the browser binary if it is not in the default macOS location.
set -e
cd "$(dirname "$0")/.."
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
# render <page> <image> [width height], in CSS pixels; the image is twice that size
render() {
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
    --window-size="${3:-1600},${4:-1000}" --virtual-time-budget=3000 \
    --screenshot="$PWD/documentation/$2" "file://$PWD/documentation/specimens/$1" 2>/dev/null
}
render 01-overview.html solvik-sample.png
render 02-weights.html solvik-weights.png
render 03-interface.html solvik-interface.png
render 04-editorial.html solvik-editorial.png
render 05-characters.html solvik-characters.png
render 06-languages.html solvik-languages.png
render 07-logos.html solvik-logos.png
render 08-webpage.html solvik-webpage.png
render 09-article.html solvik-article.png
render 10-card.html solvik-760x506.png 760 506
