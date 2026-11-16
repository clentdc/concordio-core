# Data

Where Concordio Core's data comes from, what is in each pack, and the rules that keep
it trustworthy and swappable. For file formats see [PACK-SCHEMA.md](PACK-SCHEMA.md); for
licences see [LICENSES.md](LICENSES.md).

- [Rules](#rules)
- [What is in the repository](#what-is-in-the-repository)
- [Sources](#sources)
- [Entity highlighting across translations](#entity-highlighting-across-translations)
- [Building the data](#building-the-data)
- [Known gaps](#known-gaps)
- [Adding a source](#adding-a-source)

## Rules

1. **Open sources only,** each credited in [NOTICE.md](../NOTICE.md) and in the pack's
   manifest.
2. **Never invent a link.** Every connection between a name and a verse comes from
   source data. If a source does not say a verse mentions someone, Core does not
   draw it.
3. **Neutral presentation.** Data and metadata without doctrinal commentary.
4. **Rebuilds are reproducible.** The same source revision produces byte-identical
   packs. This has been checked for `theographic`, `bsb`, `kjv`, `stepbible` and
   `bsb-tables`.
5. **A translation swap breaks nothing.** Verses are keyed by OSIS id; entity links
   live in the entities pack; translations are just text.
6. **Concordio's additions are separate and labelled.** The slug lock, the Psalm
   numbering map and the canon extensions are Concordio-authored files, each with its
   own licence statement. They sit beside the upstream data, not inside it.

## What is in the repository

Under `web/data/packs/`:

| Pack | What | Size | Source | Licence |
| --- | --- | --- | --- | --- |
| `theographic` | 66 books, 1,189 chapters, 3,067 people, 1,298 places, 450 events linked to 31,102 verses; Easton's dictionary entries | 3.0 MB | Theographic Bible Metadata | CC BY-SA 4.0 |
| `bsb` | Berean Standard Bible | 4.3 MB | berean.bible | Public domain |
| `kjv` | King James Version, 1769 text | 4.6 MB | Via Theographic | Public domain (US); UK Crown rights, see [LICENSES.md](LICENSES.md) |
| `darby` | Darby Bible (1890) | 4.5 MB | eBible.org | Public domain |
| `douay-rheims` | Douay-Rheims, Challoner revision, with the deuterocanon | 5.1 MB | eBible.org | Public domain |
| `vulgata-clementina` | Latin Vulgate, Clementine edition | 4.5 MB | eBible.org | Public domain |
| `chrome-en`, `chrome-es` | Interface strings | small | Written for the project | CC BY-SA 4.0 |
| `versify.json`, `canon-extensions.json` | Psalm numbering map; books beyond the 66 | small | Concordio | CC BY-SA 4.0 |

Under `pipeline/`: the adapters that build all of the above, and `slug-lock.json`, the
locked URL slug for every person, place and event (CC BY-SA 4.0).

**Delivered as release artifacts, not stored in git:** the `stepbible` interlinear pack
(Hebrew/Greek words with Strong's numbers and morphology, STEPBible, CC BY 4.0) and the
`bsb-tables` interlinear pack (the BSB Translation Tables with public-domain Strong's
data). Each is about 58 MB unpacked (about 9.5 MB as a tarball). Every tagged release
attaches `concordio-pack-<id>-<tag>.tar.gz` for each, plus a `SHA256SUMS` file. Fetch and
verify with `make fetch-release TAG=v0.1.0`; see [UPDATES.md](UPDATES.md#interlinear-packs-release-artifacts).
They are built in CI from pinned upstream sources (`make release-packs`), so anyone can
also rebuild them and compare hashes.

**Samples in git:** `web/data/samples/` holds a small cut of each interlinear pack so a
fresh clone has real interlinear data without a download.

| Sample | Cut of | Books | Licence |
| --- | --- | --- | --- |
| `stepbible-sample` | `stepbible` | 3 John (14 verses, Greek) | CC BY 4.0 |
| `bsb-tables-sample` | `bsb-tables` | 3 John and Obadiah (35 verses, Greek and Hebrew) | Public domain |

A sample is cut by `pipeline/samples.py`, never edited: its book files are byte-identical to
the full pack's, and its `strongs.json` and `morph_codes.json` keep only the entries those
books use. Each has its own manifest, version (`<full version>-sample`) and a `sample` block
naming its parent. They are not catalog packs: they are not in `index.json` and live outside
`web/data/packs/`, so a reader never mistakes them for the full pack. Hebrew is in the
`bsb-tables` sample only: the STEPBible sample is Greek so that it carries none of
STEPBible's Hebrew definitions, which have an open permission caveat
([LICENSES.md](LICENSES.md#attribution-cc-by-data)).

## Sources

| Source | Used for | Licence |
| --- | --- | --- |
| [Theographic Bible Metadata](https://github.com/robertrouse/theographic-bible-metadata) (Robert Rouse) | People, places, events, books, chapters, the KJV text, Easton's entries | CC BY-SA 4.0 |
| [Berean Standard Bible](https://berean.bible/) | The `bsb` pack | Public domain (dedicated 2023-04-30) |
| [eBible.org](https://ebible.org/) | `darby`, `douay-rheims`, `vulgata-clementina` | Public domain |
| [STEPBible Data](https://github.com/STEPBible/STEPBible-Data) (Tyndale House) | `stepbible` interlinear | CC BY 4.0 |
| [Strong's concise dictionaries](https://github.com/openscriptures/strongs) (Open Scriptures) | `bsb-tables` lexicon | Public domain |
| [OpenBible.info Geocoding](https://www.openbible.info/geo/) | Place coordinates, carried inside Theographic's places | CC BY 4.0 |

Theographic itself draws on many secondary sources (chronology, genealogy, gazetteers).
They are catalogued in [THEOGRAPHIC-AUDIT.md](THEOGRAPHIC-AUDIT.md).

## Entity highlighting across translations

Translation text ships as plain Unicode. To underline names, an application:

1. Builds a reverse index from verse id to the entities that name it (recipe 4 in the
   [cookbook](QUERY-COOKBOOK.md#4-which-entities-are-in-a-verse)).
2. Matches each entity's `aliases` against that verse's text, longest first, whole word,
   case-insensitive.
3. Wraps each match so it can be styled and made clickable.

A new translation is supported the moment its pack is installed; no step regenerates
markup per translation. A translation that renames an entity (such as "Simon Peter" for
"Peter") highlights that mention only if the name is in `aliases`.

## Building the data

```bash
make data            # fetch every source into .cache/, then build every pack (including the big interlinear ones)
make release-packs   # build only the two interlinear packs, into dist/packs/ (index.json untouched)
make samples         # recut web/data/samples/ from dist/packs/
make refresh-data    # the weekly job: pull the latest Theographic and BSB, rebuild theographic, bsb, kjv
make check           # data, licence and reserved-material checks
```

Each adapter in `pipeline/adapters/` fetches or reads its upstream from `.cache/`,
normalises verse keys to OSIS, writes its pack files, and writes a `manifest.json` that
records the upstream revision, licence and list of modifications. The build order is in
`pipeline/packs.py`.

**Warning:** `make data` writes `web/data/packs/index.json`, which also holds
hand-maintained licence rows. In a checkout where `index.json` matters, run a single
pack instead: `python3 -I pipeline/build.py .cache --only theographic`. The two interlinear
packs have no catalog row, so build them with `make release-packs`, which stages them in
`dist/packs/` and never touches `index.json`.

## Known gaps

- **The reader has no transliteration yet.** The interlinear packs carry a
  transliteration per word, but the reader does not show interlinear text, and there is
  no shared transliterator for other uses. On the roadmap.
- **Highlighting is by alias matching** and misses mentions whose wording is not in
  `aliases`.
- **Events have no inline target.** They link to whole verses, not phrases.
- **Entity coverage stops at the 66-book canon.** The deuterocanonical books in the
  Douay-Rheims and Vulgata packs have text (the reader's Canon select now reaches them)
  but no people, places or events. Theographic
  has no verse references for them.
- **`versify.json` maps Psalm chapters only.** The reader uses it: asking for Psalm 23 in
  the Douay-Rheims shows that translation's Psalm 22, labelled. The map has no verse
  boundaries, so where the numberings merge or split Psalms (9 and 10, 114 and 115, 116,
  147) the reader shows whole chapters, never part of one. Other books whose versification
  differs between traditions are not covered. No translation manifest says which Psalm
  numbering it uses; the reader keeps an explicit table (see
  [READER-PLAN.md](READER-PLAN.md)).
- **Psalm 151 is in `versify.json` (`lxx_only`) but in no shipped pack,** so it cannot be
  read.
- **Year 0 is assumed.** The Theographic dates use a year-0 convention; the pipeline
  does not yet assert that on every build.
- **STEPBible's lexicon does not cover every number its words use.** In the `stepbible`
  pack some extended Strong's numbers on words (for example `G3165`, `H3069`) have no
  entry in `strongs.json`, and many Hebrew morphology codes have no entry in
  `morph_codes.json`. Nothing is filled in; look a number up and handle a miss.

## Adding a source

1. Write `pipeline/adapters/<id>.py` that fetches the upstream, normalises to OSIS, and
   writes the pack files for its kind. Copy `translations_ebible.py` for a
   verse-per-line translation.
2. Add a row to `pipeline/packs.py`.
3. Add the attribution to [NOTICE.md](../NOTICE.md) and the licence and modifications to
   the manifest.
4. Add a catalog row in `web/data/packs/index.json` with the matching licence.
5. Run `make check`. The data, licence and reserved-material tests must pass.
