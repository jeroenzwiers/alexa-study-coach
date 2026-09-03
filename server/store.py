"""Study sets and practice sessions.

Content is plain JSON on disk: one file per study set, the shape a teacher's
worksheet turns into. Sessions live in memory for the length of one practice;
what survives it is the diagnosis, written to a student profile (see history.py)
so the next session can open where this one left off.
"""

from __future__ import annotations

import json
import pathlib
import random
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field

import adaptive
from grading import Candidate

CONTENT_DIR = pathlib.Path(__file__).resolve().parents[1] / "content"


@dataclass(frozen=True)
class Card:
    id: str
    question: str
    accepted: list[str]
    canonical: str
    explanation: str
    misconception: str
    difficulty: int = 2
    hint: str = ""

    def spoken_hint(self) -> str:
        """A nudge for a struggling student that does not hand over the answer."""
        if self.hint:
            return self.hint
        first = (self.canonical.lstrip("The ").lstrip("A ").strip() or "?")[0]
        return f"It starts with {first.upper()}."


@dataclass(frozen=True)
class StudySet:
    id: str
    subject: str
    title: str
    level: str
    cards: list[Card]

    def card(self, card_id: str) -> Card | None:
        return next((c for c in self.cards if c.id == card_id), None)

    def candidates_for(self, card_id: str) -> list[Candidate]:
        """Every answer in this set, labelled correct only for the asked card.

        This closed set is what makes grading a nearest-neighbour decision
        instead of an impossible similarity threshold - see grading.py.
        """
        out: list[Candidate] = []
        for card in self.cards:
            is_target = card.id == card_id
            for phrasing in card.accepted:
                out.append(
                    Candidate(
                        text=phrasing,
                        correct=is_target,
                        card_id=card.id,
                        note=None if is_target else card.misconception,
                    )
                )
        return out


def _load(path: pathlib.Path) -> StudySet:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return StudySet(
        id=raw["id"],
        subject=raw["subject"],
        title=raw["title"],
        level=raw.get("level", ""),
        cards=[
            Card(
                id=c["id"],
                question=c["question"],
                accepted=c["accepted"],
                canonical=c["canonical"],
                explanation=c["explanation"],
                misconception=c.get("misconception", ""),
                difficulty=int(c.get("difficulty", 2)),
                hint=c.get("hint", ""),
            )
            for c in raw["cards"]
        ],
    )


STUDY_SETS: dict[str, StudySet] = {
    s.id: s for s in (_load(p) for p in sorted(CONTENT_DIR.glob("*.json")))
}


# How many times a student must reach for the same wrong concept before we stop
# treating it as a slip and start treating it as a confusion worth addressing.
CONFUSION_THRESHOLD = 2

# ...and how many times they must then get it right, in a row, before we call it
# settled. Two, because one is the contrast question itself - answering that
# correctly shows recognition, and the mirrored question afterwards is what
# shows the distinction actually holds.
RESOLVE_STREAK = 2

# A confusion that returns after being drilled is worth drilling again, but not
# forever; past this the session stops nagging and leaves it for the report.
MAX_CONTRAST_ROUNDS = 2

DEFAULT_LENGTH = 8


def pair_key(a: str, b: str) -> tuple[str, str]:
    """A confusion as an unordered pair.

    Answering "chloroplast" when asked about mitochondria and "mitochondria"
    when asked about chloroplasts is one misconception seen from both sides, not
    two unrelated slips - and the pair of them is stronger evidence than either
    alone.
    """
    return tuple(sorted((a, b)))   # type: ignore[return-value]


