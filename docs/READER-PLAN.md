# Reader plan

The reader in `web/` is a deliberately small reference reader: static HTML, CSS and one
script, no build step. This page records what it does today and the order in which it
gains four things: Psalm numbering from `versify.json`, a canon selector, transliteration,
and presets beyond `default`.

## What the reader does now

- **Files.** `web/index.html`, `web/css/app.css`, `web/js/app.js` (one IIFE), `web/sw.js`.
- **Startup.** Reads `data/packs/index.json`, `theographic/books.json` (the 66 books and
  their chapter counts), the chrome pack for the interface language, the preset catalog and
  the active preset, then the active translation's `verses.json` (`?v=<pack version>`).
- **Reading.** Three selects (book, chapter, translation) plus interface language and
  "Tradition" (preset). It renders `<book>.<chapter>.<n>` until the next key is missing, and
  steps chapter by chapter with Previous and Next. State is mirrored into the URL hash
  (`b`, `c`, `tr`, `lang`, `p`).
- **Presets.** Only `default` exists (the reserved-material test allows only that id). The
  reader reads `defaultTranslation` from it and ignores every other field.
- **Interface strings.** `[data-i18n]` elements use the chrome pack and fall back to the
  English text in the HTML. Strings built in script use `t(key, fallback)`.
- **Offline.** `sw.js` precaches the shell, the catalog and `chrome-en`; everything else is
  cache-first, and pack catalogs and manifests are network-first.
- **Not used.** `versify.json`, `canon-extensions.json`, the preset's `canon`,
  `psalmNumbering` and `bookOrder`, and the interlinear packs.

Consequences: Psalm 23 in the Douay-Rheims shows the Vulgate Psalm 22 text with no sign of
the renumbering; the seven books beyond the 66 are in the Douay-Rheims and Vulgata packs
but cannot be reached, because the book list comes from `theographic/books.json`.

## Order of work

| Step | Item | Needs data not in git? | Status |
| --- | --- | --- | --- |
| 1 | (c) Use `versify.json` | No | Done |
| 2 | (b) Canon selector | No | Done |
| 3 | (a) Transliteration | Yes: the interlinear packs | Design only, below |
| 4 | (d) Presets beyond `default` | No data, but the owner decides content | Design only, below |

### (c) Psalm numbering

The reader keeps the Hebrew (Masoretic) numbering that `theographic` uses as its reference,
so the chapter list, share links (`c=`) and Previous/Next are stable across translations.
For a translation that numbers Psalms the Greek/Latin way, `web/js/versify.js` maps the
requested number through `psalms.heb_to_lxx` and shows the translation's own chapter(s),
with a label such as "Psalm 23 (numbered 22 in this translation)".

- Which translations use which numbering is **not stated in any manifest**. The reader has
  a small explicit table (`douay-rheims`, `vulgata-clementina`: Greek/Latin) and honours a
  `psalmNumbering` field in a manifest if one is ever added. A test checks the table
  against the data (Ps 9 and Ps 10 verse counts), so a wrong entry fails the build.
- `versify.json` maps chapters only. It has no verse boundaries, so the reader never splits
  a chapter: Hebrew 9 and 10 both show the whole translation Psalm 9, Hebrew 114 and 115
  both show Psalm 113, and Hebrew 116 and 147 each show two translation chapters under their
  own headings. Verse numbers are the pack's own.
- Psalm 151 is `lxx_only`. No shipped pack contains `Ps.151.*`, and the chapter list is
  Hebrew (150), so it is not reachable. A test asserts this, so it fails loudly if a pack
  later adds it and the reader needs a decision.

### (b) Canon selector

A "Canon" select (count-based labels: "66 books", "73 books"; `web/js/canon.js`) built from
`canon-extensions.json`: the extension books are inserted by resolving each `insertAfter`
chain. Chapter counts come from the same file. The option is disabled unless the active
translation has the books (probe `<osis>.1.1`), and the selection falls back to 66 when the
translation changes. It is reader state, kept in the URL hash as `canon=66|ext`; the
preset's `canon.deuterocanonBooks` and `canon.apocryphaBooks` only seed the initial choice
(any listed book selects the extended canon, all available extension books are shown; the
lists are not used to pick individual books, which is a question for the owner). No preset
is created. Extension books are named in English from `canon-extensions.json` only; the
chrome packs have no keys for them, nor for `label.canon`, `canon.count` or the `psalm.*`
notes (the reader falls back to English). Entity data
(people, places, events) does not cover these books; see DATA.md "Known gaps".

### (a) Transliteration (design, not built)

- **Where it lives.** Per word, in the interlinear packs: `interlinear/<Book>.json`, field
  `translit` next to `src`, `gloss`, `strongs`, `lemma`, `morph`. `strongs.json` carries a
  `translit` for each Strong's headword. Neither pack is in git (about 58 MB each), so
  development needs `make fetch && make data` in a scratch checkout
  (`python3 -I pipeline/build.py .cache --only stepbible`, then restore `index.json`), or a
  small hand-made fixture.
- **Reader work.** A "Show original words" toggle that loads the one-book file for the
  current book and shows, under each verse, a row of `src` / `translit` / `gloss`. It needs
  the interlinear verse numbering to match the translation's (the manifest's `shape` field
  records the differences, and Psalm superscriptions are the likely trouble spot), and a
  delivery decision for the two big packs (DATA.md "Pack delivery is undecided").
- **A shared transliterator** (for text that has no interlinear row: entity aliases,
  lemmas, search input) is a separate piece of work. It needs the owner to choose a scheme
  (the two packs already differ: STEPBible writes `be.re.Shit`, the BSB tables use another
  convention), a rule table for Hebrew (consonants, vowel points, dagesh, shva, final
  forms) and Greek (accents, breathings, diphthongs), a test corpus taken from the packs'
  own `src`/`translit` pairs, and a stated licence for the scheme. Do not derive it by
  guessing from the packs' output without checking both schemes agree.

### (d) Presets beyond `default` (design, not built)

The schema in [PRESETS.md](PRESETS.md) already carries what a preset can change:
`defaultTranslation`, `canon.*`, `psalmNumbering`, `bookOrder`, `entityLabels`. Once (b) and
(c) exist the reader can honour them with no new code paths:

- `canon.*` seeds the canon selector.
- `psalmNumbering: "septuagint"` would make the reader prefer the translation's own
  numbering for labels and the chapter list.
- `bookOrder` needs a defined vocabulary (`protestant-66`, `catholic-73`, `orthodox-76` are
  named in PRESETS.md, but only the first is implemented; the extensions file carries one
  placement, the `insertAfter` chain).
- Presets with doctrinal framing are the owner's decision and live downstream; the
  reserved-material test enforces `allowed_presets: ["default"]`. Nothing here adds one.
