// Canon selector: web/js/canon.js against canon-extensions.json and the packs.
// Plain Node (16 or later), no dependencies:   node tests/test_canon.js
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const PACKS = path.join(__dirname, '..', 'web', 'data', 'packs');
const C = require('../web/js/canon.js');
const read = (...p) => JSON.parse(fs.readFileSync(path.join(PACKS, ...p), 'utf8'));

const ext = read('canon-extensions.json');
const base = read('theographic', 'books.json');
const verses = id => read(id, 'verses.json');
const order = books => books.map(b => b.osis);

let passed = 0;
function test(name, fn) { fn(); passed++; console.log(`ok   ${name}`); }

test('Douay-Rheims and Vulgata offer all seven extension books; the others offer none', () => {
  assert.strictEqual(base.length, 66);
  for (const id of ['douay-rheims', 'vulgata-clementina']) {
    assert.strictEqual(C.availableExtensions(ext, verses(id)).length, 7, id);
  }
  for (const id of ['bsb', 'kjv', 'darby']) {
    assert.strictEqual(C.availableExtensions(ext, verses(id)).length, 0, id);
  }
});

test('the extended list has 73 books, each placed after the book canon-extensions.json names', () => {
  const books = C.buildBooks(base, C.availableExtensions(ext, verses('douay-rheims')));
  const o = order(books);
  assert.strictEqual(o.length, 73);
  for (const b of ext.books) assert.strictEqual(o[o.indexOf(b.osis) - 1], b.insertAfter, `${b.osis} after ${b.insertAfter}`);
  // The chained cases spelled out: Judith follows Tobit, which follows Nehemiah.
  assert.deepStrictEqual(o.slice(o.indexOf('Neh'), o.indexOf('Neh') + 3), ['Neh', 'Tob', 'Jdt']);
  assert.deepStrictEqual(o.slice(o.indexOf('Song'), o.indexOf('Song') + 3), ['Song', 'Wis', 'Sir']);
  assert.deepStrictEqual(o.slice(o.indexOf('Mal'), o.indexOf('Mal') + 3), ['Mal', '1Macc', '2Macc']);
  // The 66 keep their relative order.
  assert.deepStrictEqual(o.filter(x => base.some(b => b.osis === x)), order(base));
});

test('chapter counts and verses line up: every chapter of every extension book has text in the pack', () => {
  const v = verses('douay-rheims');
  const books = C.availableExtensions(ext, v);
  for (const b of books) {
    const spec = ext.books.find(x => x.osis === b.osis);
    assert.strictEqual(b.cn, spec.chapters);
    for (const [ch, n] of spec.verseCounts) {
      assert.ok(v[`${b.osis}.${ch}.1`] !== undefined, `${b.osis}.${ch}.1`);
      assert.ok(v[`${b.osis}.${ch}.${n}`] !== undefined, `${b.osis}.${ch}.${n}`);
    }
  }
});

test('an unresolved anchor leaves the book out instead of guessing', () => {
  const o = order(C.buildBooks(base, [{ osis: 'Xyz', n: 'X', insertAfter: 'Nope', ext: true }]));
  assert.strictEqual(o.length, 66);
  assert.ok(!o.includes('Xyz'));
});

test('the default preset seeds the 66; a preset that lists books seeds the extension', () => {
  assert.strictEqual(C.presetWantsExtensions(read('denominations', 'default.json')), false);
  assert.strictEqual(C.presetWantsExtensions({ canon: { deuterocanonBooks: ['Tob'] } }), true);
  assert.strictEqual(C.presetWantsExtensions(null), false);
});

console.log(`${passed} canon tests passed`);
