"""Study Coach - an Alexa+ add-on served as an MCP server.

Alexa+ supplies the conversation and the reasoning; this server supplies the
tools and, crucially, the *judgement about whether an answer was right*. That
judgement is deterministic and local (see grading.py), because the platform
budget is a 500 ms round trip and a model call would spend all of it.

Every tool result is written to be SPOKEN. Short sentences, no markup, no lists
a voice cannot read aloud, and the next question always arrives in the same
turn so the student is never left waiting in silence.
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

import store
import ui
from grading import grade

PUBLIC_URL = os.environ.get("PUBLIC_URL", "http://localhost:8080")


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

# The screen half. Additive: a speaker with no display loses only the picture.
apps = Apps()

@apps.tool(
    resource_uri="ui://study-coach/practice.html",
    title="Start practice",
    description=(
        "Start a practice session for a study set and return the first question. "
        "Returns a session id that must be passed to submit_answer."
    ),
)
def start_practice(study_set_id: str, length: int | None = None) -> PracticeTurn:
    if study_set_id not in store.STUDY_SETS:
        known = ", ".join(store.STUDY_SETS) or "none"
        return PracticeTurn(speech=f"I do not have that set. I have {known}.")

    session = store.start_session(study_set_id, length)
    study_set = store.STUDY_SETS[study_set_id]
    card = study_set.card(session.current)
    return PracticeTurn(
        session_id=session.id,
        question_number=1,
        total_questions=len(session.queue) + 1,
        question=card.question,
        speech=f"Let's revise {study_set.title}. Question one. {card.question}",
    )


@apps.tool(
    resource_uri="ui://study-coach/practice.html",
    title="Submit answer",
    description=(
        "Grade the student's spoken answer to the current question and return "
        "feedback plus the next question. Pass the transcript exactly as heard."
    ),
)
def submit_answer(session_id: str, response: str) -> PracticeTurn:
    session = store.SESSIONS.get(session_id)
    if session is None:
        return PracticeTurn(speech="That practice session has expired. Shall we start again?")
    if session.current is None:
        return PracticeTurn(speech="That session is already finished.", finished=True)

    study_set = store.STUDY_SETS[session.study_set_id]
    card = study_set.card(session.current)
    was_contrast = session.pending_contrast is not None
    session.pending_contrast = None   # cleared here so a newly queued one survives
    verdict = grade(response, study_set.candidates_for(card.id))

    session.asked += 1
    heard_as = None
    revealed = None
    if verdict.correct:
        session.correct += 1
        feedback = "Exactly - that's the difference." if was_contrast else "That's right."
    else:
        session.missed.append(card.id)
        said_card = verdict.matched.card_id if verdict.matched else None

        # A repeated wrong attribution is a misconception, not a slip. When one
        # emerges, the session stops drawing random cards and drills the contrast.
        pair = session.record_confusion(card.id, said_card)
        if pair is not None:
            store.queue_contrast(session, pair)

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

    next_id = store.advance(session)

    dominant = session.dominant_confusion()

    if next_id is None:
        return PracticeTurn(
            session_id=session.id,
            correct=verdict.correct,
            finished=True,
            speech=f"{feedback} That was the last one. {_score_line(session)}",
            grading_rung=verdict.rung,
            verdict=_verdict_word(verdict),
            heard_as=heard_as,
            correct_answer=revealed,
            confusion_count=dominant[1] if dominant else None,
        )

    next_card = study_set.card(next_id)
    number = session.asked + 1

    # If a contrast was queued for this card, ask it as a contrast: both answers
    # named, so the student must separate them rather than recognise one.
    prompt = f"Question {number}. {next_card.question}"
    contrast_pair = None
    if session.pending_contrast is not None:
        asked_card, said_card = session.pending_contrast
        if asked_card == next_id:
            confused = study_set.card(said_card)
            if confused is not None:
                options = [_spoken(next_card.canonical), _spoken(confused.canonical)]
                random.shuffle(options)
                prompt = (
                    f"Let's separate those two. {next_card.question} "
                    f"Is it {options[0]}, or {options[1]}?"
                )
                session.pending_contrast = (asked_card, said_card)
                contrast_pair = options

    return PracticeTurn(
        session_id=session.id,
        correct=verdict.correct,
        finished=False,
        question_number=number,
        total_questions=session.asked + len(session.queue) + 1,
        question=next_card.question,
        speech=f"{feedback} {prompt}",
        grading_rung=verdict.rung,
        verdict=_verdict_word(verdict),
        heard_as=heard_as,
        correct_answer=revealed,
        contrast=contrast_pair,
        confusion_count=dominant[1] if dominant else None,
    )


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
    return f"You got {session.correct} out of {session.asked}."



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
    version="0.1.0",
    instructions=(
        "Helps a student revise their own course material out loud. Use "
        "list_study_sets to see what is available, start_practice to begin, and "
        "submit_answer for each spoken reply. Read tool results aloud as given - "
        "they are already phrased for speech. Never reveal the expected answer "
        "before the student has attempted the question."
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
    if not session.missed:
        return line + " Nothing left to review."
    topics = [study_set.card(cid).canonical.rstrip(".") for cid in session.missed]
    if len(topics) == 1:
        return f"{line} Worth another look: {topics[0]}."
    return f"{line} Worth another look: " + ", ".join(topics[:-1]) + f", and {topics[-1]}."


@server.tool(
    title="Tutor report",
    description=(
        "Summarise a finished session for a parent or tutor: not just a score, "
        "but which specific confusion the errors share, if any."
    ),
)
def tutor_report(session_id: str) -> str:
    session = store.SESSIONS.get(session_id)
    if session is None:
        return "I no longer have that session."
    if session.asked == 0:
        return "There is nothing to report yet."

    study_set = store.STUDY_SETS[session.study_set_id]
    line = f"{session.correct} out of {session.asked} on {study_set.title}."

    dominant = session.dominant_confusion()
    if dominant is None:
        if session.missed:
            topics = _topics(study_set, session.missed)
            return f"{line} The misses were spread out: {topics}. No single pattern."
        return f"{line} No errors to explain."

    (asked_card, said_card), count = dominant
    asked = study_set.card(asked_card)
    said = study_set.card(said_card)
    if asked is None or said is None:
        return line

    # This is the sentence a score cannot give you.
    return (
        f"{line} The errors are not spread out. "
        f"{count} of them are the same confusion: when asked about "
        f"{asked.canonical.rstrip('.').lower()}, the answer given was "
        f"{said.canonical.rstrip('.').lower()}. "
        f"{asked.misconception} Worth going over that distinction directly."
    )


def _topics(study_set, card_ids: list[str]) -> str:
    names = [study_set.card(cid).canonical.rstrip(".") for cid in card_ids if study_set.card(cid)]
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

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8080")), log_level="warning")
