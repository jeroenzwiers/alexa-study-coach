"""What the coach remembers about a student between sessions.

A quiz that forgets you is a demo. The moment it becomes a product is the moment
it opens with "last week chloroplasts and mitochondria kept swapping places -
shall we settle that first?", because that sentence is only available to
something that kept the diagnosis rather than the score.

So this stores the one thing worth carrying: which confusions are still open,
which have been settled, and roughly where the student's level sits.

STORAGE
-------
One JSON file per student under `data/students/`. That is deliberately the
dumbest thing that works locally, and it is fenced behind `load` and `save` so
the Lambda deployment can swap in DynamoDB - keyed on the same student id -
without touching a caller. Nothing else in the server touches the filesystem.
"""

from __future__ import annotations

import datetime as _dt
import json
import pathlib
import re
from dataclasses import dataclass

DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "data" / "students"

# A student id carrying this marker is synthetic: a harness run, the
# judge-facing demo, anything driven by a script rather than by a child.
#
# Such a student still gets a real profile, because the tests and the demo exist
# to prove that the memory works across sessions - stubbing that out would prove
# nothing. But it is kept in a scratch directory beside the real ones, and never
# counted in an aggregate. Otherwise every rehearsal adds a fictional pupil to
# the class report, and after a handful of runs the teacher's "nine students
# have practised The Cell" is describing the rehearsals rather than the class.
SYNTHETIC_MARKER = "__"


def is_synthetic(student: str) -> bool:
    return (student or "").startswith(SYNTHETIC_MARKER)


def clear_scratch() -> int:
    """Throw away the synthetic profiles. Returns how many went.

    Called when the server starts, so that a run of the harness or the demo
    begins from nothing rather than from whatever the last rehearsal left
    behind. Nothing real can be reached from here: the directory only ever
    receives profiles whose student id carries the marker.
    """
    scratch = DATA_DIR.parent / "scratch"
    if not scratch.exists():
        return 0
    gone = 0
    for path in scratch.glob("*.json"):
        try:
            path.unlink()
            gone += 1
        except OSError:
            continue
    return gone


# How long a confusion stays interesting. A misconception from three months ago
# is not evidence about the student today, and re-drilling it would be a worse
# use of the session than moving on.
STALE_AFTER_DAYS = 90


def _today() -> str:
    return _dt.date.today().isoformat()


def _safe_id(student: str) -> str:
    """A filename that cannot escape the data directory."""
    cleaned = re.sub(r"[^a-z0-9_-]", "_", (student or "default").lower())[:64]
    return cleaned or "default"


def _dir_for(student: str) -> pathlib.Path:
    """Where this student's profile lives: the real set, or the scratch set.

    Read off DATA_DIR each time rather than resolved once at import, so that a
    harness which redirects DATA_DIR to a temporary directory takes the scratch
    directory along with it.
    """
    return DATA_DIR.parent / "scratch" if is_synthetic(student) else DATA_DIR


def profile_path(student: str) -> pathlib.Path:
    """Where this student's profile is written. For callers that need the file."""
    return _dir_for(student) / f"{_safe_id(student)}.json"


def _blank(student: str) -> dict:
    return {"student": student, "sets": {}}


def load(student: str) -> dict:
    path = profile_path(student)
    if not path.exists():
        return _blank(student)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # A corrupt profile must never cost the student their session.
        return _blank(student)
    data.setdefault("student", student)
    data.setdefault("sets", {})
    return data


def save(profile: dict) -> None:
    student = profile.get("student", "default")
    directory = _dir_for(student)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{_safe_id(student)}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(profile, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)   # atomic, so a crash mid-write cannot truncate a profile


def record_for(profile: dict, study_set_id: str) -> dict:
    return profile.setdefault("sets", {}).setdefault(
        study_set_id,
        {
            "sessions": 0,
            "last_seen": None,
            "last_score": None,
            "difficulty": 1,
            "open_confusions": {},
            "resolved_confusions": {},
        },
    )


