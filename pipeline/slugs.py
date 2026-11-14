"""Unique, stable URL slugs for entities (people, places, events).

Why this exists: two entities that share a display name used to share a slug
(``michael`` ×11, ``elijah`` ×2, …), so a link could only ever reach the last of
them. Every entity now carries its own ``slug`` in the pack, and the app, the
Index page and the share-link parser all read that one field. See D50 and
docs/URLS.md § Slug rules.

Rules (deterministic; the lock file makes them stable across data refreshes):

1. ``base`` = the slugified display name (lowercase, NFKD, marks stripped,
   non-alphanumeric runs → ``-``). This is the rule the old URLs used.
2. A name held by one entity: slug = base.
3. A name held by several: the **most-mentioned** entity keeps the bare base
   slug (so every existing link keeps working and now reaches the person people
   mean); the others get a qualifier, using the first rung that is unique:
     a. people: ``base-son-of-<father>`` / ``-daughter-of-`` / ``-child-of-``
     b. ``base-<first-mention>``, e.g. ``michael-1chr-12-20``
     c. ``base-<id number>``, e.g. ``michael-2064``
   The entity's pack id (``p-michael-2064``) is also always accepted in a URL.
4. ``dq`` (display qualifier, e.g. "son of Abihail" or "1 Chronicles 12:20") is
   written for **every** member of a collision group, including the one with the
   bare slug, so lists and chips can tell namesakes apart.
5. ``pipeline/slug-lock.json`` records every published id → slug. A locked slug
   never changes, even if verse counts shift on a later refresh; new entities
   are slotted around the locked ones.

Nothing here invents a link between an entity and a verse: the slug is
derived only from the entity's own name, family links and first reference.
"""
from __future__ import annotations

import collections
import json
import re
import unicodedata
from pathlib import Path

LOCK_PATH = Path(__file__).resolve().parent / "slug-lock.json"
KINDS = ("people", "places", "events")


def slugify(s) -> str:
    """Identical to ``slugify`` in web/js/app.js (URLSTATE) — keep the two in step."""
    s = unicodedata.normalize("NFKD", str(s or "").lower())
    s = re.sub(r"[̀-ͯ]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _tail_num(entity_id: str) -> str:
    m = re.search(r"(\d+)$", entity_id)
    return m.group(1) if m else entity_id


def _ref_text(osis_verse: str, book_names: dict) -> str:
    book, chapter, verse = osis_verse.split(".")
    return f"{book_names.get(book, book)} {chapter}:{verse}"


def load_lock(path: Path = LOCK_PATH) -> dict:
    if not path.exists():
        return {"schema": 1, **{k: {} for k in KINDS}}
    lock = json.loads(path.read_text(encoding="utf-8"))
    for k in KINDS:
        lock.setdefault(k, {})
    return lock


def _assign(kind, ents, lock_kind, people_names, book_names):
    ids = {e["id"] for e in ents}
    slug_of, taken = {}, {}
    for e in ents:                                    # A. honour the lock
        s = lock_kind.get(e["id"])
        if s:
            if s in taken:
                raise RuntimeError(f"{kind}: slug-lock maps two ids to {s!r}")
            slug_of[e["id"]] = s
            taken[s] = e["id"]
    for i, s in lock_kind.items():                    # slugs of vanished entities stay reserved
        taken.setdefault(s, i)

    base_of = {e["id"]: (slugify(e["n"]) or e["id"]) for e in ents}
    groups = collections.defaultdict(list)
    for idx, e in enumerate(ents):
        groups[base_of[e["id"]]].append((idx, e))
    all_bases = set(groups)

    def father_slug(e):
        f = (e.get("fa") or [None])[0]
        return slugify(people_names.get(f, "")) if f else ""

    def relation(e):
        return {"M": "son-of", "F": "daughter-of"}.get(e.get("g"), "child-of")

    for base in sorted(groups):                       # B. everything the lock did not cover
        members = sorted((t for t in groups[base] if t[1]["id"] not in slug_of),
                         key=lambda t: (-len(t[1]["verses"]), t[0]))
        if not members:
            continue
        rest = members
        if base not in taken:                         # most-mentioned namesake keeps the bare slug
            _, winner = members[0]
            slug_of[winner["id"]] = base
            taken[base] = winner["id"]
            rest = members[1:]
        pending = {e["id"]: e for _, e in rest}
        ladder = []
        if kind == "people":
            ladder.append(lambda e: f"{base}-{relation(e)}-{father_slug(e)}" if father_slug(e) else None)
        ladder.append(lambda e: f"{base}-{slugify(e['verses'][0])}" if e["verses"] else None)
        ladder.append(lambda e: f"{base}-{_tail_num(e['id'])}")
        ladder.append(lambda e: f"{base}-{slugify(e['id'])}")
        for rung in ladder:
            cands = {i: rung(e) for i, e in pending.items()}
            count = collections.Counter(c for c in cands.values() if c)
            for i, c in list(cands.items()):
                if c and count[c] == 1 and c not in taken and c not in all_bases:
                    slug_of[i] = c
                    taken[c] = i
                    del pending[i]
        if pending:
            raise RuntimeError(f"{kind}: could not make unique slugs for {sorted(pending)}")

    dq = {}                                           # display qualifier for every member of a group
    for base, members in groups.items():
        if len(members) < 2:
            continue
        fathers = collections.Counter(father_slug(e) for _, e in members if kind == "people" and father_slug(e))
        labels = {}
        for _, e in members:
            fs = father_slug(e) if kind == "people" else ""
            if fs and fathers[fs] == 1:
                role = {"M": "son", "F": "daughter"}.get(e.get("g"), "child")
                labels[e["id"]] = f"{role} of {people_names[e['fa'][0]]}"
            elif e["verses"]:
                labels[e["id"]] = _ref_text(e["verses"][0], book_names)
            else:
                labels[e["id"]] = e["id"]
        seen = collections.Counter(labels.values())
        for _, e in members:
            lab = labels[e["id"]]
            dq[e["id"]] = lab + (f" · #{_tail_num(e['id'])}" if seen[lab] > 1 else "")
    return slug_of, dq


def apply_slugs(people, places, events, books, *, lock_path: Path = LOCK_PATH, write_lock: bool = True) -> dict:
    """Add ``slug`` (always) and ``dq`` (collision-group members only) to every entity, in place."""
    book_names = {b["osis"]: b["n"] for b in books}
    people_names = {p["id"]: p["n"] for p in people}
    lock = load_lock(lock_path)
    summary = {}
    for kind, ents in zip(KINDS, (people, places, events)):
        slug_of, dq = _assign(kind, ents, lock[kind], people_names, book_names)
        for e in ents:
            e["slug"] = slug_of[e["id"]]
            if e["id"] in dq:
                e["dq"] = dq[e["id"]]
            lock[kind][e["id"]] = e["slug"]
        summary[kind] = {"entities": len(ents), "collision_groups": len({slugify(e["n"]) for e in ents if e["id"] in dq})}
    if write_lock:
        out = {"schema": 1, **{k: dict(sorted(lock[k].items())) for k in KINDS}}
        lock_path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return summary
