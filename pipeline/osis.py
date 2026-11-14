"""OSIS book abbreviations and verse-reference helpers for Concordio Core.

Verse identifiers are OSIS of the form ``<Book>.<chapter>.<verse>`` where ``<Book>``
is the standard OSIS abbreviation (``Gen``, ``Exod``, ``Ps``, ``Song``, ``Matt``,
``3John``, ``Rev``, ...). This matches the ``osisName`` field in Theographic.

Module-level data:

* ``BOOKS``: canonical 66-book list of ``(osis, name, testament)`` tuples.
* ``OSIS_SET``: set of valid OSIS codes.
* ``OSIS_ORDER``: 0-based canonical book index per OSIS code.
* ``NAME_TO_OSIS``: full English book name → OSIS. Also includes common aliases
  (``"Psalm"`` → ``"Ps"``; ``"Song of Songs"`` → ``"Song"``).
"""

BOOKS = [
    ("Gen", "Genesis", "OT"), ("Exod", "Exodus", "OT"), ("Lev", "Leviticus", "OT"),
    ("Num", "Numbers", "OT"), ("Deut", "Deuteronomy", "OT"), ("Josh", "Joshua", "OT"),
    ("Judg", "Judges", "OT"), ("Ruth", "Ruth", "OT"), ("1Sam", "1 Samuel", "OT"),
    ("2Sam", "2 Samuel", "OT"), ("1Kgs", "1 Kings", "OT"), ("2Kgs", "2 Kings", "OT"),
    ("1Chr", "1 Chronicles", "OT"), ("2Chr", "2 Chronicles", "OT"), ("Ezra", "Ezra", "OT"),
    ("Neh", "Nehemiah", "OT"), ("Esth", "Esther", "OT"), ("Job", "Job", "OT"),
    ("Ps", "Psalms", "OT"), ("Prov", "Proverbs", "OT"), ("Eccl", "Ecclesiastes", "OT"),
    ("Song", "Song of Solomon", "OT"), ("Isa", "Isaiah", "OT"), ("Jer", "Jeremiah", "OT"),
    ("Lam", "Lamentations", "OT"), ("Ezek", "Ezekiel", "OT"), ("Dan", "Daniel", "OT"),
    ("Hos", "Hosea", "OT"), ("Joel", "Joel", "OT"), ("Amos", "Amos", "OT"),
    ("Obad", "Obadiah", "OT"), ("Jonah", "Jonah", "OT"), ("Mic", "Micah", "OT"),
    ("Nah", "Nahum", "OT"), ("Hab", "Habakkuk", "OT"), ("Zeph", "Zephaniah", "OT"),
    ("Hag", "Haggai", "OT"), ("Zech", "Zechariah", "OT"), ("Mal", "Malachi", "OT"),
    ("Matt", "Matthew", "NT"), ("Mark", "Mark", "NT"), ("Luke", "Luke", "NT"),
    ("John", "John", "NT"), ("Acts", "Acts", "NT"), ("Rom", "Romans", "NT"),
    ("1Cor", "1 Corinthians", "NT"), ("2Cor", "2 Corinthians", "NT"),
    ("Gal", "Galatians", "NT"), ("Eph", "Ephesians", "NT"), ("Phil", "Philippians", "NT"),
    ("Col", "Colossians", "NT"), ("1Thess", "1 Thessalonians", "NT"),
    ("2Thess", "2 Thessalonians", "NT"), ("1Tim", "1 Timothy", "NT"),
    ("2Tim", "2 Timothy", "NT"), ("Titus", "Titus", "NT"), ("Phlm", "Philemon", "NT"),
    ("Heb", "Hebrews", "NT"), ("Jas", "James", "NT"), ("1Pet", "1 Peter", "NT"),
    ("2Pet", "2 Peter", "NT"), ("1John", "1 John", "NT"), ("2John", "2 John", "NT"),
    ("3John", "3 John", "NT"), ("Jude", "Jude", "NT"), ("Rev", "Revelation", "NT"),
]

OSIS_SET = {o for o, _, _ in BOOKS}
OSIS_ORDER = {o: i for i, (o, _, _) in enumerate(BOOKS)}

