"""Deterministic answer grading for spoken responses.

No model call happens here, and that is the point: Alexa+ expects a tool result
inside a 500 ms round trip, and a network hop to an LLM would spend the whole
budget by itself. Everything below runs in microseconds.

WHY THIS IS NOT A SIMILARITY THRESHOLD
--------------------------------------
The obvious design - "accept the answer if it is similar enough to the expected
one" - cannot work here, and we measured why. Speech recognition mangles words
phonetically, so a correct answer can arrive badly distorted while a genuinely
different answer can be spelled almost identically:

    "new clee us"  vs  "nucleus"     0.750   must be CORRECT
    "nucleus"      vs  "nucleolus"   0.875   must be WRONG

The wrong pair scores higher than the right one. No threshold separates these
classes, on raw strings or on phonetic keys - the classes genuinely overlap.

So we do not ask "is this close enough to the right answer?". We ask "of every
answer that appears anywhere in this study set, which one did the student
actually say?" - a nearest-neighbour decision over a known, closed candidate
set. `nucleolus` stops being a near-miss for `nucleus` and becomes its own
candidate that the student can be scored against. That also buys the tutoring
feature that matters most: when a student is wrong we know *which* wrong thing
they said, so the coach can name the misconception instead of just saying no.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache

import jellyfish

@dataclass(frozen=True)
class Language:
    """Everything in the grader that is language-specific, in one place.

    The submission is English, because Alexa+ is not available in the
    Netherlands and the simulator is en-US. Isolating these four things means a
    Dutch version is a swap, not a rewrite - the phonetic coder is the only part
    that needs real work, since Dutch sounds are not English sounds.
    """

    name: str
    filler: frozenset[str]
    negations: frozenset[str]
    number_words: dict[str, str]
    phonetic: object   # callable: str -> str


_FILLER = {
    "a", "an", "the", "is", "are", "was", "were", "it", "its", "of", "to",
    "in", "on", "at", "and", "that", "this", "these", "those", "i", "think",
    "um", "uh", "erm", "like", "maybe", "probably", "answer", "would", "be",
    "say", "well", "so", "just", "kind", "sort", "guess",
}

_NEGATIONS = {"not", "no", "never", "isnt", "arent", "dont", "doesnt", "cant"}

_NUMBER_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
}

ENGLISH = Language(
    name="en",
    filler=frozenset(_FILLER),
    negations=frozenset(_NEGATIONS),
    number_words=_NUMBER_WORDS,
    phonetic=jellyfish.metaphone,
)

# The active language. Swapping this is the whole localisation story.
ACTIVE = ENGLISH


# A response must beat the runner-up by this much for the match to count. Below
# it the student said something we cannot confidently attribute, and guessing
# would be worse than asking them to repeat.
_MARGIN = 0.04
# Absolute floor: nearest-neighbour still needs the winner to resemble *something*.
_FLOOR = 0.60


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def tokens(text: str) -> list[str]:
    return [ACTIVE.number_words.get(w, w) for w in normalise(text).split()]


def stem(word: str) -> str:
    """Crude suffix stripper so "make" and "making" compare equal."""
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            word = word[: -len(suffix)]
            break
    return word[:-1] if len(word) > 3 and word.endswith("e") else word


def content_tokens(text: str) -> set[str]:
    return {stem(t) for t in tokens(text) if t not in ACTIVE.filler}


def _content_string(text: str) -> str:
    return " ".join(t for t in tokens(text) if t not in ACTIVE.filler)


def phonetic_key(text: str) -> str:
    """Phonetic code of the content words, run together.

    Speech recognition splits and joins words unpredictably ("mitochondria" ->
    "might o chondria"), so we drop word boundaries before coding.
    """
    return ACTIVE.phonetic(_content_string(text).replace(" ", ""))


def has_negation(text: str) -> bool:
    return bool(ACTIVE.negations & set(tokens(text)))


@dataclass(frozen=True)
class _Prepared:
    """One string, reduced to the three forms the comparison needs."""
    raw: str        # normalised
    content: str    # content words only, spaces stripped
    key: str        # phonetic code


@lru_cache(maxsize=4096)
def _prepare(text: str) -> _Prepared:
    """Reduce a string once.

    Every answer is compared against every candidate in the study set - 42 of
    them for a thirteen-card set - and the candidate texts are the same on every
    single call. Recomputing the normalisation and the metaphone code per
    comparison made grading scale with the size of the set for no reason.
    """
    return _Prepared(
        raw=normalise(text),
        content=_content_string(text).replace(" ", ""),
        key=phonetic_key(text),
    )


def _similarity(said: _Prepared, target: _Prepared) -> float:
    scores = [
        SequenceMatcher(None, said.raw, target.raw).ratio(),
        SequenceMatcher(None, said.content, target.content).ratio(),
    ]
    if said.key and target.key:
        scores.append(
            1.0 if said.key == target.key
            else SequenceMatcher(None, said.key, target.key).ratio()
        )
    return max(scores)


def similarity(said: str, target: str) -> float:
    """How likely is it that the student uttered `target`?

    Maximum of a spelling comparison and a sound comparison: the first catches
    typed or cleanly-recognised answers, the second catches phonetic mangling.
    """
    return _similarity(_prepare(said), _prepare(target))


@dataclass(frozen=True)
class Candidate:
    """One answer the student might plausibly have said."""
    text: str
    correct: bool
    card_id: str | None = None
    note: str | None = None      # misconception line, when this is a known wrong turn


@dataclass(frozen=True)
class Grade:
    correct: bool
    rung: str                    # which comparison decided it - measured, not assumed
    score: float
    margin: float
    matched: Candidate | None


def grade(response: str, candidates: list[Candidate]) -> Grade:
    """Attribute a spoken response to the nearest candidate answer."""
    if not (response or "").strip():
        return Grade(False, "empty", 0.0, 0.0, None)

    # "It's not the nucleus" contains the keyword but asserts the opposite.
    if has_negation(response):
        return Grade(False, "negated", 0.0, 0.0, None)

    said_set = content_tokens(response)
    said_prepared = _prepare(response)

    def best_of(correct: bool) -> tuple[float, Candidate | None]:
        pool = [c for c in candidates if c.correct is correct]
        if not pool:
            return 0.0, None
        return max(
            ((_similarity(said_prepared, _prepare(c.text)), c) for c in pool),
            key=lambda p: p[0],
        )

    # Fast path: the student said an answer verbatim, or wrapped it in filler
    # ("I think it's the mitochondria"). Prefer a correct candidate when several
    # match, so alternative phrasings of the right answer never lose to a wrong one.
    said_norm = normalise(response)
    verbatim = [
        c for c in candidates
        if normalise(c.text) and (said_norm == normalise(c.text) or normalise(c.text) in said_norm)
    ]
    if verbatim:
        winner = max(verbatim, key=lambda c: (c.correct, len(c.text)))
        return Grade(winner.correct, "exact", 1.0, 1.0, winner)

    # All content words of an answer present is strong evidence on its own.
    subsets = [c for c in candidates if content_tokens(c.text) and content_tokens(c.text) <= said_set]
    if subsets:
        winner = max(subsets, key=lambda c: (c.correct, len(content_tokens(c.text))))
        return Grade(winner.correct, "token_subset", 1.0, 1.0, winner)

    # Nearest neighbour, but the comparison that decides the verdict is between
    # the best RIGHT answer and the best WRONG one. Ranking the top two
    # candidates outright is wrong: two phrasings of the same correct answer
    # ("mitochondria" and "the mitochondria") both score 1.0, cancel each other
    # out, and a correct student gets told they were not understood.
    right_score, right = best_of(True)
    wrong_score, wrong = best_of(False)

    top_score = max(right_score, wrong_score)
    margin = abs(right_score - wrong_score)

    if top_score < _FLOOR:
        return Grade(False, "ambiguous", top_score, margin, right or wrong)
    if margin < _MARGIN:
        # The student is equally close to a right and a wrong answer. Saying
        # "correct" here would be a coin flip; ask them to repeat instead.
        return Grade(False, "ambiguous", top_score, margin, wrong or right)

    if right_score > wrong_score:
        return Grade(True, "nearest", right_score, margin, right)
    return Grade(False, "nearest", wrong_score, margin, wrong)
