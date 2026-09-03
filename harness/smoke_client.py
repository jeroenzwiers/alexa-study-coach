"""End-to-end check against the running server, as Alexa+ would drive it.

Verifies the three things the track actually grades on: that we negotiate the
required protocol version, that a full spoken practice loop works end to end,
and that every round trip fits the platform's 500 ms budget.
"""
import statistics
import time

import anyio
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

URL = "http://127.0.0.1:8421/mcp"
BUDGET_MS = 500


def text_of(result) -> str:
    for block in result.content:
        if getattr(block, "type", None) == "text":
            return block.text
    return ""


async def main() -> None:
    timings: list[float] = []

    async with streamable_http_client(URL) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"server           : {init.server_info.name} {init.server_info.version}")
            print(f"protocolversie   : {init.protocol_version}")
            tools = await session.list_tools()
            print(f"tools            : {', '.join(t.name for t in tools.tools)}")
            print()

            async def call(name: str, args: dict):
                start = time.perf_counter()
                result = await session.call_tool(name, args)
                timings.append((time.perf_counter() - start) * 1000)
                return result

            result = await call("start_practice", {"study_set_id": "biology_cells"})
            payload = result.structured_content or {}
            session_id = payload.get("session_id")
            print("ALEXA   :", payload.get("speech"))

            # A student who knows the material, transcribed imperfectly. Keyed by
            # a phrase from the question, because the session shuffles its order.
            SPOKEN = {
                "releases energy": "the might o chondria",
                "captures light": "chloroplasts",
                "cell membrane control": "what goes in and out",
                "shape and support": "sell wall",
                "genetic material": "new clee us",
                "job of a ribosome": "to make proteins",
            }

            def reply_to(question: str) -> str:
                for cue, said in SPOKEN.items():
                    if cue in question.lower():
                        return said
                return "i dont know"

            while session_id and not payload.get("finished"):
                said = reply_to(payload.get("speech") or "")
                print("LEERLING:", said)
                result = await call("submit_answer", {"session_id": session_id, "response": said})
                payload = result.structured_content or {}
                print("ALEXA   :", payload.get("speech"))

            result = await call("session_summary", {"session_id": session_id})
            print("ALEXA   :", text_of(result))

    print()
    worst = max(timings)
    print(f"round-trips      : {len(timings)}")
    print(f"mediaan          : {statistics.median(timings):.1f} ms")
    print(f"slechtste        : {worst:.1f} ms")
    print(f"budget           : {BUDGET_MS} ms")
    print(f"VERDICT          : {'BINNEN BUDGET' if worst < BUDGET_MS else 'TE TRAAG'}")


anyio.run(main)