def _days_since(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        return (_dt.date.today() - _dt.date.fromisoformat(iso)).days
    except ValueError:
        return None


def open_confusions(profile: dict, study_set_id: str) -> dict:
    """Confusions still unsettled and still recent enough to matter."""
    record = record_for(profile, study_set_id)
    fresh = {}
    for key, entry in record.get("open_confusions", {}).items():
        age = _days_since(entry.get("last_seen"))
        if age is None or age <= STALE_AFTER_DAYS:
            fresh[key] = entry
    return fresh


def carried_difficulty(profile: dict, study_set_id: str) -> int:
    return int(record_for(profile, study_set_id).get("difficulty") or 1)


def remember(profile: dict, session, study_set) -> dict:
    """Fold a session's diagnosis into the long-term record.

    Everything here is about the confusions, not the score: the score is a fact
    about one evening, the confusions are a fact about the student.

    Safe to call REPEATEDLY for the same session, which is what lets a session
    be filed as it goes rather than only when its last question is answered. A
    student who puts the speaker down halfway used to lose the whole evening -
    every confusion found, every pair settled - and the ones most likely to stop
    early are the ones with the most to remember, so the loss was not evenly
    spread. `session.written` records what is already on disk so a second call
    folds in only what has happened since.
    """
    record = record_for(profile, session.study_set_id)
    if not session.persisted:
        record["sessions"] = int(record.get("sessions", 0)) + 1
        session.persisted = True
    record["last_seen"] = _today()
    record["last_score"] = [session.correct, session.asked]
    record["difficulty"] = int(getattr(session, "difficulty", 1))

    opened = dict(record.get("open_confusions", {}))
    resolved = dict(record.get("resolved_confusions", {}))

    for key, count in session.confusions.items():
        flat = "|".join(key)
        if flat in resolved and flat not in session.resolved:
            # It came back after being settled. That is worth knowing, and it
            # goes back on the open list rather than being quietly forgotten.
            resolved.pop(flat, None)
        asked, said = session.last_direction.get(key, key)
        previous = opened.get(flat, {}).get("count", 0)
        # A carried-in confusion starts the session pre-loaded with its own
        # history; adding that back would count last week's misses twice. So
        # would anything this session has already filed.
        fresh = max(0, count - session.seeded.get(key, 0) - session.written.get(key, 0))
        if not fresh and flat in opened:
            continue
        session.written[key] = count - session.seeded.get(key, 0)
        opened[flat] = {
            "count": previous + fresh,
            "asked": asked,
            "said": said,
            "last_seen": _today(),
        }

    for key in session.resolved:
        flat = "|".join(key)
        entry = opened.pop(flat, {})
        resolved[flat] = {
            "resolved_on": _today(),
            "took": entry.get("count") or session.confusions.get(key, 0),
            "asked": entry.get("asked", key[0]),
            "said": entry.get("said", key[1]),
        }

    record["open_confusions"] = opened
    record["resolved_confusions"] = resolved
    return profile


def _when(days: int | None) -> str:
    if days is None:
        return "last time"
    if days <= 0:
        return "earlier today"
    if days == 1:
        return "yesterday"
    if days <= 6:
        return "earlier this week"
    if days <= 13:
        return "last week"
    if days <= 40:
        return "a few weeks ago"
    return "a while back"


def opening(profile: dict, study_set) -> tuple[str | None, tuple[str, str] | None]:
    """The welcome-back line, and the confusion worth reopening.

    Returns (speech, pair). Both are None for a student we have not met, which
    is what keeps a first session clean rather than apologetic about having no
    history.
    """
    record = record_for(profile, study_set.id)
    if not record.get("sessions"):
        return None, None

    when = _when(_days_since(record.get("last_seen")))
    unsettled = open_confusions(profile, study_set.id)

    if unsettled:
        flat = max(unsettled, key=lambda k: unsettled[k].get("count", 0))
        entry = unsettled[flat]
        asked = study_set.card(entry.get("asked", ""))
        said = study_set.card(entry.get("said", ""))
        if asked is not None and said is not None:
            pair = (asked.id, said.id)
            return (
                f"Welcome back. {when.capitalize()} "
                f"{said.canonical.rstrip('.').lower()} and "
                f"{asked.canonical.rstrip('.').lower()} kept swapping places. "
                f"Shall we settle that first?",
                pair,
            )

    settled = record.get("resolved_confusions", {})
    if settled:
        return f"Welcome back. You sorted out {len(settled)} confusion" \
               f"{'s' if len(settled) != 1 else ''} last time. Let's keep going.", None

    score = record.get("last_score")
    if score and score[1]:
        return f"Welcome back. {when.capitalize()} you got {score[0]} out of {score[1]}.", None
    return "Welcome back.", None


def summary(profile: dict, study_set) -> str:
    """The across-time report - the thing a single session cannot say."""
    record = record_for(profile, study_set.id)
    if not record.get("sessions"):
        return f"No practice recorded yet on {study_set.title}."

    sessions = record["sessions"]
    line = (
        f"{sessions} session{'s' if sessions != 1 else ''} on {study_set.title}, "
        f"last {_when(_days_since(record.get('last_seen')))}."
    )

    settled = record.get("resolved_confusions", {})
    unsettled = open_confusions(profile, study_set.id)

    if settled:
        names = []
        for entry in settled.values():
            asked = study_set.card(entry.get("asked", ""))
            said = study_set.card(entry.get("said", ""))
            if asked is not None and said is not None:
                names.append(
                    f"{asked.canonical.rstrip('.').lower()} against "
                    f"{said.canonical.rstrip('.').lower()}"
                )
        if names:
            line += " Settled for good: " + _join(names) + "."

    if unsettled:
        names = []
        for entry in unsettled.values():
            asked = study_set.card(entry.get("asked", ""))
            said = study_set.card(entry.get("said", ""))
            if asked is not None and said is not None:
                names.append(
                    f"{asked.canonical.rstrip('.').lower()} against "
                    f"{said.canonical.rstrip('.').lower()}"
                )
        if names:
            line += " Still open: " + _join(names) + "."
    elif settled:
        line += " Nothing open at the moment."

    return line


def _join(names: list[str]) -> str:
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + f", and {names[-1]}"


# --- the same confusions, seen across everyone who studied the topic -------
#
# One student mixing osmosis up with diffusion is a fact about that student.
# Nine students doing it, and six of them going the same way round, is a fact
# about the TOPIC - and it is the one thing here a teacher cannot get from
# marking, because marking records that an answer was wrong, not which other
# idea was reached for.
#
# Everything below is aggregate by construction. It counts students per
# confusion and never carries a student's identity out of this module: the
# reports built on it can say "seven students" and cannot say which seven.
# That is deliberate for a product whose users are children.

# Below this, a "pattern across students" is one student with an opinion.
MIN_STUDENTS = 2

# A confusion counts as one-directional when this share of the students who
# have it make the same swap. Two thirds, because the interesting claim is
# "they nearly all go the same way", not "slightly more than half do".
LOPSIDED = 2 / 3


@dataclass(frozen=True)
class TopicConfusion:
    """One confusion, summed over every student who has met it."""

    pair: tuple[str, str]
    open_students: int
    settled_students: int
    directions: dict          # (asked_card, said_card) -> how many students

    @property
    def students(self) -> int:
        return self.open_students + self.settled_students

    def dominant_direction(self) -> tuple[tuple[str, str], int] | None:
        """The way round most students get it, when most of them agree.

        Returns None when the swap goes both ways roughly evenly - which is
        itself worth knowing, and worth not overstating.
        """
        if not self.directions:
            return None
        way, count = max(self.directions.items(), key=lambda kv: kv[1])
        total = sum(self.directions.values())
        return (way, count) if total and count / total >= LOPSIDED else None


def all_profiles() -> list[dict]:
    """Every stored REAL profile. On Lambda a scan; here a directory.

    Scratch profiles live elsewhere and so are already out of reach, but the id
    is checked too: a synthetic student that predates the split, or one written
    by hand, must not turn up in a class report either.
    """
    if not DATA_DIR.exists():
        return []
    out = []
    for path in sorted(DATA_DIR.glob("*.json")):
        try:
            profile = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue          # one unreadable profile must not lose the rest
        if is_synthetic(profile.get("student", "")):
            continue
        out.append(profile)
    return out


def topic_map(study_set_id: str, profiles: list[dict] | None = None) -> tuple[int, list[TopicConfusion]]:
    """Aggregate confusions over every student who has practised a study set.

    Returns how many students have practised it, and its confusions ordered by
    how many students hit them.
    """
    studied = 0
    tally: dict[tuple[str, str], dict] = {}

    for profile in (all_profiles() if profiles is None else profiles):
        record = profile.get("sets", {}).get(study_set_id)
        if not record or not record.get("sessions"):
            continue

        # A class report describes the class that is here now. A student who
        # last practised beyond the staleness window has very likely moved on,
        # and counting them told a teacher that seven of HER students share a
        # confusion when it was last year's cohort - with no date in the report
        # to make that visible. The session path already forgets on this clock;
        # the aggregate has to forget on it too.
        age = _days_since(record.get("last_seen"))
        if age is not None and age > STALE_AFTER_DAYS:
            continue

        studied += 1

        seen: set[tuple[str, str]] = set()
        for state, entries in (
            # Through `open_confusions`, so the 90-day cutoff that the session
            # path applies applies here too. Reading the record directly let a
            # class report count confusions from a cohort that has since left,
            # and it never states a date, so nobody could notice. A confusion
            # that was SETTLED does not go stale in the same way: it is a thing
            # the student demonstrated, not a thing still hanging over them.
            ("open", open_confusions(profile, study_set_id)),
            ("settled", record.get("resolved_confusions", {})),
        ):
            for flat, entry in entries.items():
                pair = tuple(flat.split("|"))
                if len(pair) != 2 or pair in seen:
                    continue      # a pair counts once per student, not once per row
                seen.add(pair)
                slot = tally.setdefault(pair, {"open": 0, "settled": 0, "dirs": {}})
                slot[state] += 1
                way = (entry.get("asked"), entry.get("said"))
                if all(way):
                    slot["dirs"][way] = slot["dirs"].get(way, 0) + 1

    confusions = [
        TopicConfusion(pair=pair, open_students=slot["open"],
                       settled_students=slot["settled"], directions=slot["dirs"])
        for pair, slot in tally.items()
    ]
    confusions.sort(key=lambda c: (-c.students, -c.open_students, c.pair))
    return studied, confusions
