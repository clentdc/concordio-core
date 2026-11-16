"""Public-domain Hebrew/Aramaic/Greek interlinear pack, built from the Berean "BSB Translation
Tables" (word-level) plus Strong's concise dictionaries for headwords.

This is the second, independent interlinear source (the first is ``stepbible``). It shares
no data with it, so either can be shown or switched off on its own licence terms.

Inputs, all under ``.cache/`` (see the ``fetch-bsb-tables`` Makefile target):

* ``bsb-tables/bsb_tables.tsv``: https://bereanbible.com/bsb_tables.tsv, one row per source
  word (Hebrew / Aramaic / Greek) with transliteration, Berean parsing code, a spelled-out
  parsing, Strong's number and the BSB's English rendering of that word. Rows are in BSB
  (English) order; the source-language reading order is in the ``Heb Sort`` / ``Greek Sort``
  columns. The file is unversioned upstream, so the build pins its SHA-256 and warns on drift.
* ``strongs-xml/strongsgreek.xml`` and ``strongs-xml/StrongHebrewG.xml``: Strong's Greek
  (Ulrik Petersen's XML, "Public Domain -- Copy Freely") and Hebrew (Open Scriptures XML,
  ``<rights>Public Domain</rights>``) dictionaries at openscriptures/strongs commit 0acd2f2.
  Only Strong's own headword, transliteration and definition are read; the Open Scriptures
  ``.js`` conversions (CC-BY-SA) and the BDB/TWOT-style ``<list>`` outlines are NOT used.

Output (same shape as ``stepbible`` so a UI can swap them):

* ``interlinear/<osisBook>.json``: ``{ "Gen.1.1": [ {src, translit, gloss, strongs, lemma,
  morph}, ... ] }`` in source reading order. Optional keys: ``lang: "arc"`` on Aramaic words,
  ``marked`` on Greek words whose reading carries an edition mark in the source.
* ``strongs.json``: Strong's number -> ``{lemma, translit, short}`` for numbers used.
* ``morph_codes.json``: the source's own code -> its spelled-out expansion.

Nothing is invented: a word the source gives no Strong's number keeps ``strongs: ""`` and
``lemma: ""``; rows with no source-language word are dropped; Hebrew is not Unicode
normalised (the Open Scriptures guidance warns against NFC, and the bytes are kept as given).
"""
from __future__ import annotations

import csv
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

from .. import osis as O
from . import make_manifest, sha256_file, write_json

ID = "bsb-tables"
KIND = "interlinear"
UPSTREAM = "https://bereanbible.com/bsb_tables.tsv"

# Pinned inputs. The tables file is not versioned upstream (Last-Modified 2026-10-27), so we pin
# the bytes we reviewed. A mismatch warns (like bsb.py's unpinned download) instead of failing,
# so the weekly refresh job keeps running; review the diff before accepting a new hash.
TABLES_SHA256 = "aa2a9a0f004d015738cd1839c7c56c3be2549e0d4f4537090c2017268c223c60"
TABLES_LAST_MODIFIED = "2026-10-27"
STRONGS_REPO = "https://github.com/openscriptures/strongs"
STRONGS_COMMIT = "0acd2f251c2d35ff8db2dece4e0593979d3ac223"
GREEK_XML_SHA256 = "df928f01b37632f8af9f16289ce58d10b958014cb5dbd1e1ea715a8d311a0625"
HEBREW_XML_SHA256 = "1f9659ea208f4c498843a0280dacb1448627c33ca77712642d8705793ab66061"

OSIS_NS = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"

# Column indexes in bsb_tables.tsv (23 columns, one header row).
C_HEB_SORT, C_GRK_SORT, C_VERSE, C_LANG = 0, 1, 3, 4
C_SRC, C_SRC_MARKED, C_TRANSLIT, C_PARSE, C_PARSE_LONG = 5, 6, 7, 8, 9
C_STR_HEB, C_STR_GRK, C_VERSEID, C_GLOSS = 10, 11, 12, 18

_TRIM = re.compile(r"\s+")


def _warn(msg: str) -> None:
    print(f"   WARNING ({ID}): {msg}", file=sys.stderr, flush=True)


