"""A judge-facing Alexa+-style shell backed by the real MCP server."""

from __future__ import annotations

import os
import pathlib
import sys
import uuid

import anyio
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

ROOT = pathlib.Path(__file__).resolve().parents[1]
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


async def run_demo() -> dict:
    events: list[dict] = []
    student = f"demo_{uuid.uuid4().hex[:10]}"
    contrast_seen = False
    first_mistake_seen = False
    contrast_started = False

    async with streamable_http_client(MCP_URL) as (read, write):
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
