"""Check a study set with the grader that will have to live with it.

Study Coach marks a spoken answer by attributing it to the nearest candidate in
a CLOSED set - every answer that appears anywhere in the study set. That is what
buys the diagnosis: being wrong stops being one bit, because we know which other
answer was said.

It also means a study set can be *wrong* in a way that reads perfectly. If two
cards accept a phrasing that sounds alike, the grader cannot choose between
them, refuses to guess, and the coach says "I did not catch that" to a student
who was right. If a card's own phrasing does not attribute to itself, that card
is unanswerable. Nothing about the questions looks amiss.

So no set ships unchecked - generated or hand-written. The checks below run the
real `grading.grade` from server/, not a copy of it:

    own phrasings       every accepted phrasing must attribute to its own card
    cross-attribution   said against a DIFFERENT card's question, a phrasing must
                        still be attributed to the card it belongs to. This is the
                        whole diagnosis in one assertion: it is how the coach knows
                        the student said "chloroplasts" rather than merely "not
                        mitochondria"
    collisions          no phrasing shared between cards, and none contained in
                        another, which would make attribution a coin flip
    structure           difficulty in range, phrasings present, and - when the
                        set carries `confused_with` labels - that each intended
                        distractor really does land on its partner

Import it, or run it: python tools/verify_study_set.py content/*.json
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from grading import Candidate, grade, normalise   # the live grader, not a copy


def candidates_for(cards: list[dict], card_id: str) -> list[Candidate]:
    """The same closed candidate set store.StudySet.candidates_for builds."""
    return [
        Candidate(text=phrasing, correct=(card["id"] == card_id), card_id=card["id"])
        for card in cards
        for phrasing in card.get("accepted", [])
    ]


def _structure(cards: list[dict], ids: set[str]) -> list[str]:
    problems = []
    for card in cards:
        if not card.get("accepted"):
            problems.append(f"{card['id']}: no accepted phrasings")
        if card.get("difficulty", 2) not in (1, 2, 3):
            problems.append(f"{card['id']}: difficulty {card.get('difficulty')} is not 1, 2 or 3")
        if not (card.get("misconception") or "").strip():
            problems.append(f"{card['id']}: no misconception line - nothing to say when it is missed")
        partner = card.get("confused_with")
        if partner and partner not in ids:
            problems.append(f"{card['id']}: confused_with '{partner}' is not a card in this set")
        if partner and partner == card["id"]:
            problems.append(f"{card['id']}: confused_with points at itself")
    return problems


def _collisions(cards: list[dict]) -> list[str]:
    problems = []
    owner: dict[str, str] = {}
    for card in cards:
        for phrasing in card.get("accepted", []):
            key = normalise(phrasing)
            if not key:
                problems.append(f"{card['id']}: empty phrasing")
                continue
            if key in owner and owner[key] != card["id"]:
                problems.append(f"{card['id']} and {owner[key]} both accept '{phrasing}'")
            owner[key] = card["id"]

    keys = sorted(owner)
    for key in keys:
        for other in keys:
            if key != other and owner[key] != owner[other] and key and key in other:
                problems.append(
                    f"'{key}' ({owner[key]}) is contained in '{other}' ({owner[other]}) - "
                    f"a student saying the longer one matches both"
                )
    return problems


def verify(cards: list[dict]) -> tuple[list[str], dict]:
    """Returns (problems, stats). An empty problems list means the set is sound."""
    ids = {c["id"] for c in cards}
    problems = _structure(cards, ids) + _collisions(cards)

    own_ok = own_bad = 0
    cross_ok = cross_bad = 0

    for card in cards:
        pool = candidates_for(cards, card["id"])
        for phrasing in card.get("accepted", []):
            verdict = grade(phrasing, pool)
            if verdict.correct:
                own_ok += 1
            else:
                own_bad += 1
                problems.append(
                    f"{card['id']}: its own phrasing '{phrasing}' does not grade as correct "
                    f"(rung={verdict.rung}) - this card is unanswerable"
                )

    # The diagnosis, asserted. Said in answer to someone else's question, a
    # phrasing must still be recognised as the thing it is.
    for card in cards:
        for other in cards:
            if other["id"] == card["id"]:
                continue
            pool = candidates_for(cards, other["id"])
            for phrasing in card.get("accepted", []):
                verdict = grade(phrasing, pool)
                landed = verdict.matched.card_id if verdict.matched else None
                if not verdict.correct and landed == card["id"]:
                    cross_ok += 1
                else:
                    cross_bad += 1
                    problems.append(
                        f"asked {other['id']}, answering '{phrasing}' ({card['id']}) "
                        f"lands on {landed or 'nothing'} - the misconception could not be named"
                    )

    # Only meaningful for sets that carry generation labels.
    pairs_ok = pairs_bad = 0
    for card in cards:
        partner_id = card.get("confused_with")
        if not partner_id or partner_id not in ids:
            continue
        partner = next(c for c in cards if c["id"] == partner_id)
        if not partner.get("accepted"):
            continue
        verdict = grade(partner["accepted"][0], candidates_for(cards, card["id"]))
        landed = verdict.matched.card_id if verdict.matched else None
        if not verdict.correct and landed == partner_id:
            pairs_ok += 1
        else:
            pairs_bad += 1

    return problems, {
        "cards": len(cards),
        "own_ok": own_ok,
        "own_bad": own_bad,
        "cross_ok": cross_ok,
        "cross_bad": cross_bad,
        "pairs_ok": pairs_ok,
        "pairs_bad": pairs_bad,
        "difficulty": {n: sum(1 for c in cards if c.get("difficulty", 2) == n) for n in (1, 2, 3)},
    }


def report(name: str, problems: list[str], stats: dict) -> None:
    print(f"{name}")
    print(f"  cards            : {stats['cards']}, difficulty {stats['difficulty']}")
    print(f"  own phrasings    : {stats['own_ok']} attributed to their own card, {stats['own_bad']} not")
    print(f"  cross-attributed : {stats['cross_ok']} land on the right card, {stats['cross_bad']} do not")
    if stats["pairs_ok"] or stats["pairs_bad"]:
        print(f"  labelled pairs   : {stats['pairs_ok']} land on their partner, {stats['pairs_bad']} do not")
    if problems:
        print(f"  {len(problems)} problem(s):")
        for problem in problems[:15]:
            print(f"    - {problem}")
        if len(problems) > 15:
            print(f"    ... and {len(problems) - 15} more")
    else:
        print("  clean")


def main(argv: list[str]) -> int:
    paths = [pathlib.Path(a) for a in argv] or sorted((ROOT / "content").glob("*.json"))
    if not paths:
        print("No study sets found.")
        return 1
    worst = 0
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        problems, stats = verify(data["cards"])
        report(f"{path.name} - {data.get('title', '?')}", problems, stats)
        print()
        worst = max(worst, 1 if problems else 0)
    return worst


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
