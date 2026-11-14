#!/bin/sh
# Render the specimen pages in documentation/specimens to PNG images in documentation/,
# at 3200 x 2000 pixels, with headless Chrome. Run `make build` first so fonts/ttf exists.
# Set CHROME to the browser binary if it is not in the default macOS location.
set -e
cd "$(dirname "$0")/.."
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
render() {
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
    --window-size=1600,1000 --virtual-time-budget=3000 \
    --screenshot="$PWD/documentation/$2" "file://$PWD/documentation/specimens/$1" 2>/dev/null
}
render 01-overview.html solvik-sample.png
render 02-weights.html solvik-weights.png
render 03-interface.html solvik-interface.png
render 04-editorial.html solvik-editorial.png
render 05-characters.html solvik-characters.png
