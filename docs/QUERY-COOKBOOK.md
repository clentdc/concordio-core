# Query cookbook

Concordio Core is a set of static JSON files, so "the API" is a handful of `fetch`
calls (or file reads) plus a few lines of code. This cookbook shows what you can ask
of the data, from the obvious (read a verse) to the novel (which chapters crowd the
most named people together?).

Every recipe below is runnable Node.js (no dependencies). `tests/test_cookbook.py` runs
each one against the packs in this repository, so the recipes cannot silently rot.
Sample output is from the packs at the time of writing; counts move a little when the
weekly upstream refresh lands.

- [Setup](#setup)
- [1. Read a verse, compare translations](#1-read-a-verse-compare-translations)
- [2. Every verse that names a person](#2-every-verse-that-names-a-person)
- [3. Who appears together?](#3-who-appears-together)
- [4. Which entities are in a verse?](#4-which-entities-are-in-a-verse)
- [5. Where does a person show up, book by book?](#5-where-does-a-person-show-up-book-by-book)
- [6. Places in a chapter, with coordinates](#6-places-in-a-chapter-with-coordinates)
- [7. A timeline slice](#7-a-timeline-slice)
- [8. Walk a family tree](#8-walk-a-family-tree)
- [9. The Easton's dictionary entry for an entity](#9-the-eastons-dictionary-entry-for-an-entity)
- [10. Search verse text across translations](#10-search-verse-text-across-translations)
- [11. The most crowded chapters](#11-the-most-crowded-chapters)
- [12. Namesakes](#12-namesakes)
- [13. Psalm numbering across traditions](#13-psalm-numbering-across-traditions)
- [14. Books beyond the 66](#14-books-beyond-the-66)
- [In a browser](#in-a-browser)
- [Pitfalls](#pitfalls)

## Setup

Run these from the repository root. Each recipe starts with this setup block.

```js
import { readFileSync } from 'node:fs';
const load = (pack, file) =>
  JSON.parse(readFileSync(`web/data/packs/${pack}/${file}`, 'utf8'));
```

Three things to know before you start:

1. **Verses are keyed by OSIS id**, `Book.chapter.verse`, for example `John.3.16`.
   The 66 book codes are `Gen Exod Lev Num Deut Josh Judg Ruth 1Sam 2Sam 1Kgs 2Kgs 1Chr
   2Chr Ezra Neh Esth Job Ps Prov Eccl Song Isa Jer Lam Ezek Dan Hos Joel Amos Obad Jonah
   Mic Nah Hab Zeph Hag Zech Mal Matt Mark Luke John Acts Rom 1Cor 2Cor Gal Eph Phil Col
   1Thess 2Thess 1Tim 2Tim Titus Phlm Heb Jas 1Pet 2Pet 1John 2John 3John Jude Rev`.
2. **People, places and events link to verses, not to translation text.** The link
   lists live in the `theographic` pack, so every recipe that finds verses works with
   any translation.
3. **Entity ids carry a numeric suffix** (`p-moses-2108`). Use the `slug` field
   (`moses`) as the stable, human-readable handle, and see [Namesakes](#12-namesakes)
   for the cases where a name is shared.

## 1. Read a verse, compare translations

```js
import { readFileSync } from 'node:fs';
const load = (pack, file) =>
  JSON.parse(readFileSync(`web/data/packs/${pack}/${file}`, 'utf8'));

const id = 'John.3.16';
for (const pack of ['bsb', 'kjv', 'darby', 'douay-rheims']) {
  console.log(`${pack.padEnd(13)} ${load(pack, 'verses.json')[id]}`);
}
```

```text
bsb           For God so loved the world that He gave His one and only Son, that everyone who believes in Him shall not perish but have eternal life.
kjv           For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life.
darby         For God so loved the world, that he gave his only-begotten Son, that whosoever believes on him may not perish, but have life eternal.
douay-rheims  For God so loved the world, as to give his only begotten Son; that whosoever believeth in him, may not perish, but may have life everlasting.
```

## 2. Every verse that names a person

The `verses` list on each person is the complete set of verses that mention them, in
canonical order.

```js
import { readFileSync } from 'node:fs';
const load = (pack, file) =>
  JSON.parse(readFileSync(`web/data/packs/${pack}/${file}`, 'utf8'));

const people = load('theographic', 'people.json');
const bsb = load('bsb', 'verses.json');

const aaron = people.find(p => p.slug === 'aaron');
console.log(`${aaron.n}: ${aaron.verses.length} verses; first three:`);
for (const v of aaron.verses.slice(0, 3)) console.log(`  ${v}  ${bsb[v]}`);
```

```text
Aaron: 331 verses; first three:
  Exod.4.14  Then the anger of the LORD burned against Moses, and He said, ...
  Exod.4.27  Meanwhile, the LORD had said to Aaron, “Go and meet Moses in the wilderness.” ...
  Exod.4.28  And Moses told Aaron everything the LORD had sent him to say, ...
```

## 3. Who appears together?

Intersect verse lists. The same pattern answers "which verses involve this person at
this place" or "which events involve these two people".

```js
import { readFileSync } from 'node:fs';
const load = (pack, file) =>
  JSON.parse(readFileSync(`web/data/packs/${pack}/${file}`, 'utf8'));

const people = load('theographic', 'people.json');
const bsb = load('bsb', 'verses.json');
const by = slug => people.find(p => p.slug === slug);

const together = by('moses').verses.filter(v => new Set(by('aaron').verses).has(v));
console.log(`Moses and Aaron are both named in ${together.length} verses`);
console.log(`first: ${together[0]}  ${bsb[together[0]]}`);
```

## 4. Which entities are in a verse?

Build a reverse index once, then look up any verse.

```js
import { readFileSync } from 'node:fs';
const load = (pack, file) =>
  JSON.parse(readFileSync(`web/data/packs/${pack}/${file}`, 'utf8'));

const kinds = { people: 'person', places: 'place', events: 'event' };
const index = new Map(); // verse id -> [{kind, name, slug}]
for (const [file, kind] of Object.entries(kinds)) {
  for (const e of load('theographic', `${file}.json`)) {
    for (const v of e.verses) {
      if (!index.has(v)) index.set(v, []);
      index.get(v).push({ kind, name: e.n, slug: e.slug });
    }
  }
}

for (const e of index.get('Gen.1.1')) console.log(e.kind.padEnd(7), e.name);
```

```text
person  God
event   Creation of all things
```

## 5. Where does a person show up, book by book?

```js
import { readFileSync } from 'node:fs';
const load = (pack, file) =>
  JSON.parse(readFileSync(`web/data/packs/${pack}/${file}`, 'utf8'));

const people = load('theographic', 'people.json');
const david = people.find(p => p.slug === 'david');

const perBook = {};
for (const v of david.verses) {
  const book = v.split('.')[0];
  perBook[book] = (perBook[book] || 0) + 1;
}
const top = Object.entries(perBook).sort((a, b) => b[1] - a[1]).slice(0, 5);
console.log(`${david.n} is named in ${david.verses.length} verses across ${Object.keys(perBook).length} books`);
for (const [book, n] of top) console.log(`  ${book.padEnd(6)} ${n}`);
```

```text
David is named in 896 verses across 28 books
  1Sam   233
  2Sam   226
  1Chr   159
  1Kgs   74
  2Chr   66
```

## 6. Places in a chapter, with coordinates

`ll` is `[latitude, longitude]`, or `null` when the place has no known location.

```js
import { readFileSync } from 'node:fs';
const load = (pack, file) =>
  JSON.parse(readFileSync(`web/data/packs/${pack}/${file}`, 'utf8'));

const chapter = 'Acts.17.';
const places = load('theographic', 'places.json')
  .filter(p => p.verses.some(v => v.startsWith(chapter)));

for (const p of places) {
  const at = p.ll ? p.ll.map(x => x.toFixed(2)).join(', ') : 'location unknown';
  console.log(`${p.n.padEnd(14)} ${at}`);
}
```

```text
Amphipolis     40.82, 23.84
Apollonia      40.62, 23.47
Areopagus      37.96, 23.71
Athens         37.97, 23.73
Berea          40.52, 22.20
Thessalonica   40.63, 22.95
```

## 7. A timeline slice

Event dates (`dt`) and birth/death years (`by`, `dy`) are strings in an astronomical
year convention that **includes a year 0**: `"-4003"` is 4004 BC and year 1 is AD 1.
A few New Testament events use a full date, such as `"0030-04-04"`. Parse before you
compare.

```js
import { readFileSync } from 'node:fs';
const load = (pack, file) =>
  JSON.parse(readFileSync(`web/data/packs/${pack}/${file}`, 'utf8'));

const year = s => parseInt(s, 10); // "-1490" -> -1490, "0030-04-04" -> 30
const label = y => (y <= 0 ? `${1 - y} BC` : `AD ${y}`);

const events = load('theographic', 'events.json')
  .filter(e => e.dt)
  .map(e => ({ ...e, y: year(e.dt) }))
  .filter(e => e.y >= -1500 && e.y <= -1400)
  .sort((a, b) => a.y - b.y);

console.log(`${events.length} events between 1501 BC and 1401 BC`);
for (const e of events.slice(0, 5)) console.log(`  ${label(e.y).padEnd(8)} ${e.n}`);
```

```text
11 events between 1501 BC and 1401 BC
  1491 BC  Exodus from Egypt
  1491 BC  Wilderness Wanderings
  1491 BC  Ten Commandments Given
  1490 BC  Tabernacle Built
  1452 BC  Death of Moses
```

The dates follow one chronology (Floyd Nolen Jones) and are not the only defensible
one. See [THEOGRAPHIC-AUDIT.md](THEOGRAPHIC-AUDIT.md) before you build on them.

## 8. Walk a family tree

`fa` (father), `mo` (mother), `sp` (spouses), `ki` (children) and `si` (siblings) are
arrays of person ids.

```js
import { readFileSync } from 'node:fs';
const load = (pack, file) =>
  JSON.parse(readFileSync(`web/data/packs/${pack}/${file}`, 'utf8'));

const people = load('theographic', 'people.json');
const byId = new Map(people.map(p => [p.id, p]));

function ancestors(id, depth) {
  const p = byId.get(id);
  const line = [{ name: p.n, depth }];
  for (const parent of [...(p.fa || []), ...(p.mo || [])]) {
    if (depth > 0) line.push(...ancestors(parent, depth - 1));
  }
  return line;
}

const moses = people.find(p => p.slug === 'moses');
for (const a of ancestors(moses.id, 3)) console.log(`${'  '.repeat(3 - a.depth)}${a.name}`);
```

```text
Moses
  Amram
    Kohath
      Levi (patriarch)
  Jochebed
    Levi (patriarch)
      Jacob (Israel)
      Leah
```

## 9. The Easton's dictionary entry for an entity

`dictionary.json` maps entity id to the text of the matching Easton's Bible Dictionary
entry (public domain, 1897). Not every entity has one.

```js
import { readFileSync } from 'node:fs';
const load = (pack, file) =>
  JSON.parse(readFileSync(`web/data/packs/${pack}/${file}`, 'utf8'));

const people = load('theographic', 'people.json');
const dictionary = load('theographic', 'dictionary.json');

const ruth = people.find(p => p.slug === 'ruth');
console.log(`${Object.keys(dictionary).length} entities have an entry`);
console.log(dictionary[ruth.id].slice(0, 200) + '…');
```

## 10. Search verse text across translations

Verse text is plain Unicode with no markup. Count occurrences of a word in each
translation, with a whole-word, case-insensitive match.

```js
import { readFileSync } from 'node:fs';
const load = (pack, file) =>
  JSON.parse(readFileSync(`web/data/packs/${pack}/${file}`, 'utf8'));

const word = /\bmercy\b/i;
for (const pack of ['bsb', 'kjv', 'darby', 'douay-rheims']) {
  const hits = Object.values(load(pack, 'verses.json')).filter(t => word.test(t));
  console.log(`${pack.padEnd(13)} ${hits.length} verses`);
}
```

Translations differ in wording, so the same idea can score very differently. To search
by *meaning* across translations, start from an entity's verse list (recipe 2) instead
of a word.

## 11. The most crowded chapters

Which chapters name the most distinct people? A one-pass tally over every person's
verse list, something no verse-text search can give you.

```js
import { readFileSync } from 'node:fs';
const load = (pack, file) =>
  JSON.parse(readFileSync(`web/data/packs/${pack}/${file}`, 'utf8'));

const named = new Map(); // "Book.chapter" -> Set of person ids
for (const p of load('theographic', 'people.json')) {
  for (const v of p.verses) {
    const ch = v.slice(0, v.lastIndexOf('.'));
    if (!named.has(ch)) named.set(ch, new Set());
    named.get(ch).add(p.id);
  }
}
const top = [...named].sort((a, b) => b[1].size - a[1].size).slice(0, 5);
for (const [ch, ids] of top) console.log(`${ch.padEnd(9)} ${ids.size} people`);
```

```text
1Chr.1    189 people
1Chr.2    143 people
Ezra.10   140 people
1Chr.7    138 people
1Chr.4    133 people
```

## 12. Namesakes

Many names are shared, so `n` is not unique. Namesakes carry a display qualifier `dq`
(for example "son of Malluch" or "1 Chronicles 12:20"), and every entity has a unique
`slug`. Never join on the display name.

```js
import { readFileSync } from 'node:fs';
const load = (pack, file) =>
  JSON.parse(readFileSync(`web/data/packs/${pack}/${file}`, 'utf8'));

const people = load('theographic', 'people.json');
const shared = people.filter(p => p.n === 'Zechariah');
console.log(`${shared.length} people named Zechariah:`);
for (const p of shared.slice(0, 4)) {
  console.log(`  ${p.slug.padEnd(26)} ${p.dq || '(no qualifier)'}`);
}
```

Slugs are locked in `pipeline/slug-lock.json`, so a slug you store today keeps meaning
the same entity after every upstream refresh.

## 13. Psalm numbering across traditions

Protestant Bibles number the Psalms by the Hebrew text. Catholic and Orthodox
traditions (and the Vulgate, so the `douay-rheims` and `vulgata-clementina` packs) follow
the Greek/Latin numbering, which diverges between Psalms 9 and 147. `versify.json` maps
one to the other.

```js
import { readFileSync } from 'node:fs';
const load = (pack, file) =>
  JSON.parse(readFileSync(`web/data/packs/${pack}/${file}`, 'utf8'));

const map = load('.', 'versify.json').psalms.heb_to_lxx;
const hebrew = 23;
const lxx = map[hebrew];
const dr = load('douay-rheims', 'verses.json');
const bsb = load('bsb', 'verses.json');

console.log(`Hebrew Psalm ${hebrew} is Psalm ${lxx} in the Greek/Latin numbering`);
console.log(`bsb          Ps.${hebrew}.1  ${bsb[`Ps.${hebrew}.1`]}`);
console.log(`douay-rheims Ps.${lxx}.1  ${dr[`Ps.${lxx}.1`]}`);
```

Within a Psalm, verse numbers can also shift where a title counts as verse 1. The
mapping covers psalm numbers only.

## 14. Books beyond the 66

`canon-extensions.json` lists the seven deuterocanonical books that the Douay-Rheims
and Vulgata packs contain, with chapter and verse counts and where Catholic ordering
places them (`insertAfter`).

```js
import { readFileSync } from 'node:fs';
const load = (pack, file) =>
  JSON.parse(readFileSync(`web/data/packs/${pack}/${file}`, 'utf8'));

const dr = load('douay-rheims', 'verses.json');
for (const b of load('.', 'canon-extensions.json').books) {
  const verses = Object.keys(dr).filter(k => k.startsWith(`${b.osis}.`)).length;
  console.log(`${b.osis.padEnd(6)} ${b.name.padEnd(22)} after ${b.insertAfter.padEnd(5)} ${b.chapters} ch, ${verses} verses`);
}
```

These books have no entity links. Theographic covers the 66-book canon only.

## In a browser

The same data is plain static files, so the recipes port directly. Replace the file
read with a fetch from wherever you serve `web/`:

```text
const load = (pack, file) =>
  fetch(`/data/packs/${pack}/${file}`).then(r => r.json());
```

Everything else is unchanged (add `await` where a recipe calls `load`). Pack files are
large, up to a few megabytes each; fetch once and keep the result.

## Pitfalls

- **Dates are strings.** `by`, `dy` and `dt` are strings, possibly negative, possibly a
  full ISO date. Year 0 exists; see recipe 7.
- **Display names repeat.** Join on `id` or `slug`.
- **Verses can be empty or missing.** The BSB omits 16 verses that later manuscripts add
  (`Matt.17.21` is one); its pack keeps the key with an empty string, so test for
  `''` as well as `undefined`. Darby has three fewer keys than the BSB, and the
  Douay-Rheims and Vulgata number the Psalms and some other books by their own
  traditions (35,000+ keys), so do not assume every translation has the same ids.
- **Alias matching is not shipped.** `aliases` lists strings an application may match
  in verse text to highlight an entity. The packs do not mark up the text for you.
- **Entity links come from Theographic only.** If a link is not there, no one has
  asserted it. Concordio does not invent links.
