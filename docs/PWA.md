# PWA / offline model

The reader is an installable Progressive Web App. On first load the service
worker precaches the shell and the entities + chrome + default-preset pack
files. Subsequent loads work offline. Added translations are fetched on first
use and cached cache-first.

## Release rule

Bump `CACHE_VERSION` in `web/sw.js` whenever anything under `web/css/`,
`web/js/`, `web/index.html`, or `web/manifest.webmanifest` changes. Data-pack
changes do not require a cache bump; the pack loader appends `?v=<version>`
to every pack file, so new pack versions produce fresh URLs and stale copies
are never requested.

## Cache strategy

| Request shape | Strategy |
| --- | --- |
| Same-origin pointer (`index.json`, per-pack `manifest.json`) | Network-first; fall back to cache. |
| Any other same-origin file | Cache-first; fetch and store on miss. |
| Navigation request | Fetch, fall back to cached `index.html`. |

## Installation

- Desktop and Android browsers offer "Install app" from the URL bar.
- iOS Safari uses "Add to Home Screen". `apple-touch-icon` links in
  `web/index.html` provide a launcher icon.
