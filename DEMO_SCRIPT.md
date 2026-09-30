# Study Coach Golden Demo Script

**Target runtime:** 2:31-2:45 depending on delivery. Hard limit 3:00 - judges
are not required to watch past it. A simulated Alexa+ experience backed by the real MCP server.

The shape is **a promise and three payoffs**. The opening tells the viewer
exactly what to watch for; the session then delivers it, and barely needs
narrating over the top. That is deliberate. Two synthesised voices carry the
session, and a narrator talking across them is what makes a demo hard to follow.

## The arithmetic, because it is tight

The synthesised voices speak 144 words across the biology act: about **58
seconds**, and not something you control. The narration is 250 words, and how
long that takes is entirely down to you.

| your delivery | narration | total |
| --- | --- | --- |
| 140 wpm, unhurried | 107 s | **2:44** |
| 150 wpm, normal | 100 s | **2:37** |
| 160 wpm, brisk | 94 s | **2:31** |

All three fit inside the three minutes, which was not true of two earlier
drafts - one ran 4:03 - so the margin is deliberate rather than lucky. Time
yourself on the 81-word opening block anyway: if it takes much over 35 seconds
you are slower than the table assumes and the close gets tight.

Two levers if you do run long, in the order I would use them:

1. Cut the persistence line at 1:50 (17 words). The card says it on screen.
2. Cut the second class-report line at 2:20 (14 words). It is the best sentence
   in the script, so cut it last.

**What is spoken and what is not.** The biology act speaks: the student's answer
in one voice, the coach's reply in the other. The ordinary correct answers, the
two persistence cards, the whole computer science act and the class report are
shown but silent - the narrator carries those, and the viewer reads them.
Speaking the computer science act as well cost 36 seconds to say what the screen
already said.

One thing the shell does that is worth knowing, because it sounds like a
mistake and is not: each coach line ends by asking the *next* question, so when
a run of silent cards breaks the chain, the next spoken card asks its own
question again before the answer. That is why you hear "Which organelle captures
light energy in a plant cell?" twice - once trailing an earlier card, once
opening this one. Without it you hear question two asked and question four
answered.

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

The intro is on the screen as well as in your mouth, so a judge watching with
the sound off still gets the premise. Under the headline sits a panel: one
sentence on what Study Coach is, then the three things to watch for, numbered.
You are reading those three items off the screen, not reciting them.

The moment you click, that panel shrinks to a thin strip and sticks to the top
of the window, and each of the three ticks itself off in teal as the session
delivers it - `attributed` at 0:45, `chosen` at 1:05, `closed` at 1:25. The
promise stays in shot the whole way. Nothing lights up early: each tick is
driven by the proof state on the card the server actually sent.

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

Then seven pale cards slide past on their own - the rest of the session, every
one correct, each tagged `correct`. Step mode does not stop on them. Four words
over that run, and do not hurry them:

> "And everything else - right."

That run is the argument nobody makes out loud. This student is not weak at
biology. They know the cell. They had one pair the wrong way round, and it is
now sorted. A score of eleven out of thirteen hides exactly that, which is the
whole reason this project exists.

**If you find you have room**, there is one more thing on those cards worth
saying, and it is not in the word count above. Every card carries
`question N of M`, and at the contrast probe the M changes: **13 becomes 15**.
The session got two questions longer because it found something. Nothing else
in the demo shows the product making a decision quite that plainly.

## 1:50-2:00 - What survives the session

> "Sessions end. Misconceptions don't. What's kept is the diagnosis, so the
> unfinished business goes first next time."

## 2:00-2:20 - None of that was about biology

A black `SECOND SUBJECT` card, then Computer Science Fundamentals. This act is
**silent** - shown, not spoken. For this audience the two words do the work on
sight, and your voice is the only thing on the soundtrack here.

> "None of that was a biology feature. Same server, another subject - and I
> suspect this pair is familiar."

The student says *authorization* to "What process verifies that a user is who
they claim to be?", and the card comes back tagged `attributed to
Authorization`. Then the mirror, and `CONFUSION_DETECTED · CONTRAST_PROBE` with
`contrast: authorization vs authentication`.

Step mode stops on both. Give them a beat each and say nothing over them.

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
