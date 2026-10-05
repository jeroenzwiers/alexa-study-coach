# Study Coach Golden Demo Script

**Target runtime:** 2:54, from the length of the recorded clips. Hard limit 3:00 - judges are not required to watch past
it. A simulated Alexa+ experience backed by the real MCP server.

**The session talks. You don't, except at the two ends.** Every card speaks -
the questions, the wrong answers, the ordinary right ones, the persistence, the
second subject. Nothing on screen is silent. Three earlier
cuts of this script had the narrator explaining a demo that had been muted to
make room for the explaining, which is backwards.

So your job is the opening and the close. In between you press the space bar and
let it run.

## The runtime

**Expected 2:54.** Every line is now a pre-recorded clip rather than a browser
voice, so the length is the sum of 33 files plus the gaps the page inserts, and
that is arithmetic rather than an estimate:

| | |
| --- | --- |
| narrator, 5 clips | 25.1 s |
| coach, 16 clips | 131.3 s |
| student, 12 clips | 8.4 s |
| gaps between cards | 9.7 s |
| **total** | **2:54** |

Six seconds of margin. If that is too tight, re-split at a higher tempo -
`--tempo 1.35` takes about twelve seconds off and still sounds unhurried.

Record once and check anyway. Every number in this file has been wrong at least
once.

## What is deliberately not in this video

**The persistence cards.** The server is still asked for the student's history
and still greets them back - `harness/test_demo_golden.py` asserts both against
a real run - but the three cards are not rendered. They cost 21 seconds of a
three-minute video, and "it remembers the diagnosis, not the score" is a claim
that reads perfectly well written down. Seeing a second subject work cannot be
written down; it has to be watched. That is the trade, and it is why the
computer science act survived and this did not.

**The class report** - the one that aggregates confusions across everyone who
studied a set and names which half of a distinction a group is missing. It is
the strongest claim this project has about impact, and it is out, because the
nine students behind it do not exist. They were seeded so the report had a
population, the card was tagged `simulated cohort`, and the narration said
"simulated" out loud. Three safeguards around a sentence that still sounds, to
someone glancing up, like nine children used this.

It belongs in the Devpost description instead, where there is room to say
plainly that the mechanism is demonstrated against generated profiles.
`harness/test_topic_map.py` proves the feature works; the video does not need to
imply a user base.

## Before you record

- **Step mode on.** The session then waits for the space bar between cards, so
  your two blocks are never rushed and the pauses are yours. It does not stop on
  the two ordinary correct answers - those speak and move on by themselves.
- **Full screen**, `F11`. A Chrome update notice in the corner is a stray line
  of Dutch in an English-only submission.
- **Zoom to about 150%**, `Ctrl` and `+`. The small monospace labels are what
  YouTube's compression eats.
- **Drop your recording level a few decibels.** The first take peaked at
  -0.1 dB, hard against the ceiling.
- **Two voices, two roles.** Pick different ones in the coach and student
  selectors. Google US English and Google UK English Female work.

## 0:00-0:35 - The problem, and why it is hard

Hold on the opening screen. Do not click until the last line is out.

The premise and the three things to watch for are on the screen, in the panel,
and they tick themselves off in green as the session delivers them. You do not
read them aloud - the panel is doing that job, and twenty words spent narrating
a visible checklist are twenty words not spent on the argument underneath it.

> "A score tells you a student got it wrong. It can't tell you what they
> believe."
>
> *(beat)*
>
> "Study Coach records which idea they reached for instead."
>
> "That's harder than it sounds. On spoken answers the worst correct one scores
> lower than the best wrong one. There is no similarity threshold to draw."
>
> "So it doesn't measure similarity. It asks which of this deck's answers the
> student actually said. Eleven milliseconds, and no model in the loop."

Those last two blocks are the strongest technical claim in the project and the
only place the video makes it. The numbers behind them: on the shipped content
the lowest legitimate speech distortion scores 0.800 and the highest wrong
answer that must be rejected scores 0.857. No line fits between them. Do not
reach for the nucleus/nucleolus example instead - `README.md` carries two honest
caveats on that pair, and this phrasing is the claim that survives them.

Click **Run live session**, and stop talking.

## 0:35-2:30 - The session, which speaks for itself

Press space between cards. Say nothing at all until the close - the coach is
already naming the attribution out loud, and narrating over it says the same
thing twice in two voices. What is happening, so you know where to
give a longer pause:

| card | what lands |
| --- | --- |
| `MCP CONNECTION` | protocol 2025-11-25, Streamable HTTP, eight tools, **no model on this path**, **grading 11 ms median** - the technical claim, carried by tags rather than by you |
| `QUESTION` | question 1 of 4 |
| `ATTRIBUTED_TO` | the first miss, tagged `attributed to The chloroplasts` - **tick one** |
| two ordinary answers | spoken, correct, set back. Not a weak topic: one pair |
| `CONTRAST_PROBE` | the mirror, both concepts named - **tick two**. The card is tagged **+2 questions to settle this pair**, and the counter goes from 4 of 4 to 5 of 6. Without that tag the jump reads as a broken counter; with it, it is the product deciding to spend two more questions on something it found |
| `SIDE_B_MASTERED` | one side right. No resolution tag yet |
| `SIDE_A_MASTERED · CONFUSION_RESOLVED` | both sides - **tick three**. Last card of the session; it ends on the good news |
| `SECOND SUBJECT` | black card. Computer Science Fundamentals |
| `QUESTION` | its own opening question, as the biology act has |
| five more | authentication against authorization, drilled and closed the same way. The act runs its session to the end, so it stops on "that was the last one" and not on a question |

The pauses that are worth holding: after each `CONFUSION_RESOLVED`, and after
the last card before you speak the close.

The server settles the chloroplasts side first, so `SIDE_B_MASTERED` appears
before `SIDE_A_MASTERED`. Deterministic, but not alphabetical.

## 2:30-2:42 - Close

> "A wrong answer isn't a score. It's evidence about what the student believes."

## If you want to say more

There is room for roughly one more sentence. The one I would spend it on, over
the final `CONFUSION_RESOLVED` card:

> "Both sides right. That's the distinction holding - and it's the only good
> news a revision session can honestly give."

Nothing goes over the first miss. The coach is speaking there.
