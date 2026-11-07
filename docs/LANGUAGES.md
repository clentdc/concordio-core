# Language and translation packs

The kernel separates **interface language** (the UI chrome) from **Scripture
translation** (the verse text). Both are packs; either can be added or removed
at runtime by a downstream application without touching the code.

## Interface language — `chrome-<lang>`

A chrome pack holds a flat key–value map of i18n keys to translated strings.
The reader applies these to every element with a `[data-i18n]` attribute.

- `chrome-en` (English) is required and precached.
- `chrome-es` (Spanish) ships as an example second language.
- Adding a new language: copy `chrome-en` to `chrome-<bcp47>`, translate
  `strings.json`, add an entry to `index.json`.

Keys follow a hierarchical dot pattern: `label.book`, `nav.next`, `fs.title`,
`footer.credit`. Missing keys fall back to the English default baked into the
HTML.

## Scripture translation — translation packs

Translations are OSIS-keyed `verses.json` files. See [PACKS.md](PACKS.md) for
the full pack format.

The kernel ships five:

| Pack id | Name | Language | Licence |
| --- | --- | --- | --- |
| `bsb` | Berean Standard Bible | English | CC-BY-SA 4.0 |
| `kjv` | King James Version (1769) | English | Public domain |
| `darby` | Darby (1890) | English | Public domain |
| `douay-rheims` | Douay-Rheims Challoner (1752) | English | Public domain |
| `vulgata-clementina` | Vulgata Clementina (1592) | Latin | Public domain |

A reusable builder sits at `pipeline/adapters/translations_ebible.py` and
pulls verse-per-line (VPL) text from eBible.org, rekeys each verse to OSIS
form, and writes a `verses.json` and `manifest.json`. Run it to add more.
