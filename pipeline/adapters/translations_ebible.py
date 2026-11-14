#!/usr/bin/env python3
"""Build translation packs from eBible.org VPL files.

Supports Darby (engDBY), Douay-Rheims (engDRA), and Vulgata Clementina
(latVUC) in this first pass. Each pack is written to
`web/data/packs/<id>/` with a `manifest.json` and `verses.json` whose
schema matches the existing BSB pack:

    { "Gen.1.1": "In the beginning God created…", ... }

Deuterocanonical books are dropped because the app's shelf is the
66-book Protestant canon. Dropped books are listed in the manifest
under `source.droppedBooks`, and the per-pack `verseCount` reflects
only the shipped (Protestant) canon.

Usage:
    python3 -I pipeline/adapters/translations_ebible.py \\
        --cache .cache/translations \\
        --out web/data/packs
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
import zipfile
from dataclasses import dataclass
from typing import Iterator

# eBible 3-letter book codes to OSIS, protestant canon.
OSIS: dict[str, str] = {
    "GEN": "Gen", "EXO": "Exod", "LEV": "Lev", "NUM": "Num", "DEU": "Deut",
    "JOS": "Josh", "JDG": "Judg", "RUT": "Ruth",
    "1SA": "1Sam", "2SA": "2Sam", "1KI": "1Kgs", "2KI": "2Kgs",
    "1CH": "1Chr", "2CH": "2Chr", "EZR": "Ezra", "NEH": "Neh", "EST": "Esth",
    "JOB": "Job", "PSA": "Ps", "PRO": "Prov", "ECC": "Eccl", "SOL": "Song",
    "ISA": "Isa", "JER": "Jer", "LAM": "Lam", "EZE": "Ezek", "DAN": "Dan",
    "HOS": "Hos", "JOE": "Joel", "AMO": "Amos", "OBA": "Obad", "JON": "Jonah",
    "MIC": "Mic", "NAH": "Nah", "HAB": "Hab", "ZEP": "Zeph",
    "HAG": "Hag", "ZEC": "Zech", "MAL": "Mal",
    "MAT": "Matt", "MAR": "Mark", "LUK": "Luke", "JOH": "John", "ACT": "Acts",
    "ROM": "Rom", "1CO": "1Cor", "2CO": "2Cor", "GAL": "Gal", "EPH": "Eph",
    "PHI": "Phil", "COL": "Col", "1TH": "1Thess", "2TH": "2Thess",
    "1TI": "1Tim", "2TI": "2Tim", "TIT": "Titus", "PHM": "Phlm",
    "HEB": "Heb", "JAM": "Jas", "1PE": "1Pet", "2PE": "2Pet",
    "1JO": "1John", "2JO": "2John", "3JO": "3John", "JUD": "Jude", "REV": "Rev",
}

# Deuterocanonical and apocryphal books. Dropped for Protestant packs;
# mapped to OSIS and shipped when a translation opts in (include_apocrypha=True).
# References: Pitts OSIS Scripture Reference manual; SBL Handbook of Style.
DEUTEROCANON: dict[str, str] = {
    "TOB": "Tob", "JDT": "Jdt", "WIS": "Wis", "SIR": "Sir", "BAR": "Bar",
    "1MA": "1Macc", "2MA": "2Macc", "3MA": "3Macc", "4MA": "4Macc",
    "1ES": "1Esd", "2ES": "2Esd", "MAN": "PrMan",
}

LINE_RE = re.compile(r"^(?P<book>\S+)\s+(?P<ch>\d+):(?P<v>\d+)\s+(?P<text>.+)$")


@dataclass(frozen=True)
class Translation:
    pack_id: str
    pack_name: str
    short_name: str
    language: str
    language_name: str
    direction: str
    year: int
    ebible_id: str
    attribution: str
    license_url: str
    note: str
    include_apocrypha: bool = False


TRANSLATIONS: list[Translation] = [
    Translation(
        pack_id="darby",
        pack_name="Darby Bible",
        short_name="DBY",
        language="en",
        language_name="English",
        direction="ltr",
        year=1890,
        ebible_id="engDBY",
        attribution="The Holy Scriptures, a New Translation from the Original Languages by J. N. Darby (1884, 1890). Public domain. Text from eBible.org.",
        license_url="https://ebible.org/engDBY/copyright.htm",
        note="Protestant canon, 66 books, no deuterocanon. Verse keying matches Theographic.",
    ),
    Translation(
        pack_id="douay-rheims",
        pack_name="Douay-Rheims Challoner",
        short_name="DRA",
        language="en",
        language_name="English",
        direction="ltr",
        year=1899,
        ebible_id="engDRA",
        attribution="Douay-Rheims-Challoner Bible, English translation from the Latin Vulgate. Public domain. Text from eBible.org.",
        license_url="https://ebible.org/engDRA/copyright.htm",
        note="Challoner revision (1750 / 1899 printing). Includes the 7 deuterocanonical books (Tobit, Judith, Wisdom, Sirach, Baruch, 1-2 Maccabees) that form the Catholic canon. The Greek additions to Esther and Daniel are rendered where present in the upstream VPL.",
        include_apocrypha=True,
    ),
    Translation(
        pack_id="vulgata-clementina",
        pack_name="Vulgata Clementina",
        short_name="VUC",
        language="la",
        language_name="Latin",
        direction="ltr",
        year=1598,
        ebible_id="latVUC",
        attribution="Biblia Sacra Vulgata Clementina (1598 edition, as described by eBible.org). Public domain. Text from eBible.org.",
        license_url="https://ebible.org/latVUC/copyright.htm",
        note="Clementine Vulgate, 1598 edition as published by eBible.org (its description: \"Clementine Vulgate of 1598 with Glossa Ordinaria, Migne edition 1880\"; the Verse-Per-Line file carries the Bible text only). Ships with the Catholic canon including the deuterocanonical books.",
        include_apocrypha=True,
    ),
]


def iter_vpl(path: pathlib.Path) -> Iterator[tuple[str, int, int, str]]:
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = LINE_RE.match(raw)
        if not m:
            continue
        yield m["book"], int(m["ch"]), int(m["v"]), m["text"].strip()


def build_pack(t: Translation, cache_dir: pathlib.Path, out_dir: pathlib.Path) -> dict:
    zip_path = cache_dir / f"{t.ebible_id}_vpl.zip"
    if not zip_path.exists():
        raise SystemExit(f"Missing cache: {zip_path}. Download from https://ebible.org/Scriptures/{t.ebible_id}_vpl.zip")
    vpl_name = f"{t.ebible_id}_vpl.txt"
    with zipfile.ZipFile(zip_path) as z:
        z.extract(vpl_name, cache_dir / t.pack_id)
    vpl_path = cache_dir / t.pack_id / vpl_name

    verses: dict[str, str] = {}
    dropped_books: set[str] = set()
    included_apocrypha: set[str] = set()
    unknown_books: set[str] = set()
    for book, ch, v, text in iter_vpl(vpl_path):
        if book in DEUTEROCANON:
            if t.include_apocrypha:
                osis = DEUTEROCANON[book]
                verses[f"{osis}.{ch}.{v}"] = text
                included_apocrypha.add(book)
            else:
                dropped_books.add(book)
            continue
        osis = OSIS.get(book)
        if not osis:
            unknown_books.add(book)
            continue
        verses[f"{osis}.{ch}.{v}"] = text

    if unknown_books:
        print(f"[{t.pack_id}] WARN: unknown book codes dropped: {sorted(unknown_books)}", file=sys.stderr)

    pack_dir = out_dir / t.pack_id
    pack_dir.mkdir(parents=True, exist_ok=True)
    verses_path = pack_dir / "verses.json"
    verses_json = json.dumps(verses, ensure_ascii=False, separators=(",", ":"))
    verses_path.write_text(verses_json, encoding="utf-8")

    fetch_hash = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    size_bytes = verses_path.stat().st_size

    manifest = {
        "id": t.pack_id,
        "kind": "translation",
        "schemaVersion": 1,
        "name": t.pack_name,
        "shortName": t.short_name,
        "lang": t.language,
        "language": t.language,
        "languageName": t.language_name,
        "textDir": t.direction,
        "year": t.year,
        "version": "2026.11-dc" if t.include_apocrypha else "2026.11",
        "verseCount": len(verses),
        "sizeBytes": size_bytes,
        "files": {"verses": "verses.json"},
        "canon": "catholic-73" if t.include_apocrypha else "protestant-66",
        "deuterocanon": sorted({DEUTEROCANON[b] for b in included_apocrypha}),
        "requires": [],
        "license": {
            "name": "Public Domain",
            "spdx": "LicenseRef-Public-Domain",
            "url": t.license_url,
            "attribution": t.attribution,
        },
        "source": {
            "upstream": f"https://ebible.org/Scriptures/{t.ebible_id}_vpl.zip",
            "revision": f"{t.ebible_id}_vpl.txt",
            "fetchHash": fetch_hash,
            "modifications": (
                "VPL parsed; book codes mapped to OSIS; deuterocanonical books "
                + ("mapped to OSIS and included." if t.include_apocrypha else "dropped to match the Protestant shelf.")
            ),
            "droppedBooks": sorted(dropped_books),
            "apocryphaBooks": sorted(included_apocrypha),
        },
        "note": t.note,
    }
    (pack_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--cache", default=".cache/translations", type=pathlib.Path)
    p.add_argument("--out", default="web/data/packs", type=pathlib.Path)
    args = p.parse_args()

    for t in TRANSLATIONS:
        manifest = build_pack(t, args.cache, args.out)
        print(f"[{t.pack_id}] {manifest['verseCount']} verses, {manifest['sizeBytes'] / 1024:.0f} KB")


if __name__ == "__main__":
    main()
