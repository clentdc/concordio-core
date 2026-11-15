/* Concordio Core: the book list for a chosen canon, driven by
 * web/data/packs/canon-extensions.json.
 *
 * The baseline is the 66 books from the entities pack. canon-extensions.json describes the
 * seven further books (chapter counts, and `insertAfter`, the book each one follows). A
 * translation offers an extension book only if its own verses contain it, so the reader
 * never lists a book it cannot show. Pure functions, no DOM; tested by tests/test_canon.js.
 * Apache-2.0.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.Canon = api;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /* Extension books (as reader book objects) that the verses actually contain. */
  function availableExtensions(extensions, verses) {
    const list = (extensions && extensions.books) || [];
    return list
      .filter(b => verses && verses[`${b.osis}.1.1`] !== undefined)
      .map(b => ({ osis: b.osis, n: b.name, s: b.short, t: b.testament, d: '', cn: b.chapters, ext: true,
                   insertAfter: b.insertAfter }));
  }

  /* The 66 with `ext` books spliced in after the book each names. An extension book may
     follow another extension book (Judith follows Tobit); anchors are resolved in passes.
     A book whose anchor never resolves is left out rather than placed by guess. */
  function buildBooks(baseBooks, ext) {
    const out = baseBooks.slice();
    let pending = ext.slice();
    while (pending.length) {
      const next = [];
      for (const b of pending) {
        const at = out.findIndex(x => x.osis === b.insertAfter);
        if (at < 0) next.push(b); else out.splice(at + 1, 0, b);
      }
      if (next.length === pending.length) break;   // no progress: unresolved anchors
      pending = next;
    }
    return out;
  }

  /* Does a preset ask for books beyond the 66? Used only to choose the starting selection. */
  function presetWantsExtensions(preset) {
    const c = preset && preset.canon;
    return !!(c && ((c.deuterocanonBooks || []).length || (c.apocryphaBooks || []).length));
  }

  return { availableExtensions, buildBooks, presetWantsExtensions };
});
