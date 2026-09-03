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

DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "data" / "students"

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


def _blank(student: str) -> dict:
    return {"student": student, "sets": {}}


def load(student: str) -> dict:
    path = DATA_DIR / f"{_safe_id(student)}.json"
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
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{_safe_id(profile.get('student', 'default'))}.json"
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

    Called when a session ends. Everything here is about the confusions, not the
    score: the score is a fact about one evening, the confusions are a fact
    about the student.
    """
    record = record_for(profile, session.study_set_id)
    record["sessions"] = int(record.get("sessions", 0)) + 1
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
        # history; adding that back would count last week's misses twice.
        fresh = max(0, count - session.seeded.get(key, 0))
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
