# How the sources were derived

Solvik's outlines, spacing and kerning were produced from Inter 4.1's static fonts by the scripts in
this folder (`build.py` and the modules it imports), then finished and checked (`finalize.py`,
`preflight.py`, `proximity.py`). `make_sources.py` turned each finished font into the UFO in
`/sources`, with its layout features decompiled into `features.fea`. `compare.py` confirms that a
font built from a UFO shapes text exactly like the finished font it came from. That held when the
UFOs were made; mark positioning for Cyrillic and Greek was added to the UFOs afterwards.

The UFOs in `/sources` are the sources of record from here on: edit them and run
`make build`. The scripts in this folder document where they came from. File paths inside
them reflect the machine they were run on.
