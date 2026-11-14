"""King James Version translation pack, sourced from Theographic's verse text.

Theographic ships the KJV with inline Markdown-style entity links
(``[Cain]([/person/cain)``). This adapter strips every link, keeping only the surface
text, and emits a plain translation pack. Entity highlighting is applied client-side
by the reader at render time using the entities pack's ``aliases[]``.

License: King James Version (1611) is public domain in the United States. See the
UK Crown copyright note in ``NOTICE.md`` and ``docs/DATA.md#legal-notes``.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .. import osis as O
from . import git_rev, make_manifest, sha256_tree, write_json

ID = "kjv"
KIND = "translation"
UPSTREAM = "https://github.com/robertrouse/theographic-bible-metadata"
REQUIRES = ["theographic"]

_LINK_RE = re.compile(r"\[([^\]]+)\]\(\[?/(?:person|place)/[^)\s]+\)")


def build(cache_dir: str, out_dir: str) -> dict:
    src = Path(cache_dir) / "theographic-bible-metadata"
    if not src.exists():
        raise FileNotFoundError(f"Theographic source missing at {src}.")

    books = {
        r["fields"]["bookOrder"]: r["fields"]["osisName"]
        for r in json.load(open(src / "json" / "books.json", encoding="utf-8"))
    }
    verses_raw = [v for v in json.load(open(src / "json" / "verses.json", encoding="utf-8"))
                  if "verseID" in v["fields"]]
    verses_raw.sort(key=lambda v: v["fields"]["verseID"])

    verses = {}
    for v in verses_raw:
        f = v["fields"]
        vid_num = f["verseID"]
        b_idx = int(vid_num[:2])
        c = int(vid_num[2:5])
        n = int(vid_num[5:8])
        osis = books[b_idx]
        text = f.get("richText") or f.get("verseText") or ""
        # Strip Markdown-style entity links, keep the visible label.
        text = _LINK_RE.sub(lambda m: m.group(1), text)
        # Replace literal braces defensively; none should appear in KJV but
        # downstream renderers may use them as sentinels.
        text = text.replace("{", "(").replace("}", ")")
        # Collapse whitespace artifacts; Theographic uses em-dashes and italics
        # markers like "_be_" in some verses — preserve for now.
        text = re.sub(r"\s+", " ", text).strip()
        verses[O.vid(osis, c, n)] = text

    if len(verses) != 31102:
        raise RuntimeError(f"Expected 31102 KJV verses, got {len(verses)}.")

    write_json(os.path.join(out_dir, "verses.json"), verses)

    rev = git_rev(src)
    fh = sha256_tree(src / "json", globs=["books.json", "verses.json"])
    return make_manifest(
        id=ID,
        name="King James Version (1769 text)",
        version=f"theographic-{rev}",
        kind=KIND,
        fetch_hash=fh,
        source_ref=rev,
        license={
            "spdx": "LicenseRef-KJV-US-PD",
            "name": "Public Domain (United States)",
            "url": "https://ebible.org/kjv/copr.htm",
            "attribution": (
                "King James Version, the 1769 Cambridge standard text (supplied through "
                "Theographic Bible Metadata). Public domain in the United States. In the "
                "United Kingdom the Crown holds rights in the Authorized Version, "
                "administered by Cambridge University Press under letters patent. No "
                "regional restriction is currently applied to this pack; UK use is "
                "subject to legal review. See NOTICE.md in the repository."
            ),
        },
        source={
            "upstream": UPSTREAM,
            "revision": (
                "theographic verses.json (verseText/richText fields); Theographic's "
                "data-source bibliography names the text 'King James Version, 1769 "
                "Cambridge Edition'; Theographic does not state its own upstream copy"
            ),
            "modifications": (
                "Markdown-style entity links (`[Cain]([/person/cain)`) stripped to "
                "surface text. Verses rekeyed to OSIS id. Underscores and italics "
                "markers kept."
            ),
        },
        out_dir=out_dir,
        files={"verses": "verses.json"},
        extra={"lang": "en", "textDir": "ltr", "verseCount": len(verses)},
    )
