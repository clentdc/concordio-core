/* Concordio Core — minimal reader.
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
const V = window.Versify;   // web/js/versify.js, loaded before this script
const Canon = window.Canon; // web/js/canon.js, loaded before this script

const state = {
  baseBooks: [],      // the 66, from the entities pack: [{osis,n,cn,t,d,...}]
  extensions: null,   // canon-extensions.json, or null if unavailable
  canon: '66',        // '66' or 'ext' (the 66 plus the extension books the translation has)
  canonTouched: false, // true once the URL or the user has chosen; until then the preset seeds it
  books: [],          // the book list in use (baseBooks, or with extensions spliced in)
  verses: {},         // OSIS -> text, for the active translation
  versify: null,      // versify.json (Psalm numbering map), or null if unavailable
  psalmNumbering: 'hebrew', // numbering the active translation uses: 'hebrew' | 'septuagint'
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
  state.baseBooks = books;
  state.books = books;
}

async function loadExtensions() {
  try { state.extensions = await fetchJSON(`${PACKS_BASE}/canon-extensions.json`); }
  catch (e) { state.extensions = null; }
}

async function loadTranslation(id) {
  const manifest = await fetchJSON(`${PACKS_BASE}/${id}/manifest.json`);
  const versesFile = manifest.files?.verses || 'verses.json';
  const verses = await fetchJSON(`${PACKS_BASE}/${id}/${versesFile}?v=${manifest.version}`);
  state.verses = verses;
  state.translation = id;
  state.psalmNumbering = V.numberingFor(id, manifest);
}

async function loadVersify() {
  try { state.versify = await fetchJSON(`${PACKS_BASE}/versify.json`); }
  catch (e) { state.versify = null; }
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

/* Rebuild the book list for the chosen canon and the active translation. An extension
   book is listed only if the translation's verses contain it; if none do, the choice falls
   back to the 66. */
function applyCanon() {
  const extra = Canon.availableExtensions(state.extensions, state.verses);
  if (!extra.length) state.canon = '66';
  state.books = state.canon === 'ext' ? Canon.buildBooks(state.baseBooks, extra) : state.baseBooks;
  if (!state.books.some(b => b.osis === state.book)) { state.book = state.baseBooks[0].osis; state.chapter = 1; }
  const sel = $('canon');
  sel.innerHTML = '';
  const options = [['66', state.baseBooks.length]];
  if (extra.length) options.push(['ext', state.baseBooks.length + extra.length]);
  for (const [value, n] of options) {
    const opt = document.createElement('option');
    opt.value = value;
    opt.textContent = t('canon.count', '{n} books').replace('{n}', String(n));
    sel.appendChild(opt);
  }
  sel.value = state.canon;
  sel.disabled = options.length < 2;
  populateBookSelect();
  populateChapterSelect();
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

/* The reader's chapter numbers are Hebrew. For a Greek/Latin-numbered translation the
   Psalm shown is the translation's own chapter(s); say so, in neutral words. */
function psalmLabel(name, hebrewNumber, res) {
  const notes = [];
  const own = res.chapters.length > 1
    ? `${res.chapters[0]}\u2013${res.chapters[res.chapters.length - 1]}` : String(res.chapters[0]);
  const renumbered = own !== String(hebrewNumber);
  if (renumbered) notes.push(t('psalm.numbered', 'numbered {n} in this translation').replace('{n}', own));
  if (res.shared.length) {
    const together = t('psalm.shared', 'together with Psalm {n}').replace('{n}', res.shared.join(', '));
    notes.push(renumbered ? together : `${together} ${t('psalm.inTranslation', 'in this translation')}`);
  }
  return notes.length ? `${name} ${hebrewNumber} \u00b7 ${notes.join(', ')}` : `${name} ${hebrewNumber}`;
}

function render() {
  const book = state.books.find(b => b.osis === state.book);
  const name = book ? book.n : state.book;
  const res = V.resolveChapter(state.versify, state.book, state.chapter, state.psalmNumbering);
  const mapped = res.chapters.length !== 1 || res.chapters[0] !== state.chapter || res.shared.length > 0;
  $('where').textContent = mapped ? psalmLabel(name, state.chapter, res) : `${name} ${state.chapter}`;
  const ol = $('verses');
  ol.innerHTML = '';
  for (const ch of res.chapters) {
    if (res.chapters.length > 1) {
      const h = document.createElement('li');
      h.className = 'chap';
      h.textContent = `${name} ${ch}`;
      ol.appendChild(h);
    }
    for (let v = 1; v <= 200; v++) {
      const text = state.verses[`${state.book}.${ch}.${v}`];
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
    }
  }
  try {
    const q = new URLSearchParams({ b: state.book, c: String(state.chapter), tr: state.translation, lang: state.lang, p: state.denom, canon: state.canon });
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
    if (q.get('canon') === '66' || q.get('canon') === 'ext') { state.canon = q.get('canon'); state.canonTouched = true; }
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
  await loadVersify();
  await loadExtensions();
  await loadDenoms();
  await loadPreset(state.denom);
  if (state.preset && !state.verses) state.translation = state.preset.defaultTranslation || state.translation;
  await loadTranslation(state.translation);
  // Starting canon: an explicit URL choice, else a link to an extension book, else the preset's.
  if (!state.canonTouched) {
    const named = ((state.extensions && state.extensions.books) || []).some(b => b.osis === state.book);
    state.canon = named || Canon.presetWantsExtensions(state.preset) ? 'ext' : '66';
  }
  applyI18N();
  applyCanon();
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
  $('canon').addEventListener('change', e => {
    state.canon = e.target.value;
    state.canonTouched = true;
    applyCanon();
    render();
  });
  $('translation').addEventListener('change', async e => {
    await loadTranslation(e.target.value);
    applyCanon();
    render();
  });
  $('lang').addEventListener('change', async e => {
    await loadStrings(e.target.value);
    applyI18N();
    applyCanon();
  });
  $('denom').addEventListener('change', async e => {
    await loadPreset(e.target.value);
    if (state.preset && state.preset.defaultTranslation) {
      state.translation = state.preset.defaultTranslation;
      $('translation').value = state.translation;
      await loadTranslation(state.translation);
    }
    state.canon = Canon.presetWantsExtensions(state.preset) ? 'ext' : '66';
    applyCanon();
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
