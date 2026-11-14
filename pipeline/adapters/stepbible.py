"""STEPBible interlinear pack: Hebrew OT (TAHOT) + Greek NT (TAGNT), with Strong's,
morphology, lemma, transliteration, and context gloss, from Tyndale House Cambridge.

Six source files under ``.cache/stepbible/``:

* ``Translators Amalgamated OT+NT/TAHOT ...``: 4 Hebrew OT TSV files (Gen-Deu,
  Jos-Est, Job-Sng, Isa-Mal).
* ``Translators Amalgamated OT+NT/TAGNT ...``: 2 Greek NT TSV files (Mat-Jhn, Act-Rev).
* ``Lexicons/TBESH ...``: Hebrew brief lexicon (abridged BDB) keyed by Strong's.
* ``Lexicons/TBESG ...``: Greek brief lexicon (corrected Abbott-Smith) keyed by Strong's.
* ``Morphology codes/TEHMC ...``: Hebrew morph-code expansions.
* ``Morphology codes/TEGMC ...``: Greek morph-code expansions.

Output:

* ``interlinear/<osisBook>.json``: one object per book, mapping OSIS verse id to a list
  of per-word records (``src``, ``translit``, ``gloss``, ``strongs``, ``lemma``,
  ``morph``).
* ``strongs.json``: Strong's number → lexicon entry.
* ``morph_codes.json``: compound morph code → prose description.

License: CC BY 4.0 (STEPBible / Tyndale House Cambridge).
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from .. import osis as O
from . import git_rev, make_manifest, sha256_tree, write_json

ID = "stepbible"
KIND = "interlinear"
UPSTREAM = "https://github.com/STEPBible/STEPBible-Data"

TAHOT_FILES = [
    "TAHOT Gen-Deu - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt",
    "TAHOT Jos-Est - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt",
    "TAHOT Job-Sng - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt",
    "TAHOT Isa-Mal - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt",
]
TAGNT_FILES = [
    "TAGNT Mat-Jhn - Translators Amalgamated Greek NT - STEPBible.org CC-BY.txt",
    "TAGNT Act-Rev - Translators Amalgamated Greek NT - STEPBible.org CC-BY.txt",
]
TBESH_FILE = "TBESH - Translators Brief lexicon of Extended Strongs for Hebrew - STEPBible.org CC BY.txt"
TBESG_FILE = "TBESG - Translators Brief lexicon of Extended Strongs for Greek - STEPBible.org CC BY.txt"
TEHMC_FILE = "TEHMC - Translators Expansion of Hebrew Morphology Codes - STEPBible.org CC BY.txt"
TEGMC_FILE = "TEGMC - Translators Expansion of Greek Morphhology Codes - STEPBible.org CC BY.txt"


# Verse-reference head: ``Gen.1.1#01=L`` or ``Mat.1.1#01=NKO``.
_REF_RE = re.compile(r"^([A-Z1-3][A-Za-z]{1,5})\.(\d+)\.(\d+)#(\d+)=([A-Za-z()]+)$")
# Lexicon rows start with a Strong's number (G0001, H0001, G12345, etc.).
_STRONGS_HEAD = re.compile(r"^[GH]\d{3,5}[A-Z]?$")
# Morph-code rows: short token followed by description columns.
_MORPH_HEAD = re.compile(r"^[A-Za-z][A-Za-z0-9/\-]{0,15}$")


def _tahot_rows(path):
    """Yield parsed Hebrew word rows from a TAHOT TSV file."""
    with open(path, encoding="utf-8") as f:
        for raw in f:
            cols = raw.rstrip("\n").split("\t")
            if len(cols) < 6:
                continue
            m = _REF_RE.match(cols[0])
            if not m:
                continue
            step_book, c, v, word_no, src_tag = m.groups()
            osis_book = O.step_to_osis(step_book)
            if osis_book is None:
                continue
            yield {
                "osis": osis_book,
                "chapter": int(c),
                "verse": int(v),
                "word": int(word_no),
                "source_tag": src_tag,
                "src": cols[1],         # Hebrew with cantillation
                "translit": cols[2],
                "gloss": cols[3],
                "strongs_raw": cols[4],
                "morph": cols[5] if len(cols) > 5 else "",
                "lemma_raw": cols[11] if len(cols) > 11 else "",
            }


def _tagnt_rows(path):
    """Yield parsed Greek word rows from a TAGNT TSV file."""
    with open(path, encoding="utf-8") as f:
        for raw in f:
            cols = raw.rstrip("\n").split("\t")
            if len(cols) < 5:
                continue
            m = _REF_RE.match(cols[0])
            if not m:
                continue
            step_book, c, v, word_no, src_tag = m.groups()
            osis_book = O.step_to_osis(step_book)
            if osis_book is None:
                continue
            # Col 3 is "G0976=N-NSF" — Strong's + morph joined by "=".
            sm = cols[3]
            if "=" in sm:
                strongs, morph = sm.split("=", 1)
            else:
                strongs, morph = sm, ""
            # Col 4 is "βίβλος=book" — lemma + gloss.
            lm = cols[4] if len(cols) > 4 else ""
            lemma = lm.split("=", 1)[0] if "=" in lm else lm
            # Col 1 contains "Βίβλος (Biblos)" — split off the transliteration.
            word = cols[1]
            translit = ""
            if "(" in word and word.endswith(")"):
                paren = word.rfind("(")
                translit = word[paren + 1:-1]
                word = word[:paren].strip()
            yield {
                "osis": osis_book,
                "chapter": int(c),
                "verse": int(v),
                "word": int(word_no),
                "source_tag": src_tag,
                "src": word,
                "translit": translit,
                "gloss": cols[2],
                "strongs_raw": strongs,
                "morph": morph,
                "lemma_raw": lemma,
            }


# Prefer rows whose source tag contains an uppercase 'N' (present in the Nestle-Aland
# critical text, the base for most modern Bibles). For OT, the only tag is 'L'
# (Leningrad), so every row passes. For NT, this filters out K-only / O-only variants.
_PREFER = re.compile(r"[NL]")


def _group_verses(rows):
    """Collapse rows to one record per word position, preferring the mainline reading."""
    by_verse: dict[tuple[str, int, int], dict[int, dict]] = {}
    for r in rows:
        k = (r["osis"], r["chapter"], r["verse"])
        bucket = by_verse.setdefault(k, {})
        current = bucket.get(r["word"])
        if current is None or (not _PREFER.search(current["source_tag"])
                               and _PREFER.search(r["source_tag"])):
            bucket[r["word"]] = r
    return by_verse


def _primary_strongs(raw):
    """Extract the primary Strong's number from a slashed, braced raw field.

    TAHOT examples: ``H9003/{H7225G}`` → ``H7225G``, ``{H1254A}`` → ``H1254A``.
    TAGNT just ships the Strong's directly (``G0976``). Prefers braced tokens over
    unbraced ones; falls back to the first ``[GH]\\d+`` match.
    """
    if not raw:
        return ""
    brace = re.findall(r"\{([GH]\d+[A-Za-z]?)\}", raw)
    if brace:
        return brace[0]
    all_hits = re.findall(r"[GH]\d+[A-Za-z]?", raw)
    return all_hits[0] if all_hits else ""


def _primary_lemma(raw):
    """Extract the lemma word from a raw lemma field (take the braced primary form)."""
    if not raw:
        return ""
    brace = re.findall(r"\{[^=}]*=([^=}]+)=", raw)
    if brace:
        return brace[0]
    if "=" in raw:
        return raw.split("=", 1)[1].split("=", 1)[0].split("»")[0]
    return raw


def _compact_hebrew_word(row):
    """Collapse a slashed Hebrew morpheme word into a single display form.

    STEPBible writes Hebrew with ``/`` between morphemes (prefix/root/suffix). The UI
    shows one glyph per word, so we join; translit and gloss get the same treatment.
    """
    for key in ("src", "translit", "gloss"):
        s = row[key]
        if "/" in s:
            # Hebrew source uses morpheme separators; translit/gloss slash the same way.
            row[key] = s.replace("/", "")
    return row


def _format_row(row, lang):
    primary_s = _primary_strongs(row["strongs_raw"])
    lemma = _primary_lemma(row["lemma_raw"]) if lang == "he" else row["lemma_raw"]
    if lang == "he":
        row = _compact_hebrew_word(dict(row))
    out = {
        "src": row["src"],
        "translit": row["translit"],
        "gloss": row["gloss"].strip(),
        "strongs": primary_s,
        "lemma": lemma,
        "morph": row["morph"],
    }
    return out


def _build_interlinear(cache_root):
    """Return a dict: osisBook → {verseId: [wordRecord, ...]} for every verse."""
    out: dict[str, dict[str, list]] = {}
    for name in TAHOT_FILES + TAGNT_FILES:
        src = cache_root / "Translators Amalgamated OT+NT" / name
        if not src.exists():
            raise FileNotFoundError(f"STEPBible source missing: {src}")
        rows = _tahot_rows(src) if "TAHOT" in name else _tagnt_rows(src)
        lang = "he" if "TAHOT" in name else "gr"
        for key, bucket in _group_verses(rows).items():
            osis_b, c, v = key
            vid = O.vid(osis_b, c, v)
            words = [_format_row(bucket[i], lang) for i in sorted(bucket)]
            out.setdefault(osis_b, {})[vid] = words
    return out


def _parse_lexicon(path, prefix):
    """Return a dict of Strong's (dStrong) → entry, from a TBES* lexicon file."""
    out = {}
    with open(path, encoding="utf-8") as f:
        for raw in f:
            cols = raw.rstrip("\n").split("\t")
            if len(cols) < 8:
                continue
            dstrong = cols[2].strip()
            if not dstrong.startswith(prefix) or not _STRONGS_HEAD.match(dstrong):
                continue
            # cols[7] is the long entry with HTML; strip tags for a short preview.
            long_html = cols[7] if len(cols) > 7 else ""
            long_text = re.sub(r"<[^>]+>", "", long_html)
            long_text = re.sub(r"\s+", " ", long_text).strip()
            if dstrong in out:
                continue  # keep first occurrence
            out[dstrong] = {
                "lemma": cols[3].strip(),
                "translit": cols[4].strip(),
                "pos": cols[5].strip(),
                "short": cols[6].strip(),
                "long": long_text[:600],
            }
    return out


