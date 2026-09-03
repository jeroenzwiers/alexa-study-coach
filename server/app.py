"""Study Coach - an Alexa+ add-on served as an MCP server.

Alexa+ supplies the conversation and the reasoning; this server supplies the
tools and, crucially, the *judgement about whether an answer was right*. That
judgement is deterministic and local (see grading.py), because the platform
budget is a 500 ms round trip and a model call would spend all of it.

Three things sit on top of that judgement, and none of them is available to a
quiz that records one bit per answer:

    diagnosis    which wrong concept was reached for, and whether it keeps
                 coming back (store.Session.record_confusion)
    resolution   whether a confusion has since been settled, which is the only
                 good news a revision session can honestly deliver
                 (store.Session.record_success)
    adaptation   whether to push, hold or ease off, read from how the answer
                 arrived rather than only from whether it was right (adaptive.py)

...and underneath all three, a memory of the student across sessions
(history.py), so a confusion left open last week is the first thing settled this
week.

Every tool result is written to be SPOKEN. Short sentences, no markup, no lists
a voice cannot read aloud, and the next question always arrives in the same turn
so the student is never left waiting in silence.
"""

from __future__ import annotations

import os
import random
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from mcp.server.apps import Apps, ResourceCsp
from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import JSONResponse

import adaptive
import history as profiles
import store
import ui
from grading import grade

PUBLIC_URL = os.environ.get("PUBLIC_URL", "http://localhost:8421")


class PracticeTurn(BaseModel):
    """One turn of a practice session.

    `speech` is the only field Alexa+ needs to read aloud; the rest lets the
    assistant reason about where the student is without re-asking the server.
    """

    speech: str = Field(description="Exactly what to say to the student.")
    session_id: str | None = Field(default=None, description="Pass this to submit_answer.")
    question_number: int | None = Field(default=None, description="1-based position in the session.")
    total_questions: int | None = Field(default=None, description="How many questions this session has.")
    correct: bool | None = Field(default=None, description="Whether the answer just given was right.")
    finished: bool = Field(default=False, description="True when no questions remain.")
    grading_rung: str | None = Field(
        default=None,
        description="Which comparison decided the grade: exact, token_subset, nearest, ambiguous, negated or empty.",
    )

    # Structured fields for a screen device. The voice experience needs only
    # `speech`; these let a display show the same turn without re-parsing it.
    question: str | None = Field(default=None, description="The question being asked, on its own.")
    verdict: str | None = Field(default=None, description="correct, incorrect or unclear.")
    heard_as: str | None = Field(default=None, description="The concept the student's answer was attributed to.")
    correct_answer: str | None = Field(default=None, description="The expected answer, once revealed.")
    contrast: list[str] | None = Field(default=None, description="Two confused concepts being separated.")
    confusion_count: int | None = Field(default=None, description="How often this confusion has appeared.")

    # The moment a confusion stops being a confusion.
    resolved_confusion: list[str] | None = Field(
        default=None, description="Two concepts the student has just told apart twice running."
    )
    resolved_total: int = Field(default=0, description="Confusions settled in this session so far.")

    # How the session is adapting to the student, rather than to the score.
    difficulty: int | None = Field(default=None, description="Level of the question being asked, 1 to 3.")
    momentum: str | None = Field(default=None, description="ease, hold or stretch - where the session is heading.")
    support: str | None = Field(default=None, description="none, hint or options - how much help this question carries.")
    returning: bool = Field(default=False, description="True when this student has practised this set before.")


# The screen half. Additive: a speaker with no display loses only the picture.
apps = Apps()


