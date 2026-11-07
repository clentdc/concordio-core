# Concordio Foundation

A minimal, offline-first Bible reader built on open Scripture packs. The reusable
core of the [Concordio](https://concordio.org) project, released separately so
other builders can start from a working kit instead of a blank page.

## What is here

- Five Bible translations, each as a self-contained data pack: Berean Standard
  Bible, King James Version, Darby, Douay-Rheims Challoner, and Vulgata
  Clementina.
- The [Theographic Bible Metadata](https://github.com/robertrouse/theographic-bible-metadata)
  pack (books, people, places, events, chronology).
- A plain vertical reader (HTML + CSS + JS). No visualizer, no 3D, no brand
  chrome — a blank canvas to build on.
- i18n layer with English and Spanish interface packs.
- A denominational preset schema with one neutral `default` preset. Forks supply
  their own.
- A service worker for offline-first PWA behavior.
- `pipeline/adapters/translations_ebible.py`, a reusable VPL fetcher.
- A font-size cycler and a pinch-to-reflow handler that converts mobile pinch
  gestures into font-size steps instead of a visual viewport zoom.

## What is **not** here

This kernel does not ship the full [Bible Explorer](https://concordio.org)
application. In particular the following belong to the Concordio application
and are not part of this kernel:

- The 3D glass-slab visualizer.
- The Concordio and Bible Explorer wordmarks and visual identity.
- Tradition-specific denominational presets (Protestant Evangelical, Catholic,
  Historical Protestant, Eastern Orthodox) with their written framings.
- Narrative pages such as `/about`, `/donate`, `/truths`.
- Deployment scripts, VPS configuration, payment integrations.

See [TRADEMARKS.md](TRADEMARKS.md) for what you may and may not do with the
Concordio and Bible Explorer marks.

## Quick start

```bash
cd web
python3 -m http.server 8000
```

Open `http://localhost:8000` and pick a book, chapter, and translation. Service
worker registers on first load; subsequent loads work offline.

## Licensing

The code in this repository is **Apache License 2.0**. See [LICENSE](LICENSE).

The data packs carry their upstream licenses, which the code license does not
override. Each pack's `manifest.json` names its license; the `web/data/packs/index.json`
catalog summarises them. In particular:

- **Berean Standard Bible**: CC-BY-SA 4.0 (verify at berean.bible).
- **King James, Darby, Douay-Rheims, Vulgata Clementina**: public domain.
- **Theographic Bible Metadata**: CC-BY-SA 4.0.

CC-BY-SA is a copyleft (share-alike) licence. If you modify a data pack and
redistribute it, your modified pack stays under the same licence. The Apache-2.0
licence on the code is unaffected; the two licences coexist by sitting in
separate directory trees. See [NOTICE.md](NOTICE.md) for the full attribution
set.

## Trademarks

"Concordio" and "Bible Explorer" are trademarks of Clent Crumley, used in
commerce at concordio.org. The Apache-2.0 licence does not grant any
trademark rights (Apache-2.0 §6). You may fork this kernel; you may not call
your fork Concordio, imply endorsement, or use the wordmarks in your
distribution. See [TRADEMARKS.md](TRADEMARKS.md).

## Contributing

Issues and pull requests welcome. Keep in mind that the kernel is deliberately
minimal: additions that would pull in brand voice, tradition-specific framings,
or heavyweight visualization belong in downstream applications, not here.
Changes to the pack format (`web/data/packs/<id>/manifest.json` shape,
`index.json` schema) are breaking and go through a schema bump.
