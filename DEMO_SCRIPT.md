# Study Coach Golden Demo Script

**Target runtime:** 2:50. Hard limit 3:00 - judges are not required to watch
past it. A simulated Alexa+ experience backed by the real MCP server.

The shape is **a promise and three payoffs**. The opening tells the viewer
exactly what to watch for; the session then delivers it, and barely needs
narrating over the top. That is deliberate. Two synthesised voices carry the
session, and a narrator talking across them is what makes a demo hard to follow.

## The arithmetic, because it is tight

The synthesised voices speak 194 words across seven cards: about **78 seconds**,
and not something you control. The narration is 245 words, and how long that
takes is entirely down to you.

| your delivery | narration | total |
| --- | --- | --- |
| 140 wpm, unhurried | 105 s | **3:03** - over the limit |
| 150 wpm, normal | 98 s | **2:56** |
| 160 wpm, brisk | 92 s | **2:49** |

So **time yourself reading the opening block before you record anything.** It is
81 words; if it takes you longer than 33 seconds, the close will fall outside
the three minutes and judges are not required to watch that far - and the close
is the punchline.

Two levers if you run long, in the order I would use them:

1. Cut the persistence line at 1:50 (17 words). The card says it on screen.
2. Cut the second class-report line at 2:20 (14 words). It is the best sentence
   in the script, so cut it last.

An earlier draft ran 4:03 and would never have been watched to the end. Three
cards - the two persistence cards and the class report - were taken out of the
spoken stream for this reason; the narrator covers them, and the viewer reads
them.

## Before you record

- **Step mode on.** The timeline otherwise advances itself 450 ms after each
  card, which leaves no gap to speak into. With it on, the session waits for you
  to press the space bar. Your narration sets the pace, not a timer.
- **Full screen**, `F11`. A Chrome update notice in the corner is a stray line
  of Dutch in an English-only submission.
- **Zoom to about 150%**, `Ctrl` and `+`. The small monospace labels -
  `CONFUSION_RESOLVED`, `SIDE_A_MASTERED` - are what YouTube's compression eats.
- **Drop your recording level a few decibels.** The first take peaked at
  -0.1 dB, hard against the ceiling.

## 0:00-0:35 - The problem, and the three things to watch for

Hold on the opening screen. Do not click.

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

Click **Run live session**.

## 0:35-0:45 - The transport is real

Over the `MCP CONNECTION` card.

> "A real MCP server underneath. And no model runs while the student waits -
> grading is deterministic, eleven milliseconds."

## 0:45-1:05 - Payoff one: attributed

Let both voices finish, then speak.

> "There. Not a cross - *attributed to the chloroplasts*. Attribution over a
> closed set of answers, not a similarity score."

## 1:05-1:25 - Payoff two: chosen, not shuffled

> "Two misses. One misconception, both sides. And that question was chosen, not
> shuffled."

## 1:25-1:50 - Payoff three: closed

On `SIDE_B_MASTERED`, before any resolution tag appears:

> "One side right is recognition. Nothing is marked resolved yet."

On `SIDE_A_MASTERED · CONFUSION_RESOLVED`:

> "Both sides. Closed - the one honest piece of good news a revision session can
> deliver."

The server settles the chloroplasts side first, so `SIDE_B_MASTERED` appears
before `SIDE_A_MASTERED`. Read the labels off the screen; the order is
deterministic but it is not alphabetical.

## 1:50-2:00 - What survives the session

> "Sessions end. Misconceptions don't. What's kept is the diagnosis, so the
> unfinished business goes first next time."

## 2:00-2:20 - None of that was about biology

A black `SECOND SUBJECT` card, then two beats on Computer Science Fundamentals.

> "None of that was a biology feature. Same server, another subject - and I
> suspect this pair is familiar."

The student says *authorization*; the coach answers **"Not quite - that's
authorization. Authentication verifies identity; authorization decides which
actions that identity may take."** Then the mirror: the student says
*authentication*, and `CONFUSION_DETECTED · CONTRAST_PROBE` comes back with
`contrast: authorization vs authentication`.

Let those two land on their own. No narration over them - the pair does the work.

## 2:20-2:45 - Across a class, it stops being about one student

The final card, `CLASS_REPORT · SIMULATED COHORT`, carrying two tags:
`counts, never names` and `simulated cohort`. It is not spoken aloud; you read
it. Say **simulated** - these are seeded profiles, not real pupils, and the rest
of this project is careful about exactly that distinction.

The card says, verbatim:

> Nine students have practised The Cell. One confusion stands out: osmosis and
> diffusion, seven students. Six of them go the same way: asked about osmosis,
> they answer diffusion. Three have since settled it. Also recurring: the
> mitochondria and the chloroplasts, four students.

> "One student mixing two ideas up is a fact about that student. Nine -
> simulated here - is a fact about the material."
>
> "And not just *that* they confuse them. **Which half of the distinction is
> missing.**"

Worth knowing, though it is too subtle to narrate: one of those nine confuses
the nucleus with the nucleolus, alone. It is counted and deliberately not
reported, because one student is not a pattern. The privacy floor is visible in
the demo by what it leaves out.

## 2:45-2:56 - Close

> "A wrong answer isn't a score. It's evidence about what the student believes."

---