def _check_hash(path: Path, expected: str, what: str) -> str:
    got = sha256_file(path)
    if got != expected:
        if os.environ.get("CONCORDIO_STRICT_PINS"):
            # The release build sets this: a release must be built from the bytes that were reviewed.
            raise SystemExit(f"{ID}: {what} SHA-256 {got} differs from the reviewed pin {expected}; "
                             "refusing to build with CONCORDIO_STRICT_PINS set.")
        _warn(f"{what} SHA-256 {got[:12]}… differs from the reviewed pin {expected[:12]}…; "
              "re-check the licence page and update the pin in the adapter once reviewed.")
    return got


# ---------------------------------------------------------------- Strong's dictionaries

def _flat(el) -> str:
    """Flatten a Strong's definition element to plain text; inline refs become G####/H####."""
    out = []

    def walk(e):
        if e.text:
            out.append(e.text)
        for ch in e:
            tag = ch.tag.split("}")[-1]
            if tag == "greek":
                out.append(ch.get("unicode", ""))
            elif tag == "strongsref":
                n = re.sub(r"\D", "", ch.get("strongs", ""))
                if n:
                    out.append(("H" if ch.get("language", "").upper().startswith("H") else "G") + f"{int(n):04d}")
            elif tag == "pronunciation":
                pass
            else:
                walk(ch)
            if ch.tail:
                out.append(ch.tail)

    walk(el)
    return _TRIM.sub(" ", "".join(out)).strip()


def _greek_dictionary(path: Path) -> dict:
    root = ET.parse(path).getroot()
    out = {}
    for e in root.find("entries").findall("entry"):
        num = int(e.get("strongs"))
        g = e.find("greek")
        d = e.find("strongs_def")
        if g is None:
            continue
        out[f"G{num:04d}"] = {
            "lemma": g.get("unicode", "").strip(),
            "translit": g.get("translit", "").strip(),
            "short": _flat(d).rstrip(":;, ").strip() if d is not None else "",
        }
    return out


def _hebrew_dictionary(path: Path) -> dict:
    out = {}
    for d in ET.parse(path).getroot().iter(OSIS_NS + "div"):
        if d.get("type") != "entry":
            continue
        w = d.find(OSIS_NS + "w")
        if w is None or not w.get("ID", "").startswith("H"):
            continue
        num = int(w.get("ID")[1:])
        # Strong's own explanation only. The <list> outlines (abridged BDB lineage) and the
        # numeric "gloss" attribute (a TWOT reference) are deliberately ignored.
        expl = ""
        for n in d.findall(OSIS_NS + "note"):
            if n.get("type") == "explanation":
                expl = _TRIM.sub(" ", "".join(n.itertext())).strip().strip("{}").strip()
                break
        out[f"H{num:04d}"] = {
            "lemma": w.get("lemma", "").strip(),
            "translit": w.get("xlit", "").strip(),
            "short": expl.rstrip(":;, ").strip(),
        }
    return out


# ---------------------------------------------------------------- the tables

def _read_rows(path: Path):
    csv.field_size_limit(1 << 30)
    with open(path, encoding="utf-8", newline="") as f:
        rd = csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(rd)  # header
        for r in rd:
            if len(r) == 23:
                yield r


def _fmt_strongs(prefix: str, raw: str) -> str:
    raw = raw.strip()
    return f"{prefix}{int(raw):04d}" if raw.isdigit() else ""


def _build_verses(rows):
    """Return (verses, stats) where verses = {osisBook: {vid: [word, ...]}} in reading order."""
    # Verse index -> OSIS id, from the labelled first row of each verse ("Psalm 23:1").
    labels = {}
    for r in rows:
        if r[C_VERSEID].strip():
            head, cv = r[C_VERSEID].strip().rsplit(" ", 1)
            book = O.book_name_to_osis(head)
            if book is None:
                raise RuntimeError(f"Unknown book label {head!r} in bsb_tables.tsv")
            c, v = cv.split(":")
            labels[int(r[C_VERSE])] = O.vid(book, int(c), int(v))

    by_verse = defaultdict(list)
    stats = Counter()
    for r in rows:
        lang = r[C_LANG]
        if lang not in ("Hebrew", "Aramaic", "Greek"):
            continue
        src = r[C_SRC].strip()
        if not src:
            stats["rows_without_source_word_dropped"] += 1
            continue
        greek = lang == "Greek"
        order = float(r[C_GRK_SORT] if greek else r[C_HEB_SORT])
        strongs = _fmt_strongs("G", r[C_STR_GRK]) if greek else _fmt_strongs("H", r[C_STR_HEB])
        w = {
            "src": src,
            "translit": r[C_TRANSLIT].strip(),
            "gloss": r[C_GLOSS].strip(),
            "strongs": strongs,
            "lemma": "",           # filled from the Strong's headword below
            "morph": r[C_PARSE].strip(),
        }
        if lang == "Aramaic":
            w["lang"] = "arc"
        marked = r[C_SRC_MARKED].strip()
        if greek and marked != src:
            w["marked"] = marked
        by_verse[int(r[C_VERSE])].append((order, w, r[C_PARSE].strip(), r[C_PARSE_LONG].strip()))
        stats[lang] += 1

    verses: dict[str, dict[str, list]] = {}
    morph_votes: dict[str, Counter] = defaultdict(Counter)
    for idx in sorted(by_verse):
        vid = labels[idx]
        book = vid.split(".")[0]
        items = sorted(by_verse[idx], key=lambda t: t[0])
        verses.setdefault(book, {})[vid] = [t[1] for t in items]
        for _, _, code, long_ in items:
            if code and long_:
                morph_votes[code][long_] += 1
    stats["verses_with_no_source_words"] = len(labels) - len(by_verse)
    stats["verses_labelled"] = len(labels)
    return verses, morph_votes, stats


