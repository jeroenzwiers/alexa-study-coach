"""Exercise the same Study Coach mechanism across three bounded domains."""

from __future__ import annotations

import copy
import json
import pathlib
import sys
import uuid

import anyio
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))
sys.path.insert(0, str(ROOT / "tools"))

import store
from grading import Candidate, grade
from verify_study_set import verify

MCP_URL = "http://127.0.0.1:8421/mcp"
DOMAINS = ["biology_cells", "computer_science_fundamentals", "history_civics_fundamentals"]


def source_data(study_set_id: str) -> dict:
    path = ROOT / "content" / f"{study_set_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def candidates(study_set, target_id: str) -> list[Candidate]:
    return study_set.candidates_for(target_id)


def card_for_question(study_set, question: str):
    return next(card for card in study_set.cards if card.question == question)


def adversarial_checks(study_set, pair: tuple[str, str]) -> dict:
    first = study_set.card(pair[0])
    second = study_set.card(pair[1])
    first_pool = candidates(study_set, first.id)
    second_pool = candidates(study_set, second.id)
    first_answer = first.accepted[0]
    second_answer = second.accepted[0]

    partial_card = next(card for card in study_set.cards if len(card.accepted[0].split()) > 1)
    partial = partial_card.accepted[0].split()[0]
    distorted = first_answer
    if first_answer == "authentication":
        distorted = "authentikayshun"
    elif first_answer == "democracy":
        distorted = "demockracy"
    elif first_answer == "mitochondria":
        distorted = "the might o chondria"

    return {
        "correct acceptance": grade(first_answer, first_pool).correct,
        "reverse correct acceptance": grade(second_answer, second_pool).correct,
        "A attributed when answering B": (
            not grade(first_answer, second_pool).correct
            and grade(first_answer, second_pool).matched.card_id == first.id
        ),
        "B attributed when answering A": (
            not grade(second_answer, first_pool).correct
            and grade(second_answer, first_pool).matched.card_id == second.id
        ),
        "unknown rejected": not grade("unrelated quantum banana", first_pool).correct,
        "partial answer not confident": not grade(partial, candidates(study_set, partial_card.id)).correct,
        "negation rejected": not grade(f"not {first_answer}", first_pool).correct,
        "filler-heavy answer accepted": grade(f"um, I think it is {first_answer}", first_pool).correct,
        "phonetic distortion accepted": grade(distorted, first_pool).correct,
    }


