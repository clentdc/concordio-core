# Updates

How data changes reach Concordio Core and the projects built on it. Short version: a
weekly job rebuilds the upstream-derived packs and opens a pull request; a human reads
the diff and merges; consumers pick up changes by moving to a new tagged release.

- [The weekly refresh](#the-weekly-refresh)
- [Reviewing a refresh pull request](#reviewing-a-refresh-pull-request)
- [Refreshing by hand](#refreshing-by-hand)
- [Pack versions and provenance](#pack-versions-and-provenance)
- [For consumers: pin a release](#for-consumers-pin-a-release)
- [Interlinear packs: release artifacts](#interlinear-packs-release-artifacts)
- [Rollback](#rollback)
- [Stability guarantees](#stability-guarantees)

## The weekly refresh

`.github/workflows/check-upstream.yml` runs every Monday at 07:17 UTC (and on demand
with `gh workflow run check-upstream.yml`):

1. `make refresh-data` pulls the latest Theographic and BSB, then rebuilds the
   `theographic`, `bsb` and `kjv` packs (the KJV text is read from Theographic).
2. `make check` runs the data, licence and reserved-material checks on the result.
3. If anything under `web/data/packs/` or `pipeline/slug-lock.json` changed, it opens a
   pull request titled `data: refresh packs from upstream`, with the manifest diff in
   the body. If nothing changed, nothing opens.

Nothing publishes without a human merging the PR. The workflow needs the repository
setting *Allow GitHub Actions to create and approve pull requests* switched on. Actions
used by the workflow are pinned to commit SHAs.

The refresh deliberately covers only the packs stored in git. The large interlinear
packs are not part of it: they are built when a release is cut (see
[below](#interlinear-packs-release-artifacts)).

## Reviewing a refresh pull request

The PR body shows the manifest diff. Check:

- **`sourceRef` and `version` moved** to the upstream revision you expect.
- **Counts** in the `theographic` manifest (`people`, `places`, `events`) changed by a
  plausible amount. They can go down as well as up; read upstream's commit log to see why.
- **The slug lock only grew.** `pipeline/slug-lock.json` should gain lines for new
  entities and change none that already existed. A changed existing slug breaks
  published URLs and must not merge.
- **Licence fields did not move.** A changed upstream licence needs a human decision
  before anything else.

GitHub does not start separate CI runs on pull requests opened by a workflow's own
token. The workflow runs the checks itself before opening the PR; to get a CI run on
the PR as well, close and reopen it.

## Refreshing by hand

```bash
make refresh-data
make check
git diff web/data/packs/*/manifest.json
```

Commit `web/data/packs/` and `pipeline/slug-lock.json` together.

## Pack versions and provenance

Every manifest pins exactly what it was built from (see
[PACK-SCHEMA.md](PACK-SCHEMA.md#manifest-manifestjson)): `version`, `source.revision`,
`sourceRef` and `fetchHash`. Two properties follow:

- **Builds are reproducible.** The same upstream revision gives byte-identical output,
  because builds read no clock and `fetchHash` covers the whole normalised input.
- **A rebuild that changes nothing opens no PR.** The pins have not moved.

A pack `version` is an opaque string; consumers compare it for equality. The reference
reader appends `?v=<version>` to every pack file request, so a new version is a new URL.

## For consumers: pin a release

Applications built on Core should not track `main`. Pin a tagged release and its
content hash, and move deliberately:

1. Take the new release tag.
2. Read its [CHANGELOG](../CHANGELOG.md) entry and the pack manifest diff.
3. Run your own checks.
4. Ship.

A pack-only update never needs an application code change, provided the pack `schemaVersion`
is unchanged. A schema change is a breaking release and will say so in the changelog.

## Interlinear packs: release artifacts

`stepbible` and `bsb-tables` are about 58 MB each, and a regenerated copy would be a new
permanent copy in git history, so core does not commit them. Each tagged release (`v*`)
carries them instead, built by `.github/workflows/release.yml`:

| Asset | What |
| --- | --- |
| `concordio-pack-stepbible-<tag>.tar.gz` | The `stepbible` pack (about 9.6 MB; 58 MB unpacked) |
| `concordio-pack-bsb-tables-<tag>.tar.gz` | The `bsb-tables` pack (about 9.4 MB; 58 MB unpacked) |
| `SHA256SUMS` | One `<sha256>  <file>` line per tarball |

The release notes list each pack's `version`, upstream revision and licence. A tarball holds a
single top-level directory (`stepbible/` or `bsb-tables/`), so it unpacks into
`web/data/packs/`.

**Fetch and verify** (no GitHub login needed, Python 3 only):

```bash
make fetch-release TAG=v0.1.0          # both packs into web/data/packs/
python3 -I pipeline/release.py fetch --tag v0.1.0 --pack bsb-tables --dest ./packs
```

`fetch` downloads `SHA256SUMS`, then each tarball, and checks every hash **before** it unpacks
anything. It refuses archives with paths outside the pack directory. It then replaces
`<dest>/<id>/`. Each pack's `manifest.json` carries its own licence and attribution.

**What the hash proves.** `SHA256SUMS` is published beside the tarballs, so it catches a
damaged or swapped download, not a compromised release. To pin against that, record the hash
in your own repository when you adopt a tag, and have your build check it. `fetch` accepts
`--sums-sha256 <hash of SHA256SUMS>` for exactly that. The hash of each tarball is also in the
release notes.

**How a release is built.** `make release-packs` fetches the pinned sources (STEPBible-Data at
a fixed commit; the BSB Translation Tables and Strong's XML by SHA-256) and builds the two packs
into `dist/packs/` with `--stage`, which leaves `index.json` alone. With
`CONCORDIO_STRICT_PINS` set, as it is in the release workflow, a source whose hash differs from
the reviewed pin stops the build instead of warning. `make release-assets VERSION=<tag>` then
writes the tarballs: entries sorted, times and owners fixed, no gzip timestamp, so the same
packs give the same bytes. Anyone can rebuild and compare: the pack files are byte-identical
for the same sources, and the tarball is too on the same zlib.

**Cutting a release.** Update `CHANGELOG.md` (a `## X.Y.Z` section), merge to `main`, then push an
annotated tag `vX.Y.Z` on that commit. The workflow refuses a tag that is not on `main` or has
no changelog section. Run the workflow by hand first (Actions, Release, Run workflow) for a dry
run: it builds and checks everything and uploads the files as a workflow artifact, but publishes
nothing. Never move or delete a published tag; fix forward with the next patch tag.

**Samples.** `web/data/samples/` holds a short cut of each pack in git (3 John; Obadiah too in
`bsb-tables-sample`), so a fresh clone has interlinear data without a download. Regenerate with
`make release-packs samples`; see [DATA.md](DATA.md#what-is-in-the-repository).

## Rollback

Everything is a git revert. Revert the merge commit of a bad refresh, or tag a fix.
Consumers pinned to an earlier release are unaffected. Old release tags and their
bytes (including the interlinear tarballs) stay available.

## Stability guarantees

| Guarantee | Mechanism |
| --- | --- |
| OSIS verse ids do not change. | Every adapter normalises to OSIS; the book table is `pipeline/osis.py`. |
| Entity slugs do not change. | `pipeline/slug-lock.json` locks every slug; new entities are slotted around it. |
| Schema breaks are explicit. | `schemaVersion` changes and a major version bump, with a changelog entry. |
| Attribution travels with the data. | `license.attribution` is required in every manifest; tests enforce it. |
| Rebuilds are deterministic. | Same upstream revision, same bytes. |
| Licence statements agree everywhere. | `tests/test_licences.py` compares README, NOTICE, docs, catalog and manifests. |
