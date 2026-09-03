"""Turn a worksheet or a topic into a study set the diagnosis can actually use.

WHY THIS IS NOT "GENERATE TWENTY QUESTIONS"
-------------------------------------------
Study Coach does not mark a spoken answer by similarity. It attributes it to the
nearest candidate in a CLOSED set - every answer that appears anywhere in the
study set (see server/grading.py). That is what buys the diagnosis: being wrong
stops being one bit, because we know which other answer was said.

It also means a naively generated set breaks the whole product. If a student
answers "chloroplasts" and no card in the set has "chloroplasts" as an answer,
the grader has nothing to attribute it to; the response comes back `ambiguous`,
the coach says "I didn't catch that", and no confusion is ever detected. The
questions look fine. The feature is dead.

So this generator is distractor-first. It is asked to build the set AROUND the
confusions - which concepts students actually swap, and in which direction -
and to guarantee that both halves of every confusion are cards. The confusion
graph is the artefact; the questions are how it is delivered.

AND THEN IT IS CHECKED BY THE REAL GRADER
-----------------------------------------
Generating content with a model and hoping is not good enough for something the
diagnosis depends on. After generation, every set is run through the actual
`grading.grade` that serves live traffic:

  * each accepted phrasing must be attributed to its own card
  * each distractor must be attributed to the card it is meant to be confused
    with - not merely marked wrong
  * no phrasing may collide across two cards, which would make attribution a
    coin flip

A set that fails is reported and not written. The model proposes; the grader
decides.

The model runs OFFLINE, here, never in the request path - the 500 ms budget in
server/app.py has no room for it, and does not need it.

Usage:
    python tools/build_study_set.py --topic "Photosynthesis" --level "GCSE biology"
    python tools/build_study_set.py --source worksheet.txt --title "Unit 3" --out content/unit3.json
    python tools/build_study_set.py --topic "French irregular verbs" --cards 10 --dry-run
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import anthropic
from pydantic import BaseModel, Field

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))
sys.path.insert(0, str(ROOT / "tools"))

from verify_study_set import verify as verify_cards

MODEL = "claude-opus-5"


class GeneratedCard(BaseModel):
    id: str = Field(description="c1, c2, c3 ... in order.")
    question: str = Field(description="One question, phrased to be read aloud.")
    accepted: list[str] = Field(
        description=(
            "Every phrasing a student might SAY for this answer, shortest first. "
            "Two to five entries. Spoken forms, not sentences."
        )
    )
    canonical: str = Field(description="The answer as the coach says it back, ending in a full stop.")
    difficulty: int = Field(description="1 easy, 2 medium, 3 hard.")
    hint: str = Field(description="A nudge that narrows it down without giving the answer.")
    explanation: str = Field(description="One or two spoken sentences on the concept.")
    confused_with: str = Field(
        description=(
            "The id of the card in THIS set whose answer a student is most likely "
            "to give instead of this one. Empty string only if there is genuinely none."
        )
    )
    misconception: str = Field(
        description=(
            "One spoken sentence naming BOTH concepts and the distinction between "
            "them. Read aloud immediately after a wrong answer."
        )
    )


class GeneratedSet(BaseModel):
    id: str = Field(description="lowercase_with_underscores, unique.")
    subject: str
    title: str
    level: str
    cards: list[GeneratedCard]


BRIEF = """You are building a study set for a voice revision coach that does something \
unusual, and the whole design depends on you understanding it.

When a student answers out loud and gets it wrong, the coach does not say "no". It works \
out WHICH other concept they reached for, and says so. It can only do that because it \
marks answers by attributing the utterance to the nearest answer in a CLOSED set - every \
answer that appears anywhere in this study set. There is no similarity threshold.

The consequence is the thing you must design around:

    If a student gives a wrong answer that is not itself an answer in this set,
    the coach cannot attribute it, cannot name the misconception, and falls back
    to "I did not catch that". The set has failed, however good the questions look.

So do not write a list of independent questions. Build the set around the confusions.

RULES

1. Choose concepts that come in confusable pairs, and put BOTH halves of every pair in \
the set. The classic shapes: two things that swap (mitochondria / chloroplasts), a \
whole and its part (nucleus / nucleolus), a general case and its special case \
(diffusion / osmosis), two things with near-identical names.

2. `confused_with` names the card in this set whose answer a student would actually give \
instead. Make the graph real: most cards should point at something, and pairs should \
usually point at each other.

3. `accepted` holds what a student SAYS. Short. "the mitochondria", "mitochondria", \
"mitochondrion" - not "The mitochondria release energy from glucose". Include the \
natural spoken variants, because speech recognition will mangle them and the grader \
compares sounds as well as letters.

4. No phrasing may appear in two cards, and no phrasing may be a substring of another \
card's phrasing. That makes attribution a coin flip and the coach will refuse to guess.

5. `misconception` names both concepts and the distinction, in one sentence a voice can \
read: "Chloroplasts capture energy from light; mitochondria release it from food."

