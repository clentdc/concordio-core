#!/usr/bin/env python3
"""Fail if a licence stated in the prose disagrees with the pack manifests.

Each pack's manifest.json (and its entry in packs/index.json) is the source of truth for
its licence. README.md, NOTICE.md and docs/*.md talk about the same packs; this check stops
them drifting apart (the Berean Standard Bible was once described as CC-BY-SA in prose
while its manifest said public domain).

It sorts every licence into a family (public-domain, cc-by, cc-by-sa, other), then looks at
each line of the prose that names a pack (by its backticked id or its exact name) and fails
if the line states a different family. Standard library only.

Run: python3 tests/test_licences.py
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PACKS = ROOT / "web" / "data" / "packs"
SAMPLES = ROOT / "web" / "data" / "samples"   # committed interlinear samples: not catalog packs, same licence rules
sys.path.insert(0, str(ROOT))
from pipeline.packs import PACKS as BUILD  # noqa: E402

# Packs delivered as release artifacts are built into web/data/packs/ on a developer's machine (git
# ignores them) and have no catalog row; every other manifest there must be listed in index.json.
RELEASE_DELIVERED = {pathlib.Path(e["out"]).name for e in BUILD if e.get("delivery") == "release"}
PROSE = [ROOT / "README.md", ROOT / "NOTICE.md", *sorted((ROOT / "docs").glob("*.md"))]


def family(text):
    t = (text or "").lower().replace("_", "-")
    if re.search(r"cc[- ]?by[- ]?sa|attribution[- ]?sharealike|share[- ]?alike", t):
        return "cc-by-sa"
    if re.search(r"cc[- ]?by\b|creative commons attribution", t):
        return "cc-by"
    if re.search(r"public[- ]domain|cc[- ]?pddc|cc0|pdm", t):
        return "public-domain"
    return "other"


def mentioned_families(line):
    """Families a line of prose states about a pack, from words in the line."""
    fams = set()
    t = line.lower()
    if re.search(r"cc[- ]?by[- ]?sa|share[- ]?alike", t):
        fams.add("cc-by-sa")
    if re.search(r"cc[- ]?by(?![- ]?sa)\b\s*[0-9.]*", t) and not re.search(r"cc[- ]?by[- ]?sa", t):
        fams.add("cc-by")
    if re.search(r"public[- ]domain", t):
        fams.add("public-domain")
    return fams


def main():
    problems = []
    packs = {}
    for mf in sorted([*PACKS.glob("*/manifest.json"), *SAMPLES.glob("*/manifest.json")]):
        m = json.loads(mf.read_text(encoding="utf-8"))
        lic = m.get("license")
        if not lic:
            problems.append(f"{mf.relative_to(ROOT)}: no license")
            continue
        name = lic.get("name") if isinstance(lic, dict) else str(lic)
        spdx = lic.get("spdx", "") if isinstance(lic, dict) else ""
        packs[m.get("id") or mf.parent.name] = (m.get("name", ""), family(f"{name} {spdx}"), name)
        if isinstance(lic, dict) and not (lic.get("attribution") or lic.get("url")):
            problems.append(f"{mf.relative_to(ROOT)}: license has neither attribution nor url")

    index = json.loads((PACKS / "index.json").read_text(encoding="utf-8"))
    for entry in index["packs"]:
        pid = entry["id"]
        if pid not in packs:
            problems.append(f"index.json lists '{pid}' but web/data/packs/{pid}/manifest.json is missing")
        elif family(entry.get("license", "")) != packs[pid][1]:
            problems.append(f"index.json: '{pid}' license '{entry.get('license')}' differs from its manifest ({packs[pid][2]})")
    for pid in packs:
        if (SAMPLES / pid / "manifest.json").exists() or pid in RELEASE_DELIVERED:
            continue
        if pid not in {e["id"] for e in index["packs"]}:
            problems.append(f"web/data/packs/{pid} has a manifest but is not in index.json")

    for doc in PROSE:
        for n, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
            # In a table row, only the first cell says which pack the row is about; later cells
            # may mention other packs' names (a source, a caveat) without making a claim about them.
            subject = line.split("|")[1] if line.lstrip().startswith("|") and line.count("|") > 2 else line
            for pid, (name, fam, lic) in packs.items():
                if f"`{pid}`" in subject or (name and len(name) > 6 and name in subject):
                    stated = mentioned_families(line)
                    # A line may legitimately name several licences (e.g. a list of packs
                    # under a heading); only flag a line that states exactly the wrong thing.
                    if stated and fam not in stated and len(stated) == 1:
                        problems.append(
                            f"{doc.relative_to(ROOT)}:{n}: says {sorted(stated)[0]} for '{pid}', but its manifest says {lic}")

    if problems:
        print("licence statements disagree:")
        print("\n".join("  " + p for p in problems))
        return 1
    print(f"licence statements agree with {len(packs)} pack manifests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