def _parse_morph_codes(path):
    """Return a dict of morph code → prose description, from a TE*MC file."""
    out = {}
    with open(path, encoding="utf-8") as f:
        for raw in f:
            cols = raw.rstrip("\n").split("\t")
            if len(cols) < 2:
                continue
            code = cols[0].strip()
            if not code or " " in code or len(code) > 24:
                continue
            if not _MORPH_HEAD.match(code):
                continue
            # TEGMC: "A-APF" → "Function=Adjective; Case=Accusative; …" in cols[1].
            # TEHMC: "Pp1c" → example in cols[1], meaning in cols[2].
            if len(cols) >= 3 and cols[2].strip():
                out[code] = cols[2].strip()
            else:
                out[code] = cols[1].strip()
    return out


def build(cache_dir: str, out_dir: str) -> dict:
    cache_root = Path(cache_dir) / "stepbible"
    if not cache_root.exists():
        raise FileNotFoundError(
            f"STEPBible cache missing at {cache_root}. Run `make fetch-stepbible`."
        )

    # Interlinear per-book
    inter = _build_interlinear(cache_root)
    inter_dir = Path(out_dir) / "interlinear"
    inter_dir.mkdir(parents=True, exist_ok=True)
    word_count = 0
    verse_count = 0
    for osis_book, verses in inter.items():
        write_json(str(inter_dir / f"{osis_book}.json"), verses)
        verse_count += len(verses)
        word_count += sum(len(v) for v in verses.values())

    # Strong's lexicon (merge Hebrew + Greek)
    strongs = _parse_lexicon(cache_root / "Lexicons" / TBESH_FILE, "H")
    strongs.update(_parse_lexicon(cache_root / "Lexicons" / TBESG_FILE, "G"))
    write_json(os.path.join(out_dir, "strongs.json"), strongs)

    # Morph-code expansions (merge Hebrew + Greek)
    morph_codes = _parse_morph_codes(cache_root / "Morphology codes" / TEHMC_FILE)
    morph_codes.update(_parse_morph_codes(cache_root / "Morphology codes" / TEGMC_FILE))
    write_json(os.path.join(out_dir, "morph_codes.json"), morph_codes)

    rev = git_rev(cache_root)
    fh = sha256_tree(cache_root, globs=[
        "Translators Amalgamated OT+NT/*.txt",
        "Lexicons/*.txt",
        "Morphology codes/*.txt",
    ])
    return make_manifest(
        id=ID,
        name="STEPBible interlinear (TAHOT + TAGNT + TBESH + TBESG + TEHMC + TEGMC)",
        version="2026.10",
        kind=KIND,
        fetch_hash=fh,
        source_ref=rev,
        license={
            "spdx": "CC-BY-4.0",
            "name": "Creative Commons Attribution 4.0 International",
            "url": "https://creativecommons.org/licenses/by/4.0/",
            "attribution": (
                "Data created by www.STEPBible.org based on work at Tyndale House "
                "Cambridge, CC BY 4.0. Source: https://STEPBible.github.io/STEPBible-Data "
                f"(revision {rev}). Changes: see source.modifications."
            ),
        },
        source={
            "upstream": UPSTREAM,
            "revision": rev,
            "modifications": (
                "TSV columns parsed; mainline reading selected per word (NA27/28 for "
                "NT, Leningrad for OT); Hebrew slashed morphemes collapsed into a "
                "composite word form; primary Strong's extracted from brace-marked "
                "primary form; HTML stripped from lexicon long entries and truncated "
                "to 600 chars; morph codes keyed by exact compound string."
            ),
        },
        out_dir=out_dir,
        files={
            "interlinear": "interlinear/*.json",
            "strongs": "strongs.json",
            "morphCodes": "morph_codes.json",
        },
        extra={
            "caveats": ["TBESH definitions: Online Bible permission pending"],
            "counts": {
                "books": len(inter),
                "verses": verse_count,
                "words": word_count,
                "strongs": len(strongs),
                "morphCodes": len(morph_codes),
            },
        },
    )
