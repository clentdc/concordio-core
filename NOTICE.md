# NOTICE

This repository is Apache License 2.0 code with bundled data from upstream
open-licensed sources. The code licence does not relicense the data; each
pack retains its own licence as named in its `manifest.json`.

## Bible texts

| Pack | Source | Licence |
| --- | --- | --- |
| `bsb` — Berean Standard Bible | https://berean.bible/ | Public domain (dedicated by the Berean Bible Translation Committee on 2023-04-30; see https://berean.bible/licensing.htm) |
| `kjv` — King James Version (1769 text) | Supplied through Theographic Bible Metadata, whose data-source list names "King James Version, 1769 Cambridge Edition" (it does not say where its own copy came from) | Public domain in the United States. In the United Kingdom the Crown holds rights in the Authorized Version, administered by Cambridge University Press under letters patent; use of this pack in the UK is subject to legal review. |
| `darby` — J. N. Darby translation (1890) | eBible.org | Public domain |
| `douay-rheims` — Douay-Rheims Bible, Challoner revision (1752) | eBible.org | Public domain |
| `vulgata-clementina` — Vulgata Clementina (1592) | eBible.org | Public domain |

## Interface strings

| Pack | Source | Licence |
| --- | --- | --- |
| `chrome-en` — English interface strings | Written for this project | CC-BY-SA 4.0 |
| `chrome-es` — Spanish interface strings | Written for this project | CC-BY-SA 4.0 |

## Concordio-authored data

| File | What it is | Licence |
| --- | --- | --- |
| `pipeline/slug-lock.json` | Stable, unique URL slugs for every Theographic person, place and event (the slug lock) | CC-BY-SA 4.0 |

The lock is a layer over Theographic Bible Metadata (CC-BY-SA 4.0); it carries the same share-alike licence.

## Metadata

- **Theographic Bible Metadata** — Robert Rouse.
  https://github.com/robertrouse/theographic-bible-metadata
  Licence: CC-BY-SA 4.0.
  Used for: books, chapters, people, places, events, chronology, the KJV verse
  text and Easton's Bible Dictionary entries. Its chronology follows Floyd Nolen
  Jones. Theographic credits further original sources, several with their own
  licences; they are catalogued in `docs/THEOGRAPHIC-AUDIT.md` and should be credited
  too.
- **OpenBible.info Bible Geocoding** — place coordinates carried inside
  Theographic's places. Licence: CC-BY 4.0. https://www.openbible.info/geo/
- **Easton's Bible Dictionary** — M. G. Easton, 1897, public domain, via Theographic.

## Software

- **Open-source fonts**: Inter (SIL OFL), Newsreader (SIL OFL). Fonts are
  linked from Google Fonts in `web/index.html`; this repository ships no
  font files.
- **Apache License 2.0** code written for the Concordio Core kernel by
  Clent Crumley and contributors.

## Trademarks

See [TRADEMARKS.md](TRADEMARKS.md). Nothing in this file grants any trademark
rights.
