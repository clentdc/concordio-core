"""Entities pack from Theographic Bible Metadata.

Reads ``.cache/theographic-bible-metadata/json/`` and emits an entities pack:
``books.json``, ``chapters.json``, ``people.json``, ``places.json``, ``events.json``,
``dictionary.json``.

Entity records are keyed by stable string ids (``p-moses``, ``l-jerusalem``,
``e-creation-of-all-things``) and reference verses by their OSIS verse id. Translation
packs do not depend on this file; the app only uses it to render traces, the detail
panel, and the entity-highlighting overlay at reader render time.

License: Theographic Bible Metadata is CC BY-SA 4.0. The derivative files emitted by
this adapter inherit CC BY-SA 4.0.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .. import osis as O
from .. import slugs as SL
from . import git_rev, make_manifest, sha256_tree, write_json

ID = "theographic"
KIND = "entities"
UPSTREAM = "https://github.com/robertrouse/theographic-bible-metadata"


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(prefix, text):
    s = _SLUG_RE.sub("-", (text or "").lower()).strip("-")
    return f"{prefix}-{s or 'unknown'}"


def _load(src, name):
    with open(src / "json" / f"{name}.json", encoding="utf-8") as f:
        return json.load(f)


def _short(t, n=None):
    """Whitespace-normalise a dictionary excerpt. `n` is retained for callers
    that want a hard cap, but the default is None (no truncation) so the
    reader sees the full Easton's entry in the side panel."""
    if isinstance(t, list):
        t = " ".join(x for x in t if isinstance(x, str))
    t = re.sub(r"\s+", " ", (t or "").replace("�", " ")).strip()
    if n is None or len(t) <= n:
        return t
    return t[: n].rsplit(" ", 1)[0] + "…"


