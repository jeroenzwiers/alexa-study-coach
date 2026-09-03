"""Does the session read the student, or only the answer?

Two halves, because the feature has two halves.

  unit          adaptive.read_signals and adaptive.update in isolation: what
                counts as strain, what counts as cruising, and the rules that
                must never fire (never push a struggling student; never pull the
                hints away and steepen the question in the same turn).
  end to end    a real session where the student falls apart and then recovers,
                checking that the questions actually get easier, that help
                actually appears, and that both are withdrawn in the right order.

The `manner` half of the signal is what Alexa+ would pass after hearing the
student, and it carries observable BEHAVIOUR only - never an emotion label, which
the server refuses even when offered. It is optional everywhere, so the whole
collapse is driven twice, once with it and once without.
"""
import pathlib
import random
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

import adaptive
import app, history, store

history.DATA_DIR = pathlib.Path(tempfile.mkdtemp(prefix="coach-")) / "students"


def unit_checks() -> dict:
    quiet = adaptive.Signals()

    heard = adaptive.read_signals("um, uh, the... mitochondria?")
    gave_up = adaptive.read_signals("i dont know")
    struggling = adaptive.read_signals("nucleus", manner="long pause, then asked to stop")
    breezy = adaptive.read_signals("nucleus", manner="answered instantly, no hesitation")
    paused = adaptive.read_signals("nucleus", manner="long pause before answering")
    # An emotion label must do nothing at all, even when handed over willingly:
    # inferring emotions in education is prohibited under EU AI Act 5(1)(f), so
    # the server declines the signal rather than quietly using it.
    emotive = adaptive.read_signals("nucleus", manner="sounding really frustrated and upset")

    slow = adaptive.read_signals(
        "nucleus",
        question="Where is the genetic material of a cell found?",
        elapsed_ms=adaptive.expected_speech_ms("Where is the genetic material of a cell found?") + 9000,
    )
    snappy = adaptive.read_signals(
        "nucleus",
        question="Where is the genetic material of a cell found?",
        elapsed_ms=adaptive.expected_speech_ms("Where is the genetic material of a cell found?") + 500,
    )

    # A student in trouble, on the transcript alone.
    strained = adaptive.update(
        correct=False, signals=adaptive.read_signals("um, i dont know"),
        strain=0.0, correct_streak=0, wrong_streak=1, difficulty=3, scaffold=0,
    )
    # The same run of right answers, once while strained and once while settled.
    pushed_while_strained = adaptive.update(
        correct=True, signals=quiet,
        strain=0.9, correct_streak=5, wrong_streak=0, difficulty=1, scaffold=0,
    )
    pushed_when_ready = adaptive.update(
        correct=True, signals=quiet,
        strain=0.0, correct_streak=3, wrong_streak=0, difficulty=1, scaffold=0,
    )
    recovering = adaptive.update(
        correct=True, signals=quiet,
        strain=0.0, correct_streak=3, wrong_streak=0, difficulty=1, scaffold=2,
    )

    return {
        "hoort aarzeling in het transcript": heard.hesitant,
        "hoort opgeven": gave_up.gave_up,
        "leest moeite af aan gedrag": struggling.manner_effortful,
        "leest vlotheid af aan gedrag": breezy.manner_fluent,
        "manner kan aarzeling melden": paused.hesitant,
        "negeert emotielabels volledig": not (
            emotive.manner_effortful or emotive.manner_fluent or emotive.hesitant
        ),
        "meet traag nadenken los van spreektijd": slow.slow and not slow.quick,
        "meet snel antwoorden": snappy.quick and not snappy.slow,
        "zakt af bij spanning": strained.direction == "ease" and strained.difficulty < 3,
        "biedt hulp aan bij spanning": strained.scaffold > 0,
        "duwt NOOIT door bij spanning": pushed_while_strained.direction != "stretch",
        "daagt uit bij een reeks goede antwoorden": pushed_when_ready.direction == "stretch",
        "neemt eerst de hulp weg, dan pas moeilijker": (
            recovering.direction == "hold"
            and recovering.scaffold == 1
            and recovering.difficulty == 1
        ),
    }


