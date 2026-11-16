"""Pack build list for Concordio Core.

Each entry names an adapter module in ``pipeline.adapters`` and the output path. The
build order is topological on each entry's ``REQUIRES`` list (declared on the adapter
module). ``kjv`` runs after ``theographic`` because it reads Theographic's verses.

``delivery`` says how a pack reaches a consumer: ``"git"`` (the files are committed under
``web/data/packs/``) or ``"release"`` (about 58 MB each, so built in CI and attached to each
tagged release as a tarball, never committed; see ``pipeline/release.py`` and docs/UPDATES.md).
"""
PACKS = [
    {"adapter": "theographic", "out": "web/data/packs/theographic", "default": False, "delivery": "git"},
    {"adapter": "bsb",         "out": "web/data/packs/bsb",         "default": True,  "delivery": "git"},
    {"adapter": "kjv",         "out": "web/data/packs/kjv",         "default": False, "delivery": "git"},
    {"adapter": "stepbible",   "out": "web/data/packs/stepbible",   "default": False, "delivery": "release"},
    {"adapter": "bsb_tables",  "out": "web/data/packs/bsb-tables",  "default": False, "delivery": "release"},
]