def build(cache_dir: str, out_dir: str) -> dict:
    src = Path(cache_dir) / "theographic-bible-metadata"
    if not src.exists():
        raise FileNotFoundError(
            f"Theographic source missing at {src}. Run `make fetch-theographic`."
        )

    books_raw = sorted(_load(src, "books"), key=lambda r: r["fields"]["bookOrder"])
    chapters_raw = _load(src, "chapters")
    verses_raw = [v for v in _load(src, "verses") if "verseID" in v["fields"]]
    people_raw = _load(src, "people")
    places_raw = _load(src, "places")
    events_raw = _load(src, "events")

    # OSIS verse id per Theographic verse record id.
    verses_raw.sort(key=lambda v: v["fields"]["verseID"])
    v_osis = {}
    for v in verses_raw:
        f = v["fields"]
        vid_num = f["verseID"]
        b_idx = int(vid_num[:2]) - 1
        c = int(vid_num[2:5])
        n = int(vid_num[5:8])
        osis = books_raw[b_idx]["fields"]["osisName"]
        v_osis[v["id"]] = O.vid(osis, c, n)
        if osis not in O.OSIS_SET:
            raise RuntimeError(f"Theographic book {b_idx} has unknown OSIS {osis}.")

    def vlist(tv):
        """Theographic verse-record ids → sorted unique OSIS verse ids."""
        seen = {v_osis[x] for x in (tv or []) if x in v_osis}
        return sorted(seen, key=lambda s: (O.OSIS_ORDER[s.split(".", 1)[0]],
                                           int(s.split(".")[1]),
                                           int(s.split(".")[2])))

    # Books
    books = []
    for r in books_raw:
        f = r["fields"]
        books.append({
            "osis": f["osisName"],
            "n": f["bookName"],
            "s": f.get("shortName", f["osisName"]),
            "t": "OT" if f["testament"].startswith("Old") else "NT",
            "d": f.get("bookDiv", ""),
            "cn": len(f.get("chapters", [])),
        })

    # Chapters — derive from verses so chapter numbers and counts are canonical.
    ch_counts = {}
    for v in verses_raw:
        osis = v_osis[v["id"]].split(".")[0]
        c = int(v["fields"]["verseID"][2:5])
        ch_counts[(osis, c)] = ch_counts.get((osis, c), 0) + 1
    chapters = [
        [osis, c, ch_counts[(osis, c)]]
        for osis in [b["osis"] for b in books]
        for c in sorted({cc for (bb, cc) in ch_counts if bb == osis})
    ]
    if len(chapters) != 1189:
        raise RuntimeError(f"Expected 1189 chapters, got {len(chapters)}.")

    # People
    p_slug = {}
    people = []
    for r in people_raw:
        f = r["fields"]
        name = f.get("displayTitle") or f.get("name") or "Unknown"
        pid = _slug("p", f.get("slug") or name)
        if pid in p_slug:
            pid = f"{pid}-{len(people)}"
        p_slug[r["id"]] = pid
        people.append({
            "id": pid,
            "n": name,
            "aliases": sorted({name, f.get("name") or name}),
            "g": (f.get("gender") or "")[:1],
            "verses": vlist(f.get("verses")),
            "by": f.get("birthYear"),
            "dy": f.get("deathYear"),
            "x": _short(f.get("dictionaryText") or f.get("dictText")),
            "_raw": {
                "fa": f.get("father") or [],
                "mo": f.get("mother") or [],
                "sp": f.get("partners") or [],
                "ki": f.get("children") or [],
                "si": f.get("siblings") or [],
                "bp": f.get("birthPlace") or [],
                "dp": f.get("deathPlace") or [],
            },
        })

    # Places
    pl_slug = {}
    places = []
    for r in places_raw:
        f = r["fields"]
        name = f.get("displayTitle") or f.get("kjvName") or "Unknown"
        pid = _slug("l", f.get("slug") or name)
        if pid in pl_slug:
            pid = f"{pid}-{len(places)}"
        pl_slug[r["id"]] = pid
        lat = f.get("latitude") or f.get("openBibleLat")
        lon = f.get("longitude") or f.get("openBibleLong")
        aliases = sorted({x for x in (name, f.get("kjvName"), f.get("name")) if x})
        places.append({
            "id": pid,
            "n": name,
            "aliases": aliases,
            "ty": f.get("featureType", ""),
            "verses": vlist(f.get("verses")),
            "ll": [float(lat), float(lon)] if lat and lon else None,
            "cm": f.get("comment", ""),
            "x": _short(f.get("dictText")),
        })

    # Resolve people's family and place links to the new string ids.
    for p, r in zip(people, people_raw):
        raw = p.pop("_raw")
        p["fa"] = [p_slug[x] for x in raw["fa"] if x in p_slug]
        p["mo"] = [p_slug[x] for x in raw["mo"] if x in p_slug]
        p["sp"] = [p_slug[x] for x in raw["sp"] if x in p_slug]
        p["ki"] = [p_slug[x] for x in raw["ki"] if x in p_slug]
        p["si"] = [p_slug[x] for x in raw["si"] if x in p_slug]
        p["bp"] = [pl_slug[x] for x in raw["bp"] if x in pl_slug]
        p["dp"] = [pl_slug[x] for x in raw["dp"] if x in pl_slug]

    # Events
    events = []
    for r in sorted(events_raw, key=lambda r: r["fields"].get("sortKey")
                    or r["fields"].get("eventID", 0)):
        f = r["fields"]
        title = f.get("title") or "Unknown event"
        events.append({
            "id": _slug("e", title),
            "n": title,
            "aliases": [title],
            "dt": f.get("startDate"),
            "verses": vlist(f.get("verses")),
            "pp": [p_slug[x] for x in (f.get("participants") or []) if x in p_slug],
        })

    # URL slugs: one unique, stable slug per entity (plus a display qualifier for namesakes).
    # Written into the pack so the app, the Index page and share links read the same field.
    SL.apply_slugs(people, places, events, books)

    # Dictionary: Easton's excerpts keyed by entity id.
    dictionary = {p["id"]: p["x"] for p in people if p["x"]}
    dictionary.update({l["id"]: l["x"] for l in places if l["x"]})

    rev = git_rev(src)
    fh = sha256_tree(src / "json", globs=["*.json"])
    write_json(os.path.join(out_dir, "books.json"), books)
    write_json(os.path.join(out_dir, "chapters.json"), chapters)
    write_json(os.path.join(out_dir, "people.json"), [_strip_x(p) for p in people])
    write_json(os.path.join(out_dir, "places.json"), [_strip_x(p) for p in places])
    write_json(os.path.join(out_dir, "events.json"), events)
    write_json(os.path.join(out_dir, "dictionary.json"), dictionary)

    # Suffix the upstream rev so that bumping only the adapter (e.g. a change
    # to _short that enlarges dictionary.json) produces a new pack URL and the
    # browser + service worker refetch instead of serving stale truncated text.
    return make_manifest(
        id=ID,
        name="Theographic Bible Metadata",
        version=f"{rev}-full-s1",     # -s1: entities carry slug/dq (D48)
        kind=KIND,
        license={
            "spdx": "CC-BY-SA-4.0",
            "name": "Creative Commons Attribution-ShareAlike 4.0 International",
            "url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "attribution": (
                "Theographic Bible Metadata by Robert Rouse, licensed under Creative "
                "Commons Attribution-ShareAlike 4.0 International. Easton's Bible "
                "Dictionary (M. G. Easton, 1897) and the KJV verse index text are "
                "public domain. Chronology within Theographic follows Dr. Floyd Nolen "
                "Jones. Place coordinates come from OpenBible.info Bible Geocoding "
                "(CC BY 4.0, https://www.openbible.info/geo/). Theographic credits "
                "further original sources, several with their own licences; please "
                "also credit them."
            ),
            "shareAlike": True,
        },
        source={
            "upstream": UPSTREAM,
            "revision": rev,
            "modifications": (
                "Books, chapters, people, places, events compacted; verse ids rekeyed "
                "to OSIS; entity ids slugified; family/place links rewritten to the "
                "new ids; Easton's excerpts carried in full, whitespace-normalised; unique URL "
                "slugs and namesake qualifiers added (pipeline/slugs.py)."
            ),
        },
        fetch_hash=fh,
        source_ref=rev,
        out_dir=out_dir,
        files={
            "books": "books.json", "chapters": "chapters.json",
            "people": "people.json", "places": "places.json",
            "events": "events.json", "dictionary": "dictionary.json",
        },
        extra={
            "alsoCredit": "https://github.com/robertrouse/theographic-bible-metadata/blob/master/docs/data-source-bibliography.md",
            "counts": {
                "books": len(books), "chapters": len(chapters),
                "verses": len(verses_raw), "people": len(people),
                "places": len(places), "events": len(events),
            },
        },
    )


def _strip_x(entity):
    """Remove the inline dictionary excerpt from a person/place record.

    The excerpt lives in ``dictionary.json`` and is loaded on demand by the detail
    panel, so keeping a copy on the main list wastes bytes on every initial fetch.
    """
    out = {k: v for k, v in entity.items() if k != "x"}
    return out
