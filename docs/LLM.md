# Guide for AI agents and LLM tooling

Concordio Core is a static, offline dataset of the Bible plus people, places and events
linked to verses. There is no server and no API key: everything is JSON files you can
read directly. This page tells an agent how to use it correctly. A shorter pointer lives
in [../llms.txt](../llms.txt).

## Orient in sixty seconds

1. Read `web/data/packs/index.json`. It lists every pack with its kind, version and licence.
2. Read a pack's `manifest.json` before its data. `files` names the data files;
   `license.attribution` is the credit you must show.
3. Verses are keyed by **OSIS id**: `Book.chapter.verse`, e.g. `John.3.16`, `Ps.23.1`,
   `1Cor.13.4`. Book codes are in [QUERY-COOKBOOK.md](QUERY-COOKBOOK.md#setup).

| To answer | Read |
| --- | --- |
| What does verse X say? | `web/data/packs/<translation>/verses.json`, key `X` |
| Who or what is named in verse X? | Reverse index over `theographic/{people,places,events}.json` (`verses` lists), [cookbook recipe 4](QUERY-COOKBOOK.md#4-which-entities-are-in-a-verse) |
| Where is person P named? | `theographic/people.json`, find by `slug`, read `verses` |
| Who are P's relatives? | `fa`, `mo`, `sp`, `ki`, `si` on the person (arrays of person ids) |
| Where is place L? | `theographic/places.json`, `ll` is `[lat, lon]` or `null` |
| When did event E happen? | `theographic/events.json`, `dt` (a string; year 0 exists) |
| Dictionary text for an entity | `theographic/dictionary.json`, keyed by entity id |
| Psalm numbering in another tradition | `web/data/packs/versify.json` |
| The Hebrew or Greek words of a verse, with Strong's numbers | An interlinear pack: `interlinear/<Book>.json`, key `X`. In a fresh clone only the samples exist (`web/data/samples/`: 3 John in both, Obadiah in `bsb-tables-sample`); the full packs come from a release, see below |

Fourteen runnable recipes are in [QUERY-COOKBOOK.md](QUERY-COOKBOOK.md). Format details
are in [PACK-SCHEMA.md](PACK-SCHEMA.md).

## Rules to follow

- **Never infer a link the data does not contain.** If an entity's `verses` list does not
  include a verse, say the data records no such link, not that the entity is absent
  from the text.
- **Cite precisely.** Give the OSIS id, the translation pack and its `version`. Entity
  claims should name the pack (`theographic`) and its `sourceRef`.
- **Join on `slug` or `id`, never on `n`.** Names repeat; 26 people are named Zechariah.
- **Dates are strings** in a year-0 convention (`"-4003"` is 4004 BC), from one chronology
  among several. Say so when you state a date; see [THEOGRAPHIC-AUDIT.md](THEOGRAPHIC-AUDIT.md).
- **Mind the translation.** Words differ between translations; entity links do not. Use
  entity links for "who/where/when" and verse text for "what is said".
- **Check for empty or missing verses.** The BSB keeps 16 keys with empty text.
- **Present neutrally.** The data carries no doctrinal framing and neither should a
  summary of it.
- **Respect the licences.** Public-domain texts are free; Theographic and the Concordio
  data files are CC BY-SA 4.0 and need credit. See [LICENSES.md](LICENSES.md).

## What is not here

No commentary, no cross-references, no entity data for the
deuterocanonical books, and no search index. The full interlinear packs are not in the git
tree (see below); only two short samples are. Build what you need on top; the files are
small enough to load whole.

## Interlinear data

The two full interlinear packs (`stepbible`, `bsb-tables`, about 58 MB each) are attached to
each tagged release as tarballs with a `SHA256SUMS` file. To use them, run
`make fetch-release TAG=<tag>`: it downloads the release, checks every hash, and unpacks into
`web/data/packs/` (git ignores those two directories). Read the pack's `manifest.json` first:
its `shape` field says how the two packs differ (gloss kind, morphology scheme, Strong's
format, verse numbering), so do not mix them within a verse. Samples are cuts of the same
data, never edited: a verse in `stepbible-sample` equals that verse in `stepbible`. Cite the
pack id and `version` (a sample's version ends in `-sample`). Details: [UPDATES.md](UPDATES.md).

## Staying current

Pin a tagged release rather than `main`; the data refreshes weekly through reviewed
pull requests ([UPDATES.md](UPDATES.md)).
