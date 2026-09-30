# Study Coach Golden Demo Script

**Target runtime:** 2:47. Hard limit 3:00 - judges are not required to watch past
it. A simulated Alexa+ experience backed by the real MCP server.

**The session talks. You don't, except at the two ends.** Every card speaks -
the questions, the wrong answers, the ordinary right ones, the persistence, the
second subject, the class report. Nothing on screen is silent. Three earlier
cuts of this script had the narrator explaining a demo that had been muted to
make room for the explaining, which is backwards.

So your job is the opening and the close. In between you press the space bar and
let it run.

## The arithmetic

| | |
| --- | --- |
| the session, spoken: 344 words | **130 s** |
| your narration: 94 words at 150 wpm | 38 s |
| **total** | **2:47** |

That leaves 13 seconds of margin. If you speak slowly, you have about 30 words
of room and no more - one extra sentence, not three. An earlier draft with 260
words of narration ran 3:11 with everything speaking.

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

## 0:00-0:38 - The problem, and the three things to watch for

Hold on the opening screen. Do not click until the last line is out.

The premise is on the screen as well as in your mouth, so a judge watching with
the sound off still gets it. Read the three items off the panel rather than
reciting them.

> "Here's a report card. Seven out of ten."
>
> *(beat)*
>
> "Now tell me what to do about it."
>
> *(beat)*
>
> "You can't. A score says how much a student got wrong. It says nothing about
> what they misunderstood."
>
> "Study Coach revises out loud with a student. When they miss, it doesn't
> record that the answer was wrong. It records **which idea they reached for
> instead**."
>
> "Three things to watch for. The word *attributed*. A question that was
> **chosen**, not shuffled. And a confusion being **closed**."

Click **Run live session**, and stop talking.

## 0:38-2:40 - The session, which speaks for itself

Press space between cards. Say nothing. What is happening, so you know where to
give a longer pause:

| card | what lands |
| --- | --- |
| `MCP CONNECTION` | protocol 2025-11-25, Streamable HTTP, eight tools |
| `QUESTION` | question 1 of 4 |
| `ATTRIBUTED_TO` | the first miss, tagged `attributed to The chloroplasts` - **tick one** |
| two ordinary answers | spoken, correct, set back. Not a weak topic: one pair |
| `CONTRAST_PROBE` | the mirror, both concepts named - **tick two**. The counter goes to 5 **of 6**: the session grew because it found something |
| `SIDE_B_MASTERED` | one side right. No resolution tag yet |
| `SIDE_A_MASTERED · CONFUSION_RESOLVED` | both sides - **tick three**. Last card of the session; it ends on the good news |
| two gold cards | settled for good, then "Welcome back" - the diagnosis outliving the session |
| `SECOND SUBJECT` | black card. Computer Science Fundamentals |
| two more | authentication against authorization, same machinery |
| `CLASS_REPORT` | nine simulated students, and which half of the distinction is missing |

The pauses that are worth holding: after `CONFUSION_RESOLVED`, and after the
class report before you speak the close.

The server settles the chloroplasts side first, so `SIDE_B_MASTERED` appears
before `SIDE_A_MASTERED`. Deterministic, but not alphabetical.

## 2:40-2:47 - Close

> "A wrong answer isn't a score. It's evidence about what the student believes."

## If you want to say more

There is room for about one more sentence, not three. In order of what I would
spend it on:

1. Over the class report, if the card has not already made it land:
   "Not just *that* they confuse them - which half of the distinction is
   missing."
2. Over the first miss: "Attribution over a closed set of answers, not a
   similarity score."

Adding both puts you at 3:01, so pick one.
