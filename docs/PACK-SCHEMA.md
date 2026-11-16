# Pack schema

The format reference for every file under `web/data/packs/`. For what is in each pack
and where it came from, see [DATA.md](DATA.md). For recipes that use these files, see
[QUERY-COOKBOOK.md](QUERY-COOKBOOK.md).

A **pack** is a directory `web/data/packs/<id>/` holding a `manifest.json` and one or
more data files. Packs are self-contained, versioned, and carry their own licence.
Readers load a pack by `kind`, so a new translation or interface language is a new
directory plus one row in the catalog, with no code change.

- [Pack kinds](#pack-kinds)
- [Catalog: `index.json`](#catalog-indexjson)
- [Manifest: `manifest.json`](#manifest-manifestjson)
- [Translation pack](#translation-pack)
- [Entities pack](#entities-pack)
- [Interlinear pack](#interlinear-pack)
- [Chrome pack](#chrome-pack)
- [Shared files at the packs root](#shared-files-at-the-packs-root)
- [Verse identifiers (OSIS)](#verse-identifiers-osis)
- [Versioning and breaking changes](#versioning-and-breaking-changes)

## Pack kinds

| Kind | Holds | In this repository |
| --- | --- | --- |
| `translation` | Verse text keyed by OSIS id | `bsb`, `kjv`, `darby`, `douay-rheims`, `vulgata-clementina` |
| `entities` | Books, chapters, people, places, events, dictionary | `theographic` |
| `chrome` | Interface strings for one language | `chrome-en`, `chrome-es` |
| `interlinear` | Word-by-word Hebrew/Greek with Strong's numbers and morphology | Release artifacts (`stepbible`, `bsb-tables`); small samples in `web/data/samples/` |
| `lexicon`, `morph-key`, `geo`, `xrefs`, `imagery` | Reserved kinds | None shipped |

Several packs of one kind can coexist. A reader lets the user pick the active
translation and the active interface language.

## Catalog: `index.json`

`web/data/packs/index.json` lists the installed packs. Readers fetch it first.

```json
{
  "schemaVersion": 2,
  "packs": [
    {
      "id": "bsb",
      "kind": "translation",
      "language": "en",
      "languageName": "English",
      "name": "Berean Standard Bible",
      "version": "2026.10",
      "required": false,
      "optional": true,
      "default": true,
      "sizeBytes": 4314175,
      "license": "CC-PDDC",
      "attribution": "Berean Standard Bible. BibleHub. https://berean.bible/"
    }
  ]
}
```

- `id` is the directory name under `web/data/packs/`.
- `version` is an opaque string; consumers compare by equality only.
- `default: true` marks the translation a reader opens with.
- `installable: false` advertises a pack that is not yet available.
- `license` and `attribution` are a summary. **The pack's own `manifest.json` is
  authoritative**, and a test checks that the two agree on the licence family (see
  [LICENSES.md](LICENSES.md)).

`index.json` holds hand-maintained licence rows, so a full pipeline run (`make data`)
overwrites it. Rebuild single packs with `--only <id>` instead.

## Manifest: `manifest.json`

```json
{
  "schemaVersion": 1,
  "id": "kjv",
  "kind": "translation",
  "name": "King James Version (1769 text)",
  "lang": "en",
  "textDir": "ltr",
  "version": "theographic-744355c",
  "sizeBytes": 4627857,
  "files": { "verses": "verses.json" },
  "license": {
    "name": "Public Domain (United States)",
    "spdx": "LicenseRef-KJV-US-PD",
    "url": "https://ebible.org/kjv/copr.htm",
    "attribution": "King James Version, the 1769 Cambridge standard text …"
  },
  "source": {
    "upstream": "https://github.com/robertrouse/theographic-bible-metadata",
    "revision": "…",
    "modifications": "Verses rekeyed to OSIS id. …"
  },
  "sourceRef": "744355c",
  "fetchHash": "7c51f6a7…",
  "verseCount": 31102,
  "requires": []
}
```

Required in every data pack (enforced by `tests/test_data.py`): `id`, `name`,
`version`, `kind`, `license`, `source`, `sizeBytes`, `files`, `schemaVersion`. Chrome
packs use a lighter manifest.

| Field | Meaning |
| --- | --- |
| `license.spdx` | An SPDX identifier where one exists (`CC-BY-SA-4.0`, `CC-PDDC`), otherwise a `LicenseRef-…` name. |
| `license.attribution` | The credit line to show. Travels with the pack. |
| `source.upstream` | Where the data came from. |
| `source.revision` | The upstream revision, tag or filename the build read. |
| `source.modifications` | What the adapter changed. Required for CC BY and CC BY-SA attribution. |
| `sourceRef` | Short identifier for the exact upstream read (a git short hash or hash prefix). |
| `fetchHash` | SHA-256 over the normalised upstream input. Detects drift even when the revision does not move. |
| `files` | Role-to-filename map. Always resolve file names through this, not by guessing. |
| `requires` | Other pack ids this pack needs. |

Builds are wall-clock-free: two builds from the same upstream revision produce
byte-identical files and manifests.

## Translation pack

`verses.json` is a flat object from OSIS verse id to plain UTF-8 text, with no markup
and no entity tags:

```json
{
  "Gen.1.1": "In the beginning God created the heavens and the earth.",
  "Gen.1.2": "Now the earth was formless and void, …"
}
```

A reader looks up `<book>.<chapter>.<verse>` and renders verses in order until the
next key is missing. Notes:

- Verse counts differ between packs: BSB and KJV have 31,102 keys; the Douay-Rheims and
  Vulgata packs number some books differently (about 35,800 keys).
- Where a translation omits a verse, the key may be present with an empty string
  (the BSB does this for 16 verses) or absent.
- Entity links are never stored in translation text. They live in the entities pack,
  so swapping translations cannot break them.

## Entities pack

The `theographic` pack. Files (named in `files`):

| File | Shape |
| --- | --- |
| `books.json` | 66 objects, canonical order: `osis`, `n` (name), `s` (short name), `t` (`OT`/`NT`), `d` (division), `cn` (chapter count). |
| `chapters.json` | 1,189 triples `[osisBook, chapter, verseCount]`. |
| `people.json` | People, see below. |
| `places.json` | Places, see below. |
| `events.json` | Events, see below. |
| `dictionary.json` | Object from entity id (`p-…`, `l-…`) to the matching Easton's Bible Dictionary text (public domain, 1897). Only entities with an entry appear. |

Fields common to people, places and events:

| Field | Meaning |
| --- | --- |
| `id` | Pack-scoped id, prefixed `p-`, `l-` or `e-`, with a numeric suffix for people and places (`p-moses-2108`). |
| `slug` | Unique, URL-safe handle. Locked by `pipeline/slug-lock.json`, so it does not change across refreshes. Use this as your stable key. |
| `n` | Display name. **Not unique.** |
| `dq` | Display qualifier, present on namesakes only (`son of Malluch`, `1 Chronicles 12:20`). |
| `aliases` | Strings an application may match in verse text to highlight this entity. |
| `verses` | Sorted OSIS ids of every verse that names the entity. |

People add: `g` (`M`/`F`), `by` and `dy` (birth and death year, strings), `bp` and
`dp` (birth and death place ids, arrays), `fa`, `mo`, `sp`, `ki`, `si` (father, mother,
spouses, children, siblings; arrays of person ids).

Places add: `ty` (feature type, `Water`, `City`, …), `ll` (`[latitude, longitude]` or
`null`), `cm` (a short comment, often the modern name).

Events add: `dt` (start date) and `pp` (participant person ids).

**Dates are strings** in an astronomical convention with a year 0: `"-4003"` is
4004 BC, `"0030-04-04"` is a full date. See
[THEOGRAPHIC-AUDIT.md](THEOGRAPHIC-AUDIT.md) for the chronology behind them.

## Interlinear pack

Built by the pipeline from STEPBible (`stepbible`) or the BSB Translation Tables
(`bsb-tables`). Large (about 58 MB each), so they are not stored in git: each tagged release
attaches them as tarballs with a `SHA256SUMS` file (`make fetch-release TAG=v0.1.0`; see
[UPDATES.md](UPDATES.md#interlinear-packs-release-artifacts)), and `make release-packs`
rebuilds them. A tarball holds one top-level directory, `<id>/`, so it unpacks into
`web/data/packs/`. A short sample of each is committed in `web/data/samples/` (see below).
One file per book at `interlinear/<Book>.json`, from OSIS id to an array of word records in
reading order:

```json
{
  "Gen.1.1": [
    { "src": "בְּרֵאשִׁ֖ית", "translit": "be.re.Shit", "gloss": "in beginning",
      "strongs": "H7225G", "lemma": "רֵאשִׁית", "morph": "HR/Ncfsa" }
  ]
}
```

- `src` is the original word exactly as the source gives it. It is **not**
  Unicode-normalised (Hebrew keeps the source's mark order). Compare with a normalised
  copy (NFD, marks stripped), never raw string equality.
- `strongs` is an extended Strong's number in `stepbible` (`H7225G`) and a base number
  in `bsb-tables` (`H7225`). The two packs differ in gloss, morphology scheme and verse
  numbering, so do not mix them within a verse. The manifest's `shape` field declares
  the differences.
- `strongs.json` maps a Strong's number to `{lemma, translit, pos, short, long}`;
  `morph_codes.json` maps each exact morphology code to prose.
- Words with no Strong's number keep `strongs: ""`. Nothing is filled in.

### Interlinear samples

`web/data/samples/<id>/` holds `stepbible-sample` and `bsb-tables-sample`: the same pack
format, cut down to one or two short books (`pipeline/samples.py`). A sample's manifest is the
full pack's with a different `id`, a `version` of `<full version>-sample`, its own `counts` and
`sizeBytes`, and a `sample` block:

```json
"sample": { "of": "stepbible", "ofVersion": "2026.10", "books": ["3John"], "note": "…" }
```

Book files are byte-identical to the full pack's; `strongs.json` and `morph_codes.json` keep
only the entries the sampled words use. Samples are **not** catalog packs: they are not listed
in `index.json`, and the rule that an interlinear pack has all 66 books applies to full packs
only. `tests/test_interlinear_samples.py` holds them to the manifest, licence, size and word
rules, and checks them against a fresh cut of the full pack when one is on disk.

## Chrome pack

`strings.json` is a flat object of interface keys to text, using dotted keys
(`label.book`, `nav.next`). A reader applies it to elements with a `[data-i18n]`
attribute and falls back to the English text baked into the HTML for missing keys. To
add a language, copy `chrome-en` to `chrome-<bcp47>`, translate, and add a catalog row.

## Shared files at the packs root

| File | Purpose |
| --- | --- |
| `versify.json` | Psalm numbering map between the Hebrew and Greek/Latin systems (`psalms.heb_to_lxx`, plus `lxx_only` for Psalm 151). Chapters only, no verse boundaries. The reader applies it to translations it knows use Greek/Latin numbering (`douay-rheims`, `vulgata-clementina`), or whose manifest sets `"psalmNumbering": "septuagint"` (an optional field; `"hebrew"` otherwise). |
| `canon-extensions.json` | The seven deuterocanonical books beyond the 66: OSIS code, name, chapter and verse counts, and `insertAfter` (Catholic ordering). |
| `denominations/` | Preset schema and a neutral `default` preset. See [PRESETS.md](PRESETS.md). |

## Verse identifiers (OSIS)

`<Book>.<chapter>.<verse>` with the standard OSIS book code: `Gen.1.1`,
`Ps.119.176`, `3John.1.14`. Codes for the 66 books are listed in
[QUERY-COOKBOOK.md](QUERY-COOKBOOK.md#setup) and in `pipeline/osis.py` (which also
carries English-name aliases). OSIS is the scholarly standard, matches citation habits,
and keeps every pack interoperable. No file keys by a numeric verse index; compute one
at load time if you need it.

## Versioning and breaking changes

- `schemaVersion` in a manifest or the catalog changes only for breaking format changes.
- A pack's `version` changes whenever its content does. Packs are cache-keyed by
  `id + version`; the reference reader appends `?v=<version>` to every pack file request.
- Core's own releases follow semantic versioning once tagged; see
  [UPDATES.md](UPDATES.md) and [../CHANGELOG.md](../CHANGELOG.md).
