# Theographic source audit

The `theographic` pack is a compacted copy of
[Theographic Bible Metadata](https://github.com/robertrouse/theographic-bible-metadata)
by Robert Rouse. Theographic in turn draws on many secondary sources. This page records
what they are, which fields they support, and which of them reach the data Core ships, so
that builders can credit them and judge how far to trust a date or a coordinate.

**Audited:** 6 November 2026, by Clent Crumley with AI assistance, against Theographic
commit `744355c`. Every claim traces to Theographic's own documentation
(`README`, `data-source-bibliography.md`, `chronology-and-dates.md`). Theographic has
moved since (the weekly refresh now tracks it), and these findings have not been
re-verified against newer commits.

## Headline findings

1. **Event and people dates follow Floyd Nolen Jones**, not Edwin Thiele, including the
   Divided Monarchy kings. Theographic moved off Thiele in October 2026 (its
   `chronology-and-dates.md` has the corrections log).
2. **Verse years follow Ussher**, via the marginal dates in R. A. Torrey's *Treasury of
   Scripture Knowledge* (1880). They can differ from event dates by a few years, and in
   the New Testament by three (crucifixion AD 30 per Jones; AD 33 per Ussher at
   Acts 2:1). Core does not ship verse years.
3. **Acts event dates come from Todd Atwood** (ThM), not Jones. They use the same AD 30
   crucifixion anchor, so they agree with the Gospel events.
4. **Easton's Bible Dictionary text** comes from the Christian Classics Ethereal Library
   XML edition, not a fresh transcription of the 1897 print edition.
5. **Place coordinates are the best of two gazetteers.** Each place record carries both
   OpenBible.info and Recogito coordinates, and Theographic picks one as the resolved
   `latitude`/`longitude`. Core's `ll` comes from that resolved pair, falling back to
   the OpenBible value.
6. **Paul's journey routes** are academically cited, but the routes are not in the
   `places.json` Core ships (see below).

## What reaches Core's `theographic` pack

| Core field | Theographic field | Source |
| --- | --- | --- |
| `events[].dt` | `events.startDate` | Jones (OT and Gospels); Atwood (Acts) |
| `people[].by`, `dy` | `people.birthYear`, `deathYear` | Jones |
| `people[].fa/mo/sp/ki/si` | family relationships | Marshall Genealogy; Complete Bible Genealogy |
| `*.verses` | verse tagging | STEPBible TIPNR (people); Theographic's own tagging |
| `places[].ll` | `latitude`/`longitude` | OpenBible.info Geocoding and Pelagios Recogito |
| `dictionary.json` | `dictText` | Easton's Bible Dictionary (CCEL XML) |
| `kjv/verses.json` | `verseText` | King James Version, 1769 Cambridge edition |

Not shipped in Core: verse years (`yearNum`), the 1,030-place geospatial file enriched
from Pleiades, Digital Manna, Wikidata and PeriodO, and Paul's journey route files.

## Source catalogue

**Translation base:** King James Version, 1769 Cambridge edition (US public domain).

**Chronology:**

- Floyd Nolen Jones, *The Chronology of the Old Testament: A Return to the Basics*
  (Master Books; first edition 1993). Jones's framework and anchor dates come from
  James Ussher, *Annales Veteris Testamenti* (1650-54).
- Todd Atwood, ThM, timelines of the Book of Acts, supplied to Theographic.
- R. A. Torrey, *The Treasury of Scripture Knowledge* (1880), for verse years.

**People:**

- STEPBible, *Translators Individualised Proper Names with all References* (TIPNR),
  Tyndale House, CC BY 4.0.
- Marshall Genealogy (marshallgenealogy.org/bible; an archive copy as of April 2026).
- Complete Bible Genealogy (complete-bible-genealogy.com).

**Dictionary:** M. G. Easton, *Easton's Bible Dictionary* (1897), via CCEL.

**Places:**

| Source | Role | Licence |
| --- | --- | --- |
| OpenBible.info, Bible Geocoding | Coordinates, names, comments | CC BY 4.0 |
| Pelagios Network, Recogito | Coordinates and gazetteer links | CC BY |
| Pleiades; Wikidata; GeoNames | Identity links (geospatial file only) | CC BY; CC0; CC BY |
| Digital Manna, *Encyclopedia: Places* | Identity merging (geospatial file only) | Site terms of use; non-commercial |
| E. Stern (ed.), *New Encyclopedia of Archaeological Excavations in the Holy Land* (1993) | Period encoding via PeriodO | Periods via PeriodO; book text not redistributed |

**Paul's journeys (not shipped):** Mark Wilson (2009), *NTS* 55(4), 471; Gary Thompson
and Mark Wilson (2016), *Tyndale Bulletin* 67.2, 217-246; J. L. Hurlbut, *Rand McNally
Bible Atlas* (1962); T. V. Brisco, *Holman Bible Atlas* (1998); Ancient World Mapping
Center; Johan Åhlfeldt, *Digital Atlas of the Roman Empire*; Walter Scheidel, *ORBIS*;
the Linked Places Format (Grossner, Janowicz and Keßler).

## Anchor dates

Event dates use an astronomical convention that **includes a year 0** (year 0 is 1 BC;
year -4003 is 4004 BC). Check your reading of the data against these anchors:

| Event | Label | Core `dt` |
| --- | --- | --- |
| Creation | 4004 BC | `"-4003"` |
| The Flood begins | 2348 BC | `"-2347"` |
| Birth of Isaac | 1896 BC | `"-1895"` |
| Exodus from Egypt | 1491 BC | `"-1490"` |
| Solomon's Temple construction begins | 1012 BC | `"-1011"` |
| Death of Solomon | 975 BC | `"-974"` |
| Crucifixion and Burial | AD 30 | `"0030-04-04"` |

Converting a year `y` to a label: `y <= 0 ? (1 - y) + " BC" : "AD " + y`.

Data exported by Theographic before October 2026 used plain BC years with no year 0, so
every BC date was one lower. Core's pipeline does not yet assert that year 0 is present,
so a future import of old-format data would not be caught automatically; that check is
on the roadmap.

## Which chronology?

Jones tracks Ussher on most dates and does not follow Thiele's reconciliation of the
Divided Monarchy. Thiele's remains the mainstream evangelical chronology among
scholars. Core ships the dataset as Theographic publishes it and does not adjudicate;
applications that present dates should say which chronology they use. Where verse years
and event dates disagree, Theographic recommends event dates for timeline work.

## Confidence

- **High:** the headline findings, checked against Theographic's own documentation.
- **Medium:** which gazetteer supplied an individual place's coordinates. Theographic
  makes that choice per record; Core trusts it.
- **Deferred:** a read of Theographic's `etl/` scripts for any source the documentation
  omits. If you spot one, open an issue.
