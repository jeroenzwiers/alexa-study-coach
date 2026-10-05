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
    # Concepts from this subject that a student reaches for INSTEAD, and that
    # this study set has no card for. Without them the grader has nowhere to put
    # such an answer: nearest-neighbour over the cards alone hands "the mode" to
    # the median and calls it right, and the student walks away uncorrected.
    # Declaring them makes the closed set closed over the classroom's vocabulary
    # rather than over the deck's.
    near_misses: list[str] = field(default_factory=list)

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
    # Which pairs the set's author declared confusable. Loaded because the
    # support scaffold has to offer the student a REAL distinction to choose
    # between; picking any card of similar difficulty offered "the perimeter,
    # or the coefficient", which is a free mark handed out at the exact moment
    # the session decided the student needed help.
    confusable_pairs: list[tuple[str, str]] = field(default_factory=list)

    def confusable_with(self, card_id: str) -> list[str]:
        return [
            b if a == card_id else a
            for a, b in self.confusable_pairs
            if card_id in (a, b)
        ]

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
            # Named wrong answers with no card of their own. `card_id=None` is
            # what marks them: the answer is wrong, and there is no pair to
            # record, because the student did not confuse two cards - they
            # reached outside the set entirely.
            for phrasing in card.near_misses:
                out.append(Candidate(text=phrasing, correct=False, card_id=None))
        return out