async def exercise_domain(study_set_id: str, pair: tuple[str, str]) -> dict:
    study_set = store.STUDY_SETS[study_set_id]
    # The leading marker keeps this run out of the real profiles and out of
    # every class report - see history.SYNTHETIC_MARKER. Persistence itself is
    # untouched, which is what the two memory checks below rely on.
    student = f"__generalization_{study_set_id}_{uuid.uuid4().hex[:8]}__"
    wrong_submitted: set[str] = set()
    events: list[dict] = []

    async with streamable_http_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()
            await client.list_tools()
            result = await client.call_tool(
                "start_practice",
                {"study_set_id": study_set_id, "length": len(study_set.cards), "student": student},
            )
            turn = dict(result.structured_content or {})

            for _ in range(len(study_set.cards) * 4):
                if turn.get("finished"):
                    break
                current = card_for_question(study_set, turn["question"])
                if turn.get("contrast"):
                    answer = current.accepted[0]
                elif current.id in pair and current.id not in wrong_submitted:
                    other_id = pair[1] if current.id == pair[0] else pair[0]
                    answer = study_set.card(other_id).accepted[0]
                    wrong_submitted.add(current.id)
                else:
                    answer = current.accepted[0]
                result = await client.call_tool(
                    "submit_answer",
                    {"session_id": turn["session_id"], "response": answer},
                )
                turn = dict(result.structured_content or {})
                events.append({"asked": current.id, "answer": answer, "turn": turn})

    async with streamable_http_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()
            progress_result = await client.call_tool(
                "student_progress",
                {"student": student, "study_set_id": study_set_id},
            )
            progress_text = " ".join(
                block.text for block in progress_result.content
                if getattr(block, "type", None) == "text"
            )
            restarted = await client.call_tool(
                "start_practice",
                {"study_set_id": study_set_id, "length": 1, "student": student},
            )
            restart_turn = dict(restarted.structured_content or {})

    # Every lookup below may legitimately find nothing when the run went wrong,
    # and a bare next() would then raise StopIteration - which inside a
    # coroutine surfaces as an unreadable RuntimeError naming no check at all.
    # A missing event is a failed check, reported by name like any other.
    def first(candidates, predicate) -> dict | None:
        return next((event for event in candidates if predicate(event)), None)

    wrong_a = first(events, lambda e: e["asked"] == pair[0] and e["answer"] == study_set.card(pair[1]).accepted[0])
    wrong_b = first(events, lambda e: e["asked"] == pair[1] and e["answer"] == study_set.card(pair[0]).accepted[0])
    contrast = first(events, lambda e: e["turn"].get("contrast"))
    mastery = [event for event in events if event["turn"].get("resolved_confusion") or (
        event["turn"].get("verdict") == "correct" and event["asked"] in pair and event["turn"].get("contrast") is None
    )]
    mastery = [event for event in mastery if event["asked"] in pair]
    first_mastery = first(mastery, lambda e: not e["turn"].get("resolved_confusion"))
    resolved = first(events, lambda e: e["turn"].get("resolved_confusion"))
    asked_ids = {event["asked"] for event in events}

    checks = {
        "both sides of the pair asked": set(pair) <= asked_ids,
        "first wrong attribution": wrong_a is not None and wrong_a["turn"].get("heard_as") == study_set.card(pair[1]).canonical.rstrip("."),
        "mirrored wrong attribution": wrong_b is not None and wrong_b["turn"].get("heard_as") == study_set.card(pair[0]).canonical.rstrip("."),
        "confusion and contrast": contrast is not None and contrast["turn"].get("contrast") is not None,
        "first side not resolved": first_mastery is not None and first_mastery["turn"].get("resolved_confusion") is None,
        "second side resolved": resolved is not None and bool(resolved["turn"].get("resolved_confusion")),
        "persisted settled result": "settled for good" in progress_text.lower(),
        "restart has context": "welcome back" in restart_turn.get("speech", "").lower(),
    }
    checks.update(adversarial_checks(study_set, pair))
    return {
        "cards": len(study_set.cards),
        "pairs": len(source_data(study_set_id).get("confusable_pairs") or [["c1", "c6"]]),
        "checks": checks,
        "false_attributions": sum(not value for value in checks.values()),
    }


def malformed_checks() -> dict:
    data = source_data("computer_science_fundamentals")
    malformed = copy.deepcopy(data["cards"])
    malformed[0]["difficulty"] = 9
    contained = [
        {"id": "x1", "question": "What is data?", "accepted": ["data"], "canonical": "Data.", "misconception": "One concept differs from another."},
        {"id": "x2", "question": "What is a database?", "accepted": ["database"], "canonical": "A database.", "misconception": "One concept differs from another."},
    ]
    bad_metadata = verify(malformed)[0]
    contained_problems = verify(contained)[0]
    ambiguous = grade(
        "auth",
        [
            Candidate("authentication", True, "a"),
            Candidate("authorization", False, "b"),
        ],
    )
    return {
        "malformed metadata rejected": any("is not 1, 2 or 3" in problem for problem in bad_metadata),
        "contained concept rejected": any("contained in" in problem for problem in contained_problems),
        "close two-concept answer rejected": ambiguous.rung == "ambiguous" and not ambiguous.correct,
    }


async def main_async() -> int:
    pair_by_domain = {
        domain: tuple((source_data(domain).get("confusable_pairs") or [["c1", "c6"]])[0])
        for domain in DOMAINS
    }
    reports = {}
    failed = []
    for domain in DOMAINS:
        reports[domain] = await exercise_domain(domain, pair_by_domain[domain])
        failed.extend(
            f"{domain}: {name}"
            for name, ok in reports[domain]["checks"].items()
            if not ok
        )
    malformed = malformed_checks()
    failed.extend(name for name, ok in malformed.items() if not ok)
    print(json.dumps({"domains": reports, "malformed": malformed, "failed": failed}, indent=2))
    return 0 if not failed else 1


def main() -> int:
    return anyio.run(main_async)


if __name__ == "__main__":
    raise SystemExit(main())