@apps.tool(
    resource_uri="ui://study-coach/practice.html",
    title="Start practice",
    description=(
        "Start a practice session for a study set and return the first question. "
        "Returns a session id that must be passed to submit_answer. Pass `student` "
        "when you know who is practising, so the session can pick up the "
        "confusions they left unsettled last time."
    ),
)
def start_practice(
    study_set_id: str,
    length: int | None = None,
    student: str = "default",
) -> PracticeTurn:
    if study_set_id not in store.STUDY_SETS:
        known = ", ".join(store.STUDY_SETS) or "none"
        return PracticeTurn(speech=f"I do not have that set. I have {known}.")

    study_set = store.STUDY_SETS[study_set_id]

    # What we remember about this student decides how the session opens, what it
    # asks first, and how hard it starts.
    saved = profiles.load(student)
    greeting, carried_pair = profiles.opening(saved, study_set)
    carried_count = 0
    if carried_pair:
        entry = profiles.open_confusions(saved, study_set_id).get(
            "|".join(store.pair_key(*carried_pair)), {}
        )
        carried_count = int(entry.get("count", 0))

    session = store.start_session(
        study_set_id,
        length,
        student=student,
        difficulty=profiles.carried_difficulty(saved, study_set_id),
        carried_pair=carried_pair,
        carried_count=carried_count,
    )

    card = study_set.card(session.current)
    prompt, contrast_pair, support = _ask(session, study_set, card, 1)

    if greeting:
        speech = f"{greeting} {prompt}"
    else:
        speech = f"Let's revise {study_set.title}. {prompt}"

    return PracticeTurn(
        session_id=session.id,
        question_number=1,
        total_questions=session.total_questions,
        question=card.question,
        speech=speech,
        difficulty=card.difficulty,
        momentum="hold",
        support=support,
        contrast=contrast_pair,
        returning=session.returning,
    )


@apps.tool(
    resource_uri="ui://study-coach/practice.html",
    title="Submit answer",
    description=(
        "Grade the student's spoken answer to the current question and return "
        "feedback plus the next question. Pass the transcript exactly as heard, "
        "including any hesitation - the filler words are signal here. "
        "Optionally pass a short `manner` note describing what the student DID, "
        "as plain observable behaviour: 'long pause before answering', 'asked "
        "to stop', 'answered instantly', 'started over twice', 'went quiet'. "
        "Describe behaviour only - do not report or guess at the student's "
        "emotions or mood, which this tool neither wants nor uses. The session "
        "adapts without `manner`; it adapts better with it."
    ),
)
def submit_answer(session_id: str, response: str, manner: str | None = None) -> PracticeTurn:
    session = store.SESSIONS.get(session_id)
    if session is None:
        return PracticeTurn(speech="That practice session has expired. Shall we start again?")
    if session.current is None:
        return PracticeTurn(speech="That session is already finished.", finished=True)

    study_set = store.STUDY_SETS[session.study_set_id]
    card = study_set.card(session.current)
    was_contrast = session.pending_contrast is not None
    session.pending_contrast = None   # cleared here so a newly queued one survives

    # Read the student before grading the answer: how it arrived is independent
    # of whether it was right, and the raw transcript is the evidence.
    signals = adaptive.read_signals(
        response,
        question=card.question,
        elapsed_ms=session.elapsed_ms(),
        manner=manner,
    )
    verdict = grade(response, study_set.candidates_for(card.id))

    session.asked += 1
    heard_as = None
    revealed = None
    settled: list[tuple[str, str]] = []

    if verdict.correct:
        session.correct += 1
        session.correct_streak += 1
        session.wrong_streak = 0

        # Did that just settle something? Two right answers on both sides of a
        # confusion is the distinction holding, not a lucky recognition.
        settled = session.record_success(card.id)
        if settled:
            feedback = _settled_line(study_set, session, settled[0])
        elif was_contrast:
            feedback = "Exactly - that's the difference."
        else:
            feedback = "That's right."
    else:
        session.correct_streak = 0
        session.wrong_streak += 1
        session.missed.append(card.id)
        said_card = verdict.matched.card_id if verdict.matched else None

        # A repeated wrong attribution is a misconception, not a slip. When one
        # emerges, the session stops drawing random cards and drills the contrast.
        pair = session.record_confusion(card.id, said_card)
        if pair is not None:
            store.queue_contrast(session, pair)
        elif said_card:
            # Not yet a pattern - but now worth finding out whether the swap
            # goes both ways, rather than hoping the shuffle asks.
            store.probe(session, said_card)

        said = study_set.card(said_card) if said_card else None
        heard_as = said.canonical.rstrip(".") if said is not None else None
        if verdict.rung in ("ambiguous", "empty"):
            # Never guess at a half-heard answer - ask, or give the answer plainly.
            feedback = f"I didn't quite catch that. The answer is {card.canonical}"
            revealed = card.canonical.rstrip(".")
            heard_as = None
        elif said is not None and pair is not None:
            # A contrast question is coming next, so withhold the answer -
            # revealing it here would leave nothing to distinguish.
            feedback = f"Not quite - that's {_spoken(said.canonical)}."
        elif said is not None:
            revealed = card.canonical.rstrip(".")
            # We know WHICH concept was reached for, so name it. A flashcard app
            # has one bit here - right or wrong - and can only ever say "no".
            feedback = (
                f"Not quite - that's {_spoken(said.canonical)}. "
                f"{card.misconception} The answer is {card.canonical}"
            )
        else:
            feedback = f"Not quite. The answer is {card.canonical}"
            revealed = card.canonical.rstrip(".")

    # Where the session goes next: harder, easier, or steady - decided from how
    # the student is coping rather than from the score alone.
    adjustment = adaptive.update(
        correct=verdict.correct,
        signals=signals,
        strain=session.strain,
        correct_streak=session.correct_streak,
        wrong_streak=session.wrong_streak,
        difficulty=session.difficulty,
        scaffold=session.scaffold,
    )
    session.strain = adjustment.strain
    session.difficulty = adjustment.difficulty
    session.scaffold = adjustment.scaffold
    session.last_direction_of_travel = adjustment.direction
    if adjustment.direction == "stretch":
        # The streak bought this step up; it must not buy the next one too.
        session.correct_streak = 0
    if settled:
        # Settling a confusion is the strongest possible evidence the student is
        # back on their feet; do not let an old strain reading outlive it.
        session.strain = max(0.0, session.strain - 0.25)

    next_id = store.advance(session)
    dominant = session.dominant_confusion()

    common = dict(
        session_id=session.id,
        correct=verdict.correct,
        grading_rung=verdict.rung,
        verdict=_verdict_word(verdict),
        heard_as=heard_as,
        correct_answer=revealed,
        confusion_count=dominant[1] if dominant else None,
        resolved_confusion=_pair_names(study_set, session, settled[0]) if settled else None,
        resolved_total=len(session.resolved),
        momentum=adjustment.direction,
        returning=session.returning,
    )

    if next_id is None:
        _remember(session)
        return PracticeTurn(
            finished=True,
            speech=f"{feedback} That was the last one. {_score_line(session)}",
            difficulty=card.difficulty,
            **common,
        )

    next_card = study_set.card(next_id)
    number = session.asked + 1
    prompt, contrast_pair, support = _ask(session, study_set, next_card, number)

    # Only announce a change of gear when there is one, and never on top of the
    # news that a confusion has just been settled - one thing at a time.
    aside = adjustment.line if (adjustment.direction != "hold" and not settled) else None
    speech = " ".join(part for part in (feedback, aside, prompt) if part)

    return PracticeTurn(
        finished=False,
        question_number=number,
        total_questions=session.total_questions,
        question=next_card.question,
        speech=speech,
        contrast=contrast_pair,
        difficulty=next_card.difficulty,
        support=support,
        **common,
    )


