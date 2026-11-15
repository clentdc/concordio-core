// Psalm numbering: web/js/versify.js against web/data/packs/versify.json and the packs.
// Plain Node (16 or later), no dependencies:   node tests/test_versify.js
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const PACKS = path.join(__dirname, '..', 'web', 'data', 'packs');
const V = require('../web/js/versify.js');
const read = (...p) => JSON.parse(fs.readFileSync(path.join(PACKS, ...p), 'utf8'));

const versify = read('versify.json');
const index = read('index.json');
const hebrewCounts = {};   // Hebrew Psalm number -> verse count, from the entities pack
for (const [osis, c, n] of read('theographic', 'chapters.json')) if (osis === 'Ps') hebrewCounts[c] = n;
const translations = index.packs.filter(p => p.kind === 'translation');
const verses = {};
for (const p of translations) verses[p.id] = read(p.id, 'verses.json');
const countIn = (id, ch) => {
  let n = 0;
  while (verses[id][`Ps.${ch}.${n + 1}`] !== undefined) n++;
  return n;
};

let passed = 0;
function test(name, fn) { fn(); passed++; console.log(`ok   ${name}`); }

test('Douay-Rheims: Hebrew Psalm 23 is its Psalm 22, with the expected text', () => {
  const r = V.resolveChapter(versify, 'Ps', 23, V.numberingFor('douay-rheims', null));
  assert.deepStrictEqual(r.chapters, [22]);
  assert.deepStrictEqual(r.shared, []);
  assert.ok(verses['douay-rheims']['Ps.22.1'].includes('The Lord ruleth me'));
  assert.ok(verses['douay-rheims']['Ps.22.1'].includes('shall want nothing'));
});

test('Vulgata Clementina: Hebrew Psalm 23 is its Psalm 22', () => {
  const r = V.resolveChapter(versify, 'Ps', 23, V.numberingFor('vulgata-clementina', null));
  assert.deepStrictEqual(r.chapters, [22]);
  assert.ok(verses['vulgata-clementina']['Ps.22.1'].includes('Dominus regit me'));
});

test('boundary cases follow versify.json exactly', () => {
  const at = n => V.resolveChapter(versify, 'Ps', n, 'septuagint');
  const flat = n => [at(n).chapters, at(n).shared];
  assert.deepStrictEqual(flat(8),   [[8], []]);
  assert.deepStrictEqual(flat(9),   [[9], [10]]);      // Hebrew 9 and 10 are one chapter
  assert.deepStrictEqual(flat(10),  [[9], [9]]);
  assert.deepStrictEqual(flat(11),  [[10], []]);
  assert.deepStrictEqual(flat(113), [[112], []]);
  assert.deepStrictEqual(flat(114), [[113], [115]]);   // Hebrew 114 and 115 are one chapter
  assert.deepStrictEqual(flat(115), [[113], [114]]);
  assert.deepStrictEqual(flat(116), [[114, 115], []]); // one Hebrew Psalm is two chapters
  assert.deepStrictEqual(flat(117), [[116], []]);
  assert.deepStrictEqual(flat(146), [[145], []]);
  assert.deepStrictEqual(flat(147), [[146, 147], []]);
  assert.deepStrictEqual(flat(148), [[148], []]);
});

test('every Hebrew Psalm maps to chapters that exist in each Greek/Latin pack, and all 150 are covered', () => {
  for (const id of ['douay-rheims', 'vulgata-clementina']) {
    const seen = new Set();
    for (let n = 1; n <= 150; n++) {
      const r = V.resolveChapter(versify, 'Ps', n, 'septuagint');
      assert.ok(r.chapters.length > 0, `Ps ${n}`);
      for (const ch of r.chapters) {
        assert.ok(countIn(id, ch) > 0, `${id}: Hebrew ${n} -> missing chapter ${ch}`);
        seen.add(ch);
      }
    }
    assert.strictEqual(seen.size, 150, `${id}: mapped chapters cover 1..150`);
  }
});

test('Hebrew-numbered translations and other books are not remapped', () => {
  for (const n of [9, 10, 23, 116, 147]) {
    assert.deepStrictEqual(V.resolveChapter(versify, 'Ps', n, 'hebrew'), { chapters: [n], shared: [] });
  }
  assert.deepStrictEqual(V.resolveChapter(versify, 'Gen', 23, 'septuagint'), { chapters: [23], shared: [] });
});

test('missing or malformed versify data falls back to the requested chapter', () => {
  assert.deepStrictEqual(V.resolveChapter(null, 'Ps', 23, 'septuagint'), { chapters: [23], shared: [] });
  assert.deepStrictEqual(V.resolveChapter({ psalms: { heb_to_lxx: { 23: 'x' } } }, 'Ps', 23, 'septuagint'),
    { chapters: [23], shared: [] });
  assert.strictEqual(V.parseTarget('116-114'), null);
});

test('the numbering table matches the data (guards a wrong or stale entry)', () => {
  for (const p of translations) {
    const numbering = V.numberingFor(p.id, null);
    if (numbering === 'hebrew') {
      for (const n of [9, 10, 23, 116, 147]) {
        assert.strictEqual(countIn(p.id, n), hebrewCounts[n], `${p.id}: Ps ${n} should match the Hebrew verse count`);
      }
    } else {
      // Where the Greek/Latin numbering splits or joins whole Hebrew Psalms, the verse
      // counts add up exactly: 114+115 = LXX 113; 116 = LXX 114 + 115; 147 = LXX 146 + 147.
      assert.strictEqual(countIn(p.id, 113), hebrewCounts[114] + hebrewCounts[115], `${p.id}: Ps 113`);
      assert.strictEqual(countIn(p.id, 114) + countIn(p.id, 115), hebrewCounts[116], `${p.id}: Ps 114+115`);
      assert.strictEqual(countIn(p.id, 146) + countIn(p.id, 147), hebrewCounts[147], `${p.id}: Ps 146+147`);
      assert.notStrictEqual(countIn(p.id, 10), hebrewCounts[10], `${p.id}: Ps 10 differs from Hebrew`);
    }
  }
  assert.strictEqual(V.numberingFor('douay-rheims', null), 'septuagint');
  assert.strictEqual(V.numberingFor('bsb', null), 'hebrew');
});

test('a manifest psalmNumbering field wins over the table', () => {
  assert.strictEqual(V.numberingFor('bsb', { psalmNumbering: 'septuagint' }), 'septuagint');
  assert.strictEqual(V.numberingFor('douay-rheims', { psalmNumbering: 'hebrew' }), 'hebrew');
  assert.strictEqual(V.numberingFor('douay-rheims', { psalmNumbering: 'bogus' }), 'septuagint');
});

test('Psalm 151 (lxx_only) is unreachable: no pack has it and the chapter list stops at 150', () => {
  assert.deepStrictEqual(versify.psalms.lxx_only, ['151']);
  assert.strictEqual(Math.max(...Object.keys(hebrewCounts).map(Number)), 150);
  for (const p of translations) assert.strictEqual(verses[p.id]['Ps.151.1'], undefined, `${p.id} has Ps.151`);
});

console.log(`${passed} versify tests passed`);
