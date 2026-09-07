"""Does the session diagnose and then SETTLE, or only score?

Drives a student who mixes two concepts up, is drilled on the contrast, and
then gets both sides right. Checks the whole arc: the confusion is noticed as a
pattern rather than bad luck, the other side of it is probed rather than left to
the shuffle, the contrast is drilled, and - the part a flashcard app can never
reach - the confusion is declared settled and reported as settled.
"""
import pathlib
import random
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

import app, history, store
from grading import grade

history.DATA_DIR = pathlib.Path(tempfile.mkdtemp(prefix="coach-")) / "students"

# A student who has mitochondria and chloroplasts the wrong way round and knows
# the rest - until the contrast question teaches them the difference, after
# which they have it right. Keyed on a phrase from the question, since the deck
# is both shuffled and adaptive.
WRONG = {
    "releases energy": "chloroplasts",          # wrong - the confusion
    "captures light": "mitochondria",           # wrong - same confusion, mirrored
}
RIGHT = {
    "releases energy": "the might o chondria",  # and still mangled by the ASR
    "captures light": "chloroplasts",
}
KNOWN = {
    "cell membrane control": "what goes in and out",
    "shape and support": "sell wall",
    "genetic material": "new clee us",
    "job of a ribosome": "to make proteins",
    "inside the nucleus": "the nucleolus",
    "movement of water": "osmosis",
    "movement of particles": "diffusion",
    "stores cell sap": "the vacuole",
    "chemical reactions": "cytoplasm",
    "no nucleus": "a prokaryotic cell",
    "packages proteins": "the golgi apparatus",
}


def reply_to(question: str, taught: bool) -> str:
    lowered = question.lower()
    for cue, said in {**KNOWN, **(RIGHT if taught else WRONG)}.items():
        if cue in lowered:
            return said
    return "i dont know"


def resolution_invariant_checks() -> dict:
    """A pair resolves only after correct answers from both target sides."""
    cases = {
        "A then A stays open": ("c1", "c1", False),
        "B then B stays open": ("c6", "c6", False),
        "A then B resolves": ("c1", "c6", True),
        "B then A resolves": ("c6", "c1", True),
    }
    checks = {}
    for label, (first, second, expected) in cases.items():
        session = store.Session(id=label, study_set_id="biology_cells")
        key = store.pair_key("c1", "c6")
        session.confusions[key] = store.CONFUSION_THRESHOLD
        session.contested.add(key)
        session.record_success(first)
        resolved = bool(session.record_success(second))
        checks[label] = resolved is expected
    return checks


def probe_survival_checks(rounds: int = 80) -> dict:
    """A probe scheduled late in a session must still be asked.

    `store.probe` takes the other side of a suspected confusion out of the pool
    and promises it a turn a couple of questions downstream. When the miss
    happens near the end of a session that turn used to never arrive: the pool
    emptied first, the session closed, and the pair was never tested both ways
    round - so the confusion could not be diagnosed at all. It went unnoticed
    because a returning student has the pair forced to the front, which hides
    it; only a first-ever session shows the drop.

    Swept over many shuffles rather than one, because whether it happens at all
    depends on where the shuffle puts the missed card.
    """
    study_set = store.STUDY_SETS["biology_cells"]
    pair = ("c1", "c6")
    incomplete, undiagnosed = [], []

    for seed in range(rounds):
        random.seed(seed)
        wrong: set[str] = set()
        asked: list[str] = []
        turn = app.start_practice(
            "biology_cells", length=len(study_set.cards), student=f"__probe_{seed}__"
        )
        for _ in range(len(study_set.cards) * 4):
            if turn.finished or not turn.question:
                break
            card = next(c for c in study_set.cards if c.question == turn.question)
            asked.append(card.id)
            if turn.contrast or card.id not in pair or card.id in wrong:
                said = card.accepted[0]
            else:
                other = pair[1] if card.id == pair[0] else pair[0]
                said = study_set.card(other).accepted[0]
                wrong.add(card.id)
            turn = app.submit_answer(turn.session_id, said)

        session = store.SESSIONS[turn.session_id]
        key = store.pair_key(*pair)
        if not set(pair) <= set(asked):
            incomplete.append(seed)
        elif session.confusions[key] < store.CONFUSION_THRESHOLD:
            # Seen from both sides, so it must have been counted as a pattern -
            # whether it then got settled is a separate question.
            undiagnosed.append(seed)

    return {
        f"beide kanten van het paar altijd gevraagd ({rounds} shuffles)": not incomplete,
        f"verwarring altijd gediagnosticeerd ({rounds} shuffles)": not undiagnosed,
    }


