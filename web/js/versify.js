/* Concordio Core: Psalm numbering, driven by web/data/packs/versify.json.
 *
 * The reader's reference numbering is Hebrew (Masoretic), the one theographic uses.
 * Some translations number Psalms the Greek/Latin (Septuagint, Vulgate) way. This module
 * maps a Hebrew Psalm number to the chapter(s) of such a translation. It only reads
 * versify.json: it never invents a mapping, and it does not split a chapter, because the
 * file maps chapters, not verses.
 *
 * Pure functions, no DOM, so Node can test it (tests/test_versify.js).
 * Apache-2.0.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.Versify = api;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /* No manifest states which numbering a translation uses, so the reader keeps this
     small explicit table. A manifest `psalmNumbering` field ("hebrew" | "septuagint"),
     if one is ever added, wins. tests/test_versify.js checks the table against the data. */
  const PSALM_NUMBERING = {
    'douay-rheims': 'septuagint',
    'vulgata-clementina': 'septuagint',
  };

  function numberingFor(packId, manifest) {
    const declared = manifest && manifest.psalmNumbering;
    if (declared === 'hebrew' || declared === 'septuagint') return declared;
    return PSALM_NUMBERING[packId] || 'hebrew';
  }

  /* "9" -> [9]; "114-115" -> [114, 115]. Returns null for anything else. */
  function parseTarget(s) {
    const m = /^(\d+)(?:-(\d+))?$/.exec(String(s));
    if (!m) return null;
    const a = parseInt(m[1], 10);
    const b = m[2] === undefined ? a : parseInt(m[2], 10);
    if (b < a) return null;
    const out = [];
    for (let i = a; i <= b; i++) out.push(i);
    return out;
  }

  /* Map a Hebrew Psalm number to the translation's chapter(s).
     Returns { chapters: [n, ...], shared: [hebrewNumber, ...] } where `shared` lists the
     other Hebrew Psalms that map onto any of the same chapters (Hebrew 9 and 10 are one
     chapter in the Greek/Latin numbering). Returns null when versify.json has no entry,
     so callers fall back to the requested number. */
  function resolvePsalm(versify, hebrewNumber, numbering) {
    if (numbering !== 'septuagint') return { chapters: [hebrewNumber], shared: [] };
    const map = versify && versify.psalms && versify.psalms.heb_to_lxx;
    if (!map) return null;
    const chapters = parseTarget(map[String(hebrewNumber)]);
    if (!chapters) return null;
    const shared = [];
    for (const k of Object.keys(map)) {
      const other = parseInt(k, 10);
      if (other === hebrewNumber) continue;
      const theirs = parseTarget(map[k]);
      if (theirs && theirs.some(c => chapters.includes(c))) shared.push(other);
    }
    shared.sort((a, b) => a - b);
    return { chapters, shared };
  }

  /* Chapters of `book` to read for the reader's (Hebrew-numbered) chapter. Only Psalms
     are renumbered; every other book, and every Hebrew-numbered translation, is identity. */
  function resolveChapter(versify, book, chapter, numbering) {
    if (book !== 'Ps') return { chapters: [chapter], shared: [] };
    return resolvePsalm(versify, chapter, numbering) || { chapters: [chapter], shared: [] };
  }

  return { PSALM_NUMBERING, numberingFor, parseTarget, resolvePsalm, resolveChapter };
});
