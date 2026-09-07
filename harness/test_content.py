"""Is the study set itself sound, or only plausible-looking?

A study set can be wrong in a way that reads perfectly. Because grading
attributes an answer to the nearest candidate in a closed set, two cards that
accept similar-sounding phrasings leave the grader unable to choose - so it
refuses to guess, and a student who was right is told "I did not catch that".
Nothing about the questions looks amiss.

Two halves here, and the second matters as much as the first:

  the real sets    everything in content/ must pass, generated or hand-written.
  the checker      deliberately broken sets must FAIL. A check that never fires
                   proves nothing, and this one guards content nobody reviews
                   line by line.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from verify_study_set import verify

CONTENT = ROOT / "content"


def card(cid, question, accepted, canonical, difficulty=1, confused=None):
    return {
        "id": cid,
        "question": question,
        "accepted": accepted,
        "canonical": canonical,
        "difficulty": difficulty,
        "hint": "a hint",
        "explanation": "an explanation",
        "misconception": "One thing is not the other.",
        **({"confused_with": confused} if confused else {}),
    }


# A set where two cards answer to the same words. The grader cannot attribute
# the utterance, so both cards become unanswerable.
COLLIDING = [
    card("c1", "Where is the genetic material?", ["the nucleus", "nucleus"], "The nucleus."),
    card("c2", "Which structure makes ribosomes?", ["the nucleus"], "The nucleolus."),
]

# A set where one phrasing sits inside another. A student saying the longer one
# matches both, and the margin rule refuses to pick.
CONTAINED = [
    card("c1", "What surrounds the cell?", ["cell"], "The cell."),
    card("c2", "What gives a plant cell shape?", ["cell wall"], "The cell wall."),
]

# A set with nothing to say when a card is missed - the coach can only say "no".
NO_MISCONCEPTION = [
    dict(card("c1", "Which organelle releases energy?", ["mitochondria"], "The mitochondria."),
         misconception=""),
    card("c2", "Which organelle captures light?", ["chloroplasts"], "The chloroplasts."),
]

# A card whose difficulty is outside the range the adaptive session moves in.
BAD_DIFFICULTY = [
    card("c1", "Which organelle releases energy?", ["mitochondria"], "The mitochondria.", difficulty=7),
    card("c2", "Which organelle captures light?", ["chloroplasts"], "The chloroplasts."),
]

# A label claiming a confusion the grader cannot deliver: nothing in c1 would
# ever be heard as c2, so the misconception could never be named.
BROKEN_LABEL = [
    card("c1", "Which organelle releases energy?", ["mitochondria"], "The mitochondria.",
         confused="c3"),
    card("c2", "Which organelle captures light?", ["chloroplasts"], "The chloroplasts."),
]


# A set that names no near-misses at all. It looks perfectly sound by every
# other check, and it is exactly the shape that marks "the mode" correct when a
# student is asked about the median.
NO_NEAR_MISSES = [
    {"id": "n1", "question": "What is the middle value called?",
     "accepted": ["the median"], "canonical": "The median.", "difficulty": 1,
     "misconception": "The median is the middle; the mean is the total shared out."},
    {"id": "n2", "question": "What is the total shared out called?",
     "accepted": ["the mean"], "canonical": "The mean.", "difficulty": 1,
     "misconception": "The mean is the total shared out; the median is the middle."},
]

# ...and a set that declares one but has it in `accepted` somewhere too, so the
# concept it means to refuse is still handed out as a correct answer.
BAD_NEAR_MISS = [
    {"id": "b1", "question": "What is the middle value called?",
     "accepted": ["the median"], "canonical": "The median.", "difficulty": 1,
     "near_misses": ["the mode"],
     "misconception": "The median is the middle; the mode is the commonest."},
    {"id": "b2", "question": "What is the commonest value called?",
     "accepted": ["the mode"], "canonical": "The mode.", "difficulty": 1,
     "misconception": "The mode is the commonest; the median is the middle."},
]


def main() -> int:
    checks = {}

    files = sorted(CONTENT.glob("*.json"))
    checks["er is minstens een studieset"] = bool(files)

    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        problems, stats = verify(data["cards"])
        print(f"{path.name} - {data.get('title')}")
        print(f"  {stats['cards']} kaarten, moeilijkheid {stats['difficulty']}")
        print(f"  eigen formuleringen : {stats['own_ok']} goed toegewezen, {stats['own_bad']} niet")
        print(f"  kruistoewijzing     : {stats['cross_ok']} landen goed, {stats['cross_bad']} niet")
        for problem in problems[:10]:
            print(f"    - {problem}")
        print()
        checks[f"{path.name}: geen enkel probleem"] = not problems
        checks[f"{path.name}: elke formulering wijst naar de eigen kaart"] = stats["own_bad"] == 0
        checks[f"{path.name}: elk antwoord is toe te wijzen aan de juiste kaart"] = stats["cross_bad"] == 0
        checks[f"{path.name}: moeilijkheid is gespreid"] = len(
            [n for n, k in stats["difficulty"].items() if k]
        ) >= 2

    # The checker must actually fire. Each of these is a way a set can look fine
    # and still break the product.
    for label, cards, needle in (
        ("botsende formuleringen", COLLIDING, "both accept"),
        ("formulering zit in een andere", CONTAINED, "contained in"),
        ("geen misconception-regel", NO_MISCONCEPTION, "no misconception"),
        ("moeilijkheid buiten bereik", BAD_DIFFICULTY, "is not 1, 2 or 3"),
        ("verwijst naar een kaart die niet bestaat", BROKEN_LABEL, "is not a card"),
        ("geen enkele near-miss gedeclareerd", NO_NEAR_MISSES, "declares `near_misses`"),
        ("near-miss wordt juist goedgerekend", BAD_NEAR_MISS, "must never be accepted"),
    ):
        problems, _ = verify(cards)
        found = any(needle in p for p in problems)
        checks[f"checker vangt: {label}"] = found
        if not found:
            print(f"  NIET GEVANGEN ({label}): {problems}")

    for label, ok in checks.items():
        print(f"  {'OK  ' if ok else 'FOUT'} {label}")
    failed = [k for k, v in checks.items() if not v]
    print(f"\n{len(checks) - len(failed)}/{len(checks)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