def seed_at_top_level(student: str) -> None:
    """Give the student a history that leaves them working at the hardest level.

    Without it there is nothing to come down FROM: a new student starts at level
    one, and "the questions got easier" is not a claim you can test against a
    floor.
    """
    saved = history.load(student)
    record = history.record_for(saved, "biology_cells")
    record.update({"sessions": 4, "difficulty": adaptive.MAX_DIFFICULTY,
                   "last_seen": history._today(), "last_score": [9, 10]})
    history.save(saved)


def collapse(student: str, manner: str | None) -> dict:
    """A student who falls apart, then recovers. Returns what the session did."""
    seed_at_top_level(student)
    turn = app.start_practice("biology_cells", length=10, student=student)
    session = store.SESSIONS[turn.session_id]
    trail = [{"support": turn.support, "difficulty": turn.difficulty,
              "target": session.difficulty, "momentum": turn.momentum}]

    print(f"--- instorten en herstellen (manner={manner!r}) ---")
    print("ALEXA   :", turn.speech)

    for step in range(9):
        # Four turns of giving up, then answering everything correctly again.
        if step < 4:
            said, note = "um... i dont know", manner
        else:
            said, note = _answer(turn.question), ("answered instantly" if manner else None)
        print("LEERLING:", said)
        turn = app.submit_answer(turn.session_id, said, manner=note)
        print("ALEXA   :", turn.speech)
        trail.append({
            "support": turn.support,
            "difficulty": turn.difficulty,
            "target": session.difficulty,
            "momentum": turn.momentum,
            "strain": round(session.strain, 2),
        })
        if turn.finished:
            break
    print()
    return {"trail": trail, "session": session}


ANSWERS = {
    "releases energy": "the mitochondria", "captures light": "chloroplasts",
    "cell membrane control": "what goes in and out", "shape and support": "cell wall",
    "genetic material": "nucleus", "job of a ribosome": "to make proteins",
    "inside the nucleus": "the nucleolus", "movement of water": "osmosis",
    "movement of particles": "diffusion", "stores cell sap": "the vacuole",
    "chemical reactions": "cytoplasm", "no nucleus": "a prokaryotic cell",
    "packages proteins": "the golgi apparatus",
}


def _answer(question: str | None) -> str:
    for cue, said in ANSWERS.items():
        if cue in (question or "").lower():
            return said
    return "i dont know"


def main() -> int:
    random.seed(5)
    checks = unit_checks()

    with_manner = collapse("__test_adaptive_a__", "long pause, then asked to stop")
    without_manner = collapse("__test_adaptive_b__", None)

    for label, result in (("met manner", with_manner), ("zonder manner", without_manner)):
        trail = result["trail"]
        supports = [t["support"] for t in trail]
        targets = [t["target"] for t in trail]
        served = [t["difficulty"] for t in trail if t["difficulty"]]
        checks[f"{label}: mikt op makkelijkere vragen"] = min(targets) < targets[0]
        checks[f"{label}: en stelt ze ook echt"] = min(served) < served[0]
        checks[f"{label}: hulp verschijnt"] = "hint" in supports or "options" in supports
        checks[f"{label}: zakt af, niet door"] = any(
            t.get("momentum") == "ease" for t in trail
        )
        checks[f"{label}: hulp verdwijnt weer bij herstel"] = supports[-1] == "none"

    # The invariant is about the DECISION, not about which card happened to be
    # nearest the target: a step up must never be taken while the student is
    # still leaning on hints.
    for label, result in (("met manner", with_manner), ("zonder manner", without_manner)):
        trail = result["trail"]
        rank = {"options": 2, "hint": 1, "none": 0, None: 0}
        bad = [
            (a, b) for a, b in zip(trail, trail[1:])
            if b.get("momentum") == "stretch" and rank[a["support"]] > 0
        ]
        checks[f"{label}: nooit zwaarder terwijl er nog hulp staat"] = not bad
        # ...and difficulty must never rise on a turn the session called "ease".
        checks[f"{label}: 'zakt af' zakt ook echt af"] = not [
            (a, b) for a, b in zip(trail, trail[1:])
            if b.get("momentum") == "ease" and b["target"] > a["target"]
        ]

    print("=" * 64)
    for label, ok in checks.items():
        print(f"  {'OK  ' if ok else 'FOUT'} {label}")
    failed = [k for k, v in checks.items() if not v]
    print(f"\n{len(checks) - len(failed)}/{len(checks)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
