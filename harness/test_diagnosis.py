"""Does the session actually diagnose, or only score?

Drives a student who consistently mixes up two concepts and checks that the
session stops treating it as bad luck: names the confusion, drills the contrast,
and reports the pattern rather than a number.
"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

import app, store

# A student who has mitochondria and chloroplasts the wrong way round, and knows
# the rest. Keyed on a phrase from the question, since the deck is shuffled.
ANSWERS = {
    "releases energy": "chloroplasts",          # wrong - the confusion
    "captures light": "mitochondria",           # wrong - same confusion, mirrored
    "cell membrane control": "what goes in and out",
    "shape and support": "sell wall",
    "genetic material": "new clee us",
    "job of a ribosome": "to make proteins",
}

def reply_to(question: str) -> str:
    lowered = question.lower()
    for cue, said in ANSWERS.items():
        if cue in lowered:
            return said
    return "i dont know"

def main() -> int:
    turn = app.start_practice("biology_cells")
    session_id = turn.session_id
    print("ALEXA   :", turn.speech)

    for _ in range(12):
        said = reply_to(turn.speech)
        print("LEERLING:", said)
        turn = app.submit_answer(session_id, said)
        print("ALEXA   :", turn.speech)
        if turn.finished:
            break

    print()
    print("RAPPORT :", app.tutor_report(session_id))

    session = store.SESSIONS[session_id]
    print()
    checks = {
        "een verwisseling herkend als patroon": session.dominant_confusion() is not None,
        "contrastvraag gesteld": bool(session.contrasts_done),
        "rapport benoemt de verwarring": "same confusion" in app.tutor_report(session_id),
    }
    for label, ok in checks.items():
        print(f"  {'OK  ' if ok else 'FOUT'} {label}")
    return 0 if all(checks.values()) else 1

if __name__ == "__main__":
    raise SystemExit(main())