@dataclass
class Session:
    id: str
    study_set_id: str
    student: str = "default"

    pool: list[str] = field(default_factory=list)     # not yet asked
    forced: list[str] = field(default_factory=list)   # ask these next, whatever the level
    deferred: list = field(default_factory=list)      # (ask once asked >= n, card id)
    planned: int = DEFAULT_LENGTH
    bonus: int = 0                                    # extra turns added by drilling
    asked: int = 0
    correct: int = 0
    missed: list[str] = field(default_factory=list)
    current: str | None = None

    # The diagnosis. A flashcard app records one bit per answer - right or wrong.
    # Because grading attributes a spoken answer to a specific candidate, we can
    # record WHICH wrong concept was reached for, and a repeated pair is a
    # misconception rather than a slip.
    confusions: Counter = field(default_factory=Counter)   # pair -> times seen
    seeded: Counter = field(default_factory=Counter)        # of which, carried in from before
    last_direction: dict = field(default_factory=dict)     # pair -> (asked, said)
    contested: set = field(default_factory=set)            # pairs being drilled now
    resolved: set = field(default_factory=set)             # pairs settled this session
    pair_streak: Counter = field(default_factory=Counter)  # consecutive corrects per pair
    contrast_rounds: Counter = field(default_factory=Counter)
    pending_contrast: tuple | None = None

    # How the student is coping, not just how they are scoring - see adaptive.py.
    difficulty: int = 1
    scaffold: int = 0
    strain: float = 0.0
    correct_streak: int = 0
    wrong_streak: int = 0
    asked_at: float | None = None      # when the current question was handed over
    last_direction_of_travel: str = "hold"

    # Carried in from a previous session, if there was one.
    returning: bool = False
    carried_pair: tuple | None = None

    @property
    def finished(self) -> bool:
        return self.current is None

    @property
    def total_questions(self) -> int:
        return self.planned + self.bonus

    def elapsed_ms(self) -> float | None:
        if self.asked_at is None:
            return None
        return (time.monotonic() - self.asked_at) * 1000.0

    # --- the diagnosis ----------------------------------------------------

    def record_confusion(self, asked_card: str, said_card: str) -> tuple[str, str] | None:
        """Log a wrong attribution; return it if it has become a pattern."""
        if not said_card or said_card == asked_card:
            return None
        key = pair_key(asked_card, said_card)
        self.confusions[key] += 1
        self.last_direction[key] = (asked_card, said_card)
        self.pair_streak[key] = 0          # a miss breaks any run towards resolved
        self.resolved.discard(key)         # and un-settles it if it had been settled

        ripe = self.confusions[key] >= CONFUSION_THRESHOLD
        room = self.contrast_rounds[key] < MAX_CONTRAST_ROUNDS
        if ripe and room and key not in self.contested:
            return (asked_card, said_card)
        return None

    def record_success(self, card_id: str) -> list[tuple[str, str]]:
        """Credit a correct answer against any confusion it belongs to.

        Returns the pairs this answer has just settled. That list is the whole
        point: a session that can only ever report what went wrong
        has no moment worth staying for.
        """
        settled: list[tuple[str, str]] = []
        for key in list(self.contested):
            if card_id not in key:
                continue
            self.pair_streak[key] += 1
            if self.pair_streak[key] >= RESOLVE_STREAK:
                self.contested.discard(key)
                self.resolved.add(key)
                settled.append(key)
        return settled

    def dominant_confusion(self) -> tuple[tuple[str, str], int] | None:
        """The confusion the errors keep returning to, if one is still open."""
        candidates = [
            (key, count)
            for key, count in self.confusions.most_common()
            if count >= CONFUSION_THRESHOLD and key not in self.resolved
        ]
        if not candidates:
            return None
        key, count = candidates[0]
        return self.last_direction.get(key, key), count

    def named_pair(self, key: tuple[str, str]) -> tuple[str, str]:
        return self.last_direction.get(key, key)


SESSIONS: dict[str, Session] = {}


# --- choosing what to ask next -------------------------------------------

def _pick_by_difficulty(pool: list[str], study_set: StudySet, target: int) -> str:
    """The unasked card closest to the target level, ties broken at random.

    Not a filter: a session must never stall because the student's level has no
    cards left in it. Nearest-available degrades gracefully to "whatever is left".
    """
    best = min(
        (abs((study_set.card(cid).difficulty if study_set.card(cid) else 2) - target) for cid in pool),
        default=0,
    )
    tied = [
        cid for cid in pool
        if abs((study_set.card(cid).difficulty if study_set.card(cid) else 2) - target) == best
    ]
    return random.choice(tied)


