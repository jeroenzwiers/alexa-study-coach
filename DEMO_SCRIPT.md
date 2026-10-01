# Study Coach Golden Demo Script

**Target runtime:** 2:47. Hard limit 3:00 - judges are not required to watch past
it. A simulated Alexa+ experience backed by the real MCP server.

**The session talks. You don't, except at the two ends.** Every card speaks -
the questions, the wrong answers, the ordinary right ones, the persistence, the
second subject. Nothing on screen is silent. Three earlier
cuts of this script had the narrator explaining a demo that had been muted to
make room for the explaining, which is backwards.

So your job is the opening and the close. In between you press the space bar and
let it run.

## The arithmetic

| | |
| --- | --- |
| the session, spoken: 29 utterances | **127 s** |
| your narration: 90 words at 150 wpm | 36 s |
| **total** | **2:43** |

Measured, not estimated: `harness/test_demo_browser.mjs` drives the page in a
real browser, records every utterance with the time real speech would take, and
adds them up. At 140 wpm you land on 2:45 - seventeen seconds of margin, the most this
script has ever had. The class report came out and the second act got an ending.

The voices run at rate 1.13, which is brisk. If it sounds hurried to you it can
go back to 1.06, but that is eight seconds and you would have to drop a line.

That leaves about 10 seconds. You have room for one extra sentence, not three -
an earlier draft with 260 words of narration ran 3:11.

## What is deliberately not in this video

The class report - the one that aggregates confusions across everyone who
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
> "Study Coach records **which idea they reached for instead**."
>
> "Three things to watch for. The word *attributed*. A question that was
> **chosen**, not shuffled. And a confusion being **closed**."

Click **Run live session**, and stop talking.

## 0:45 - One line, over the first miss

This is the only place you speak during the session, and it is the sentence that
makes the difference between a nice feature and the idea the project is built
on. Let the coach finish, then:

> "Attributed - not marked wrong. A closed set of answers, not a similarity
> score."

## 0:38-2:40 - The session, otherwise speaking for itself

Press space between cards. Say nothing else. What is happening, so you know where to
give a longer pause:

| card | what lands |
| --- | --- |
| `MCP CONNECTION` | protocol 2025-11-25, Streamable HTTP, eight tools, **no model on this path**, **grading 11 ms median** - the technical claim, carried by tags rather than by you |
| `QUESTION` | question 1 of 4 |
| `ATTRIBUTED_TO` | the first miss, tagged `attributed to The chloroplasts` - **tick one** |
| two ordinary answers | spoken, correct, set back. Not a weak topic: one pair |
| `CONTRAST_PROBE` | the mirror, both concepts named - **tick two**. The counter goes to 5 **of 6**: the session grew because it found something |
| `SIDE_B_MASTERED` | one side right. No resolution tag yet |
| `SIDE_A_MASTERED · CONFUSION_RESOLVED` | both sides - **tick three**. Last card of the session; it ends on the good news |
| two gold cards | settled for good, then "Welcome back" - the diagnosis outliving the session |
| one more answer | the returning session's question, answered right. It is there so the greeting does not end on a question nobody answers |
| `SECOND SUBJECT` | black card. Computer Science Fundamentals |
| `QUESTION` | its own opening question, as the biology act has |
| five more | authentication against authorization, drilled and closed the same way. The act runs its session to the end, so it stops on "that was the last one" and not on a question |

The pauses that are worth holding: after each `CONFUSION_RESOLVED`, and after
the last card before you speak the close.

The server settles the chloroplasts side first, so `SIDE_B_MASTERED` appears
before `SIDE_A_MASTERED`. Deterministic, but not alphabetical.

## 2:35-2:43 - Close

> "A wrong answer isn't a score. It's evidence about what the student believes."

## If you want to say more

There is room for about one more sentence, not three. In order of what I would
spend it on:

1. Over the first miss: "Attribution over a closed set of answers, not a
   similarity score."

That line is already in the script at 0:45; this is where it would go if you
cut it and changed your mind.
