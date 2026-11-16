"""Guards for the release path: reproducible tarballs, verified fetch, a locked-down workflow.

The two large interlinear packs are not stored in git; each tagged release carries them as
tarballs plus SHA256SUMS (pipeline/release.py, .github/workflows/release.yml). Nothing here
downloads anything: fetch is exercised against a file:// release built in a temp directory.

Also, when the full packs have been built into dist/packs (make release-packs, as the release
workflow does), checks that they are whole: 66 books, the word shape, the manifest fields.

Run: python3 tests/test_release.py
"""
import gzip
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import release as R  # noqa: E402
from pipeline.packs import PACKS  # noqa: E402


def fake_pack(base, pack_id, version='1'):
    d = Path(base) / pack_id
    (d / 'interlinear').mkdir(parents=True)
    (d / 'interlinear' / 'Gen.json').write_text('{"Gen.1.1":[{"src":"x"}]}', encoding='utf-8')
    (d / 'strongs.json').write_text('{}', encoding='utf-8')
    size = sum(p.stat().st_size for p in d.rglob('*') if p.is_file())
    (d / 'manifest.json').write_text(json.dumps({
        'id': pack_id, 'version': version, 'sizeBytes': size, 'sourceRef': 'abc1234',
        'license': {'name': 'Test licence', 'attribution': 'Test attribution.'}}), encoding='utf-8')
    return d


def make_release(tmp, version='v9.9.9'):
    packs, out = Path(tmp) / 'packs', Path(tmp) / 'release'
    for pid in R.release_ids():
        fake_pack(packs, pid)
    R.main(['pack', '--version', version, '--packs', str(packs), '--out', str(out)])
    return packs, out


def fetch(out, dest, version='v9.9.9', *extra):
    R.main(['fetch', '--tag', version, '--base-url', Path(out).resolve().as_uri(), '--dest', str(dest), *extra])


def expect_exit(fn, needle):
    try:
        fn()
    except SystemExit as e:
        assert needle in str(e), f'expected an error mentioning {needle!r}, got {e}'
        return
    raise AssertionError(f'expected a failure mentioning {needle!r}')


def quiet(fn):
    old, sys.stdout = sys.stdout, io.StringIO()
    try:
        return fn()
    finally:
        sys.stdout = old


# -- which packs ship how ------------------------------------------------------

def test_delivery_is_declared_for_every_pack():
    assert all(e.get('delivery') in ('git', 'release') for e in PACKS), 'every pack in packs.py needs a delivery'
    assert R.release_ids() == ['stepbible', 'bsb-tables']


def test_release_delivered_packs_are_ignored_by_git_and_git_delivered_ones_are_not():
    ignored = set((ROOT / '.gitignore').read_text(encoding='utf-8').splitlines())
    for e in PACKS:
        line = e['out'].rstrip('/') + '/'
        assert (line in ignored) == (e['delivery'] == 'release'), f"{e['out']}: .gitignore disagrees with delivery"
    # No release-delivered pack may be committed (checked against the git index when this is a git checkout).
    if (ROOT / '.git').exists():
        out = subprocess.run(['git', '-C', str(ROOT), 'ls-files'] + [e['out'] for e in PACKS if e['delivery'] == 'release'],
                             capture_output=True, text=True)
        assert out.returncode == 0 and out.stdout.strip() == '', 'release-delivered packs must not be tracked in git'


# -- tarballs ------------------------------------------------------------------

def test_tarballs_are_reproducible():
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        da, db = fake_pack(a, 'stepbible'), fake_pack(b, 'stepbible')
        os.utime(db / 'strongs.json', (86400, 86400))   # a different mtime must not change the bytes
        ta, tb = Path(a) / 't.tar.gz', Path(b) / 't.tar.gz'
        R.make_tarball(da, 'stepbible', ta)
        R.make_tarball(db, 'stepbible', tb)
        assert ta.read_bytes() == tb.read_bytes()
        with tarfile.open(ta) as tar:
            names = tar.getnames()
            assert names[0] == 'stepbible' and set(n.split('/')[0] for n in names) == {'stepbible'}
            assert all(m.mtime == 0 and m.uid == 0 and m.gid == 0 and m.uname == '' for m in tar.getmembers())
        assert gzip.decompress(ta.read_bytes())[:6] != b''
        # gzip header carries no timestamp or filename
        assert ta.read_bytes()[4:8] == b'\0\0\0\0' and ta.read_bytes()[3] == 0


def test_pack_writes_sums_that_sha256sum_would_accept_and_refuses_a_dirty_staging_dir():
    with tempfile.TemporaryDirectory() as tmp:
        packs, out = Path(tmp) / 'packs', Path(tmp) / 'release'
        for pid in R.release_ids():
            fake_pack(packs, pid)
        quiet(lambda: R.main(['pack', '--version', 'v9.9.9', '--packs', str(packs), '--out', str(out)]))
        sums = R.parse_sums((out / 'SHA256SUMS').read_text(encoding='utf-8'))
        assert set(sums) == {R.asset_name(p, 'v9.9.9') for p in R.release_ids()}
        for name, digest in sums.items():
            assert R.sha256_file(out / name) == digest
        notes = (out / 'RELEASE-NOTES.md').read_text(encoding='utf-8')
        assert all(d in notes for d in sums.values()) and 'Test attribution.' in notes
        (packs / 'stepbible' / 'stray.json').write_text('{}', encoding='utf-8')
        expect_exit(lambda: quiet(lambda: R.main(['pack', '--version', 'v9.9.9', '--packs', str(packs), '--out', str(out)])),
                    'leftovers')
        expect_exit(lambda: R.main(['pack', '--version', '0.1.0', '--packs', str(packs), '--out', str(out)]), 'v0.1.0')


