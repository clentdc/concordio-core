"""Berean Standard Bible translation pack.

Reads ``.cache/bsb/bsb.txt`` (the tab-separated plain-text download from
https://bereanbible.com/bsb.txt) and emits ``verses.json``: a map of OSIS verse id to
plain verse text.

License: public domain since 2023-04-30. "Licensing is not required for any use."
Source: https://berean.bible/licensing.htm
"""
from __future__ import annotations

import os
from pathlib import Path

from .. import osis as O
from . import make_manifest, sha256_file, write_json

ID = "bsb"
KIND = "translation"
UPSTREAM = "https://bereanbible.com/bsb.txt"


def _parse(lines):
    """Yield (osis_verse_id, text) for each verse line in bsb.txt.

    The file begins with three header lines (two of them notice/preamble, then a
    "Verse\\tBerean Standard Bible" column header). Each verse line is of the form
    ``"Genesis 1:1\\tIn the beginning God created…"``.
    """
    for raw in lines:
        line = raw.rstrip("\r\n")
        if not line or "\t" not in line:
            continue
        ref, text = line.split("\t", 1)
        if ref in ("Verse", ""):
            continue
        # ref looks like "Genesis 1:1" or "1 Kings 8:11".
        if ":" not in ref:
            continue
        head, cv = ref.rsplit(" ", 1)
        osis = O.book_name_to_osis(head)
        if osis is None:
            continue
        c, v = cv.split(":")
        yield O.vid(osis, int(c), int(v)), text.strip()


def build(cache_dir: str, out_dir: str) -> dict:
    src = Path(cache_dir) / "bsb" / "bsb.txt"
    if not src.exists():
        raise FileNotFoundError(
            f"BSB source missing at {src}. Run `make fetch-bsb` to download it from "
            f"{UPSTREAM}."
        )
    with open(src, encoding="utf-8") as f:
        verses = dict(_parse(f))
    if not verses:
        raise RuntimeError(f"Parsed zero verses from {src}; check the file format.")
    write_json(os.path.join(out_dir, "verses.json"), verses)
    fh = sha256_file(src)
    return make_manifest(
        id=ID,
        name="Berean Standard Bible",
        version="2026.10",
        kind=KIND,
        fetch_hash=fh,
        source_ref=fh[:12],
        license={
            "spdx": "LicenseRef-Public-Domain",
            "name": "Public Domain",
            "url": "https://berean.bible/licensing.htm",
            "attribution": (
                "Berean Standard Bible, dedicated to the public domain by the Berean "
                "Bible Translation Committee on April 30, 2023. Produced in "
                "cooperation with Bible Hub, Discovery Bible, unfoldingWord, Bible "
                "Aquifer, OpenBible.com, and the Berean Bible Translation Committee."
            ),
        },
        source={
            "upstream": UPSTREAM,
            "revision": "bsb.txt",
            "modifications": (
                "Each verse rekeyed to OSIS id; tab-separated plain text parsed into a "
                "verseId → text JSON object. Preamble lines dropped."
            ),
        },
        out_dir=out_dir,
        files={"verses": "verses.json"},
        extra={"lang": "en", "textDir": "ltr", "verseCount": len(verses)},
    )
