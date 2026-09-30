"""Seed a simulated class so the demo's class report has something to report.

The class report counts real students, and a fresh checkout has none. This
writes nine fabricated profiles into `data/students/` so the third act of the
demo has a population to aggregate - the same shape `harness/test_topic_map.py`
asserts against, and the same one the README quotes.

They are fabrications and the demo narration says so out loud. Two things keep
that honest rather than merely stated:

  - `data/` is gitignored, so nothing here reaches anyone who clones the repo.
  - every name is prefixed `demo_`, so `--clear` can remove exactly these and
    nothing else.

    python preview/seed_class.py          # write them
    python preview/seed_class.py --clear  # remove them again
"""

from __future__ import annotations

import datetime
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

import history  # noqa: E402  - needs ROOT on the path first

TODAY = datetime.date.today().isoformat()
SET = "biology_cells"
PREFIX = "demo_pupil_"

# c8 osmosis / c9 diffusion, c1 mitochondria / c6 chloroplasts,
# c4 nucleus / c7 nucleolus.
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


def seed() -> None:
    # Six swap osmosis and diffusion the same way round - asked about osmosis,
    # they answer diffusion. Three of those six have since settled it, which is
    # what lets the report say so.
    for i in range(3):
        profile(f"{PREFIX}{i}", open_pairs=[(OSMOSIS, DIFFUSION)])
    for i in range(3, 6):
        profile(f"{PREFIX}{i}", settled_pairs=[(OSMOSIS, DIFFUSION)])
    # One goes the other way, so the direction is lopsided rather than unanimous.
    # A report that claimed unanimity here would be overstating its evidence.
    profile(f"{PREFIX}6", open_pairs=[(DIFFUSION, OSMOSIS)])
    # Four also swap the two organelles: a second, smaller pattern underneath.
    for i in (0, 1, 2, 7):
        name = f"{PREFIX}{i}"
        existing = history.load(name)
        record = history.record_for(existing, SET)
        record["sessions"] = max(record.get("sessions", 0), 2)
        record["last_seen"] = TODAY
        record["open_confusions"][f"{MITO}|{CHLORO}"] = {
            "count": 2, "asked": MITO, "said": CHLORO, "last_seen": TODAY,
        }
        history.save(existing)
    # And one alone confuses the nucleus with the nucleolus. One student is not
    # a pattern and must not be reported as one - which is the privacy floor
    # doing its job, visible in the demo by its absence.
    profile(f"{PREFIX}8", open_pairs=[(NUCLEUS, NUCLEOLUS)])


def clear() -> int:
    removed = 0
    for path in sorted(history.DATA_DIR.glob(f"{PREFIX}*.json")):
        path.unlink()
        removed += 1
    return removed


def main() -> int:
    if "--clear" in sys.argv:
        print(f"removed {clear()} seeded profiles from {history.DATA_DIR}")
        return 0
    seed()
    written = len(list(history.DATA_DIR.glob(f"{PREFIX}*.json")))
    print(f"wrote {written} simulated profiles to {history.DATA_DIR}")
    print("These are fabrications. The demo narration says 'simulated' out loud.")
    print("Remove them with: python preview/seed_class.py --clear")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
