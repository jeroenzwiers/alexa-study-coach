"""Does the coach remember the student, or start from nothing every time?

Three sessions with the same student:

  Monday     they mix mitochondria and chloroplasts up and never sort it out.
  Tuesday    the session must OPEN on that confusion - name it, and ask those
             two first - rather than shuffling and hoping.
  Tuesday    they get both sides right, so it moves from open to settled, and
             stays settled the next time they are asked.

That second opening line is the whole point: it is only available to something
that kept the diagnosis rather than the score.
"""
import datetime
import json
import pathlib
import random
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

import app, history, store

history.DATA_DIR = pathlib.Path(tempfile.mkdtemp(prefix="coach-")) / "students"
STUDENT = "__test_memory__"

KNOWN = {
    "cell membrane control": "what goes in and out",
    "shape and support": "cell wall",
    "genetic material": "nucleus",
    "job of a ribosome": "to make proteins",
    "inside the nucleus": "the nucleolus",
    "movement of water": "osmosis",
    "movement of particles": "diffusion",
    "stores cell sap": "the vacuole",
    "chemical reactions": "cytoplasm",
    "no nucleus": "a prokaryotic cell",
    "packages proteins": "the golgi apparatus",
}
SWAPPED = {"releases energy": "chloroplasts", "captures light": "mitochondria"}
SORTED_OUT = {"releases energy": "mitochondria", "captures light": "chloroplasts"}


def reply_to(question: str, confused: bool) -> str:
    lowered = question.lower()
    for cue, said in {**KNOWN, **(SWAPPED if confused else SORTED_OUT)}.items():
        if cue in lowered:
            return said
    return "i dont know"


def play(length: int, confused: bool, label: str) -> str:
    turn = app.start_practice("biology_cells", length=length, student=STUDENT)
    opening = turn.speech
    print(f"--- {label} ---")
    print("ALEXA   :", opening)
    session_id = turn.session_id
    for _ in range(24):
        said = reply_to(turn.speech, confused)
        print("LEERLING:", said)
        turn = app.submit_answer(session_id, said)
        print("ALEXA   :", turn.speech)
        if turn.finished:
            break
    print()
    return opening


def saved() -> dict:
    path = history.DATA_DIR / f"{STUDENT}.json"
    return json.loads(path.read_text(encoding="utf-8"))["sets"]["biology_cells"]


def age_by_a_day() -> None:
    """Backdate the profile so the returning line has to phrase a real gap."""
    path = history.DATA_DIR / f"{STUDENT}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    data["sets"]["biology_cells"]["last_seen"] = yesterday
    for entry in data["sets"]["biology_cells"]["open_confusions"].values():
        entry["last_seen"] = yesterday
    path.write_text(json.dumps(data), encoding="utf-8")


def main() -> int:
    random.seed(11)

    first_opening = play(8, confused=True, label="MAANDAG (eerste sessie ooit)")
    after_first = saved()
    age_by_a_day()

    second_opening = play(6, confused=False, label="DINSDAG (terugkerend)")
    after_second = saved()

    third_opening = play(6, confused=False, label="WOENSDAG (na het oplossen)")

    print("profiel na dinsdag:", json.dumps(after_second, sort_keys=True))
    print()

    checks = {
        "eerste sessie groet niet met 'welcome back'":
            "welcome back" not in first_opening.lower(),
        "maandag laat een open verwarring achter":
            bool(after_first["open_confusions"]),
        "dinsdag opent met herkenning":
            "welcome back" in second_opening.lower(),
        "dinsdag benoemt de verwarring uit maandag":
            "mitochondria" in second_opening.lower() and "chloroplast" in second_opening.lower(),
        "dinsdag verwoordt wanneer dat was":
            "yesterday" in second_opening.lower(),
        "dinsdag stelt die vraag ook meteen":
            "captures light" in second_opening.lower() or "releases energy" in second_opening.lower(),
        "verwarring staat na dinsdag als opgelost":
            bool(after_second["resolved_confusions"]),
        "en niet meer als open":
            not after_second["open_confusions"],
        "woensdag begint niet opnieuw over de opgeloste verwarring":
            "swapping places" not in third_opening.lower(),
        "voortgang over sessies heen is op te vragen":
            "settled for good" in app.student_progress(STUDENT, "biology_cells").lower(),
    }
    for label, ok in checks.items():
        print(f"  {'OK  ' if ok else 'FOUT'} {label}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