def build(cache_dir: str, out_dir: str) -> dict:
    cache = Path(cache_dir)
    tsv = cache / "bsb-tables" / "bsb_tables.tsv"
    gxml = cache / "strongs-xml" / "strongsgreek.xml"
    hxml = cache / "strongs-xml" / "StrongHebrewG.xml"
    for p in (tsv, gxml, hxml):
        if not p.exists():
            raise FileNotFoundError(f"{p} missing. Run `make fetch-bsb-tables`.")
    tsv_hash = _check_hash(tsv, TABLES_SHA256, "bsb_tables.tsv")
    gh = _check_hash(gxml, GREEK_XML_SHA256, "strongsgreek.xml")
    hh = _check_hash(hxml, HEBREW_XML_SHA256, "StrongHebrewG.xml")

    lex = {**_hebrew_dictionary(hxml), **_greek_dictionary(gxml)}
    rows = list(_read_rows(tsv))
    verses, morph_votes, stats = _build_verses(rows)

    # Lemma = Strong's headword for the word's number (derived from the number, not guessed).
    used, missing = set(), Counter()
    for book in verses.values():
        for words in book.values():
            for w in words:
                s = w["strongs"]
                if not s:
                    stats["words_without_strongs"] += 1
                    continue
                entry = lex.get(s)
                if entry is None:
                    missing[s] += 1
                    continue
                w["lemma"] = entry["lemma"]
                used.add(s)
    if missing:
        _warn(f"{len(missing)} Strong's numbers not in the dictionaries: {sorted(missing)[:8]}")

    out = Path(out_dir)
    nwords = nverses = 0
    for book in sorted(verses, key=O.OSIS_ORDER.get):
        write_json(str(out / "interlinear" / f"{book}.json"), verses[book])
        nverses += len(verses[book])
        nwords += sum(len(v) for v in verses[book].values())
    write_json(str(out / "strongs.json"), {k: lex[k] for k in sorted(used)})

    # Morph key: the source's own code -> expansion. If a code carries several expansions (a few
    # source inconsistencies), keep the most frequent one and count the rest.
    morph_codes, conflicts = {}, 0
    for code in sorted(morph_votes):
        votes = morph_votes[code]
        if len(votes) > 1:
            conflicts += 1
        morph_codes[code] = sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    write_json(str(out / "morph_codes.json"), morph_codes)

    fetch_hash = sha256_file(tsv)[:16] + gh[:16] + hh[:16]
    return make_manifest(
        id=ID,
        name="Hebrew-Greek interlinear (BSB Translation Tables + Strong's)",
        version="2026.11",
        kind=KIND,
        fetch_hash=fetch_hash,
        source_ref=f"tables-{tsv_hash[:12]}",
        license={
            "spdx": "LicenseRef-Public-Domain",
            "name": "Public domain (Berean Bible Translation Committee dedication of 2023-04-30; Strong's concise dictionaries)",
            "url": "https://berean.bible/terms.htm",
            "attribution": (
                "Hebrew, Aramaic and Greek words, transliteration, parsing, Strong's numbers and "
                "English renderings are from the Berean Bible BSB Translation Tables "
                "(bereanbible.com), dedicated to the public domain by the Berean Bible Translation "
                "Committee on April 30, 2023. Strong's headwords and definitions are from "
                "Strong's Exhaustive Concordance dictionaries (public domain), via Ulrik Petersen's "
                "XML edition and the Open Scriptures XML edition."
            ),
            "parts": [
                {"what": "BSB Translation Tables (words, translit, parsing, Strong's, English rendering)",
                 "licence": "Public domain dedication, 2023-04-30",
                 "url": "https://berean.bible/terms.htm",
                 "licensePage": "https://berean.bible/licensing.htm"},
                {"what": "Strong's Greek dictionary (headword, translit, definition)",
                 "licence": "Public domain (file prologue: \"Public Domain -- Copy Freely\")",
                 "url": f"{STRONGS_REPO}/tree/{STRONGS_COMMIT}/greek/StrongsGreekDictionaryXML_1.4"},
                {"what": "Strong's Hebrew dictionary (headword, translit, definition)",
                 "licence": "Public domain (file header: <rights>Public Domain</rights>)",
                 "url": f"{STRONGS_REPO}/blob/{STRONGS_COMMIT}/hebrew/StrongHebrewG.xml"},
            ],
        },
        source={
            "upstream": UPSTREAM,
            "revision": f"sha256:{tsv_hash}",
            "lastModified": TABLES_LAST_MODIFIED,
            "lexicon": {"upstream": STRONGS_REPO, "revision": STRONGS_COMMIT[:7],
                        "files": {"greek/StrongsGreekDictionaryXML_1.4/strongsgreek.xml": f"sha256:{gh}",
                                  "hebrew/StrongHebrewG.xml": f"sha256:{hh}"}},
            "modifications": (
                "Tab-separated word rows regrouped by verse (BSB English versification, keyed by OSIS id) "
                "and ordered in source reading order using the Heb Sort / Greek Sort columns; rows with "
                "no source-language word dropped; Strong's numbers prefixed H/G and zero-padded to four "
                "digits (Aramaic numbers use H); lemma set to the Strong's headword for the word's "
                "number; English rendering ('gloss') kept verbatim, including the '-' (no English "
                "counterpart), '. . .' and [bracketed supplied words] conventions; Berean parsing code "
                "kept verbatim as 'morph' with its own spelled-out expansion collected into "
                "morph_codes.json; Greek words carrying an edition mark in the source keep the marked "
                "form in 'marked'; Aramaic words tagged lang 'arc'; no Unicode normalisation applied."
            ),
        },
        out_dir=out_dir,
        files={
            "interlinear": "interlinear/*.json",
            "strongs": "strongs.json",
            "morphCodes": "morph_codes.json",
        },
        extra={
            "shape": {
                "wordFields": ["src", "translit", "gloss", "strongs", "lemma", "morph"],
                "optionalWordFields": {"lang": "'arc' on Aramaic words", "marked": "Greek reading with edition marks"},
                "verseKey": "OSIS, BSB English versification",
                "wordOrder": "source reading order (Hebrew/Aramaic right to left when displayed)",
                "strongsFormat": "H|G + 4-digit zero-padded base number, no letter suffix",
                "glossKind": "bsb-rendering",
                "lemmaKind": "strongs-headword",
                "morphScheme": "berean",
                "morphKeyFile": "morph_codes.json (exact code -> expansion)",
                "lexiconFile": "strongs.json ({lemma, translit, short}; Strong's own definitions only)",
            },
            "licenseEvidence": "pipeline/licence-evidence/bsb-tables-2026-11-12.txt",
            "languages": ["he", "arc", "grc"],
            "sourceTexts": {"OT": "Westminster Leningrad Codex (as used by the BSB)",
                            "NT": "Nestle 1904 base with edition marks (as used by the BSB)"},
            "counts": {
                "books": len(verses),
                "verses": nverses,
                "words": nwords,
                "hebrewWords": stats["Hebrew"],
                "aramaicWords": stats["Aramaic"],
                "greekWords": stats["Greek"],
                "wordsWithoutStrongs": stats["words_without_strongs"],
                "versesWithoutSourceWords": stats["verses_with_no_source_words"],
                "strongs": len(used),
                "morphCodes": len(morph_codes),
                "morphCodesWithConflictingExpansions": conflicts,
            },
            "notes": ("Glosses are the BSB's English rendering of each word, not a neutral word-for-word "
                      "gloss. Words with no Strong's number in the source (chiefly Hebrew prepositions with "
                      "pronominal suffixes) are left without one. Berean asks that works differing from its "
                      "official text not use the Berean name; this pack is named for its data source only."),
        },
    )
