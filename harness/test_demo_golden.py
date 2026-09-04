"""Deterministic golden run for the judge-facing MCP-backed demo."""

from __future__ import annotations

import inspect
import pathlib
import sys

import anyio

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "preview"))
import demo_server


def run() -> dict:
    return anyio.run(demo_server.run_demo)


def main() -> int:
    result = run()
    events = result["events"]
    answers = [event for event in events if event["kind"] == "answer"]
    wrong_a = next(
        event for event in answers
        if "releases energy" in event["asked_question"].lower()
        and event["answer"] == "chloroplasts"
    )
    wrong_b = next(
        event for event in answers
        if "captures light" in event["asked_question"].lower()
        and event["answer"] == "mitochondria"
    )
    mastery = [
        event for event in answers
        if "SIDE_A_MASTERED" in event["state"] or "SIDE_B_MASTERED" in event["state"]
    ]
    first_mastery, second_mastery = mastery[:2]
    persisted = next(event for event in events if event["kind"] == "persistence")
    restarted = next(event for event in events if event["kind"] == "restart")

    checks = {
        "MCP protocol is 2025-11-25": events[0]["protocol"] == "2025-11-25",
        "transport is Streamable HTTP": events[0]["transport"] == "Streamable HTTP",
        "tools/list is real": len(events[0]["tools"]) == 8,
        "first wrong answer is attributed to chloroplasts": (
            wrong_a["turn"]["heard_as"] == "The chloroplasts"
        ),
        "mirrored wrong answer is attributed to mitochondria": (
            wrong_b["turn"]["heard_as"] == "The mitochondria"
        ),
        "confusion is detected and contrast is scheduled": (
            any(event["state"] == "CONFUSION_DETECTED · CONTRAST_PROBE" for event in answers)
        ),
        "first distinct correct side does not resolve": (
            first_mastery["turn"].get("resolved_confusion") is None
        ),
        "second distinct correct side resolves": (
            first_mastery["state"] != second_mastery["state"]
            and bool(second_mastery["turn"].get("resolved_confusion"))
        ),
        "persisted result is read from the server": (
            "settled for good" in persisted["text"].lower()
        ),
        "restart restores server context": "welcome back" in restarted["turn"]["speech"].lower(),
        "demo does not contain domain implementation": not any(
            name in inspect.getsource(demo_server)
            for name in ("from grading", "record_confusion", "queue_contrast", "topic_map", "history.save")
        ),
        "critical path does not pass manner": "manner" not in inspect.getsource(demo_server.run_demo),
    }

    for label, ok in checks.items():
        print(f"{'OK  ' if ok else 'FAIL'} {label}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
