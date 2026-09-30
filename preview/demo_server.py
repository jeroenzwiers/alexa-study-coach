"""A judge-facing Alexa+-style shell backed by the real MCP server."""

from __future__ import annotations

import os
import pathlib
import sys
import uuid

import anyio
from mcp.client.session import ClientSession
from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))
import auth  # noqa: E402  - needs ROOT on the path first

MCP_URL = os.environ.get("MCP_URL", "http://127.0.0.1:8421/mcp")

ANSWERS = {
    "cell membrane control": "what goes in and out",
    "shape and support": "cell wall",
    "genetic material": "nucleus",
    "job of a ribosome": "to make proteins",
    "inside the nucleus": "the nucleolus",
    "movement of water": "osmosis",
    "movement of particles": "diffusion",
    "stores cell sap": "the vacuole",
    "chemical reactions": "cytoplasm",
    "no nucleus": "a prokaryotic cell",
    "packages proteins": "the golgi apparatus",
}


# The second act. Biology proves the mechanism; this proves it was never about
# biology. The pair is chosen for the audience: authentication and authorization
# is the confusion every engineer in the room has explained to a junior.
CS_ANSWERS = {
    "overlapping time periods": "concurrency",
    "multiple processors": "parallelism",
    "last in, first out": "the stack",
    "dynamically allocated": "the heap",
    "translates an entire source": "a compiler",
    "translates and executes": "an interpreter",
    "protected ciphertext": "encryption",
    "one-way digest": "hashing",
    "recently used data": "a cache",
    "durable retrieval": "a database",
}
CS_IDENTITY = "verifies that a user"
CS_PERMISSION = "decides which actions"


def cs_answer(question: str, mirrored: bool) -> str:
    """Scripted learner speech for the cut-in: the pair wrong, everything else right."""
    lowered = (question or "").lower()
    if CS_IDENTITY in lowered:
        return "authorization"
    if CS_PERMISSION in lowered:
        return "authentication"
    for cue, answer in CS_ANSWERS.items():
        if cue in lowered:
            return answer
    return "i dont know"


def payload(result) -> dict:
    return dict(result.structured_content or {})


def learner_answer(
    question: str,
    contrast: list[str] | None,
    first_mistake_seen: bool,
    contrast_seen: bool,
) -> str:
    """Supply scripted learner speech; all tutoring decisions stay on the MCP server."""
    lowered = (question or "").lower()
    if contrast:
        if "captures light" in lowered:
            return "chloroplasts"
        return "mitochondria"
    if "releases energy" in lowered:
        return "the mitochondria" if contrast_seen else "chloroplasts"
    if "captures light" in lowered:
        return "chloroplasts" if not first_mistake_seen else "mitochondria"
    for cue, answer in ANSWERS.items():
        if cue in lowered:
            return answer
    return "i dont know"


async def run_cs_cutin(client, events: list[dict]) -> None:
    """Two beats on a second subject: the same pair mechanism, no new code."""
    student = f"__demo_{uuid.uuid4().hex[:10]}__"
    turn = None
    for _ in range(32):
        result = await client.call_tool(
            "start_practice",
            {"study_set_id": "computer_science_fundamentals", "length": 12, "student": student},
        )
        candidate = payload(result)
        if CS_IDENTITY in candidate.get("question", "").lower():
            turn = candidate
            break
    if turn is None:
        raise RuntimeError("Could not select the deterministic authentication demo start")

    events.append({
        "kind": "subject",
        "state": "SECOND SUBJECT",
        "title": "Computer Science Fundamentals",
        "text": "Same server, same machinery, a different subject.",
    })

    mirrored = False
    for _ in range(24):
        if turn.get("finished"):
            break
        asked = turn.get("question", "")
        answer = cs_answer(asked, mirrored)
        result = await client.call_tool(
            "submit_answer", {"session_id": turn["session_id"], "response": answer}
        )
        turn = payload(result)
        lowered = asked.lower()
        if CS_IDENTITY in lowered:
            mirrored = True
            events.append({
                "kind": "answer",
                "state": "ANSWER_RECEIVED · ATTRIBUTED_TO",
                "asked_question": asked,
                "answer": answer,
                "turn": turn,
            })
        elif CS_PERMISSION in lowered:
            events.append({
                "kind": "answer",
                "state": "CONFUSION_DETECTED · CONTRAST_PROBE"
                if turn.get("contrast")
                else "ANSWER_RECEIVED · ATTRIBUTED_TO",
                "asked_question": asked,
                "answer": answer,
                "turn": turn,
            })
            if turn.get("contrast"):
                return


