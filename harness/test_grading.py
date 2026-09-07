"""Grading accuracy on the cases that broke the threshold design.

Every row is a real failure mode of spoken answers, not a spelling curiosity.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "server"))
from grading import Candidate, grade

# The closed answer set for the biology deck, plus the distractors a student
# actually reaches for. Exactly what a real study set gives us for free.
DECK = {
    "mitochondria": ["mitochondria", "mitochondrion"],
    "nucleus": ["nucleus"],
    "ribosome": ["ribosome", "making proteins", "protein synthesis"],
    "cell wall": ["cell wall"],
    "cell membrane": ["cell membrane"],
    "chloroplast": ["chloroplast", "chloroplasts"],
    "vacuole": ["vacuole", "permanent vacuole"],
    # known wrong turns for this topic
    "nucleolus": ["nucleolus"],
    "mitosis": ["mitosis"],
    "vesicle": ["vesicle"],
}

def candidates_for(target_key: str) -> list[Candidate]:
    out = []
    for key, phrasings in DECK.items():
        for phrasing in phrasings:
            out.append(Candidate(text=phrasing, correct=(key == target_key), card_id=key))
    return out

CASES = [
    # (what the recogniser delivered, which card is being asked, expected verdict)
    ("mitochondria",            "mitochondria", True),
    ("the might o chondria",    "mitochondria", True),
    ("mite oh kondria",         "mitochondria", True),
    ("my toe kondria",          "mitochondria", True),
    ("I think its the mitochondria", "mitochondria", True),
    ("new clee us",             "nucleus",      True),
    ("nucleus",                 "nucleus",      True),
    ("sell wall",               "cell wall",    True),
    ("rye bo some",             "ribosome",     True),
    ("to make proteins",        "ribosome",     True),
    ("um i think making proteins yeah", "ribosome", True),
    # must stay wrong - these are different answers, not distorted right ones
    ("nucleolus",               "nucleus",      False),
    ("mitosis",                 "mitochondria", False),
    ("chloroplast",             "mitochondria", False),
    ("cell membrane",           "cell wall",    False),
    ("vesicle",                 "vacuole",      False),
    ("its not the nucleus",     "nucleus",      False),
    ("i dont know",             "nucleus",      False),
    ("",                        "nucleus",      False),
    ("ribosome",                "nucleus",      False),
    # A leading "no" retracts the student's own false start, not the answer.
    # This is how a hesitant speaker answers, and throwing the turn away also
    # threw away the attribution the whole diagnosis depends on.
    ("no wait the mitochondria", "mitochondria", True),
    ("no, the nucleus",         "nucleus",      True),
    ("nope um the cell wall",   "cell wall",    True),
    # ...but a negation that denies the answer still denies it.
    ("no its not the nucleus",  "nucleus",      False),
    # Containing the answer is not saying it. The trailing word is not filler,
    # it is the thing that names a different concept - and these used to come
    # back `exact`, scored 1.0, and marked correct.
    ("mitochondrion wall",      "mitochondria", False),
    ("cell membrane protein",   "cell membrane", False),
    # Filler may still run ahead of the answer, or trail it as an affirmation.
    ("el promedio, um, the mitochondria", "mitochondria", True),
    ("the cell wall yeah",      "cell wall",    True),
]

def main() -> int:
    failures = []
    print(f"{'gesproken':38} {'verwacht':9} {'kreeg':7} {'via':13} {'score':>6} {'marge':>6}  toegeschreven aan")
    print("-" * 110)
    for said, target, expected in CASES:
        g = grade(said, candidates_for(target))
        ok = g.correct == expected
        if not ok:
            failures.append((said, target, expected, g))
        attributed = g.matched.card_id if g.matched else "-"
        print(f"{said!r:38} {str(expected):9} {str(g.correct):7} {g.rung:13} "
              f"{g.score:6.3f} {g.margin:6.3f}  {attributed}   {'' if ok else '<-- FOUT'}")
    print("-" * 110)
    print(f"{len(CASES) - len(failures)}/{len(CASES)} geslaagd")
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
