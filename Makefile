# Concordio Core: build the data packs, run the checks. `make help` lists the tasks.
PY   ?= python3
PORT ?= 8000

CACHE   := .cache
THEO    := $(CACHE)/theographic-bible-metadata
BSB_TXT := $(CACHE)/bsb/bsb.txt
STEP    := $(CACHE)/stepbible
BTAB    := $(CACHE)/bsb-tables/bsb_tables.tsv
SXML    := $(CACHE)/strongs-xml
# Pinned inputs for the bsb-tables interlinear pack (see pipeline/adapters/bsb_tables.py).
BTAB_SHA  := aa2a9a0f004d015738cd1839c7c56c3be2549e0d4f4537090c2017268c223c60
STRONGS_C := 0acd2f251c2d35ff8db2dece4e0593979d3ac223

.PHONY: help serve data refresh-data check test fetch fetch-theographic fetch-bsb fetch-stepbible fetch-bsb-tables

help:            ## List the available tasks
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/ -/'

serve:           ## Serve web/ at http://localhost:$(PORT) (the reader needs http, not file://)
	cd web && $(PY) -m http.server $(PORT)

# Source fetches: each target downloads one upstream into .cache/ (which git ignores).
$(THEO):
	git clone --depth 1 https://github.com/robertrouse/theographic-bible-metadata.git $(THEO)

$(BSB_TXT):
	mkdir -p $(CACHE)/bsb
	curl -fsSL -o $(BSB_TXT) https://bereanbible.com/bsb.txt

# STEPBible is a large repo; sparse-clone only the folders we use.
$(STEP):
	mkdir -p $(STEP)
	cd $(STEP) && git clone --depth 1 --filter=blob:none --sparse https://github.com/STEPBible/STEPBible-Data.git . \
	  && git sparse-checkout set "Translators Amalgamated OT+NT" "Lexicons" "Morphology codes"

# BSB Translation Tables (about 85 MB, unversioned upstream: the hash is checked and a mismatch warns)
# and the two Strong's dictionary XML files, pinned to an openscriptures/strongs commit.
$(BTAB):
	mkdir -p $(CACHE)/bsb-tables
	curl -fsSL -o $(BTAB) https://bereanbible.com/bsb_tables.tsv
	@echo "$(BTAB_SHA)  $(BTAB)" | sha256sum -c - || echo "WARNING: bsb_tables.tsv differs from the reviewed pin; re-check berean.bible/terms.htm and update the pin"

$(SXML)/strongsgreek.xml:
	mkdir -p $(SXML)
	curl -fsSL -o $@ https://raw.githubusercontent.com/openscriptures/strongs/$(STRONGS_C)/greek/StrongsGreekDictionaryXML_1.4/strongsgreek.xml

$(SXML)/StrongHebrewG.xml:
	mkdir -p $(SXML)
	curl -fsSL -o $@ https://raw.githubusercontent.com/openscriptures/strongs/$(STRONGS_C)/hebrew/StrongHebrewG.xml

fetch-theographic: $(THEO)       ## Clone Theographic Bible Metadata into .cache/
fetch-bsb:         $(BSB_TXT)    ## Download the Berean Standard Bible plain text into .cache/
fetch-stepbible:   $(STEP)       ## Sparse-clone STEPBible interlinear, lexicons and morphology into .cache/
fetch-bsb-tables:  $(BTAB) $(SXML)/strongsgreek.xml $(SXML)/StrongHebrewG.xml  ## Download the BSB Translation Tables and Strong's XML into .cache/
fetch: fetch-theographic fetch-bsb fetch-stepbible fetch-bsb-tables  ## Download every source the pack builders need

# Rebuilding writes into web/data/packs/. Use --only to rebuild one pack and keep the
# hand-maintained rows of index.json (licences, translations, interface strings):
#   python3 -I pipeline/build.py .cache --only theographic
data: fetch      ## Rebuild every pack the pipeline owns (overwrites index.json: review the diff)
	$(PY) -I pipeline/build.py $(CACHE)

# The weekly job. It rebuilds only the packs core tracks in git (index.json also holds
# hand-maintained rows, so a full `make data` would overwrite it) and fetches no big packs.
refresh-data:    ## Pull the latest Theographic and BSB, then rebuild those packs (and KJV) in web/data/packs/
	$(MAKE) $(THEO) $(BSB_TXT)
	git -C $(THEO) pull --ff-only
	rm -f $(BSB_TXT)
	$(MAKE) $(BSB_TXT)
	for id in theographic bsb kjv; do $(PY) -I pipeline/build.py $(CACHE) --only $$id || exit 1; done

check:           ## Run the data, licence, reserved-material, cookbook and reader checks
	node --check web/js/app.js
	node --check web/js/versify.js
	node --check web/sw.js
	$(PY) -m json.tool web/manifest.webmanifest > /dev/null
	$(PY) tests/test_data.py
	$(PY) tests/test_licences.py
	$(PY) tests/test_cookbook.py
	node tests/test_versify.js
	$(PY) tests/test_reserved_material.py

test: check      ## Alias for check
