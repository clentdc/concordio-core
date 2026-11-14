#!/usr/bin/env python3
"""Fail if anything proprietary, secret, or too large has been put into concordio-core.

concordio-core is public and Apache-2.0. The 3D visualizer, tradition presets, brand
material, image art, deploy scripts and secrets belong to downstream (private) projects.
This is the guard that keeps that line: it checks every file in the working tree against
tests/reserved-material.json. Standard library only.

Run: python3 tests/test_reserved_material.py
"""
import fnmatch
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "tests" / "reserved-material.json").read_text(encoding="utf-8"))
SKIP_DIRS = {".git", "__pycache__", "node_modules"}
THIS_FILES = {"tests/reserved-material.json", "tests/test_reserved_material.py"}


def files():
    """Every file git knows about (tracked, or untracked and not ignored).

    Ignored files (.cache/, build output, virtualenvs) are never published, so they are not
    scanned: a weekly refresh fetches sources into .cache/ without tripping this guard.
    Outside a git checkout, fall back to walking the tree.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            check=True, capture_output=True).stdout.decode("utf-8")
        rels = sorted(pathlib.Path(p) for p in out.split("\0") if p)
    except (OSError, subprocess.CalledProcessError):
        rels = sorted(p.relative_to(ROOT) for p in ROOT.rglob("*"))
    for rel in rels:
        path = ROOT / rel
        if any(part in SKIP_DIRS for part in rel.parts) or not path.is_file():
            continue
        yield path, rel


def main():
    problems = []
    forbidden_names = CFG["forbidden_names"]
    text_rx = [(p, re.compile(p)) for p in CFG["forbidden_text"]]
    suffixes = set(CFG["text_suffixes"])
    for path, rel in files():
        relposix = rel.as_posix()
        for part in rel.parts:
            for pat in forbidden_names:
                if fnmatch.fnmatch(part, pat):
                    problems.append(f"{relposix}: reserved name '{part}' (matches '{pat}')")
        if path.stat().st_size > CFG["max_file_bytes"]:
            problems.append(f"{relposix}: larger than {CFG['max_file_bytes']} bytes (GitHub rejects 100 MB; ship big data as a release artifact)")
        if relposix in THIS_FILES or path.suffix not in suffixes:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern, rx in text_rx:
            m = rx.search(text)
            if m:
                line = text.count("\n", 0, m.start()) + 1
                problems.append(f"{relposix}:{line}: reserved text /{pattern}/: {m.group(0)[:60]}")

    # Presets: the kernel ships only the neutral ones listed in the config.
    catalog = ROOT / "web" / "data" / "packs" / "denominations" / "catalog.json"
    if catalog.exists():
        allowed = set(CFG["allowed_presets"])
        ids = {p["id"] for p in json.loads(catalog.read_text(encoding="utf-8"))["presets"]}
        for extra in sorted(ids - allowed):
            problems.append(f"denominations/catalog.json: preset '{extra}' is not allowed in core (allowed: {sorted(allowed)})")
        for f in catalog.parent.glob("*.json"):
            if f.name != "catalog.json" and f.stem not in allowed:
                problems.append(f"denominations/{f.name}: preset file not allowed in core")

    if problems:
        print("reserved material found in concordio-core:")
        print("\n".join("  " + p for p in problems))
        return 1
    print("no reserved material in concordio-core")
    return 0


if __name__ == "__main__":
    sys.exit(main())