def start_session(
    study_set_id: str,
    length: int | None = None,
    student: str = "default",
    difficulty: int = 1,
    carried_pair: tuple[str, str] | None = None,
    carried_count: int = 0,
) -> Session:
    study_set = STUDY_SETS[study_set_id]
    pool = [c.id for c in study_set.cards]
    random.shuffle(pool)

    planned = min(length or DEFAULT_LENGTH, len(pool))
    session = Session(
        id=uuid.uuid4().hex[:12],
        study_set_id=study_set_id,
        student=student,
        pool=pool,
        planned=planned,
        difficulty=max(adaptive.MIN_DIFFICULTY, min(adaptive.MAX_DIFFICULTY, difficulty)),
        returning=carried_pair is not None or carried_count > 0,
    )

    # A confusion the student left open last time is not a fresh question - it is
    # unfinished business, so it goes first and starts already contested, with
    # its history intact. Two right answers now settle it for good.
    if carried_pair and all(study_set.card(cid) for cid in carried_pair):
        key = pair_key(*carried_pair)
        session.carried_pair = carried_pair
        session.confusions[key] = max(carried_count, CONFUSION_THRESHOLD)
        session.seeded[key] = session.confusions[key]
        session.last_direction[key] = carried_pair
        session.contested.add(key)
        session.contrast_rounds[key] = 1
        for cid in carried_pair:
            if cid in session.pool:
                session.pool.remove(cid)
        session.forced = list(carried_pair)

    SESSIONS[session.id] = session
    advance(session)
    return session


def advance(session: Session) -> str | None:
    """Set the next question: forced drilling first, then level-matched.

    Deliberately does not touch `pending_contrast`: queue_contrast sets it
    immediately before this runs, and the turn that consumes it clears it.
    """
    due = next((item for item in session.deferred if session.asked >= item[0]), None)
    if session.forced:
        session.current = session.forced.pop(0)
    elif due is not None:
        session.deferred.remove(due)
        session.current = due[1]
    elif session.asked >= session.planned or not session.pool:
        session.current = None
    else:
        study_set = STUDY_SETS[session.study_set_id]
        session.current = _pick_by_difficulty(session.pool, study_set, session.difficulty)
        session.pool.remove(session.current)

    session.asked_at = time.monotonic() if session.current else None
    return session.current


def probe(session: Session, card_id: str, delay: int = 2) -> None:
    """Ask the other side of a suspected confusion, shortly.

    One wrong attribution is not yet evidence - the pair only becomes a
    diagnosis when the student swaps the two concepts BOTH ways round. Whether
    that ever gets tested should not be left to the shuffle, and adaptive
    difficulty makes it worse: a student who is being stepped up may never meet
    the easier half of the pair again.

    Deliberately not asked immediately. Straight after the miss it would test
    what the student heard ten seconds ago rather than what they understand, so
    it goes a couple of questions downstream.
    """
    if card_id == session.current or card_id in session.forced:
        return
    if any(cid == card_id for _, cid in session.deferred):
        return
    if card_id in session.pool:
        session.pool.remove(card_id)     # it was going to be asked anyway
    else:
        session.bonus += 1               # a genuine extra turn
    session.deferred.append((session.asked + delay, card_id))


def queue_contrast(session: Session, pair: tuple[str, str]) -> None:
    """Drill a confusion from both sides, starting now.

    Discrimination practice: ask the missed question again with the two confused
    answers named side by side, then ask the OTHER concept straight after. One
    right answer is recognition; both is the distinction actually holding, which
    is what `record_success` is waiting for.
    """
    asked_card, said_card = pair
    key = pair_key(asked_card, said_card)
    session.contested.add(key)
    session.contrast_rounds[key] += 1
    session.pair_streak[key] = 0

    session.deferred = [item for item in session.deferred if item[1] not in pair]
    for cid in (said_card, asked_card):        # inserted in reverse: asked goes first
        if cid in session.pool:
            session.pool.remove(cid)
        session.forced.insert(0, cid)
        session.bonus += 1

    session.pending_contrast = pair
