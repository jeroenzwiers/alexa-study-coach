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
    path = history.profile_path(STUDENT)
    return json.loads(path.read_text(encoding="utf-8"))["sets"]["biology_cells"]


def age_by_a_day() -> None:
    """Backdate the profile so the returning line has to phrase a real gap."""
    path = history.profile_path(STUDENT)
    data = json.loads(path.read_text(encoding="utf-8"))
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    data["sets"]["biology_cells"]["last_seen"] = yesterday
    for entry in data["sets"]["biology_cells"]["open_confusions"].values():
        entry["last_seen"] = yesterday
    path.write_text(json.dumps(data), encoding="utf-8")


def abandonment_checks() -> dict:
    """A session put down halfway must still be remembered.

    `_remember` used to run on exactly one path - the turn that answers the last
    question - so a student who stopped early wrote nothing at all. The students
    likeliest to stop are the ones with the most confusions, and drilling makes
    their session the longest, so the loss was concentrated on exactly the
    evenings worth keeping. It also silently narrowed the class report to
    students who finish.

    Also checks the other half: filing on every turn must not count the session
    more than once, or inflate a confusion by re-adding it on each write.
    """
    study_set = store.STUDY_SETS["biology_cells"]
    pair = ("c1", "c6")

    def play(student: str, stop_after: int | None) -> None:
        random.seed(5)
        turn = app.start_practice("biology_cells", length=13, student=student)
        asked = 0
        while not turn.finished and turn.question:
            asked += 1
            card = next(c for c in study_set.cards if c.question == turn.question)
            other = pair[1] if card.id == pair[0] else pair[0]
            said = (
                study_set.card(other).accepted[0] if card.id in pair else card.accepted[0]
            )
            turn = app.submit_answer(turn.session_id, said)
            if stop_after is not None and asked >= stop_after:
                return          # the student puts the speaker down

    def record(student: str) -> dict:
        path = history.profile_path(student)
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))["sets"]["biology_cells"]

    play("__abandon_half__", stop_after=6)
    half = record("__abandon_half__")
    play("__abandon_full__", stop_after=None)
    full = record("__abandon_full__")

    return {
        "afgebroken sessie wordt toch bewaard": bool(half),
        "afgebroken sessie bewaart de verwarring": bool(half.get("open_confusions")),
        "afgebroken sessie telt als een sessie": half.get("sessions") == 1,
        "uitgespeelde sessie telt ook maar een keer": full.get("sessions") == 1,
        "schrijven per beurt telt de verwarring niet dubbel": (
            0 < half["open_confusions"]["c1|c6"]["count"]
            <= full["open_confusions"]["c1|c6"]["count"]
        ),
    }


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
    checks.update(abandonment_checks())
    for label, ok in checks.items():
        print(f"  {'OK  ' if ok else 'FOUT'} {label}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