NAME_TO_OSIS = {name: o for o, name, _ in BOOKS}
# Common aliases from source datasets with different naming conventions.
NAME_TO_OSIS.update({
    "Psalm": "Ps", "Psalms": "Ps",
    "Song of Songs": "Song", "Canticles": "Song",
    "Qoheleth": "Eccl",
    "1 Kingdoms": "1Sam", "2 Kingdoms": "2Sam",
    "3 Kingdoms": "1Kgs", "4 Kingdoms": "2Kgs",
    "Philem": "Phlm", "Philemon": "Phlm",
})

# STEPBible uses its own 3-letter book codes (Exo, Deu, Mat, Mrk, …) that differ in a
# number of places from the standard OSIS abbreviations Theographic uses (Exod, Deut,
# Matt, Mark, …). This table maps every STEPBible code we have seen in TAHOT and
# TAGNT to its OSIS equivalent. Codes not listed are identical in both schemes
# (Gen, Lev, Num, Dan, Ezr, Neh, Job, Isa, Jer, Lam, Hos, Mic, Hab, Hag, Mal, Rom,
# Gal, Eph, Col, Tit, Heb, Jas, Rev).
STEP_TO_OSIS = {
    "Exo": "Exod", "Deu": "Deut", "Jos": "Josh", "Jdg": "Judg", "Rut": "Ruth",
    "1Sa": "1Sam", "2Sa": "2Sam", "1Ki": "1Kgs", "2Ki": "2Kgs",
    "1Ch": "1Chr", "2Ch": "2Chr", "Ezr": "Ezra", "Est": "Esth",
    "Psa": "Ps", "Pro": "Prov", "Ecc": "Eccl", "Sng": "Song",
    "Ezk": "Ezek", "Jol": "Joel", "Amo": "Amos", "Oba": "Obad",
    "Jon": "Jonah", "Nam": "Nah", "Zep": "Zeph", "Zec": "Zech",
    "Mat": "Matt", "Mrk": "Mark", "Luk": "Luke", "Jhn": "John", "Act": "Acts",
    "1Co": "1Cor", "2Co": "2Cor", "Php": "Phil",
    "1Th": "1Thess", "2Th": "2Thess", "1Ti": "1Tim", "2Ti": "2Tim",
    "Tit": "Titus", "Phm": "Phlm",
    "1Pe": "1Pet", "2Pe": "2Pet", "1Jn": "1John", "2Jn": "2John", "3Jn": "3John",
    "Jud": "Jude",
}


def step_to_osis(code):
    """Translate a STEPBible book code (``Mat``, ``Exo``, ``1Jn``, …) to standard OSIS.

    Returns the input unchanged for codes that already match the standard scheme
    (``Gen``, ``Rev``, …). Returns ``None`` if the result is not a valid OSIS code.
    """
    out = STEP_TO_OSIS.get(code, code)
    return out if out in OSIS_SET else None


def vid(osis, chapter, verse):
    """Return the OSIS verse id ``f"{osis}.{chapter}.{verse}"``.

    Does not validate; callers that want validation should check ``osis in OSIS_SET``.
    """
    return f"{osis}.{chapter}.{verse}"


def parse_vid(s):
    """Parse an OSIS verse id. Returns ``(osis, chapter, verse)`` or ``None``.

    Accepts the single canonical form ``<Book>.<chapter>.<verse>``. Chapter and verse
    must be positive integers. Unknown book codes return ``None``.
    """
    parts = s.split(".")
    if len(parts) != 3:
        return None
    osis, c, v = parts
    if osis not in OSIS_SET:
        return None
    try:
        c, v = int(c), int(v)
    except ValueError:
        return None
    if c < 1 or v < 1:
        return None
    return osis, c, v


def book_name_to_osis(name):
    """Map an English book name (``"Genesis"``, ``"1 Kings"``) to its OSIS code.

    Returns ``None`` for unknown names. Trims whitespace; case-sensitive on the first
    word (``"genesis"`` won't match — the main caller is parsing well-formed source
    data, not user input).
    """
    name = (name or "").strip()
    return NAME_TO_OSIS.get(name)
