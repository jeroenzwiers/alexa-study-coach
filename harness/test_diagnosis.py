"""Does the session diagnose and then SETTLE, or only score?

Drives a student who mixes two concepts up, is drilled on the contrast, and
then gets both sides right. Checks the whole arc: the confusion is noticed as a
pattern rather than bad luck, the other side of it is probed rather than left to
the shuffle, the contrast is drilled, and - the part a flashcard app can never
reach - the confusion is declared settled and reported as settled.
"""
import pathlib
import random
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

import app, history, store

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


def main() -> int:
    random.seed(7)
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
    checks = {
        "een verwisseling herkend als patroon": bool(session.confusions),
        "andere kant van de verwarring actief bevraagd": session.bonus > 0 or saw_contrast,
        "contrastvraag gesteld": saw_contrast,
        "verwarring opgelost gemeld tijdens de sessie": saw_resolution,
        "verwarring staat als opgelost in de sessie": bool(session.resolved),
        "rapport benoemt de oplossing": "settled during the session" in report,
        "geen open verwarring meer over": session.dominant_confusion() is None,
    }
    for label, ok in checks.items():
        print(f"  {'OK  ' if ok else 'FOUT'} {label}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
