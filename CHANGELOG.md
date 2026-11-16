# Changelog

All notable changes to Concordio Core. This project follows
[semantic versioning](https://semver.org/): a change to a pack's `schemaVersion` or to a
slug is a major version; new packs and data refreshes are minor or patch. Each tagged release
also carries the two large interlinear packs as tarballs with a `SHA256SUMS` file
([docs/UPDATES.md](docs/UPDATES.md#interlinear-packs-release-artifacts)).

## Unreleased

## 0.1.0 (2026-11-15)

First tagged release.

### Changed

- **Theographic refresh** (weekly job, PR #1): upstream `744355c` to `3d8aa2e`. Events 450 to 490,
  places 1,298 to 1,296, people unchanged. The slug lock gained 50 event slugs and no existing slug
  changed. `theographic` is now `3d8aa2e-full-s1` and `kjv` `theographic-3d8aa2e`, so cached clients
  refetch. The `bsb` pack did not change.
- **Service worker cache** bumped to `v3` (was `v2`) for the reader changes and the samples below.
- **Credit line.** The `chrome-en` and `chrome-es` manifests now credit "Concordio project, 2026"
  (was "Bible Explorer project"), matching `versify.json` and `canon-extensions.json`. Both
  packs move to 1.0.1 so cached clients refresh; the service-worker cache is bumped to v2.

### Added

- **Interlinear packs as release artifacts.** `stepbible` and `bsb-tables` (about 58 MB each) are not
  stored in git. Every tagged release attaches `concordio-pack-<id>-<tag>.tar.gz` for each, plus a
  `SHA256SUMS` file, built by `.github/workflows/release.yml` (a `v*` tag publishes; a manual run is
  a dry run that publishes nothing; only the publish job has write access). `make fetch-release
  TAG=v0.1.0` downloads a release, verifies every hash before unpacking, and refuses unsafe archive
  paths. Tarballs are reproducible. See `docs/UPDATES.md`.
- **Interlinear samples in git** (`web/data/samples/`): `stepbible-sample` (3 John, CC BY 4.0) and
  `bsb-tables-sample` (3 John and Obadiah, public domain), cut from the full packs by
  `pipeline/samples.py`: book files byte-identical, lexicon and morph files cut to the entries used.
  Not catalog packs. `tests/test_interlinear_samples.py` and `tests/test_release.py` (both in
  `make check` and CI) guard them and the release path.
- **Pipeline:** `build.py --stage DIR` (build into a staging directory, leave `index.json` alone),
  a `delivery` field on each entry in `pipeline/packs.py` (`git` or `release`), `make release-packs`,
  `release-assets`, `samples` and `fetch-release`.
- **Pinned sources.** STEPBible-Data is fetched at a fixed commit (`be4191f`, the revision the
  `stepbible` pack was first built from); before, it tracked the default branch. With
  `CONCORDIO_STRICT_PINS` set (the release build), a `bsb-tables` source whose SHA-256 differs from
  the reviewed pin stops the build instead of warning.
- **Pipeline.** The build for every pack (`pipeline/`): adapters for Theographic, the
  BSB, the KJV, eBible.org translations, STEPBible interlinear and the BSB Translation
  Tables. Rebuilds are byte-identical for a given upstream revision.
- **Slug lock** (`pipeline/slug-lock.json`): a locked, unique URL slug for every
  Theographic person, place and event, CC BY-SA 4.0.
- **Packs:** Theographic refreshed; Douay-Rheims and Vulgata Clementina with the
  deuterocanon; `versify.json` (Psalm numbering map); `canon-extensions.json`.
- **Weekly upstream refresh** (`.github/workflows/check-upstream.yml`): rebuilds
  Theographic, BSB and KJV, runs the checks, and opens a pull request for review.
- **Tests and CI:** data integrity, a reserved-material guard (keeps application-only
  material out of this public repository), licence consistency, and the cookbook recipes.
- **Docs:** data, pack schema, updates, licences, a query cookbook with 14 runnable
  recipes, a guide for AI agents, the Theographic source audit, and `llms.txt`.

- **Reader: Psalm numbering.** The reader now uses `versify.json`. For the Douay-Rheims
  and Vulgata Clementina, Psalm 23 shows that translation's Psalm 22 with a neutral note;
  Psalms 114/115, 116 and 147 show the matching whole chapters (`web/js/versify.js`,
  `tests/test_versify.js`).

- **Reader: canon selector.** A "Canon" select offers "66 books" or "73 books" when the
  active translation contains the seven books in `canon-extensions.json` (Douay-Rheims,
  Vulgata Clementina), placed by their `insertAfter` entries; it is disabled otherwise
  (`web/js/canon.js`, `tests/test_canon.js`). Share links carry `canon=`.

### Fixed

- The BSB is public domain (dedicated 2023-04-30); it had been recorded as CC BY-SA.
- The KJV source is stated correctly (it comes through Theographic), and the UK Crown
  rights caveat is recorded.
- The interface-string packs and the slug lock are CC BY-SA 4.0 consistently, in the
  README, NOTICE, catalog and manifests.
- Catalog licence rows now agree with manifests.

### Known gaps

- The reader has no transliteration yet, and does not show interlinear text.
- The `stepbible` lexicon and morph-code files do not cover every number and code its words
  use; nothing is filled in (see `docs/DATA.md`).
- The pipeline does not yet assert year 0 in Theographic dates.
