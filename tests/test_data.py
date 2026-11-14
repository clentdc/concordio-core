"""Integrity checks for the generated pack files and the PWA shell.

Runs with plain Python (no dependencies):   python3 tests/test_data.py
Also collected by pytest if you have it:    pytest tests/

These guard the project's core data rules:
- Every entity's verse list points at real OSIS verse ids present in the entities pack.
- Each translation pack covers every verse that the entities pack enumerates.
- Pack manifests have the required fields and valid license references.
- The service worker precaches every file it claims to.
- Entity slugs are unique, stable and match pipeline/slug-lock.json.
"""
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(__file__), '..')
WEB = os.path.join(ROOT, 'web')
PACKS_ROOT = os.path.join(WEB, 'data', 'packs')


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


# -- Pack discovery ----------------------------------------------------------

def _packs():
    index = load(os.path.join(PACKS_ROOT, 'index.json'))
    return index['packs']


def _manifest(pack_id):
    return load(os.path.join(PACKS_ROOT, pack_id, 'manifest.json'))


def _pack_file(pack_id, filename):
    return load(os.path.join(PACKS_ROOT, pack_id, filename))


# -- Entities pack -----------------------------------------------------------

ENTITIES = next((p for p in _packs() if p['kind'] == 'entities'), None)
assert ENTITIES is not None, "No entities pack found in web/data/packs/index.json"

BOOKS = _pack_file(ENTITIES['id'], 'books.json')
CHAPTERS = _pack_file(ENTITIES['id'], 'chapters.json')
PEOPLE = _pack_file(ENTITIES['id'], 'people.json')
PLACES = _pack_file(ENTITIES['id'], 'places.json')
EVENTS = _pack_file(ENTITIES['id'], 'events.json')

VERSE_IDS = set()
for osis, c, count in CHAPTERS:
    for v in range(1, count + 1):
        VERSE_IDS.add(f"{osis}.{c}.{v}")


def test_canon_counts():
    assert len(BOOKS) == 66, f"Expected 66 books, got {len(BOOKS)}"
    assert len(CHAPTERS) == 1189, f"Expected 1189 chapters, got {len(CHAPTERS)}"
    assert len(VERSE_IDS) == 31102, f"Expected 31102 verses, got {len(VERSE_IDS)}"
    assert sum(1 for b in BOOKS if b['t'] == 'OT') == 39


def test_chapters_match_books():
    for b in BOOKS:
        ch_for_book = [c for c in CHAPTERS if c[0] == b['osis']]
        assert len(ch_for_book) == b['cn'], \
            f"{b['osis']}: book claims {b['cn']} chapters, chapters list has {len(ch_for_book)}"


def test_entity_verses_resolve():
    for kind, entities in (('people', PEOPLE), ('places', PLACES), ('events', EVENTS)):
        for e in entities:
            v = e['verses']
            assert v == sorted(v, key=_vid_sort), f"{kind}:{e['id']}: verse list not canonically sorted"
            assert all(vid in VERSE_IDS for vid in v), \
                f"{kind}:{e['id']}: contains a verse id not in the chapters list"


def test_entity_ids_are_unique_per_kind():
    for kind, entities in (('people', PEOPLE), ('places', PLACES), ('events', EVENTS)):
        ids = [e['id'] for e in entities]
        assert len(ids) == len(set(ids)), f"{kind}: duplicate entity ids"


def test_entity_aliases_present():
    for kind, entities in (('people', PEOPLE), ('places', PLACES)):
        for e in entities:
            assert e['aliases'], f"{kind}:{e['id']}: empty aliases (highlighting needs them)"
            assert e['n'] in e['aliases'], f"{kind}:{e['id']}: display name not in aliases"


# -- Entity slugs (D48) ------------------------------------------------------
# A URL names an entity by its pack `slug`. These tests keep the pack, the lock file, the app
# parser and the Index page in step: every entity reachable by exactly one slug, every namesake
# told apart, and no second slug algorithm hiding in the pages.