async def run_demo() -> dict:
    events: list[dict] = []
    # Marked synthetic (history.SYNTHETIC_MARKER): a rehearsal of the demo must
    # not add a pupil to the class report the demo goes on to show.
    student = f"__demo_{uuid.uuid4().hex[:10]}__"
    contrast_seen = False
    first_mistake_seen = False
    contrast_started = False

    async with auth.connect(MCP_URL) as (read, write):
        async with ClientSession(read, write) as client:
            initialized = await client.initialize()
            tool_list = await client.list_tools()
            events.append({
                "kind": "protocol",
                "protocol": str(client.protocol_version),
                "transport": "Streamable HTTP",
                "tools": [tool.name for tool in tool_list.tools],
                "server": initialized.server_info.name,
            })

            turn = None
            for _ in range(32):
                result = await client.call_tool(
                    "start_practice",
                    {"study_set_id": "biology_cells", "length": 13, "student": student},
                )
                candidate = payload(result)
                if "releases energy" in candidate.get("question", "").lower():
                    turn = candidate
                    break
            if turn is None:
                raise RuntimeError("Could not select the deterministic mitochondria demo start")
            events.append({"kind": "start", "state": "QUESTION", "turn": turn})

            for _ in range(24):
                if turn.get("finished"):
                    break
                asked_question = turn.get("question", "")
                answer = learner_answer(
                    asked_question, turn.get("contrast"), first_mistake_seen, contrast_seen
                )
                result = await client.call_tool(
                    "submit_answer",
                    {"session_id": turn["session_id"], "response": answer},
                )
                turn = payload(result)
                if turn.get("contrast"):
                    contrast_started = True
                    contrast_seen = True
                if "releases energy" in asked_question.lower() and answer == "chloroplasts":
                    first_mistake_seen = True
                state = "ANSWER_RECEIVED"
                if turn.get("heard_as"):
                    state += " · ATTRIBUTED_TO"
                if turn.get("contrast"):
                    state = "CONFUSION_DETECTED · CONTRAST_PROBE"
                elif contrast_started and turn.get("verdict") == "correct":
                    if "releases energy" in asked_question.lower():
                        state = "SIDE_A_MASTERED"
                    elif "captures light" in asked_question.lower():
                        state = "SIDE_B_MASTERED"
                if turn.get("resolved_confusion"):
                    state = f"{state} · CONFUSION_RESOLVED"
                events.append({
                    "kind": "answer",
                    "state": state,
                    "asked_question": asked_question,
                    "answer": answer,
                    "turn": turn,
                })

            progress = await client.call_tool(
                "student_progress",
                {"student": student, "study_set_id": "biology_cells"},
            )
            events.append({
                "kind": "persistence",
                "state": "PERSISTED_STATE",
                "text": next(
                    (block.text for block in progress.content if getattr(block, "type", None) == "text"),
                    "",
                ),
            })

            restarted = await client.call_tool(
                "start_practice",
                {"study_set_id": "biology_cells", "length": 1, "student": student},
            )
            events.append({"kind": "restart", "state": "PERSISTED_STATE", "turn": payload(restarted)})

            await run_cs_cutin(client, events)

            # The third act. The same confusions, summed over everyone who
            # studied the set, stop being a fact about one student. The
            # population is seeded by preview/seed_class.py and is fabricated;
            # the narration says so, and the synthetic runs above are excluded
            # from it by history.is_synthetic rather than by hoping.
            report = await client.call_tool("class_report", {"study_set_id": "biology_cells"})
            events.append({
                "kind": "class",
                "state": "CLASS_REPORT · SIMULATED COHORT",
                "text": next(
                    (b.text for b in report.content if getattr(b, "type", None) == "text"),
                    "",
                ),
            })

    return {"events": events, "mcp_url": MCP_URL}


async def index(request) -> HTMLResponse:
    page = (ROOT / "preview" / "demo.html").read_text(encoding="utf-8")
    return HTMLResponse(page)


async def demo(request) -> JSONResponse:
    try:
        return JSONResponse(await run_demo())
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)


app = Starlette(routes=[
    Route("/", index),
    Route("/api/demo", demo, methods=["POST"]),
])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("DEMO_PORT", "8430")))