# --- how a question gets asked -------------------------------------------

def _ask(session, study_set, card, number: int) -> tuple[str, list[str] | None, str]:
    """Phrase the next question at the current level of support.

    Three rungs, and they are not decoration: a student who is struggling gets a
    genuinely easier task, not the same task said more kindly.
    """
    # A queued contrast outranks everything - it is the diagnostic drill, and it
    # already has the right pair of options.
    if session.pending_contrast is not None:
        asked_card, said_card = session.pending_contrast
        if asked_card == card.id:
            confused = study_set.card(said_card)
            if confused is not None:
                options = [_spoken(card.canonical), _spoken(confused.canonical)]
                random.shuffle(options)
                return (
                    f"Let's separate those two. {card.question} "
                    f"Is it {options[0]}, or {options[1]}?",
                    options,
                    "options",
                )

    if session.scaffold >= 2:
        other = _distractor(study_set, card)
        if other is not None:
            options = [_spoken(card.canonical), _spoken(other.canonical)]
            random.shuffle(options)
            return (
                f"Question {number}. {card.question} Is it {options[0]}, or {options[1]}?",
                options,
                "options",
            )

    if session.scaffold == 1:
        return f"Question {number}. {card.question} {card.spoken_hint()}", None, "hint"

    return f"Question {number}. {card.question}", None, "none"


