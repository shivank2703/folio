"""Correct misspelled question words against the selected filing's own vocabulary.

"totla assets navneet" was refused at the similarity floor: the embedding of a
misspelled word lands nowhere near "TOTAL ASSETS", and keyword search cannot
match "totla" at all. The fix is string work, not a model call: a word the
filing never prints is replaced by the closest word it does print, when one
is close enough. The filing is the dictionary because its vocabulary is the
one retrieval has to meet — a general English dictionary would happily keep
"totla" and know nothing of "EBITDA" or "Gadepan".

Correcting against the filing alone was measured and is unsafe: words the
filing never prints are often real ones, and "drones" became "does",
"patents" "payments", "Brazil" "rail" and "poem" "oem" — each turning a
not-in-the-filing question into a different, possibly answerable one. So a
word is left alone when it is common English, judged by whether tiktoken's
cl100k vocabulary holds it as a single token (the chunker's tokenizer, already
installed; a typo like "totla" splits into pieces). A correction must also be
one edit away (a transposition, insertion, deletion or substitution) from a
word the filing prints at least three times.

Only words of four letters or more are touched, so a correctly spelled
question comes back unchanged.
"""

from __future__ import annotations

import re
from collections import Counter

WORD = re.compile(r"[A-Za-z]+")

MIN_LENGTH = 4
MIN_COUNT = 3

_vocabularies: dict[tuple[int, str], Counter] = {}


def vocabulary(table, company: str) -> Counter:
    """How often the filing prints each lower-cased word; read once per filing per process."""
    cache_key = (id(table), company)
    if cache_key not in _vocabularies:
        rows = (table.search().where("company = '" + company.replace("'", "''") + "'")
                .select(["text"]).limit(1_000_000).to_list())
        _vocabularies[cache_key] = Counter(w.lower() for r in rows for w in WORD.findall(r["text"]))
    return _vocabularies[cache_key]


def one_edit(a: str, b: str) -> bool:
    """True if b is one insertion, deletion, substitution or adjacent swap away from a."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diff = [i for i in range(len(a)) if a[i] != b[i]]
        return len(diff) == 1 or (len(diff) == 2 and diff[1] == diff[0] + 1
                                  and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]])
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    return any(long_[:i] + long_[i + 1:] == short for i in range(len(long_)))


def is_common_word(word: str) -> bool:
    """A word cl100k encodes as one token, bare or capitalised, is ordinary English, not a typo."""
    from ingest.chunk import ENCODING

    return any(len(ENCODING.encode(" " + form)) == 1 for form in (word, word.capitalize()))


def closest(word: str, words: Counter) -> str | None:
    """The filing's most frequent word one edit away from `word`, if it prints one often enough."""
    candidates = [w for w in words if words[w] >= MIN_COUNT and one_edit(word, w)]
    return max(candidates, key=lambda w: words[w]) if candidates else None


def correct(question: str, table, company: str | None) -> str:
    """The question with each unknown word replaced by its closest filing word, or unchanged."""
    if not company:
        return question
    words = vocabulary(table, company)

    def fix(match: re.Match[str]) -> str:
        word = match.group(0)
        lower = word.lower()
        if len(lower) < MIN_LENGTH or lower in words or is_common_word(lower):
            return word
        return closest(lower, words) or word

    return WORD.sub(fix, question)