sys.path.insert(0, os.path.abspath(ROOT))
from pipeline.slugs import LOCK_PATH, slugify as _slugify  # noqa: E402

KINDS = (('people', PEOPLE, 'p'), ('places', PLACES, 'l'), ('events', EVENTS, 'e'))


def test_entity_slugs_are_present_unique_and_normalised():
    for kind, entities, _ in KINDS:
        slugs = [e.get('slug') for e in entities]
        assert all(slugs), f"{kind}: an entity has no slug"
        assert len(set(slugs)) == len(slugs), f"{kind}: duplicate slugs"
        # The URL parser runs every token through slugify(); a slug it would rewrite cannot round-trip.
        bad = [s for s in slugs if _slugify(s) != s]
        assert not bad, f"{kind}: slugs the parser would rewrite: {bad[:5]}"


def test_slug_lock_matches_the_pack():
    lock = load(str(LOCK_PATH))
    for kind, entities, _ in KINDS:
        for e in entities:
            assert lock[kind].get(e['id']) == e['slug'], f"{kind}:{e['id']}: slug differs from pipeline/slug-lock.json"


def test_namesakes_are_told_apart():
    for kind, entities, _ in KINDS:
        groups = {}
        for e in entities:
            groups.setdefault(_slugify(e['n']) or e['id'], []).append(e)
        for base, members in groups.items():
            if len(members) < 2:
                assert 'dq' not in members[0], f"{kind}:{base}: qualifier on a lone name"
                continue
            bare = [m for m in members if m['slug'] == base]
            assert len(bare) == 1, f"{kind}:{base}: {len(bare)} entities hold the bare slug"
            for m in members:
                assert m.get('dq'), f"{kind}:{m['id']}: namesake without a display qualifier"
                assert m is bare[0] or m['slug'].startswith(base + '-'), f"{kind}:{m['id']}: slug does not extend {base}"


def test_pack_ids_are_accepted_tokens_without_clashing_with_slugs():
    for kind, entities, _ in KINDS:
        slugs = {e['slug']: e['id'] for e in entities}
        for e in entities:
            assert _slugify(e['id']) == e['id'], f"{kind}:{e['id']}: id would be rewritten by the parser"
            other = slugs.get(e['id'])
            assert other in (None, e['id']), f"{kind}:{e['id']}: id equals another entity's slug"


def test_every_link_resolves_to_the_entity_it_names():
    """Replays URLSTATE.parseToken + the slug index for every entity (and the Index page's link shapes)."""
    prefix = {'p': '', 'l': '@', 'e': '!'}
    for kind, entities, k in KINDS:
        index = {e['slug']: e['id'] for e in entities}
        index.update({e['id']: e['id'] for e in entities if e['id'] not in index})
        for e in entities:
            for token in (prefix[k] + e['slug'], prefix[k] + e['id']):
                body = token[1:] if token[:1] in '@!' else token
                assert index.get(_slugify(body)) == e['id'], f"{kind}:{token} does not resolve to {e['id']}"


# -- Translation packs -------------------------------------------------------

# Verses deliberately omitted by critical-text translations on
# text-critical grounds. The RSV, NIV, ESV, Darby, and others treat
# these as later additions not present in the earliest manuscripts.
# When a translation drops one, it is not a bug in our pipeline.
CRITICAL_OMISSIONS = {
    'Matt.17.21', 'Matt.18.11', 'Matt.23.14',
    'Mark.7.16', 'Mark.9.44', 'Mark.9.46', 'Mark.11.26', 'Mark.15.28',
    'Luke.17.36', 'Luke.23.17',
    'John.5.4',
    'Acts.8.37', 'Acts.15.34', 'Acts.24.7', 'Acts.28.29',
    'Rom.16.24',
}