def _load(path: pathlib.Path) -> StudySet:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return StudySet(
        id=raw["id"],
        subject=raw["subject"],
        title=raw["title"],
        level=raw.get("level", ""),
        confusable_pairs=[
            (pair[0], pair[1])
            for pair in raw.get("confusable_pairs", []) or []
            if len(pair) == 2
        ],
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
                near_misses=list(c.get("near_misses", []) or []),
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

# The most a session may grow beyond the length it promised. Drilling is meant
# to lengthen a session, but `planned` only ever gated the drawing of FRESH
# cards: forced contrast questions and probes bypassed it entirely, so a student
# who kept missing could be held indefinitely - sessions of two hundred
# questions, and closed loops of the same six. A revision session that has
# doubled has stopped being the session the student agreed to, and whatever is
# still unresolved at that point belongs in the report rather than in one more
# question.
MAX_SESSION_MULTIPLE = 2

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
    closing: bool = False                             # draining owed probes, taking no new ones
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
    written: Counter = field(default_factory=Counter)       # ...and how much is already on disk
    persisted: bool = False                                 # has this session been filed at all
    last_direction: dict = field(default_factory=dict)     # pair -> (asked, said)
    contested: set = field(default_factory=set)            # pairs being drilled now
    resolved: set = field(default_factory=set)             # pairs settled this session
    pair_streak: Counter = field(default_factory=Counter)  # consecutive corrects per pair
    successful_sides: dict = field(default_factory=dict)   # pair -> card ids answered correctly
    contrast_rounds: Counter = field(default_factory=Counter)
    pending_contrast: tuple | None = None

    # Seeded for synthetic students so a demo repeats; None means the real
    # module-level random, which is what a real student gets.
    rng: random.Random | None = None

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
    def ceiling(self) -> int:
        """The hard stop, however much drilling is still outstanding."""
        return max(1, self.planned) * MAX_SESSION_MULTIPLE

    @property
    def total_questions(self) -> int:
        return min(self.planned + self.bonus, self.ceiling)

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
        self.successful_sides[key] = set() # both sides must be demonstrated in sequence
        self.resolved.discard(key)         # and un-settles it if it had been settled

        ripe = self.confusions[key] >= CONFUSION_THRESHOLD
        room = self.contrast_rounds[key] < MAX_CONTRAST_ROUNDS

        # Only a drill that is actually in flight should block another one.
        # `contested` cannot answer that question: it also means "this pair is
        # being tracked for resolution", and a confusion carried in from a
        # previous session is put there before any drill has run. Gating on it
        # made the carried pair unreachable - the student came back still
        # confused, missed it again, and the drill that exists for exactly that
        # moment could never fire. MAX_CONTRAST_ROUNDS is what limits repeats.
        drilling = (
            self.pending_contrast is not None
            and pair_key(*self.pending_contrast) == key
        )
        if ripe and room and not drilling:
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
            sides = self.successful_sides.setdefault(key, set())
            sides.add(card_id)
            if len(sides) == len(key) and self.pair_streak[key] >= RESOLVE_STREAK:
                self.contested.discard(key)
                self.resolved.add(key)
                settled.append(key)
        return settled

    def fresh_confusion_count(self, key: tuple[str, str]) -> int:
        """Times this pair was missed THIS session, excluding what it arrived with.

        `start_session` seeds a carried confusion's counter so the drill treats
        it as already ripe, and `seeded` records how much of the count came in
        that way. The total is the right number for "mixed up N times so far";
        it is the wrong number for any sentence about tonight, where the seed
        would be counted as errors the student did not just make.
        """
        return max(0, self.confusions[key] - self.seeded.get(key, 0))

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

def _pick_by_difficulty(pool: list[str], study_set: StudySet, target: int,
                        rng: random.Random | None = None) -> str:
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
    return (rng or random).choice(tied)


# Only the demo. Synthetic students in general - the smoke client, the
# generalization sweep, test_memory - want the real shuffle, because a test that
# always draws the same cards in the same order stops testing the shuffle. An
# earlier version of this seeded every synthetic session and broke two suites
# whose scenarios depend on the draw.
DEMO_MARKER = "__demo_"


def _reproducible(student: str) -> bool:
    return (student or "").startswith(DEMO_MARKER)


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
    # A demo session is reproducible. The recorded audio is keyed to the exact
    # sentences the session speaks, and a reshuffled filler question changes the
    # words and orphans a recording - so the shuffle and every later tie-break
    # run off a seeded generator. Everyone else keeps the real shuffle: being
    # asked the same cards in the same order every evening is not revision.
    rng = random.Random(f"{study_set_id}:{length}:{student}") if _reproducible(student) else None
    (rng or random).shuffle(pool)

    # Clamped at both ends. Alexa+ passes through whatever it understood the
    # student to have asked for, so a negative length is a thing that arrives,
    # and it used to leave the session with no first card and crash the tool.
    planned = max(1, min(length or DEFAULT_LENGTH, len(pool)))
    session = Session(
        id=uuid.uuid4().hex[:12],
        study_set_id=study_set_id,
        student=student,
        pool=pool,
        planned=planned,
        difficulty=max(adaptive.MIN_DIFFICULTY, min(adaptive.MAX_DIFFICULTY, difficulty)),
        returning=carried_pair is not None or carried_count > 0,
        rng=rng,
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
    if session.asked >= session.ceiling:
        # Nothing outranks the ceiling - not a forced drill, not an owed probe.
        session.current = None
        session.asked_at = None
        return None

    due = next((item for item in session.deferred if session.asked >= item[0]), None)
    if session.forced:
        session.current = session.forced.pop(0)
    elif due is not None:
        session.deferred.remove(due)
        session.current = due[1]
    elif session.asked >= session.planned or not session.pool:
        # The session has reached its length or run out of fresh cards, but a
        # probe may still be outstanding: the other side of a suspected
        # confusion, pulled from the pool and promised a turn a couple of
        # questions downstream that never arrived. Ending here would abandon
        # the very diagnosis the probe exists to make - a miss late in the
        # session would silently never be tested both ways round - so a
        # question we already owe is asked before the session closes.
        if session.deferred:
            session.closing = True     # honour what is owed, but take on nothing new
            session.deferred.sort(key=lambda item: item[0])
            _, session.current = session.deferred.pop(0)
            if session.asked >= session.planned:
                session.bonus += 1     # owed beyond the planned length
        else:
            session.current = None
    else:
        study_set = STUDY_SETS[session.study_set_id]
        session.current = _pick_by_difficulty(
            session.pool, study_set, session.difficulty, session.rng
        )
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
    if session.closing:
        # The session is already asking the questions it owes and is on its way
        # out. A student who keeps getting the pair wrong would otherwise
        # schedule a fresh probe on every drained turn and the session would
        # never end. What is still unresolved belongs in the report, not in one
        # more question.
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
    session.successful_sides[key] = set()

    session.deferred = [item for item in session.deferred if item[1] not in pair]
    for cid in (said_card, asked_card):        # inserted in reverse: asked goes first
        if cid in session.pool:
            session.pool.remove(cid)
        session.forced.insert(0, cid)
        session.bonus += 1

    session.pending_contrast = pair
