"""Package and fetch the release artifacts: the two large interlinear packs.

``stepbible`` and ``bsb-tables`` are about 58 MB each, so core does not store them in git. Every
tagged release (``v*``) attaches, built by ``.github/workflows/release.yml``:

* ``concordio-pack-<id>-<tag>.tar.gz`` for each pack with ``delivery: "release"`` in
  ``pipeline/packs.py``, holding ``<id>/manifest.json``, ``<id>/interlinear/*.json`` and so on, so
  it unpacks straight into ``web/data/packs/``;
* ``SHA256SUMS``, one ``<sha256>  <file>`` line per tarball, checked with ``sha256sum -c``;
* the release notes carry each pack's version, upstream revision and licence.

Two subcommands, standard library only::

    python3 -I pipeline/release.py pack  --version v0.1.0 --packs dist/packs --out dist/release
    python3 -I pipeline/release.py fetch --tag v0.1.0

``pack`` is deterministic: entries are sorted, mtimes, owners and modes are fixed, and gzip carries no
timestamp or name, so the same built packs give the same tarball bytes (on the same zlib).

``fetch`` downloads ``SHA256SUMS`` and the tarballs for a tag, verifies every hash before unpacking
anything, refuses unsafe archive paths, and replaces ``<dest>/<id>/``. ``SHA256SUMS`` comes from the
same release as the tarballs, so it catches corruption and a swapped asset but not a compromised
release: to pin against that, record the hash of ``SHA256SUMS`` (or of each tarball) in your own
repository and pass ``--sums-sha256`` (see docs/UPDATES.md).
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.packs import PACKS  # noqa: E402

REPO = "clentdc/concordio-core"
ASSET_RE = re.compile(r"^concordio-pack-([a-z0-9][a-z0-9-]*)-(v[0-9][0-9A-Za-z.+-]*)\.tar\.gz$")
TAG_RE = re.compile(r"^v[0-9][0-9A-Za-z.+-]*$")
SUMS = "SHA256SUMS"


def release_ids():
    """Pack ids delivered as release artifacts, in build order."""
    return [Path(e["out"]).name for e in PACKS if e.get("delivery") == "release"]


def asset_name(pack_id, version):
    return f"concordio-pack-{pack_id}-{version}.tar.gz"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- pack

def _tar_info(name, *, size=0, is_dir=False):
    ti = tarfile.TarInfo(name)
    ti.mtime = 0
    ti.uid = ti.gid = 0
    ti.uname = ti.gname = ""
    ti.mode = 0o755 if is_dir else 0o644
    ti.type = tarfile.DIRTYPE if is_dir else tarfile.REGTYPE
    ti.size = 0 if is_dir else size
    return ti


def make_tarball(pack_dir, pack_id, dest):
    """Write a reproducible ``dest`` (.tar.gz) holding ``pack_dir`` as ``<pack_id>/...``."""
    pack_dir = Path(pack_dir)
    entries = sorted(p for p in pack_dir.rglob("*"))
    with open(dest, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.GNU_FORMAT) as tar:
                tar.addfile(_tar_info(pack_id, is_dir=True))
                for p in entries:
                    rel = f"{pack_id}/{p.relative_to(pack_dir).as_posix()}"
                    if p.is_dir():
                        tar.addfile(_tar_info(rel, is_dir=True))
                    elif p.is_file():
                        with open(p, "rb") as f:
                            tar.addfile(_tar_info(rel, size=p.stat().st_size), f)
                    else:
                        raise SystemExit(f"{p}: not a regular file or directory")


def check_staged(pack_dir, pack_id):
    """A staged pack must be a clean build: manifest id matches and sizeBytes equals what is on disk."""
    mf = Path(pack_dir) / "manifest.json"
    if not mf.exists():
        raise SystemExit(f"{mf} not found. Run `make release-packs` first.")
    m = json.loads(mf.read_text(encoding="utf-8"))
    if m.get("id") != pack_id:
        raise SystemExit(f"{mf}: id is {m.get('id')!r}, expected {pack_id!r}")
    on_disk = sum(p.stat().st_size for p in Path(pack_dir).rglob("*") if p.is_file() and p.name != "manifest.json")
    if on_disk != m["sizeBytes"]:
        raise SystemExit(f"{pack_dir}: {on_disk} bytes on disk but the manifest says {m['sizeBytes']}; "
                         "the staging directory holds leftovers from another build. Use a fresh dist/.")
    return m


def release_notes(version, rows):
    lines = [
        f"# Concordio Core {version}",
        "",
        "The two large interlinear packs, built by `.github/workflows/release.yml` from the pinned upstream sources",
        "and attached as tarballs. The small packs, the pipeline and the reader are in the source tree at this tag.",
        "A short sample of each interlinear pack is committed under `web/data/samples/`.",
        "",
        "## Assets",
        "",
        "| File | Pack | Version | Source revision | Licence | Size | SHA-256 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        lines.append(f"| `{r['file']}` | `{r['id']}` | {r['version']} | `{r['sourceRef']}` | {r['licence']} | {r['bytes']:,} B | `{r['sha256']}` |")
    lines += [
        "",
        "`SHA256SUMS` lists the same hashes. Fetch and verify with `make fetch-release TAG=" + version + "`, or by hand:",
        "",
        "```bash",
        f"curl -fsSLO https://github.com/{REPO}/releases/download/{version}/{SUMS}",
        "sha256sum -c SHA256SUMS --ignore-missing   # after downloading the tarballs you want",
        "tar -xzf concordio-pack-stepbible-" + version + ".tar.gz -C web/data/packs",
        "```",
        "",
        "## Licences",
        "",
    ]
    for r in rows:
        lines.append(f"- `{r['id']}`: {r['licence']}. {r['attribution']}")
    lines += ["", "Full terms: `docs/LICENSES.md` and `NOTICE.md` at this tag. See `CHANGELOG.md` for what changed.", ""]
    return "\n".join(lines)


def cmd_pack(args):
    if not TAG_RE.match(args.version):
        raise SystemExit(f"--version {args.version!r} must look like v0.1.0")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for pack_id in release_ids():
        pack_dir = Path(args.packs) / pack_id
        m = check_staged(pack_dir, pack_id)
        name = asset_name(pack_id, args.version)
        dest = out / name
        make_tarball(pack_dir, pack_id, dest)
        lic = m["license"]
        rows.append({"file": name, "id": pack_id, "version": m["version"], "sourceRef": m.get("sourceRef", ""),
                     "licence": lic.get("name", ""), "attribution": lic.get("attribution", ""),
                     "bytes": dest.stat().st_size, "sha256": sha256_file(dest)})
        print(f"-> {name}: {rows[-1]['bytes']:,} bytes, sha256 {rows[-1]['sha256']}")
    (out / SUMS).write_text("".join(f"{r['sha256']}  {r['file']}\n" for r in rows), encoding="utf-8")
    (out / "RELEASE-NOTES.md").write_text(release_notes(args.version, rows), encoding="utf-8")
    print(f"-> {SUMS} and RELEASE-NOTES.md in {out}")


# ---------------------------------------------------------------- fetch

def parse_sums(text):
    """Return {file: sha256} from SHA256SUMS text, rejecting anything that is not ``<64 hex>  <name>``."""
    sums = {}
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        m = re.match(r"^([0-9a-f]{64})  ([^/\\\s]+)$", line)
        if not m:
            raise SystemExit(f"{SUMS} line {n} is malformed: {line!r}")
        sums[m.group(2)] = m.group(1)
    if not sums:
        raise SystemExit(f"{SUMS} lists no files")
    return sums


def _download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "concordio-core-fetch-release"})
    try:
        with urllib.request.urlopen(req) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f, 1 << 20)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{url}: HTTP {e.code}. Is the tag right, and is the release published?")


def safe_extract(tar_path, pack_id, into):
    """Extract a pack tarball into ``into``, allowing only ``<pack_id>/...`` regular files and directories."""
    with tarfile.open(tar_path, "r:gz") as tar:
        members = tar.getmembers()
        for m in members:
            parts = Path(m.name).parts
            if (not parts or parts[0] != pack_id or m.name.startswith("/") or ".." in parts
                    or not (m.isfile() or m.isdir())):
                raise SystemExit(f"{tar_path.name}: refusing unsafe or unexpected entry {m.name!r}")
        for m in members:
            target = Path(into) / m.name
            if m.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(m) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst, 1 << 20)


def cmd_fetch(args):
    if not TAG_RE.match(args.tag):
        raise SystemExit("Give the release tag, for example: make fetch-release TAG=v0.1.0")
    base = args.base_url or f"https://github.com/{args.repo}/releases/download/{args.tag}"
    dest = Path(args.dest)
    with tempfile.TemporaryDirectory(prefix="concordio-fetch-") as tmp:
        tmp = Path(tmp)
        _download(f"{base}/{SUMS}", tmp / SUMS)
        got = sha256_file(tmp / SUMS)
        if args.sums_sha256 and got != args.sums_sha256.lower():
            raise SystemExit(f"{SUMS} hash {got} does not match --sums-sha256 {args.sums_sha256}")
        print(f"{SUMS} sha256 {got}")
        sums = parse_sums((tmp / SUMS).read_text(encoding="utf-8"))
        wanted = {}
        for name, digest in sums.items():
            m = ASSET_RE.match(name)
            if not m or m.group(2) != args.tag:
                raise SystemExit(f"{SUMS} lists {name!r}, which is not a pack tarball for {args.tag}")
            wanted[name] = (m.group(1), digest)
        if args.pack:
            wanted = {n: v for n, v in wanted.items() if v[0] in args.pack}
            missing = set(args.pack) - {v[0] for v in wanted.values()}
            if missing:
                raise SystemExit(f"{args.tag} has no pack(s) {sorted(missing)}")
        for name, (pack_id, digest) in sorted(wanted.items()):
            print(f"downloading {name} ...")
            _download(f"{base}/{name}", tmp / name)
            actual = sha256_file(tmp / name)
            if actual != digest:
                raise SystemExit(f"{name}: sha256 {actual} does not match {SUMS} ({digest}). Nothing was unpacked.")
            print(f"  verified {digest}")
        # Everything verified: unpack to a staging folder, then replace each pack directory.
        stage = tmp / "unpacked"
        for name, (pack_id, _) in sorted(wanted.items()):
            safe_extract(tmp / name, pack_id, stage)
            if not (stage / pack_id / "manifest.json").exists():
                raise SystemExit(f"{name}: no {pack_id}/manifest.json inside")
        dest.mkdir(parents=True, exist_ok=True)
        for name, (pack_id, _) in sorted(wanted.items()):
            target = dest / pack_id
            if target.exists():
                shutil.rmtree(target)
            shutil.move(str(stage / pack_id), str(target))
            version = json.loads((target / "manifest.json").read_text(encoding="utf-8"))["version"]
            print(f"unpacked {pack_id} (version {version}) into {target}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pack", help="make the tarballs, SHA256SUMS and release notes")
    p.add_argument("--version", required=True, help="release tag, e.g. v0.1.0")
    p.add_argument("--packs", default="dist/packs", help="directory of built packs (default dist/packs)")
    p.add_argument("--out", default="dist/release", help="output directory (default dist/release)")
    p.set_defaults(fn=cmd_pack)
    f = sub.add_parser("fetch", help="download a release, verify SHA256SUMS, unpack the packs")
    f.add_argument("--tag", required=True, help="release tag, e.g. v0.1.0")
    f.add_argument("--dest", default=str(ROOT / "web" / "data" / "packs"), help="where to unpack (default web/data/packs)")
    f.add_argument("--pack", action="append", help="fetch only this pack id (repeatable)")
    f.add_argument("--sums-sha256", help="expected SHA-256 of the release's SHA256SUMS file, recorded out of band")
    f.add_argument("--repo", default=REPO, help=f"GitHub repository (default {REPO})")
    f.add_argument("--base-url", help="override the download base URL (for mirrors and tests); a file:// URL works")
    f.set_defaults(fn=cmd_fetch)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
