"""Cut the small interlinear samples that are committed to git.

The two full interlinear packs (``stepbible``, ``bsb-tables``) are about 58 MB each and are
delivered as release artifacts, not stored in git (see ``pipeline/release.py``). So that a fresh
clone still has real interlinear data to read, test against and build on, this script slices one
or two short books out of a full pack into ``web/data/samples/<id>/``.

A sample is **cut, never edited**: each book file is copied byte for byte from the full pack,
``strongs.json`` and ``morph_codes.json`` keep only the entries the sampled words use (same values,
same order), and the manifest is the parent's with the id, name, version, counts, size and a
``sample`` block changed. Nothing is invented, so a sample's words are exactly the full pack's.
``tests/test_interlinear_samples.py`` regenerates each sample from the full pack when it is
present and fails on any difference.

Usage (after ``make release-packs``)::

    python3 -I pipeline/samples.py --packs dist/packs

Which books, and why:

* ``stepbible-sample``: 3 John only. 3 John is the shortest NT book (14 verses). A Greek-only slice
  also carries none of STEPBible's Hebrew lexicon (TBESH), whose definitions carry an open
  permission caveat (docs/LICENSES.md), so the sample is clean under CC BY 4.0 alone.
* ``bsb-tables-sample``: 3 John and Obadiah (21 verses). The BSB tables are public domain, so a
  Hebrew book can be included: it exercises right-to-left text, Hebrew that is deliberately not
  Unicode-normalised, and the Hebrew Strong's form. Its 3 John can be compared with
  ``stepbible-sample``'s (the two schemes differ in gloss, morphology and Strong's format).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.adapters import size_bytes, write_json  # noqa: E402

SAMPLES_DIR = ROOT / "web" / "data" / "samples"

SAMPLES = [
    {"id": "stepbible-sample", "of": "stepbible", "books": ["3John"]},
    {"id": "bsb-tables-sample", "of": "bsb-tables", "books": ["3John", "Obad"]},
]


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_sample(parent_dir, spec, out_dir):
    """Write the sample described by ``spec`` from the full pack at ``parent_dir`` into ``out_dir``."""
    parent_dir, out_dir = Path(parent_dir), Path(out_dir)
    parent = _load(parent_dir / "manifest.json")
    if parent["id"] != spec["of"]:
        raise SystemExit(f"{parent_dir} is pack {parent['id']!r}, expected {spec['of']!r}")
    books = spec["books"]

    (out_dir / "interlinear").mkdir(parents=True, exist_ok=True)
    words = []
    verses = 0
    for book in books:
        src = parent_dir / "interlinear" / f"{book}.json"
        shutil.copyfile(src, out_dir / "interlinear" / f"{book}.json")  # verbatim
        data = _load(src)
        verses += len(data)
        for ws in data.values():
            words.extend(ws)

    used_strongs = {w["strongs"] for w in words if w.get("strongs")}
    used_morph = {w["morph"] for w in words if w.get("morph")}
    strongs = {k: v for k, v in _load(parent_dir / "strongs.json").items() if k in used_strongs}
    morph = {k: v for k, v in _load(parent_dir / "morph_codes.json").items() if k in used_morph}
    write_json(str(out_dir / "strongs.json"), strongs)
    write_json(str(out_dir / "morph_codes.json"), morph)

    m = json.loads(json.dumps(parent))  # deep copy
    m["id"] = spec["id"]
    m["name"] = f"{parent['name']}: sample ({', '.join(books)})"
    m["version"] = f"{parent['version']}-sample"
    m["counts"] = {"books": len(books), "verses": verses, "words": len(words),
                   "strongs": len(strongs), "morphCodes": len(morph)}
    m["sample"] = {
        "of": parent["id"],
        "ofVersion": parent["version"],
        "books": books,
        "note": ("A cut of the full pack, committed to git so a fresh clone has interlinear data. "
                 "Book files are byte-identical to the full pack's; strongs.json and morph_codes.json "
                 "keep only the entries these books use. The full pack ships as a release artifact "
                 "(docs/UPDATES.md)."),
    }
    m["source"]["modifications"] = (m["source"]["modifications"] + " Sample: restricted to "
                                    + ", ".join(books) + "; lexicon and morph-code files cut to the entries those books use.")
    # The Hebrew-definitions caveat belongs to the lexicon entries; a sample with none of them has no caveat.
    if "caveats" in m and not any(k.startswith("H") for k in strongs):
        m["caveats"] = []
    m["sizeBytes"] = size_bytes(str(out_dir))
    write_json(str(out_dir / "manifest.json"), m, pretty=True)
    return m


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--packs", default="dist/packs", help="directory holding the built full packs (default dist/packs)")
    ap.add_argument("--out", default=str(SAMPLES_DIR), help="where to write the samples (default web/data/samples)")
    args = ap.parse_args(argv)
    for spec in SAMPLES:
        parent_dir = Path(args.packs) / spec["of"]
        if not (parent_dir / "manifest.json").exists():
            raise SystemExit(f"{parent_dir}/manifest.json not found. Run `make release-packs` first.")
        out_dir = Path(args.out) / spec["id"]
        m = build_sample(parent_dir, spec, out_dir)
        print(f"-> {spec['id']}: {m['counts']['verses']} verses, {m['counts']['words']} words, "
              f"{m['sizeBytes']} bytes in {os.path.relpath(out_dir)}")


if __name__ == "__main__":
    main()