# -- fetch ---------------------------------------------------------------------

def test_fetch_verifies_then_unpacks_the_exact_files():
    with tempfile.TemporaryDirectory() as tmp:
        packs, out = quiet(lambda: make_release(tmp))
        dest = Path(tmp) / 'dest'
        quiet(lambda: fetch(out, dest))
        for pid in R.release_ids():
            for p in (packs / pid).rglob('*'):
                if p.is_file():
                    assert (dest / pid / p.relative_to(packs / pid)).read_bytes() == p.read_bytes()
        digest = R.sha256_file(out / 'SHA256SUMS')
        quiet(lambda: fetch(out, dest, 'v9.9.9', '--sums-sha256', digest, '--pack', 'stepbible'))
        expect_exit(lambda: quiet(lambda: fetch(out, dest, 'v9.9.9', '--sums-sha256', '0' * 64)), 'does not match --sums-sha256')


def test_fetch_refuses_a_tampered_tarball_and_unpacks_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        _, out = quiet(lambda: make_release(tmp))
        victim = out / R.asset_name('bsb-tables', 'v9.9.9')
        victim.write_bytes(victim.read_bytes() + b'x')
        dest = Path(tmp) / 'dest'
        expect_exit(lambda: quiet(lambda: fetch(out, dest)), 'does not match SHA256SUMS')
        assert not dest.exists() or not any(dest.iterdir()), 'nothing may be unpacked after a hash failure'


def test_fetch_refuses_unsafe_archive_paths_and_unexpected_sums_entries():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / 'release'
        out.mkdir()
        name = R.asset_name('stepbible', 'v9.9.9')
        with tarfile.open(out / name, 'w:gz') as tar:
            data = b'{}'
            ti = tarfile.TarInfo('stepbible/../../evil.json')
            ti.size = len(data)
            tar.addfile(ti, io.BytesIO(data))
        (out / 'SHA256SUMS').write_text(f"{R.sha256_file(out / name)}  {name}\n", encoding='utf-8')
        expect_exit(lambda: quiet(lambda: fetch(out, Path(tmp) / 'dest')), 'unsafe')
        assert not (Path(tmp) / 'evil.json').exists()
        # a SHA256SUMS naming anything but a pack tarball for this tag is rejected
        (out / 'SHA256SUMS').write_text('a' * 64 + '  ../etc-passwd\n', encoding='utf-8')
        expect_exit(lambda: quiet(lambda: fetch(out, Path(tmp) / 'dest')), 'malformed')
        (out / 'SHA256SUMS').write_text('a' * 64 + '  other-v9.9.9.tar.gz\n', encoding='utf-8')
        expect_exit(lambda: quiet(lambda: fetch(out, Path(tmp) / 'dest')), 'not a pack tarball')
        expect_exit(lambda: R.main(['fetch', '--tag', 'main', '--base-url', out.as_uri()]), 'release tag')


# -- the workflow --------------------------------------------------------------

def test_release_workflow_is_pinned_and_only_the_publish_job_can_write():
    text = (ROOT / '.github' / 'workflows' / 'release.yml').read_text(encoding='utf-8')
    uses = re.findall(r'^\s*-?\s*uses:\s*(\S+)', text, re.M)
    assert uses, 'no actions found'
    for u in uses:
        assert re.fullmatch(r'[\w.-]+/[\w./-]+@[0-9a-f]{40}', u), f'action not pinned to a commit SHA: {u}'
    assert re.search(r"^on:\s*\n\s+push:\s*\n\s+tags:\s*\['v\*'\]", text, re.M), 'must trigger on v* tags'
    assert 'workflow_dispatch:' in text
    assert re.search(r'^permissions:\s*\n\s+contents: read\s*$', text, re.M), 'top-level permissions must be contents: read'
    assert text.count('contents: write') == 1, 'exactly one job (publish) may have contents: write'
    publish = text[text.index('\n  publish:'):]
    assert 'contents: write' in publish and "github.event_name == 'push'" in publish.split('steps:')[0]
    build = text[:text.index('\n  publish:')]
    assert 'gh release' not in build and 'contents: write' not in build, 'the build job must not publish'


# -- the full packs, when built --------------------------------------------------

def test_staged_full_packs_are_whole_when_present():
    ran = 0
    for pid in R.release_ids():
        d = ROOT / 'dist' / 'packs' / pid
        if not (d / 'manifest.json').exists():
            continue
        m = json.loads((d / 'manifest.json').read_text(encoding='utf-8'))
        for field in ('id', 'name', 'version', 'kind', 'license', 'source', 'sizeBytes', 'files', 'schemaVersion', 'fetchHash', 'sourceRef'):
            assert field in m, f'{pid}: manifest missing {field}'
        assert m['license'].get('attribution')
        books = json.loads((ROOT / 'web' / 'data' / 'packs' / 'theographic' / 'books.json').read_text(encoding='utf-8'))
        have = {p.stem for p in (d / 'interlinear').glob('*.json')}
        assert {b['osis'] for b in books} == have, f"{pid}: books differ from the 66: {sorted({b['osis'] for b in books} ^ have)}"
        for book in ('Gen', 'Rev'):
            data = json.loads((d / 'interlinear' / f'{book}.json').read_text(encoding='utf-8'))
            for vid, ws in list(data.items())[:3]:
                assert ws and all({'src', 'strongs', 'morph'} <= set(w) for w in ws), f'{pid}:{vid}: bad word records'
        assert json.loads((d / 'strongs.json').read_text(encoding='utf-8')) and json.loads((d / 'morph_codes.json').read_text(encoding='utf-8'))
        ran += 1
    print(f'     ({ran} of {len(R.release_ids())} full packs found in dist/packs; absent ones are skipped)')


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