6. Spread `difficulty` across 1, 2 and 3. Roughly half at 1, and at least two at 3.

7. Everything is spoken. No markup, no lists, no brackets, no "e.g.".

Write %(n)d cards."""


def build_prompt(args, source_text: str | None) -> str:
    brief = BRIEF % {"n": args.cards}
    if source_text:
        return (
            f"{brief}\n\nBuild the set from this material. Keep to what it covers; "
            f"add a card only when it is the missing half of a confusion pair.\n\n"
            f"<material>\n{source_text}\n</material>"
        )
    return (
        f"{brief}\n\nTopic: {args.topic}\nLevel: {args.level}\n\n"
        "Pick the concepts on this topic that students most reliably get mixed up."
    )


def generate(args, source_text: str | None) -> tuple[GeneratedSet, object]:
    client = anthropic.Anthropic()
    # Non-streaming with the documented parse() helper: one study set is a few
    # thousand output tokens, well inside both max_tokens and the default
    # 10-minute client timeout. Raise --cards far beyond ~25 and that stops
    # being true.
    response = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": build_prompt(args, source_text)}],
        output_format=GeneratedSet,
    )
    return response.parsed_output, response.usage


# --- checking the model's work with the code that will have to live with it ---

def verify(study_set: GeneratedSet) -> tuple[list[str], dict]:
    """Run the generated set through the live grader.

    The checks live in verify_study_set.py because they are not a generation
    concern: a hand-written set can fail them just as easily, and one that does
    must not ship either. See harness/test_content.py.
    """
    return verify_cards([card.model_dump() for card in study_set.cards])


def to_content_json(study_set: GeneratedSet, note: str) -> dict:
    """The on-disk shape server/store.py loads. `confused_with` is deliberately
    not written: it was scaffolding for generation, and at runtime the confusion
    graph is discovered from what the student actually says."""
    return {
        "id": study_set.id,
        "subject": study_set.subject,
        "title": study_set.title,
        "level": study_set.level,
        "source_note": note,
        "cards": [
            {
                "id": c.id,
                "question": c.question,
                "accepted": c.accepted,
                "canonical": c.canonical,
                "difficulty": c.difficulty,
                "hint": c.hint,
                "explanation": c.explanation,
                "misconception": c.misconception,
            }
            for c in study_set.cards
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--topic", help="What to build a set about.")
    src.add_argument("--source", type=pathlib.Path, help="A worksheet or notes to build from.")
    ap.add_argument("--level", default="secondary", help="Who it is for, e.g. 'GCSE biology'.")
    ap.add_argument("--cards", type=int, default=13, help="How many cards (default 13).")
    ap.add_argument("--out", type=pathlib.Path, help="Where to write. Defaults to content/<id>.json")
    ap.add_argument("--dry-run", action="store_true", help="Print the set; write nothing.")
    ap.add_argument("--force", action="store_true", help="Write even if verification fails.")
    args = ap.parse_args()

    source_text = args.source.read_text(encoding="utf-8") if args.source else None

    print(f"Generating {args.cards} cards with {MODEL}...", file=sys.stderr)
    study_set, usage = generate(args, source_text)
    problems, stats = verify(study_set)

    print(file=sys.stderr)
    print(f"  set          : {study_set.id} - {study_set.title} ({study_set.subject})", file=sys.stderr)
    print(f"  cards        : {stats['cards']}, difficulty {stats['difficulty']}", file=sys.stderr)
    labelled = sum(1 for c in study_set.cards if c.confused_with)
    print(f"  confusions   : {labelled} cards point at a partner", file=sys.stderr)
    print(f"  own phrasings: {stats['own_ok']} attributed to their own card, "
          f"{stats['own_bad']} not", file=sys.stderr)
    print(f"  cross-check  : {stats['cross_ok']} answers land on the right card, "
          f"{stats['cross_bad']} do not", file=sys.stderr)
    print(f"  distractors  : {stats['pairs_ok']} land on their intended partner, "
          f"{stats['pairs_bad']} do not", file=sys.stderr)
    print(f"  tokens       : {usage.input_tokens} in, {usage.output_tokens} out", file=sys.stderr)

    if problems:
        print(f"\n  {len(problems)} problem(s):", file=sys.stderr)
        for problem in problems[:20]:
            print(f"    - {problem}", file=sys.stderr)
        if len(problems) > 20:
            print(f"    ... and {len(problems) - 20} more", file=sys.stderr)
    else:
        print("\n  clean - every phrasing and every distractor lands where it should",
              file=sys.stderr)

    payload = to_content_json(
        study_set,
        f"Generated by tools/build_study_set.py from "
        f"{'a worksheet' if source_text else repr(args.topic)}, then verified against grading.py.",
    )

    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if not problems else 1

    if problems and not args.force:
        print("\nNot written. Re-run to try again, or pass --force to keep it anyway.",
              file=sys.stderr)
        return 1

    out = args.out or (ROOT / "content" / f"{study_set.id}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWritten to {out.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