def ceiling_checks(rounds: int = 25) -> dict:
    """A student who gets EVERYTHING wrong still reaches the end of the session.

    This is the case every other test in this file misses. `reply_to` answers
    most cards correctly, so a student driven by it learns in the end; the
    student this product exists for is the one who does not. Answering every
    card with some OTHER card's answer keeps each miss attributable, which is
    what breeds confusion pairs - and drilling those used to bypass `planned`
    entirely, because it only ever gated the drawing of fresh cards. Sessions
    of three hundred questions, and closed loops of the same six.

    Varies WHICH wrong answer is given, since a fixed one concentrates every
    miss onto a single pair and hides the problem.
    """
    study_set = store.STUDY_SETS["biology_cells"]
    hard_stop = 400                      # far above the ceiling; only to end a runaway
    overruns, over_ceiling = [], []

    for seed in range(rounds):
        random.seed(seed)
        turn = app.start_practice(
            "biology_cells", length=len(study_set.cards), student=f"__ceiling_{seed}__"
        )
        ceiling = turn.total_questions and store.SESSIONS[turn.session_id].ceiling
        asked = 0
        while not turn.finished and turn.question and asked < hard_stop:
            asked += 1
            card = next(c for c in study_set.cards if c.question == turn.question)
            others = [c for c in study_set.cards if c.id != card.id]
            turn = app.submit_answer(turn.session_id, random.choice(others).accepted[0])
        if not turn.finished:
            overruns.append(seed)
        elif asked > ceiling:
            over_ceiling.append((seed, asked, ceiling))

    return {
        f"sessie eindigt ook als ALLES fout gaat ({rounds} shuffles)": not overruns,
        "sessie blijft binnen het plafond van twee keer de lengte": not over_ceiling,
    }


def carried_confusion_checks(rounds: int = 20) -> dict:
    """A confusion carried in from last time can still be drilled and settled.

    `start_session` marks a carried pair `contested` before any drill has run,
    and `record_confusion` used to refuse a drill for anything already in that
    set. So the student came back still confused, missed the pair again, and the
    contrast drill built for exactly that moment could never fire - the feature
    worked only for the student who no longer needed it.
    """
    study_set = store.STUDY_SETS["biology_cells"]
    pair = ("c1", "c6")

    def other(card_id: str) -> str:
        return pair[1] if card_id == pair[0] else pair[0]

    def play(student: str, slips: int | None) -> tuple[bool, bool, bool]:
        """slips=None means wrong every time; otherwise wrong that many times."""
        turn = app.start_practice(
            "biology_cells", length=len(study_set.cards), student=student
        )
        returning, saw_contrast, settled, used = bool(turn.returning), False, False, 0
        while not turn.finished and turn.question:
            card = next(c for c in study_set.cards if c.question == turn.question)
            if turn.contrast:
                saw_contrast = True
            wrong = card.id in pair and (slips is None or used < slips)
            if wrong and slips is not None:
                used += 1
            said = study_set.card(other(card.id)).accepted[0] if wrong else card.accepted[0]
            turn = app.submit_answer(turn.session_id, said)
            if turn.resolved_confusion:
                settled = True
        return returning, saw_contrast, settled

    carried, drilled, settled_after_slip = 0, 0, 0
    for seed in range(rounds):
        random.seed(seed)
        student = f"__carried_{seed}__"
        play(student, None)                       # two sessions of getting it wrong
        play(student, None)
        returning, saw_contrast, _ = play(student, None)   # back, still wrong
        carried += returning
        drilled += saw_contrast

        random.seed(seed)
        student = f"__carried_slip_{seed}__"
        play(student, None)
        play(student, None)
        _, _, settled = play(student, 1)          # back, slips once, then has it
        settled_after_slip += settled

    return {
        f"verwarring wordt meegedragen naar de volgende sessie ({rounds}x)": carried == rounds,
        "terugkerende leerling die het nog fout heeft krijgt de contrastvraag": drilled == rounds,
        "terugkerende leerling die een keer glipt kan het alsnog afsluiten":
            settled_after_slip == rounds,
    }


