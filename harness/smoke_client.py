"""End-to-end check against the running server, as Alexa+ would drive it.

Verifies the things the track actually grades on: that we negotiate the required
protocol version, that a full spoken practice loop works over the wire, that the
diagnosis survives the round trip - and that every call fits the platform's
500 ms budget, including the turn that writes the student's profile to disk.

Drives a student who has two concepts the wrong way round, is drilled on the
contrast, and settles it. The `manner` argument is passed on some turns exactly
as Alexa+ would pass it, and left off on others, because it has to be optional.
"""
import statistics
import time

import anyio
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

URL = "http://127.0.0.1:8421/mcp"
BUDGET_MS = 500
# Marked synthetic (history.SYNTHETIC_MARKER), so this run persists like any
# student - which is the point, the progress line below reads it back - but in
# the scratch directory, and never as a pupil in a class report.
STUDENT = "__smoke__"


def text_of(result) -> str:
    for block in result.content:
        if getattr(block, "type", None) == "text":
            return block.text
    return ""


# A student who knows the material, transcribed imperfectly - except for the two
# organelles they have back to front, until the contrast question sorts it out.
SPOKEN = {
    "cell membrane control": "what goes in and out",
    "shape and support": "sell wall",
    "genetic material": "new clee us",
    "job of a ribosome": "to make proteins",
    "inside the nucleus": "the nucleolus",
    "movement of water": "os mosis",
    "movement of particles": "diffusion",
    "stores cell sap": "the vacuole",
    "chemical reactions": "site oh plasm",
    "no nucleus": "a pro carry ottic cell",
    "packages proteins": "the goal gee apparatus",
}
SWAPPED = {"releases energy": "chloroplasts", "captures light": "mitochondria"}
LEARNT = {"releases energy": "the might o chondria", "captures light": "chloroplasts"}


def reply_to(question: str, taught: bool) -> str:
    lowered = (question or "").lower()
    for cue, said in {**SPOKEN, **(LEARNT if taught else SWAPPED)}.items():
        if cue in lowered:
            return said
    return "i dont know"


async def main() -> None:
    timings: list[float] = []
    saw_contrast = False
    saw_resolution = False

    async with streamable_http_client(URL) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"server           : {init.server_info.name} {init.server_info.version}")
            print(f"protocolversie   : {init.protocol_version}")
            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print(f"tools            : {', '.join(names)}")
            print()

            async def call(name: str, args: dict):
                start = time.perf_counter()
                result = await session.call_tool(name, args)
                timings.append((time.perf_counter() - start) * 1000)
                return result

            # The whole deck, not a sample of it. This run has to reach the
            # contrast and the resolution to prove anything, and a shorter
            # session leaves that to the shuffle: the two swapped organelles
            # simply may not come up, and the smoke test then fails for no
            # reason but bad luck. The client cannot seed the server's shuffle,
            # so it asks for every card instead.
            result = await call(
                "start_practice",
                {"study_set_id": "biology_cells", "length": 13, "student": STUDENT},
            )
            payload = result.structured_content or {}
            session_id = payload.get("session_id")
            print("ALEXA   :", payload.get("speech"))

            taught = False
            turns = 0
            while session_id and not payload.get("finished") and turns < 24:
                turns += 1
                said = reply_to(payload.get("question") or payload.get("speech"), taught)
                print("LEERLING:", said)

                # Alexa+ heard the student; sometimes it has something to say
                # about how. The server must cope either way.
                args = {"session_id": session_id, "response": said}
                if turns == 1:
                    args["manner"] = "steady, no hesitation"

                result = await call("submit_answer", args)
                payload = result.structured_content or {}
                print("ALEXA   :", payload.get("speech"))

                if payload.get("resolved_confusion"):
                    saw_resolution = True
                    print("          >>> OPGELOST:", " / ".join(payload["resolved_confusion"]))
                if "separate those two" in (payload.get("speech") or "").lower():
                    saw_contrast = True
                    taught = True

            result = await call("session_summary", {"session_id": session_id})
            print()
            print("SAMENVATTING:", text_of(result))
            result = await call("tutor_report", {"session_id": session_id})
            print("RAPPORT     :", text_of(result))
            result = await call(
                "student_progress",
                {"student": STUDENT, "study_set_id": "biology_cells"},
            )
            print("VOORTGANG   :", text_of(result))

    worst = max(timings)
    checks = {
        "protocolversie 2025-11-25": str(init.protocol_version) == "2025-11-25",
        "acht tools aangeboden": len(names) == 8,
        "student_progress bestaat": "student_progress" in names,
        "class_report bestaat": "class_report" in names,
        "sessie afgerond": bool(payload.get("finished")),
        "contrastvraag over de lijn": saw_contrast,
        "verwarring opgelost gemeld": saw_resolution,
        f"elke round-trip onder {BUDGET_MS} ms": worst < BUDGET_MS,
    }
    print()
    print(f"round-trips      : {len(timings)}")
    print(f"mediaan          : {statistics.median(timings):.1f} ms")
    print(f"slechtste        : {worst:.1f} ms")
    print(f"budget           : {BUDGET_MS} ms")
    print()
    for label, ok in checks.items():
        print(f"  {'OK  ' if ok else 'FOUT'} {label}")
    print()
    print("VERDICT          :", "GESLAAGD" if all(checks.values()) else "GEZAKT")
    raise SystemExit(0 if all(checks.values()) else 1)


anyio.run(main)
