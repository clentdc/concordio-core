/* Concordio Core — service worker.
 * Offline-first for the app shell; cache-first for same-origin resources;
 * pack catalog and per-pack manifests are network-first so updates land.
 * Bump CACHE_VERSION with any change under web/.
 */
const CACHE_VERSION = 'v1';
const CACHE = `concordio-core-${CACHE_VERSION}`;
const PRECACHE = [
  './',
  './index.html',
  './css/app.css',
  './js/app.js',
  './manifest.webmanifest',
  './icons/icon.svg',
  './data/packs/index.json',
  './data/packs/chrome-en/manifest.json',
  './data/packs/chrome-en/strings.json',
  './data/packs/theographic/manifest.json',
  './data/packs/theographic/books.json',
  './data/packs/denominations/catalog.json',
  './data/packs/denominations/default.json',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k.startsWith('concordio-core-') && k !== CACHE).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

function isPointer(url) {
  const p = url.pathname;
  return p.endsWith('/data/packs/index.json') || /\/data\/packs\/[^/]+\/manifest\.json$/.test(p);
}

async function cacheFirst(request) {
  const cache = await caches.open(CACHE);
  const hit = await cache.match(request);
  if (hit) return hit;
  const res = await fetch(request);
  if (res && (res.ok || res.type === 'opaque')) cache.put(request, res.clone());
  return res;
}

async function networkFirst(request) {
  const cache = await caches.open(CACHE);
  try {
    const res = await fetch(request);
    if (res && res.ok) cache.put(request, res.clone());
    return res;
  } catch (_) {
    const hit = await cache.match(request);
    if (hit) return hit;
    throw _;
  }
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (req.mode === 'navigate') {
    event.respondWith(fetch(req).catch(() => caches.match('./index.html')));
    return;
  }
  if (url.origin === self.location.origin) {
    event.respondWith(isPointer(url) ? networkFirst(req) : cacheFirst(req));
  }
});