def report_honesty_checks(rounds: int = 20) -> dict:
    """The report never claims more errors than the student actually made.

    A carried confusion arrives with its counter seeded so the drill treats it
    as ripe. That seed is not something the student did tonight, and printing it
    in "N of them are the same confusion" told a parent their child had repeated
    every old mistake - counts larger than the number of questions asked.
    """
    study_set = store.STUDY_SETS["biology_cells"]
    pair = ("c1", "c6")

    def other(card_id: str) -> str:
        return pair[1] if card_id == pair[0] else pair[0]

    def play(student: str) -> tuple[str, int]:
        turn = app.start_practice(
            "biology_cells", length=len(study_set.cards), student=student
        )
        session_id, misses = turn.session_id, 0
        while not turn.finished and turn.question:
            card = next(c for c in study_set.cards if c.question == turn.question)
            said = (
                study_set.card(other(card.id)).accepted[0]
                if card.id in pair else card.accepted[0]
            )
            turn = app.submit_answer(turn.session_id, said)
            if turn.verdict != "correct":
                misses += 1
        return app.tutor_report(session_id), misses

    overstated = []
    for seed in range(rounds):
        random.seed(seed)
        student = f"__honest_{seed}__"
        play(student)                       # session one seeds the carry
        report, misses = play(student)      # session two: the returning student
        claimed = re.search(r"(\d+) of them are the same confusion", report)
        if claimed and int(claimed.group(1)) > misses:
            overstated.append((seed, int(claimed.group(1)), misses))

    return {
        f"rapport claimt nooit meer fouten dan er gemaakt zijn ({rounds}x)": not overstated,
    }


def input_checks() -> dict:
    """Alexa+ passes through whatever it understood; the tool must survive it."""
    checks = {}
    for length in (-5, -1, 0, 1, 100000):
        try:
            turn = app.start_practice(
                "biology_cells", length=length, student=f"__len_{length}__"
            )
            checks[f"length={length} levert een vraag op"] = bool(turn.question)
        except Exception as exc:
            checks[f"length={length} levert een vraag op"] = False
            checks[f"length={length} zonder exceptie"] = f"{type(exc).__name__}"
    return checks


def ambiguous_records_nothing_checks() -> dict:
    """A verdict the grader could not resolve must not become a diagnosis.

    `grade` returns the nearest candidate even when it reports `ambiguous` -
    the rung means "I cannot choose between these", not "there is no match".
    Reading that candidate anyway wrote a confusion to the profile, queued a
    contrast drill, scheduled a probe and summed the pair into the class
    report, while the only surface that told the truth was the sentence the
    student heard: "I didn't quite catch that."

    The case below is real: "the intercept" against the x-intercept card scores
    0.947 with a margin of exactly zero.
    """
    study_set = store.STUDY_SETS["algebra_foundations"]
    verdict = grade("the intercept", study_set.candidates_for("c5"))

    turn = app.start_practice("algebra_foundations", length=12, student="__ambiguous__")
    session = store.SESSIONS[turn.session_id]
    session.current = "c5"
    out = app.submit_answer(turn.session_id, "the intercept")

    return {
        "onbeslisbaar antwoord heet ook onbeslisbaar": verdict.rung == "ambiguous",
        "onbeslisbaar antwoord wijst nog wel ergens naar": verdict.matched is not None,
        "maar legt geen verwarring vast": not session.confusions,
        "en plant geen contrastdrill": not session.forced,
        "en plant geen probe": not session.deferred,
        "en noemt geen begrip tegen de leerling": out.heard_as is None,
    }


def main() -> int:
    random.seed(7)
    checks = resolution_invariant_checks()
    checks.update(probe_survival_checks())
    checks.update(ceiling_checks())
    checks.update(carried_confusion_checks())
    checks.update(report_honesty_checks())
    checks.update(input_checks())
    checks.update(ambiguous_records_nothing_checks())
    turn = app.start_practice("biology_cells", length=8, student="__test_diagnosis__")
    session_id = turn.session_id
    print("ALEXA   :", turn.speech)

    taught = False
    saw_contrast = False
    saw_resolution = False

    for _ in range(24):
        said = reply_to(turn.speech, taught)
        print("LEERLING:", said)
        turn = app.submit_answer(session_id, said)
        print("ALEXA   :", turn.speech)
        if turn.resolved_confusion:
            saw_resolution = True
            print("          >>> OPGELOST:", " / ".join(turn.resolved_confusion))
        if "separate those two" in (turn.speech or "").lower():
            saw_contrast = True
            taught = True       # the contrast is what teaches the distinction
        if turn.finished:
            break

    report = app.tutor_report(session_id)
    print()
    print("RAPPORT :", report)

    session = store.SESSIONS[session_id]
    print()
    checks.update({
        "een verwisseling herkend als patroon": bool(session.confusions),
        "andere kant van de verwarring actief bevraagd": session.bonus > 0 or saw_contrast,
        "contrastvraag gesteld": saw_contrast,
        "verwarring opgelost gemeld tijdens de sessie": saw_resolution,
        "verwarring staat als opgelost in de sessie": bool(session.resolved),
        "rapport benoemt de oplossing": "settled during the session" in report,
        "geen open verwarring meer over": session.dominant_confusion() is None,
    })
    for label, ok in checks.items():
        print(f"  {'OK  ' if ok else 'FOUT'} {label}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
