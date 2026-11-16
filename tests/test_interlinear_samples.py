"""Guards for the committed interlinear samples in web/data/samples/.

The two full interlinear packs are release artifacts, not stored in git. The samples are small
cuts of them (pipeline/samples.py) so a fresh clone still has real interlinear data. They are not
catalog packs: they sit outside web/data/packs/, so tests/test_data.py (which wants all 66 books in
an interlinear pack) and index.json do not apply. This file holds them to the same rules instead:
required manifest fields, a licence that matches their parent, sizes that match the disk, the word
shape the reader and cookbook expect, and, when the full pack is on disk, byte equality with a fresh cut.

Run: python3 tests/test_interlinear_samples.py
"""
import json
import os
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)
from pipeline.samples import SAMPLES, SAMPLES_DIR, build_sample  # noqa: E402

REQUIRED = {'id', 'name', 'version', 'kind', 'license', 'source', 'sizeBytes', 'files', 'schemaVersion', 'sample'}
WORD_FIELDS = {'src', 'translit', 'gloss', 'strongs', 'lemma', 'morph'}
LICENCE_SPDX = {'stepbible-sample': 'CC-BY-4.0', 'bsb-tables-sample': 'LicenseRef-Public-Domain'}
GREEK_ONLY = {'stepbible-sample'}


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def sample_dir(spec):
    return os.path.join(str(SAMPLES_DIR), spec['id'])


def files_under(root):
    out = {}
    for base, _, names in os.walk(root):
        for n in names:
            p = os.path.join(base, n)
            out[os.path.relpath(p, root)] = p
    return out


def test_samples_on_disk_are_exactly_the_declared_ones():
    on_disk = sorted(d for d in os.listdir(str(SAMPLES_DIR)) if os.path.isdir(os.path.join(str(SAMPLES_DIR), d)))
    assert on_disk == sorted(s['id'] for s in SAMPLES), f'samples on disk {on_disk} differ from pipeline/samples.py'


def test_sample_manifests_are_complete_and_carry_their_parents_licence():
    for spec in SAMPLES:
        m = load(os.path.join(sample_dir(spec), 'manifest.json'))
        assert not REQUIRED - set(m), f"{spec['id']}: manifest missing {sorted(REQUIRED - set(m))}"
        assert m['id'] == spec['id'] and m['kind'] == 'interlinear'
        assert m['license']['spdx'] == LICENCE_SPDX[spec['id']], f"{spec['id']}: wrong licence {m['license']['spdx']}"
        assert m['license'].get('attribution'), f"{spec['id']}: license.attribution is empty"
        assert m['sample']['of'] == spec['of'] and m['sample']['books'] == spec['books']
        assert m['version'] == f"{m['sample']['ofVersion']}-sample", f"{spec['id']}: version must differ from the full pack's"
        assert m['id'] != spec['of'], 'a sample must never share a cache key with its full pack'


def test_sample_sizes_and_files_match_the_disk():
    for spec in SAMPLES:
        d = sample_dir(spec)
        m = load(os.path.join(d, 'manifest.json'))
        files = files_under(d)
        on_disk = sum(os.path.getsize(p) for rel, p in files.items() if rel != 'manifest.json')
        assert on_disk == m['sizeBytes'], f"{spec['id']}: {on_disk} bytes on disk, manifest says {m['sizeBytes']}"
        expected = {'manifest.json', 'strongs.json', 'morph_codes.json',
                    *(os.path.join('interlinear', f'{b}.json') for b in spec['books'])}
        assert set(files) == expected, f"{spec['id']}: files {sorted(files)} differ from {sorted(expected)}"


def test_sample_words_have_the_shape_the_reader_expects():
    for spec in SAMPLES:
        d = sample_dir(spec)
        m = load(os.path.join(d, 'manifest.json'))
        strongs = load(os.path.join(d, 'strongs.json'))
        morph = load(os.path.join(d, 'morph_codes.json'))
        verses = words = 0
        used_s, used_m = set(), set()
        for book in spec['books']:
            data = load(os.path.join(d, 'interlinear', f'{book}.json'))
            for vid, ws in data.items():
                assert vid.split('.')[0] == book, f"{spec['id']}: {vid} is in {book}.json"
                assert isinstance(ws, list) and ws, f"{spec['id']}:{vid}: empty word list"
                verses += 1
                for w in ws:
                    assert WORD_FIELDS <= set(w), f"{spec['id']}:{vid}: word missing {WORD_FIELDS - set(w)}"
                    assert w['src'], f"{spec['id']}:{vid}: a word with no source text"
                    words += 1
                    if w['strongs']:
                        used_s.add(w['strongs'])
                    if w['morph']:
                        used_m.add(w['morph'])
        assert set(strongs) <= used_s and set(morph) <= used_m, f"{spec['id']}: lexicon or morph file holds entries no word uses"
        assert strongs, f"{spec['id']}: empty strongs.json"
        assert morph, f"{spec['id']}: empty morph_codes.json"
        assert m['counts'] == {'books': len(spec['books']), 'verses': verses, 'words': words,
                               'strongs': len(strongs), 'morphCodes': len(morph)}, f"{spec['id']}: counts are stale"


def test_greek_sample_carries_no_hebrew_lexicon_so_no_caveat_applies():
    # STEPBible's Hebrew definitions (TBESH) have an open permission caveat (docs/LICENSES.md). The sample
    # must not include any of them, and its manifest must not claim a caveat it does not need.
    for spec in SAMPLES:
        if spec['id'] not in GREEK_ONLY:
            continue
        d = sample_dir(spec)
        strongs = load(os.path.join(d, 'strongs.json'))
        assert not [k for k in strongs if k.startswith('H')], f"{spec['id']}: Hebrew lexicon entries in a Greek-only sample"
        assert load(os.path.join(d, 'manifest.json')).get('caveats') == []


def test_samples_equal_a_fresh_cut_of_the_full_pack_when_it_is_present():
    ran = 0
    for spec in SAMPLES:
        for base in (os.path.join(ROOT, 'dist', 'packs'), os.path.join(ROOT, 'web', 'data', 'packs')):
            parent = os.path.join(base, spec['of'])
            if not os.path.exists(os.path.join(parent, 'manifest.json')):
                continue
            with tempfile.TemporaryDirectory() as tmp:
                build_sample(parent, spec, tmp)
                fresh, committed = files_under(tmp), files_under(sample_dir(spec))
                assert set(fresh) == set(committed), f"{spec['id']}: file list differs from a fresh cut of {parent}"
                for rel in fresh:
                    with open(fresh[rel], 'rb') as a, open(committed[rel], 'rb') as b:
                        assert a.read() == b.read(), f"{spec['id']}/{rel} differs from a fresh cut of {parent}: re-run `make samples`"
            ran += 1
            break
    print(f'     ({ran} of {len(SAMPLES)} samples compared with a full pack; with no full pack on disk the comparison is skipped)')


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
