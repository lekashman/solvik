SOURCES=$(shell python3 scripts/read-config.py --sources )
FAMILY=$(shell python3 scripts/read-config.py --family )

help:
	@echo "###"
	@echo "# Build targets for $(FAMILY)"
	@echo "###"
	@echo
	@echo "  make build:  Builds the fonts and places them in the fonts/ directory"
	@echo "  make test:   Tests the fonts with fontspector"
	@echo "  make proof:  Creates HTML proof documents in the out/proof directory"
	@echo

build: build.stamp

venv: venv/touchfile

# gftools builder makes the static fonts. It writes a STAT table only for variable fonts,
# so scripts/add_stat.py adds one to each static font afterwards.
build.stamp: venv sources/config.yaml $(SOURCES) scripts/add_stat.py
	rm -rf fonts
	(for config in sources/config*.yaml; do . venv/bin/activate; gftools builder $$config; done) && . venv/bin/activate && python3 scripts/add_stat.py fonts/ttf/*.ttf && touch build.stamp

venv/touchfile: requirements.txt requirements.in
	test -d venv || python3 -m venv venv
	. venv/bin/activate; pip install -Ur requirements.txt
	touch venv/touchfile

test: build.stamp
	which fontspector || (echo "fontspector not found. Please install it with 'cargo binstall fontspector'." && exit 1)
	mkdir -p out/ out/fontspector; fontspector --profile googlefonts -l warn --full-lists --succinct --html out/fontspector/fontspector-report.html --ghmarkdown out/fontspector/fontspector-report.md --badges out/badges fonts/ttf/*.ttf || echo '::warning file=sources/config.yaml,title=fontspector failures::The fontspector QA check reported errors in your font. Please check the generated report.'

proof: venv build.stamp
	which diff3proof || (echo "diff3proof not found. Please install it with 'cargo binstall diffenator3'." && exit 1)
	mkdir -p out/ out/proof; for font in fonts/ttf/*.ttf; do diff3proof $$font --output out/proof/$$(basename $$font .ttf) || exit 1; done

clean:
	rm -rf venv build.stamp out
	find . -name "*.pyc" -delete

.PHONY: help build venv test proof clean
