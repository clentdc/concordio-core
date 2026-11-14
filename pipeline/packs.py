"""Pack build list for Concordio Core.

Each entry names an adapter module in ``pipeline.adapters`` and the output path. The
build order is topological on each entry's ``REQUIRES`` list (declared on the adapter
module). ``kjv`` runs after ``theographic`` because it reads Theographic's verses.
"""
PACKS = [
    {"adapter": "theographic", "out": "web/data/packs/theographic", "default": False},
    {"adapter": "bsb",         "out": "web/data/packs/bsb",         "default": True},
    {"adapter": "kjv",         "out": "web/data/packs/kjv",         "default": False},
    {"adapter": "stepbible",   "out": "web/data/packs/stepbible",   "default": False},
    {"adapter": "bsb_tables",  "out": "web/data/packs/bsb-tables",  "default": False},
]
