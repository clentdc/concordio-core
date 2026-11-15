# Changelog

All notable changes to Concordio Core. This project will follow
[semantic versioning](https://semver.org/) from its first tagged release: a change to a
pack's `schemaVersion` or to a slug is a major version; new packs and data refreshes
are minor or patch.

## Unreleased (toward 0.1.0)

### Added

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

### Fixed

- The BSB is public domain (dedicated 2023-04-30); it had been recorded as CC BY-SA.
- The KJV source is stated correctly (it comes through Theographic), and the UK Crown
  rights caveat is recorded.
- The interface-string packs and the slug lock are CC BY-SA 4.0 consistently, in the
  README, NOTICE, catalog and manifests.
- Catalog licence rows now agree with manifests.

### Known gaps

- The reader has no transliteration or canon selector yet, and ignores `versify.json`.
- The two interlinear packs (about 58 MB each) are built locally, not stored in git.
- The pipeline does not yet assert year 0 in Theographic dates.