def _distractor(study_set, card):
    """A plausible wrong option: another answer at a similar level.

    Drawn from the same closed candidate set the grader works over, so a student
    who picks the distractor is still telling us something we can attribute.
    """
    others = [c for c in study_set.cards if c.id != card.id]
    if not others:
        return None
    nearest = min(abs(c.difficulty - card.difficulty) for c in others)
    return random.choice([c for c in others if abs(c.difficulty - card.difficulty) == nearest])


# --- speech helpers -------------------------------------------------------

def _settled_line(study_set, session, key: tuple[str, str]) -> str:
    """The sentence this whole design exists to be able to say."""
    asked_id, said_id = session.named_pair(key)
    asked, said = study_set.card(asked_id), study_set.card(said_id)
    if asked is None or said is None:
        return "That's right."
    key = store.pair_key(asked_id, said_id)
    if session.carried_pair and key == store.pair_key(*session.carried_pair):
        # This is the one they came back for. Saying "twice tonight" about
        # misses made last week would be a small lie in the one sentence that
        # most needs to be true.
        return (
            f"Yes - and that settles it. {_spoken(asked.canonical).capitalize()} and "
            f"{_spoken(said.canonical)} are the pair you came back to, and you've "
            f"just had them both right. That one's done."
        )
    times = session.confusions.get(key, 0)
    return (
        f"Yes - and that's the pair sorted. You had {_spoken(asked.canonical)} and "
        f"{_spoken(said.canonical)} the wrong way round {_count(times)} tonight, and "
        f"you've just had them both right. That one's done."
    )


def _count(n: int) -> str:
    """Spoken counts. "2 times" is not something a person says out loud."""
    return {1: "once", 2: "twice", 3: "three times"}.get(n, f"{n} times")


def _pair_names(study_set, session, key: tuple[str, str]) -> list[str] | None:
    asked_id, said_id = session.named_pair(key)
    asked, said = study_set.card(asked_id), study_set.card(said_id)
    if asked is None or said is None:
        return None
    return [asked.canonical.rstrip("."), said.canonical.rstrip(".")]


def _verdict_word(verdict) -> str:
    if verdict.correct:
        return "correct"
    return "unclear" if verdict.rung in ("ambiguous", "empty") else "incorrect"


def _spoken(canonical: str) -> str:
    """A canonical answer as it should sound inside a sentence: no full stop,
    no sentence-initial capital."""
    text = canonical.strip().rstrip(".")
    return text[:1].lower() + text[1:] if text else text


def _score_line(session) -> str:
    line = f"You got {session.correct} out of {session.asked}."
    if session.resolved:
        n = len(session.resolved)
        return f"{line} And you settled {n} confusion{'s' if n != 1 else ''} on the way."
    return line


def _remember(session) -> None:
    """Write the diagnosis to the student's profile. Called once, at the end.

    Deliberately outside the answering path: this is the only filesystem touch
    in the server, and it happens on the one turn that has no next question to
    get back to in time.
    """
    try:
        saved = profiles.load(session.student)
        study_set = store.STUDY_SETS.get(session.study_set_id)
        profiles.remember(saved, session, study_set)
        profiles.save(saved)
    except OSError:
        pass   # a session that cannot be filed is still a session worth finishing


apps.add_html_resource(
    "ui://study-coach/practice.html",
    ui.PRACTICE_HTML,
    title="Study Coach",
    description="The current question, and - when a confusion keeps recurring - the two concepts side by side.",
    csp=ResourceCsp(resource_domains=["https://cdn.jsdelivr.net"]),
    prefers_border=True,
)

server = MCPServer(
    name="study-coach",
    title="Study Coach",
    version="0.2.0",
    instructions=(
        "Helps a student revise their own course material out loud. Use "
        "list_study_sets to see what is available, start_practice to begin, and "
        "submit_answer for each spoken reply. Read tool results aloud as given - "
        "they are already phrased for speech. Never reveal the expected answer "
        "before the student has attempted the question. Pass the student's name "
        "to start_practice when you know it, and tell submit_answer how the "
        "student sounded when it is worth noting - the session uses both."
    ),
    extensions=[apps],
)


@server.tool(
    title="List study sets",
    description="List the study sets this student can practise, with subject and length.",
)
def list_study_sets() -> str:
    if not store.STUDY_SETS:
        return "There are no study sets loaded yet."
    parts = [
        f"{s.title} in {s.subject}, {len(s.cards)} questions"
        for s in store.STUDY_SETS.values()
    ]
    if len(parts) == 1:
        return f"You have one set ready: {parts[0]}."
    return "You can practise " + "; ".join(parts[:-1]) + f"; or {parts[-1]}."


