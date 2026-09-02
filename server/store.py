"""Study sets and practice sessions.

Content is plain JSON on disk: one file per study set, the shape a teacher's
worksheet turns into. Sessions live in memory for local development; on Lambda
they move to DynamoDB keyed by the MCP session id (week 5 - see PLAN.md).
"""

from __future__ import annotations

import json
import pathlib
import random
import uuid
from collections import Counter
from dataclasses import dataclass, field

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


@dataclass
class Session:
    id: str
    study_set_id: str
    queue: list[str]
    asked: int = 0
    correct: int = 0
    missed: list[str] = field(default_factory=list)
    current: str | None = None

    # The diagnosis. A flashcard app records one bit per answer - right or wrong.
    # Because grading attributes a spoken answer to a specific candidate, we can
    # record WHICH wrong concept was reached for, and a repeated pair is a
    # misconception rather than a slip.
    confusions: Counter = field(default_factory=Counter)   # unordered pair -> count
    last_direction: dict = field(default_factory=dict)     # pair -> (asked, said)
    contrasts_done: set = field(default_factory=set)
    pending_contrast: tuple | None = None

    @property
    def finished(self) -> bool:
        return self.current is None and not self.queue

    def record_confusion(self, asked_card: str, said_card: str) -> tuple[str, str] | None:
        """Log a wrong attribution; return it if it has become a pattern.

        Counted as an UNORDERED pair. Answering "chloroplast" when asked about
        mitochondria and "mitochondria" when asked about chloroplasts is one
        misconception seen from both sides, not two unrelated slips - and the
        pair of them is stronger evidence than either alone.
        """
        if not said_card or said_card == asked_card:
            return None
        key = tuple(sorted((asked_card, said_card)))
        self.confusions[key] += 1
        self.last_direction[key] = (asked_card, said_card)
        if self.confusions[key] >= CONFUSION_THRESHOLD and key not in self.contrasts_done:
            return (asked_card, said_card)
        return None

    def dominant_confusion(self) -> tuple[tuple[str, str], int] | None:
        """The confusion the errors keep returning to, if there is one."""
        if not self.confusions:
            return None
        key, count = self.confusions.most_common(1)[0]
        if count < CONFUSION_THRESHOLD:
            return None
        return self.last_direction.get(key, key), count


SESSIONS: dict[str, Session] = {}


def start_session(study_set_id: str, length: int | None = None) -> Session:
    study_set = STUDY_SETS[study_set_id]
    order = [c.id for c in study_set.cards]
    random.shuffle(order)
    if length:
        order = order[:length]
    session = Session(id=uuid.uuid4().hex[:12], study_set_id=study_set_id, queue=order)
    session.current = session.queue.pop(0) if session.queue else None
    SESSIONS[session.id] = session
    return session


def advance(session: Session) -> str | None:
    session.current = session.queue.pop(0) if session.queue else None
    return session.current


def queue_contrast(session: Session, pair: tuple[str, str]) -> None:
    """Put the confused card back next, to be asked as a direct contrast.

    Discrimination practice: rather than moving on and hoping, ask the same
    question again with the two confused answers named side by side, so the
    student has to separate them instead of recognising one.
    """
    asked_card, said_card = pair
    session.contrasts_done.add(tuple(sorted((asked_card, said_card))))
    session.queue.insert(0, asked_card)
    session.pending_contrast = pair
