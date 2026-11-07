# Data pack format

Every data file in `web/data/packs/<id>/` is a **pack**. Packs are
self-contained, versioned, and cache-keyed by `id + version`. New packs can
be shipped without a service worker cache bump, because the loader appends
`?v=<pack.version>` to every pack file request and stale versions are simply
never requested again.

## Pack kinds

| Kind | Purpose | Required? |
| --- | --- | --- |
| `entities` | People, places, events, dictionary, books, chapters metadata. | Required (used by the reader for book/chapter metadata). |
| `translation` | Verse text, keyed by OSIS id. | At least one required at runtime; swappable at runtime. |
| `chrome` | UI strings for an interface language. | At least one required (default `chrome-en`). |
| `interlinear` | Word-level Hebrew/Greek with Strong's and morphology. Not bundled in the kernel. | Optional. |
| `imagery` | Stock or custom imagery for entities. | Optional. |

## Catalog — `web/data/packs/index.json`

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
      "license": "CC-BY-SA-4.0",
      "attribution": "Berean Standard Bible. BibleHub."
    }
  ]
}
```

- `id` — directory name under `web/data/packs/`.
- `version` — any string; comparisons are equality-based.
- `installable: false` marks packs that are advertised but not yet available
  (shipped as skeletons for forks to fill in).
- `license` and `attribution` are advisory at the catalog level; the pack's
  own `manifest.json` is authoritative.

## Per-pack manifest — `web/data/packs/<id>/manifest.json`

```json
{
  "schemaVersion": 1,
  "id": "bsb",
  "kind": "translation",
  "name": "Berean Standard Bible",
  "lang": "en",
  "textDir": "ltr",
  "version": "2026.10",
  "sizeBytes": 4314175,
  "files": { "verses": "verses.json" },
  "license": {
    "name": "Public Domain",
    "spdx": "CC-PDDC",
    "url": "https://berean.bible/licensing.htm",
    "attribution": "Berean Standard Bible…"
  },
  "source": {
    "upstream": "https://bereanbible.com/bsb.txt",
    "revision": "bsb.txt",
    "modifications": "Each verse rekeyed to OSIS id…"
  },
  "verseCount": 31102
}
```

## Translation pack — `verses.json`

A flat object keyed by OSIS id:

```json
{
  "Gen.1.1": "In the beginning God created the heavens and the earth.",
  "Gen.1.2": "Now the earth was formless and void…"
}
```

The reader looks up `<book>.<chapter>.<verse>` and renders each in order until
the next verse is missing.

## Chrome pack — `strings.json`

A flat object of i18n keys to translated strings:

```json
{
  "app.title": "Concordio Core",
  "label.book": "Book",
  "label.chapter": "Chapter"
}
```

The reader applies these to `[data-i18n]` elements in `web/index.html`.

## Denominational preset

See [PRESETS.md](PRESETS.md).