@server.tool(
    title="Explain",
    description="Explain the concept behind a question the student got wrong, in one or two spoken sentences.",
)
def explain(study_set_id: str, card_id: str) -> str:
    study_set = store.STUDY_SETS.get(study_set_id)
    card = study_set.card(card_id) if study_set else None
    if card is None:
        return "I could not find that question."
    return card.explanation


@server.tool(
    title="Session summary",
    description="Report how a practice session went and what still needs work.",
)
def session_summary(session_id: str) -> str:
    session = store.SESSIONS.get(session_id)
    if session is None:
        return "I no longer have that session."
    if session.asked == 0:
        return "You haven't answered anything in that session yet."

    study_set = store.STUDY_SETS[session.study_set_id]
    line = f"You answered {session.correct} of {session.asked} correctly."

    if session.resolved:
        pairs = [_pair_names(study_set, session, key) for key in session.resolved]
        named = [f"{p[0].lower()} and {p[1].lower()}" for p in pairs if p]
        if named:
            line += " You sorted out " + _topics_from(named) + "."

    if not session.missed:
        return line + " Nothing left to review."
    unsettled = [
        cid for cid in dict.fromkeys(session.missed)
        if not any(cid in key for key in session.resolved)
    ]
    if not unsettled:
        return line + " Nothing still open."
    return f"{line} Worth another look: {_topics(study_set, unsettled)}."


@server.tool(
    title="Tutor report",
    description=(
        "Summarise a finished session for a parent or tutor: not just a score, "
        "but which specific confusion the errors share, if any, and which ones "
        "the student has now settled."
    ),
)
def tutor_report(session_id: str) -> str:
    session = store.SESSIONS.get(session_id)
    if session is None:
        return "I no longer have that session."
    if session.asked == 0:
        return "There is nothing to report yet."

    study_set = store.STUDY_SETS[session.study_set_id]
    parts = [f"{session.correct} out of {session.asked} on {study_set.title}."]

    for key in session.resolved:
        names = _pair_names(study_set, session, key)
        if names:
            parts.append(
                f"One confusion was settled during the session: "
                f"{names[0].lower()} against {names[1].lower()}, "
                f"answered correctly from both sides at the end."
            )
            break

    dominant = session.dominant_confusion()
    if dominant is None:
        if session.missed and not session.resolved:
            parts.append(
                f"The misses were spread out: {_topics(study_set, session.missed)}. No single pattern."
            )
        elif not session.missed:
            parts.append("No errors to explain.")
    else:
        (asked_card, said_card), count = dominant
        asked = study_set.card(asked_card)
        said = study_set.card(said_card)
        if asked is not None and said is not None:
            # This is the sentence a score cannot give you.
            parts.append(
                f"The errors are not spread out. "
                f"{count} of them are the same confusion: when asked about "
                f"{asked.canonical.rstrip('.').lower()}, the answer given was "
                f"{said.canonical.rstrip('.').lower()}. "
                f"{asked.misconception} Worth going over that distinction directly."
            )

    if session.last_direction_of_travel == "ease" or session.strain >= adaptive.STRAINED:
        parts.append(
            "The session was eased off towards the end - the answers were "
            "getting slower and less certain, so it stepped down a level rather "
            "than pressing on."
        )
    elif session.difficulty >= adaptive.MAX_DIFFICULTY:
        parts.append("It was going in easily enough that the questions were stepped up.")

    return " ".join(parts)


@server.tool(
    title="Student progress",
    description=(
        "How a student is doing on a study set across all their sessions so far: "
        "which confusions they have settled for good, and which are still open."
    ),
)
def student_progress(student: str = "default", study_set_id: str = "") -> str:
    saved = profiles.load(student)
    if study_set_id in store.STUDY_SETS:
        sets = [store.STUDY_SETS[study_set_id]]
    else:
        sets = list(store.STUDY_SETS.values())
    lines = [profiles.summary(saved, s) for s in sets]
    lines = [line for line in lines if not line.startswith("No practice recorded")]
    if not lines:
        return "I have no practice history for that student yet."
    return " ".join(lines)


