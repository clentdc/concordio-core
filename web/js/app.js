/* Concordio Foundation — minimal reader.
 *
 * Loads book metadata from the theographic pack, verse text from a
 * translation pack, UI strings from a chrome pack, and optional
 * denominational presets from the denominations catalog. Offline-first
 * via web/sw.js. Plain vertical reader; no visualizer, no 3D.
 *
 * Apache-2.0.
 */
(() => {
'use strict';

const PACKS_BASE = 'data/packs';
const $ = (id) => document.getElementById(id);

const state = {
  books: [],          // [{osis,n,cn,t,d,...}]
  verses: {},         // OSIS -> text, for the active translation
  translation: 'bsb',
  translations: [],   // from index.json where kind === 'translation'
  langs: [],          // chrome packs
  lang: 'en',
  strings: {},        // i18n
  denom: 'default',
  denoms: [],
  preset: null,
  book: 'Gen',
  chapter: 1,
};

async function fetchJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.json();
}

async function loadIndex() {
  return fetchJSON(`${PACKS_BASE}/index.json`);
}

async function loadBooks() {
  const books = await fetchJSON(`${PACKS_BASE}/theographic/books.json`);
  state.books = books;
}

async function loadTranslation(id) {
  const manifest = await fetchJSON(`${PACKS_BASE}/${id}/manifest.json`);
  const versesFile = manifest.files?.verses || 'verses.json';
  const verses = await fetchJSON(`${PACKS_BASE}/${id}/${versesFile}?v=${manifest.version}`);
  state.verses = verses;
  state.translation = id;
}

async function loadStrings(lang) {
  try {
    const packId = `chrome-${lang}`;
    const manifest = await fetchJSON(`${PACKS_BASE}/${packId}/manifest.json`);
    const file = manifest.files?.strings || 'strings.json';
    state.strings = await fetchJSON(`${PACKS_BASE}/${packId}/${file}?v=${manifest.version}`);
    state.lang = lang;
    document.documentElement.lang = lang;
    try { localStorage.setItem('cf.lang', lang); } catch (e) {}
  } catch (e) {
    state.strings = {};
    state.lang = 'en';
  }
}

function t(key, fallback) {
  return state.strings[key] || fallback || key;
}

async function loadDenoms() {
  try {
    const catalog = await fetchJSON(`${PACKS_BASE}/denominations/catalog.json`);
    state.denoms = catalog.presets || [];
  } catch (e) {
    state.denoms = [{ id: 'default', name: 'Default', shortName: 'Default', defaultTranslation: 'bsb' }];
  }
}

async function loadPreset(id) {
  try {
    const p = await fetchJSON(`${PACKS_BASE}/denominations/${id}.json`);
    state.preset = p;
    state.denom = id;
    try { localStorage.setItem('cf.denom', id); } catch (e) {}
    if (p.defaultTranslation && state.verses[`${state.book}.${state.chapter}.1`] === undefined) {
      // noop; translation swap handled by the controls when user picks it.
    }
  } catch (e) {
    state.preset = null;
    state.denom = 'default';
  }
}

function populateBookSelect() {
  const sel = $('book');
  sel.innerHTML = '';
  for (const b of state.books) {
    const opt = document.createElement('option');
    opt.value = b.osis;
    opt.textContent = b.n;
    sel.appendChild(opt);
  }
  sel.value = state.book;
}

function populateChapterSelect() {
  const book = state.books.find(b => b.osis === state.book);
  const n = book ? book.cn : 1;
  const sel = $('chapter');
  sel.innerHTML = '';
  for (let i = 1; i <= n; i++) {
    const opt = document.createElement('option');
    opt.value = String(i);
    opt.textContent = String(i);
    sel.appendChild(opt);
  }
  sel.value = String(state.chapter);
}

function populateTranslationSelect(index) {
  const sel = $('translation');
  sel.innerHTML = '';
  state.translations = index.packs.filter(p => p.kind === 'translation' && p.installable !== false);
  for (const p of state.translations) {
    const opt = document.createElement('option');
    opt.value = p.id;
    opt.textContent = `${p.name} (${p.languageName || p.language})`;
    sel.appendChild(opt);
  }
  sel.value = state.translation;
}

function populateLangSelect(index) {
  const sel = $('lang');
  sel.innerHTML = '';
  state.langs = index.packs.filter(p => p.kind === 'chrome');
  for (const p of state.langs) {
    const opt = document.createElement('option');
    opt.value = p.language;
    opt.textContent = p.name;
    sel.appendChild(opt);
  }
  sel.value = state.lang;
}

function populateDenomSelect() {
  const sel = $('denom');
  sel.innerHTML = '';
  for (const p of state.denoms) {
    const opt = document.createElement('option');
    opt.value = p.id;
    opt.textContent = p.shortName || p.name;
    sel.appendChild(opt);
  }
  sel.value = state.denom;
}

function applyI18N() {
  for (const el of document.querySelectorAll('[data-i18n]')) {
    const key = el.getAttribute('data-i18n');
    const val = state.strings[key];
    if (val) el.textContent = val;
  }
}

function render() {
  const book = state.books.find(b => b.osis === state.book);
  const name = book ? book.n : state.book;
  $('where').textContent = `${name} ${state.chapter}`;
  const ol = $('verses');
  ol.innerHTML = '';
  let v = 1;
  while (true) {
    const key = `${state.book}.${state.chapter}.${v}`;
    const text = state.verses[key];
    if (text === undefined) break;
    const li = document.createElement('li');
    const n = document.createElement('span');
    n.className = 'vnum';
    n.textContent = String(v);
    const tx = document.createElement('span');
    tx.className = 'vtext';
    tx.textContent = text;
    li.appendChild(n);
    li.appendChild(tx);
    ol.appendChild(li);
    v++;
    if (v > 200) break;
  }
  try {
    const q = new URLSearchParams({ b: state.book, c: String(state.chapter), tr: state.translation, lang: state.lang, p: state.denom });
    history.replaceState(null, '', `#${q.toString()}`);
  } catch (e) {}
  updatePaging();
}

function updatePaging() {
  const book = state.books.find(b => b.osis === state.book);
  const bi = state.books.findIndex(b => b.osis === state.book);
  const atStart = bi === 0 && state.chapter === 1;
  const atEnd = bi === state.books.length - 1 && state.chapter === (book ? book.cn : 1);
  $('prev').disabled = atStart;
  $('next').disabled = atEnd;
}

function stepChapter(dir) {
  const book = state.books.find(b => b.osis === state.book);
  const n = book ? book.cn : 1;
  let c = state.chapter + dir;
  if (c < 1) {
    const bi = state.books.findIndex(b => b.osis === state.book);
    if (bi <= 0) return;
    state.book = state.books[bi - 1].osis;
    const prev = state.books[bi - 1];
    c = prev.cn;
  } else if (c > n) {
    const bi = state.books.findIndex(b => b.osis === state.book);
    if (bi >= state.books.length - 1) return;
    state.book = state.books[bi + 1].osis;
    c = 1;
  }
  state.chapter = c;
  populateBookSelect();
  populateChapterSelect();
  render();
}

/* Font-size cycler and pinch-to-reflow — same approach as upstream
   Bible Explorer, shipped here as a reusable kernel pattern. */
const FS = {
  order: ['sm', 'lg', 'xl'],
  current: 'sm',
  apply(size) {
    const r = document.documentElement;
    r.classList.remove('fs-sm', 'fs-lg', 'fs-xl');
    if (size !== 'sm') r.classList.add('fs-' + size);
    try { localStorage.setItem('cf.fs', size); } catch (e) {}
    this.current = size;
    const btn = $('fs-button');
    if (btn) btn.setAttribute('aria-pressed', size !== 'sm' ? 'true' : 'false');
  },
  cycle() {
    const i = this.order.indexOf(this.current);
    this.apply(this.order[(i + 1) % this.order.length]);
  },
  step(dir) {
    const i = this.order.indexOf(this.current);
    const n = Math.max(0, Math.min(this.order.length - 1, i + (dir > 0 ? 1 : -1)));
    if (this.order[n] !== this.current) this.apply(this.order[n]);
  },
  init() {
    try { this.current = localStorage.getItem('cf.fs') || 'sm'; } catch (e) {}
    this.apply(this.current);
    const btn = $('fs-button');
    if (btn) btn.addEventListener('click', () => this.cycle());
  },
};

const PINCH = {
  active: false, baseDist: 0,
  _dist(ts) { const dx = ts[0].clientX - ts[1].clientX, dy = ts[0].clientY - ts[1].clientY; return Math.hypot(dx, dy); },
  onStart(e) {
    if (e.touches.length !== 2) { this.active = false; return; }
    this.active = true;
    this.baseDist = this._dist(e.touches);
  },
  onMove(e) {
    if (!this.active || e.touches.length !== 2) return;
    e.preventDefault();
    const d = this._dist(e.touches);
    if (!this.baseDist) return;
    const r = d / this.baseDist;
    if (r >= 1.25) { FS.step(+1); this.baseDist = d; }
    else if (r <= 0.8) { FS.step(-1); this.baseDist = d; }
  },
  onEnd(e) { if (!e.touches || e.touches.length < 2) this.active = false; },
  init() {
    document.addEventListener('touchstart', e => this.onStart(e), { passive: true });
    document.addEventListener('touchmove', e => this.onMove(e), { passive: false });
    document.addEventListener('touchend', e => this.onEnd(e), { passive: true });
    document.addEventListener('touchcancel', e => this.onEnd(e), { passive: true });
    let gActive = false, gBase = 1;
    document.addEventListener('gesturestart', e => { gActive = true; gBase = 1; e.preventDefault(); });
    document.addEventListener('gesturechange', e => {
      if (!gActive) return;
      e.preventDefault();
      const s = e.scale / gBase;
      if (s >= 1.25) { FS.step(+1); gBase = e.scale; }
      else if (s <= 0.8) { FS.step(-1); gBase = e.scale; }
    });
    document.addEventListener('gestureend', () => { gActive = false; });
  },
};

function restoreFromHash() {
  try {
    const q = new URLSearchParams(location.hash.slice(1));
    if (q.get('b')) state.book = q.get('b');
    if (q.get('c')) state.chapter = parseInt(q.get('c'), 10) || 1;
    if (q.get('tr')) state.translation = q.get('tr');
    if (q.get('lang')) state.lang = q.get('lang');
    if (q.get('p')) state.denom = q.get('p');
  } catch (e) {}
  try {
    state.lang = state.lang || localStorage.getItem('cf.lang') || 'en';
    state.denom = state.denom || localStorage.getItem('cf.denom') || 'default';
  } catch (e) {}
}

async function init() {
  restoreFromHash();
  FS.init();
  PINCH.init();
  const index = await loadIndex();
  await loadBooks();
  await loadStrings(state.lang);
  await loadDenoms();
  await loadPreset(state.denom);
  if (state.preset && !state.verses) state.translation = state.preset.defaultTranslation || state.translation;
  await loadTranslation(state.translation);
  applyI18N();
  populateBookSelect();
  populateChapterSelect();
  populateTranslationSelect(index);
  populateLangSelect(index);
  populateDenomSelect();
  render();

  $('book').addEventListener('change', e => {
    state.book = e.target.value;
    state.chapter = 1;
    populateChapterSelect();
    render();
  });
  $('chapter').addEventListener('change', e => {
    state.chapter = parseInt(e.target.value, 10) || 1;
    render();
  });
  $('translation').addEventListener('change', async e => {
    await loadTranslation(e.target.value);
    render();
  });
  $('lang').addEventListener('change', async e => {
    await loadStrings(e.target.value);
    applyI18N();
  });
  $('denom').addEventListener('change', async e => {
    await loadPreset(e.target.value);
    if (state.preset && state.preset.defaultTranslation) {
      state.translation = state.preset.defaultTranslation;
      $('translation').value = state.translation;
      await loadTranslation(state.translation);
    }
    render();
  });
  $('prev').addEventListener('click', () => stepChapter(-1));
  $('next').addEventListener('click', () => stepChapter(+1));

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }
}

init().catch(err => {
  console.error('init failed', err);
  const w = $('where'); if (w) w.textContent = 'Reader failed to load. Check the browser console.';
});
})();