# Packs that follow the Vulgate's versification (different psalm, Chronicles,
# Samuel, and Daniel verse boundaries than the Protestant / Masoretic text).
# A verse-by-verse coverage check against VERSE_IDS is not meaningful for them;
# they ship with an `approximate_canon_coverage` flag in their manifest and a
# `versify.json` mapping is planned as a follow-up (D35).
VULGATE_VERSIFIED = {'douay-rheims', 'vulgata-clementina'}


def test_translation_packs_cover_every_verse():
    for pack in _installable_packs():
        if pack['kind'] != 'translation':
            continue
        verses = _pack_file(pack['id'], 'verses.json')
        if pack['id'] in VULGATE_VERSIFIED:
            # Vulgate-versified packs must at least carry most of the canon.
            assert len(verses) >= 30_000, \
                f"translation:{pack['id']}: Vulgate-versified pack has only {len(verses)} verses"
            continue
        missing = (VERSE_IDS - set(verses.keys())) - CRITICAL_OMISSIONS
        assert not missing, \
            f"translation:{pack['id']}: missing {len(missing)} verses beyond known critical omissions (e.g., {sorted(missing)[:3]})"
        extra = set(verses.keys()) - VERSE_IDS
        # Translations may ship with slight versification differences; warn but allow.
        if extra:
            print(f"note: {pack['id']} has {len(extra)} verses not in the canon index")


def test_translation_packs_have_no_replacement_characters():
    for pack in _installable_packs():
        if pack['kind'] != 'translation':
            continue
        verses = _pack_file(pack['id'], 'verses.json')
        for vid, text in verses.items():
            assert '�' not in text, f"translation:{pack['id']}: U+FFFD in {vid}"


# -- Interlinear packs -------------------------------------------------------

def test_interlinear_packs_cover_every_book():
    for pack in _packs():
        if pack['kind'] != 'interlinear':
            continue
        pack_dir = os.path.join(PACKS_ROOT, pack['id'], 'interlinear')
        assert os.path.isdir(pack_dir), f"interlinear:{pack['id']}: missing interlinear/ dir"
        have = {name[:-5] for name in os.listdir(pack_dir) if name.endswith('.json')}
        expected = {b['osis'] for b in BOOKS}
        missing = expected - have
        assert not missing, f"interlinear:{pack['id']}: no interlinear for books {sorted(missing)}"


def test_interlinear_word_records_have_required_fields():
    required = {'src', 'strongs', 'morph'}
    for pack in _packs():
        if pack['kind'] != 'interlinear':
            continue
        pack_dir = os.path.join(PACKS_ROOT, pack['id'], 'interlinear')
        # Sample two books to keep the test fast; a schema break will show here.
        for book in ('Gen', 'Rev'):
            data = load(os.path.join(pack_dir, f'{book}.json'))
            for vid, words in list(data.items())[:3]:
                assert isinstance(words, list) and words, f"{pack['id']}:{vid}: empty word list"
                for w in words:
                    missing = required - set(w.keys())
                    assert not missing, f"{pack['id']}:{vid}: word missing {missing}"


def test_interlinear_strongs_and_morph_files_exist():
    for pack in _packs():
        if pack['kind'] != 'interlinear':
            continue
        pack_dir = os.path.join(PACKS_ROOT, pack['id'])
        strongs = load(os.path.join(pack_dir, 'strongs.json'))
        morph = load(os.path.join(pack_dir, 'morph_codes.json'))
        assert strongs, f"interlinear:{pack['id']}: empty strongs.json"
        assert morph, f"interlinear:{pack['id']}: empty morph_codes.json"


# -- Manifests ---------------------------------------------------------------

REQUIRED_MANIFEST_FIELDS = {'id', 'name', 'version', 'kind', 'license', 'source',
                            'sizeBytes', 'files', 'schemaVersion'}
KNOWN_KINDS = {'translation', 'interlinear', 'entities', 'entities-i18n',
               'lexicon', 'morph-key', 'geo', 'xrefs', 'chrome', 'imagery'}

