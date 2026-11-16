# Licences, in plain language

What you may do with Concordio Core and its data, and what you owe in return. This is
a practical guide, not legal advice. The authoritative statements are each pack's
`manifest.json`, [NOTICE.md](../NOTICE.md) and the licence texts themselves. A test
(`tests/test_licences.py`) keeps this page, the README, NOTICE and the manifests from
disagreeing.

- [At a glance](#at-a-glance)
- [Code](#code)
- [Public-domain texts](#public-domain-texts)
- [Share-alike data (CC BY-SA 4.0)](#share-alike-data-cc-by-sa-40)
- [Attribution CC BY data](#attribution-cc-by-data)
- [The KJV outside the United States](#the-kjv-outside-the-united-states)
- [Checklist for an application built on Core](#checklist-for-an-application-built-on-core)
- [Trademarks](#trademarks)

## At a glance

| What | Licence | In one line |
| --- | --- | --- |
| Code (reader, pipeline, tests) | Apache-2.0 | Use freely, keep the notices, no trademark grant. |
| `bsb` | Public domain | Dedicated 2023-04-30. No conditions. |
| `darby`, `douay-rheims`, `vulgata-clementina` | Public domain | No conditions. |
| `kjv` | Public domain in the US | UK Crown rights; see [below](#the-kjv-outside-the-united-states). |
| `theographic` (people, places, events, books, chapters, dictionary) | CC BY-SA 4.0 | Credit, and share modifications alike. |
| `pipeline/slug-lock.json` | CC BY-SA 4.0 | Concordio's slug mapping, a layer over Theographic. Same terms. |
| `chrome-en`, `chrome-es`, `versify.json`, `canon-extensions.json` | CC BY-SA 4.0 | Concordio-authored. Credit, and share modifications alike. |
| `stepbible` interlinear (release artifact; sample in git) | CC BY 4.0 | Credit Tyndale House and STEPBible. One definitions caveat, below. |
| `bsb-tables` interlinear (release artifact; sample in git) | Public domain | BSB tables and Strong's dictionaries. |

## Code

The code is Apache-2.0: use, modify and distribute it, commercially or not. Keep the
licence and notices. Apache-2.0 grants no rights in the Concordio name (§6); see
[Trademarks](#trademarks).

## Public-domain texts

Use them however you like. Crediting the source is courteous and each manifest has a
suggested line. The BSB's dedication, by the Berean Bible Translation Committee, is at
<https://berean.bible/licensing.htm>.

## Share-alike data (CC BY-SA 4.0)

Theographic and the Concordio-authored data files are CC BY-SA 4.0. In practice:

- **Credit** the creators and say what you changed. Each manifest carries a ready
  credit line and a `source.modifications` field describing the changes made so far.
- **Share modifications alike.** If you modify one of these files and distribute your
  version, your version stays CC BY-SA 4.0.
- **Do not merge it into a differently licensed file.** Keep share-alike data in its own
  files. A file that contains or is derived from Theographic stays share-alike.
- **Separate works side by side are fine.** An application that loads the packs next to
  its own code, or next to public-domain texts, does not become share-alike
  itself. Apache-2.0 code and CC BY-SA data coexist because they sit in separate files.
- **Credit Theographic's own sources too.** Theographic credits further original
  sources (chronology, genealogy, gazetteers), some with their own terms. They are
  listed in [THEOGRAPHIC-AUDIT.md](THEOGRAPHIC-AUDIT.md).

Share-alike is a deliberate choice. Core exists to be a shared foundation, and
share-alike keeps improvements to the data flowing back to everyone.

## Attribution CC BY data

STEPBible's data (the `stepbible` interlinear pack) and OpenBible.info's coordinates
(carried inside Theographic's places file) are CC BY 4.0: credit them, and you can
combine them with share-alike data. The STEPBible Hebrew definitions (TBESH) are based on the Abridged BDB
from Online Bible, whose file asks for Online Bible's permission before reuse; Concordio
is seeking it, and the `stepbible` manifest records the caveat. If that matters to you,
use the `bsb-tables` pack instead, which shares no data with STEPBible.

## The KJV outside the United States

The KJV text is public domain in the United States. In the United Kingdom the Crown
holds rights in the Authorized Version, administered by Cambridge University Press under
letters patent. The `kjv` pack applies no regional restriction. If you distribute in the
UK, take your own advice, or leave the pack out; nothing else depends on it.

## Checklist for an application built on Core

1. Show each pack's `license.attribution` somewhere reachable, such as a credits page.
2. Credit the Theographic sources as well as Theographic itself.
3. Keep share-alike data in separate files and mark your changes.
4. Keep the Apache-2.0 notices with any code you copy.
5. Do not use the Concordio or Bible Explorer names for your project.

## Trademarks

"Concordio" and "Bible Explorer" are trademarks of Clent Crumley. You may fork Core; you
may not name the fork Concordio or imply endorsement. See [TRADEMARKS.md](../TRADEMARKS.md).