@server.tool(
    title="Class report",
    description=(
        "For a teacher or tutor: which confusions keep coming up across ALL the "
        "students who have practised a study set, how many have settled them, "
        "and whether the swap goes both ways or mostly one way. Aggregate only - "
        "it reports counts, never who."
    ),
)
def class_report(study_set_id: str = "", minimum: int | None = None) -> str:
    study_set = store.STUDY_SETS.get(study_set_id) or next(iter(store.STUDY_SETS.values()), None)
    if study_set is None:
        return "There are no study sets loaded yet."

    floor = profiles.MIN_STUDENTS if minimum is None else max(1, minimum)
    studied, confusions = profiles.topic_map(study_set.id)

    if not studied:
        return f"No one has practised {study_set.title} yet."

    who = f"{_number(studied)} student{'s' if studied != 1 else ''}"
    shared = [c for c in confusions if c.students >= floor]
    if not shared:
        return (
            f"{who.capitalize()} {'have' if studied != 1 else 'has'} practised "
            f"{study_set.title}. No confusion is shared by more than "
            f"{_number(floor - 1)} of them yet."
        )

    top = shared[0]
    parts = [
        f"{who.capitalize()} {'have' if studied != 1 else 'has'} practised "
        f"{study_set.title}.",
        f"One confusion stands out: {_pair_phrase(study_set, top)}."
        if len(shared) > 1 else f"One confusion is shared: {_pair_phrase(study_set, top)}.",
    ]

    # The asymmetry is the teachable part. "They confuse these two" tells you to
    # revise both; "they nearly all answer diffusion when asked about osmosis"
    # tells you which half of the distinction is missing.
    lopsided = top.dominant_direction()
    if lopsided is not None:
        (asked_id, said_id), count = lopsided
        asked, said = study_set.card(asked_id), study_set.card(said_id)
        if asked is not None and said is not None:
            parts.append(
                f"{_number(count).capitalize()} of them go the same way: asked "
                f"about {asked.canonical.rstrip('.').lower()}, they answer "
                f"{said.canonical.rstrip('.').lower()}."
            )
    elif top.directions:
        parts.append("It goes both ways round in roughly equal numbers.")

    if top.settled_students:
        parts.append(
            f"{_number(top.settled_students).capitalize()} "
            f"{'have' if top.settled_students != 1 else 'has'} since settled it."
        )

    if len(shared) > 1:
        rest = [
            f"{_pair_phrase(study_set, c)}"
            for c in shared[1:3]
        ]
        parts.append("Also recurring: " + _topics_from(rest) + ".")

    return " ".join(parts)


def _pair_phrase(study_set, confusion) -> str:
    """A confusion named, with how many students have met it."""
    a, b = (study_set.card(cid) for cid in confusion.pair)
    if a is None or b is None:
        return "an answer no longer in this set"
    return (
        f"{a.canonical.rstrip('.').lower()} and {b.canonical.rstrip('.').lower()}, "
        f"{_number(confusion.students)} student{'s' if confusion.students != 1 else ''}"
    )


_NUMBER_WORDS = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve",
)


def _number(n: int) -> str:
    """Small counts as words. A voice saying "7" sounds like a form, not a person."""
    return _NUMBER_WORDS[n] if 0 <= n < len(_NUMBER_WORDS) else str(n)


def _topics(study_set, card_ids: list[str]) -> str:
    names = [study_set.card(cid).canonical.rstrip(".") for cid in card_ids if study_set.card(cid)]
    return _topics_from(names)


def _topics_from(names: list[str]) -> str:
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + f", and {names[-1]}"


# --- Endpoints the Alexa+ MCP Toolkit requires -----------------------------
# The toolkit expects 401 on unauthenticated calls and OAuth metadata at a
# well-known path. Local development runs open; AUTH_REQUIRED turns the gate on
# so we can verify the real behaviour before deploying.

@server.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])
async def oauth_metadata(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "issuer": PUBLIC_URL,
            "authorization_endpoint": f"{PUBLIC_URL}/oauth/authorize",
            "token_endpoint": f"{PUBLIC_URL}/oauth/token",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "scopes_supported": ["study.read", "study.practise"],
        }
    )


@server.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    return JSONResponse({"ok": True, "study_sets": list(store.STUDY_SETS)})


app = server.streamable_http_app(streamable_http_path="/mcp", json_response=True)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8421")), log_level="warning")
