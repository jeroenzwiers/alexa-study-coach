"""Does the same confusion, seen across students, become a fact about the topic?

One student mixing osmosis up with diffusion is a fact about that student. Nine
students doing it, six of them the same way round, is a fact about the topic -
and it is the thing a teacher cannot get from marking, because marking records
that an answer was wrong, not which other idea was reached for.

Builds a synthetic class of nine and checks four things: that the aggregate is
right, that the asymmetry is found (which is the teachable part - it says which
HALF of the distinction is missing), that a confusion held by one student alone
is not dressed up as a pattern, and that nothing identifying a student can reach
the report.
"""
import datetime
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

import app, history, store

history.DATA_DIR = pathlib.Path(tempfile.mkdtemp(prefix="coach-")) / "students"

TODAY = datetime.date.today().isoformat()
SET = "biology_cells"

# c8 osmosis / c9 diffusion; c1 mitochondria / c6 chloroplasts; c4 nucleus / c7 nucleolus
OSMOSIS, DIFFUSION = "c8", "c9"
MITO, CHLORO = "c1", "c6"
NUCLEUS, NUCLEOLUS = "c4", "c7"


def profile(name: str, *, open_pairs=(), settled_pairs=()) -> None:
    record = {
        "sessions": 2,
        "last_seen": TODAY,
        "last_score": [5, 8],
        "difficulty": 2,
        "open_confusions": {
            f"{min(a, b)}|{max(a, b)}": {"count": 3, "asked": a, "said": b, "last_seen": TODAY}
            for a, b in open_pairs
        },
        "resolved_confusions": {
            f"{min(a, b)}|{max(a, b)}": {"resolved_on": TODAY, "took": 3, "asked": a, "said": b}
            for a, b in settled_pairs
        },
    }
    history.save({"student": name, "sets": {SET: record}})


def build_class() -> None:
    # Six students swap osmosis and diffusion the SAME way: asked about osmosis,
    # they answer diffusion. Three of those six have since settled it.
    for i in range(3):
        profile(f"pupil_{i}", open_pairs=[(OSMOSIS, DIFFUSION)])
    for i in range(3, 6):
        profile(f"pupil_{i}", settled_pairs=[(OSMOSIS, DIFFUSION)])
    # One goes the other way round, so the direction is lopsided but not unanimous.
    profile("pupil_6", open_pairs=[(DIFFUSION, OSMOSIS)])
    # Four students also swap the two organelles - a second, smaller pattern.
    for i in (0, 1, 2, 7):
        name = f"pupil_{i}"
        existing = history.load(name)
        record = history.record_for(existing, SET)
        # record_for() seeds sessions at 0, and a student with no sessions is
        # correctly not counted as having practised - so set it, don't default it.
        record["sessions"] = max(record.get("sessions", 0), 2)
        record["last_seen"] = TODAY
        record["open_confusions"][f"{MITO}|{CHLORO}"] = {
            "count": 2, "asked": MITO, "said": CHLORO, "last_seen": TODAY,
        }
        history.save(existing)
    # And one student alone confuses nucleus with nucleolus. One student is not
    # a pattern, and must not be reported as one.
    profile("pupil_8", open_pairs=[(NUCLEUS, NUCLEOLUS)])


def main() -> int:
    build_class()
    studied, confusions = history.topic_map(SET)
    report = app.class_report(SET)

    print("KLAS     :", studied, "leerlingen")
    for c in confusions:
        way = c.dominant_direction()
        print(f"  {c.pair}  studenten={c.students} open={c.open_students} "
              f"opgelost={c.settled_students} richting={way}")
    print()
    print("RAPPORT  :", report)
    print()

    top = confusions[0] if confusions else None
    lopsided = top.dominant_direction() if top else None
    singleton = next((c for c in confusions if set(c.pair) == {NUCLEUS, NUCLEOLUS}), None)
    lower = report.lower()

    checks = {
        "telt alle leerlingen die de set deden": studied == 9,
        "grootste verwarring is osmose/diffusie": top is not None
            and set(top.pair) == {OSMOSIS, DIFFUSION},
        "zeven leerlingen hebben die verwarring": top is not None and top.students == 7,
        "drie ervan hebben hem opgelost": top is not None and top.settled_students == 3,
        "vindt de scheve richting": lopsided is not None and lopsided[1] == 6,
        "richting klopt: gevraagd naar osmose, gezegd diffusie": lopsided is not None
            and lopsided[0] == (OSMOSIS, DIFFUSION),
        "tweede patroon telt vier leerlingen": any(
            set(c.pair) == {MITO, CHLORO} and c.students == 4 for c in confusions
        ),
        "eenling wordt geteld maar niet als patroon": singleton is not None
            and singleton.students == 1,
        "rapport noemt osmose en diffusie": "osmosis" in lower and "diffusion" in lower,
        "rapport spreekt aantallen uit": "nine students" in lower and "seven student" in lower,
        "rapport benoemt de scheve richting": "same way" in lower,
        "rapport meldt wie het al opgeloste heeft": "settled" in lower,
        "rapport verzwijgt de eenling": "nucleolus" not in lower,
        "rapport bevat geen enkele leerlingnaam": "pupil" not in lower,
        "minimum nul blijft privacyvloer twee": "nucleolus" not in app.class_report(SET, minimum=0).lower(),
        "minimum een blijft privacyvloer twee": "nucleolus" not in app.class_report(SET, minimum=1).lower(),
    }
    for label, ok in checks.items():
        print(f"  {'OK  ' if ok else 'FOUT'} {label}")
    failed = [k for k, v in checks.items() if not v]
    print(f"\n{len(checks) - len(failed)}/{len(checks)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
