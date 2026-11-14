"""Build every pack listed in ``pipeline/packs.py`` and emit ``web/data/packs/index.json``.

Usage: ``python3 -I pipeline/build.py [cache_dir]``

``cache_dir`` defaults to ``.cache/``. Each adapter reads its upstream from a known
subdirectory (``.cache/bsb/bsb.txt``, ``.cache/theographic-bible-metadata/json/``, …)
and writes under its pack's ``out`` directory.

Build order is topological on each adapter module's optional ``REQUIRES`` list.
Everything is deterministic for a given upstream revision: ``make check`` can hash the
output for CI.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path

# Allow `python3 pipeline/build.py` from the repo root without a packaging install.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.adapters import write_json  # noqa: E402
from pipeline.packs import PACKS  # noqa: E402


def _topo(entries):
    """Return the entries re-ordered so each adapter's REQUIRES run first."""
    by_id = {}
    for e in entries:
        mod = importlib.import_module(f"pipeline.adapters.{e['adapter']}")
        by_id[mod.ID] = (e, mod)
    order = []
    seen = set()

    def visit(pack_id):
        if pack_id in seen:
            return
        if pack_id not in by_id:
            raise RuntimeError(f"Pack {pack_id!r} is required but not in packs.py.")
        for dep in getattr(by_id[pack_id][1], "REQUIRES", []):
            visit(dep)
        seen.add(pack_id)
        order.append(by_id[pack_id])

    for e in entries:
        mod = importlib.import_module(f"pipeline.adapters.{e['adapter']}")
        visit(mod.ID)
    return order


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("cache", nargs="?", default=".cache",
                   help="Path to the sources cache directory (default: .cache)")
    p.add_argument("--out", default="web/data/packs",
                   help="Pack catalog root (default: web/data/packs)")
    p.add_argument("--only", metavar="PACK_ID",
                   help="Rebuild just this pack and patch its row in index.json (other rows are kept)")
    args = p.parse_args(argv)

    cache = str(Path(args.cache).resolve())
    catalog = []

    for entry, mod in _topo(PACKS):
        if args.only and mod.ID != args.only:
            continue
        out_dir = str(ROOT / entry["out"])
        os.makedirs(out_dir, exist_ok=True)
        print(f"-> building {mod.ID} ({mod.KIND}) in {entry['out']} …", flush=True)
        manifest = mod.build(cache, out_dir)
        # Each adapter returns a manifest dict ready to write.
        write_json(os.path.join(out_dir, "manifest.json"), manifest, pretty=True)
        print(f"   wrote {manifest['sizeBytes']} bytes in "
              f"{len(manifest.get('files', {}))} files", flush=True)
        catalog.append({
            "id": manifest["id"],
            "version": manifest["version"],
            "kind": manifest["kind"],
            "default": entry.get("default", False),
            "sizeBytes": manifest["sizeBytes"],
        })

    index_path = ROOT / args.out / "index.json"
    if args.only:
        # index.json also lists packs this script does not build (chrome, translations, roadmap
        # stubs) and is hand-formatted, so a partial rebuild patches one row's version and size
        # in place instead of rewriting the catalog.
        import re
        text = index_path.read_text(encoding="utf-8")
        for row in catalog:
            m = re.search(r'\{[^{}]*"id": "%s"[^{}]*\}' % re.escape(row["id"]), text)
            if not m:
                raise SystemExit(f"{row['id']} has no row in {args.out}/index.json; add one by hand first")
            block = re.sub(r'("version": )"[^"]*"', lambda x: f'{x.group(1)}"{row["version"]}"', m.group(0))
            block = re.sub(r'("sizeBytes": )\d+', lambda x: f'{x.group(1)}{row["sizeBytes"]}', block)
            text = text[:m.start()] + block + text[m.end():]
        index_path.write_text(text, encoding="utf-8")
        print(f"\nPatched {args.only} in {args.out}/index.json")
        return
    write_json(str(index_path), {"packs": catalog, "schemaVersion": 1}, pretty=True)
    print(f"\nWrote catalog with {len(catalog)} packs at {args.out}/index.json")
    for row in catalog:
        default = " (default)" if row.get("default") else ""
        print(f"  {row['kind']:<12} {row['id']:<16} {row['version']:<16} "
              f"{row['sizeBytes']:>10} bytes{default}")


if __name__ == "__main__":
    main()
