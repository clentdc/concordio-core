"""Pipeline adapters.

Each adapter is a module in this package that exposes:

* ``ID``: pack id, e.g. ``"bsb"``.
* ``KIND``: pack kind, one of ``"translation" | "interlinear" | "entities" | "lexicon"
  | "morph-key" | "geo" | "xrefs"``.
* ``REQUIRES`` (optional): list of pack ids this one depends on at build time.
* ``build(cache_dir, out_dir)``: read the upstream from ``cache_dir``, write pack
  files to ``out_dir``, return a dict for ``manifest.json``.

``build.py`` is the orchestrator; it calls ``build()`` for each entry in
``pipeline/packs.py`` and writes the manifest.

The ``write_json`` helper below writes compact UTF-8 JSON with sorted keys for stable
diffs. The ``size_bytes`` helper sums the on-disk size of the pack's output files.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any


def write_json(path: str, data: Any, *, pretty: bool = False) -> None:
    """Write ``data`` as JSON to ``path``, UTF-8, no trailing newline. Compact by default."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        else:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"), sort_keys=False)


def size_bytes(out_dir: str) -> int:
    total = 0
    for root, _, files in os.walk(out_dir):
        for name in files:
            if name == "manifest.json":
                continue
            total += os.path.getsize(os.path.join(root, name))
    return total


def sha256_file(path: str | os.PathLike) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_tree(root: str | os.PathLike, *, globs: list[str] | None = None) -> str:
    """Return a stable hash over every file (or every file matching ``globs``) under ``root``.

    Deterministic for a given set of inputs: files are sorted by their path relative to
    ``root``; each file contributes its relative path plus its sha256 to a running hash.
    Used so an adapter can record the exact bytes it read from ``.cache/``, independent
    of whether the upstream is a git clone, a downloaded file, or a tarball.
    """
    root = Path(root)
    paths: list[Path] = []
    if globs:
        for pat in globs:
            paths.extend(root.glob(pat))
    else:
        for base, _, names in os.walk(root):
            for n in names:
                paths.append(Path(base) / n)
    paths = sorted(set(paths))
    h = hashlib.sha256()
    for p in paths:
        rel = p.relative_to(root).as_posix().encode("utf-8")
        h.update(len(rel).to_bytes(2, "big") + rel)
        h.update(sha256_file(p).encode("ascii"))
    return h.hexdigest()


def git_rev(repo_path: str | os.PathLike, *, short: int = 7) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo_path), "rev-parse", f"--short={short}", "HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "unknown"


def make_manifest(*, id: str, name: str, version: str, kind: str,
                  license: dict, source: dict, out_dir: str,
                  requires: list[str] | None = None,
                  files: dict[str, str] | None = None,
                  extra: dict | None = None,
                  fetch_hash: str | None = None,
                  source_ref: str | None = None) -> dict:
    """Build a pack manifest dict.

    ``fetch_hash`` and ``source_ref`` are optional but strongly encouraged: they let the
    weekly upstream-check job compare what we built against what's live, and let future
    rebuilds confirm they reproduce the same bytes from the same source. See
    ``docs/UPDATES.md`` for how these fields are consumed. We deliberately do NOT stamp
    a wall-clock build time into the manifest — determinism is more valuable than
    reporting when the file was last touched; two rebuilds from the same source produce
    byte-identical manifests, which is a precondition for CI drift detection.
    """
    m = {
        "id": id,
        "name": name,
        "version": version,
        "kind": kind,
        "license": license,
        "source": source,
        "requires": requires or [],
        "sizeBytes": size_bytes(out_dir),
        "files": files or {},
        "schemaVersion": 1,
    }
    if fetch_hash:
        m["fetchHash"] = fetch_hash
    if source_ref:
        m["sourceRef"] = source_ref
    if extra:
        m.update(extra)
    return m
