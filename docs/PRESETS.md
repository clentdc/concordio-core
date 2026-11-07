# Denominational preset schema

A preset bundles the choices a tradition would make about which books to show,
which translation to default to, how to number Psalms, and which labels to use
for certain entities. The kernel ships one neutral `default` preset. Richer
tradition-specific presets (Protestant Evangelical, Catholic, Eastern
Orthodox, Historical Protestant, etc.) are the responsibility of the
downstream application that offers them; they are not part of the kernel.

## Catalog — `web/data/packs/denominations/catalog.json`

```json
{
  "schemaVersion": 1,
  "presets": [
    { "id": "default", "name": "Default", "shortName": "Default",
      "summary": "A neutral 66-book preset.",
      "defaultTranslation": "bsb" }
  ]
}
```

## Preset — `web/data/packs/denominations/<id>.json`

```json
{
  "schemaVersion": 1,
  "id": "default",
  "name": "Default",
  "shortName": "Default",
  "summary": "A neutral 66-book preset with no tradition-specific framings.",
  "defaultTranslation": "bsb",
  "defaultTranslationAlternates": ["kjv", "darby"],
  "canon": {
    "deuterocanonBooks": [],
    "apocryphaBooks": []
  },
  "psalmNumbering": "hebrew",
  "bookOrder": "protestant-66",
  "entityLabels": {},
  "sources": [],
  "notes": ""
}
```

Field notes:

- `defaultTranslation` — pack id of the translation to select when this preset
  is active.
- `canon.deuterocanonBooks` / `canon.apocryphaBooks` — OSIS book ids that this
  preset considers part of its canon in addition to the 66-book baseline.
  The kernel's packs do not include these books; forks supply the packs.
- `psalmNumbering` — "hebrew" (1 to 150, Masoretic) or "septuagint" (LXX
  numbering, as in the Orthodox tradition). The kernel ships Hebrew-numbered
  Psalms; forks that want Septuagint numbering ship a versify mapping.
- `bookOrder` — short identifier for the book order, e.g. `protestant-66`,
  `catholic-73`, `orthodox-76`. The downstream application interprets this.
- `entityLabels` — overrides for entity display names, as a map of OSIS entity
  id to display label. Applied by the downstream application in the entity
  dossier.

## Forking

Copy `default.json` to a new file and edit. Add an entry to `catalog.json`.
Nothing in the kernel enforces a specific tradition, canon, or framing; a
fork's choices are its own.