# Chrome and imagery packs use a lighter manifest schema than data packs
# (no `source`, no `schemaVersion`, no byte-count guarantee), so the strict
# field + size checks apply only to the data kinds.
STRICT_KINDS = {'translation', 'interlinear', 'entities', 'lexicon',
                'morph-key', 'geo', 'xrefs'}


def _installable_packs():
    """Catalog entries that promise on-disk files.

    Skips packs marked `installable: false` (roadmap stubs like Reina-Valera),
    which exist as pointers in index.json but do not have per-pack manifests
    yet.
    """
    return [p for p in _packs() if p.get('installable', True)]


def test_manifests_have_required_fields():
    for pack in _installable_packs():
        m = _manifest(pack['id'])
        assert m['kind'] in KNOWN_KINDS, f"{pack['id']}: unknown kind {m['kind']}"
        if m['kind'] in STRICT_KINDS:
            missing = REQUIRED_MANIFEST_FIELDS - set(m.keys())
            assert not missing, f"{pack['id']}: manifest missing {missing}"
            assert m['license'].get('attribution'), f"{pack['id']}: license.attribution is empty"
        else:
            # chrome and imagery packs may carry a bare SPDX string in `license`
            # instead of a dict; just confirm licensing info is present.
            assert m.get('license'), f"{pack['id']}: license is missing"


def test_manifest_sizes_match_disk():
    for pack in _installable_packs():
        m = _manifest(pack['id'])
        if m['kind'] not in STRICT_KINDS:
            # chrome and imagery packs do not carry a verified sizeBytes.
            continue
        on_disk = 0
        pack_dir = os.path.join(PACKS_ROOT, pack['id'])
        for root, _, names in os.walk(pack_dir):
            for n in names:
                if n == 'manifest.json':
                    continue
                on_disk += os.path.getsize(os.path.join(root, n))
        # Allow 1 KB slack for stable-key JSON ordering drift between manifest-time
        # and test-time (none expected, but it keeps CI resilient).
        delta = abs(on_disk - m['sizeBytes'])
        assert delta <= 1024, \
            f"{pack['id']}: on-disk size {on_disk} vs manifest {m['sizeBytes']} (delta {delta})"


# -- PWA shell ---------------------------------------------------------------

def test_service_worker_precache_files_exist():
    with open(os.path.join(WEB, 'sw.js'), encoding='utf-8') as f:
        sw = f.read()
    start = sw.index('const PRECACHE = [')
    block = sw[start:sw.index('];', start)]
    for path in re.findall(r"'\./([^']*)'", block):
        target = os.path.join(WEB, path or 'index.html')
        assert os.path.exists(target), f'precached file missing: {path}'


def test_manifest_icons_exist():
    with open(os.path.join(WEB, 'manifest.webmanifest'), encoding='utf-8') as f:
        manifest = json.load(f)
    purposes = {i.get('purpose', 'any') for i in manifest['icons']}
    # The minimal reader ships one SVG icon; a maskable icon is the downstream app's job.
    assert 'any' in purposes
    for icon in manifest['icons']:
        assert os.path.exists(os.path.join(WEB, icon['src'])), icon['src']


# -- Sort key for OSIS verse ids (used by test_entity_verses_resolve) --------

_OSIS_ORDER = {b['osis']: i for i, b in enumerate(BOOKS)}


def _vid_sort(vid):
    osis, c, v = vid.split('.')
    return (_OSIS_ORDER[osis], int(c), int(v))


# -- Runner ------------------------------------------------------------------

if __name__ == '__main__':
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print('ok  ', name)
        except AssertionError as e:
            print(f'FAIL {name}: {e}')
            failed += 1
    if failed:
        print(f'\n{failed} of {len(tests)} checks failed')
        sys.exit(1)
    print(f'\n{len(tests)} checks passed')
