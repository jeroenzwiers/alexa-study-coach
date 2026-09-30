# Study Coach Golden Demo Script

**Target runtime:** 2:42-2:55 depending on delivery. Hard limit 3:00 - judges are
not required to watch past it. A simulated Alexa+ experience backed by the real
MCP server.

The shape is **a promise and three payoffs**. The opening tells the viewer what
to watch for; the session then delivers it, and the two synthesised voices carry
it. Your narration goes in the gaps, not across them.

## The arithmetic

| your delivery | narration, 260 words | + session, 68 s | total |
| --- | --- | --- | --- |
| 140 wpm, unhurried | 111 s | | **2:59** - no margin |
| 150 wpm, normal | 104 s | | **2:52** |
| 160 wpm, brisk | 98 s | | **2:45** |

**Aim for 150 and do not drop below it.** At 140 the close lands on 2:59, and
the close is the punchline - judges are not required to watch past three
minutes. Time yourself on the 81-word opening block before recording anything:
33 seconds is on pace, 35 is the edge.

Two cuts if you run long, in the order I would make them:

1. The persistence line at 1:55 (17 words). The cards say it on screen.
2. The second class-report line at 2:25 (14 words). It is the best sentence in
   the script, so cut it last.

**The biology session is four questions long, and every card in it is spoken** -
the mistakes and the ordinary correct answers alike. The server grows a session
when it finds something, so asking for four gives seven cards and the last one
is the resolution. Asking for thirteen, as an earlier cut did, gave the same
seven and then nine more with nothing left to say.

Shown but **not** spoken: the two persistence cards, the computer science act,
and the class report. You are talking over all three, so none of them is
silence. Speaking the computer science act as well costs 36 seconds to say what
the screen already says - if you would rather hear it, the trade is cutting the
narration to about 150 words.

## Before you record

- **Step mode on.** The timeline otherwise advances itself, which leaves no gap
  to speak into. With it on, the session waits for the space bar. It does not
  stop on the two ordinary answers - those speak and move on by themselves.
- **Full screen**, `F11`. A Chrome update notice in the corner is a stray line
  of Dutch in an English-only submission.
- **Zoom to about 150%**, `Ctrl` and `+`. The small monospace labels are what
  YouTube's compression eats.
- **Drop your recording level a few decibels.** The first take peaked at
  -0.1 dB, hard against the ceiling.

## 0:00-0:35 - The problem, and the three things to watch for

Hold on the opening screen. Do not click.

The intro is on the screen as well as in your mouth, so a judge watching with
the sound off still gets the premise. Under the headline: one sentence on what
Study Coach is, then the three things to watch for, numbered. Read them off the
screen rather than reciting them.

The moment you click, that panel shrinks to a strip and sticks to the top of the
window, and each item ticks itself off in teal as the session delivers it.
Nothing lights up early - each tick is driven by the proof state on the card the
server actually sent.

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

Question 1, the wrong answer, the coach's reply. Let all three voices finish.

> "There. Not a cross - *attributed to the chloroplasts*. Attribution over a
> closed set of answers, not a similarity score."

## 1:05-1:20 - Two right, in passing

Questions 3 and 4 go by spoken, correct, and set back on the page. Step mode
does not stop on them. One line over the pair:

> "And the rest of it, right. This isn't a weak topic - it's one pair."

That is the difference between a score and a diagnosis. Eleven out of thirteen
tells a parent their child is middling at biology. This says they know the cell
and hold one distinction backwards.

## 1:20-1:35 - Payoff two: chosen, not shuffled

The mirrored question arrives, the second miss lands, and the contrast probe
comes back naming both concepts.

> "Two misses. One misconception, both sides. And that question was chosen, not
> shuffled."

Watch the counter on the card: **question 5 of 6**, where a moment ago the total
was 4. The session got longer because it found something.

## 1:35-1:55 - Payoff three: closed

On `SIDE_B_MASTERED`, before any resolution tag appears:

> "One side right is recognition. Nothing is marked resolved yet."

On `SIDE_A_MASTERED · CONFUSION_RESOLVED`:

> "Both sides. Closed - the one honest piece of good news a revision session can
> deliver."

The server settles the chloroplasts side first, so `SIDE_B_MASTERED` appears
before `SIDE_A_MASTERED`. Read the labels off the screen; the order is
deterministic but it is not alphabetical. This is the last card of the session -
it ends on the resolution rather than trailing off.

## 1:55-2:05 - What survives the session

Two gold cards, silent. You carry them.

> "Sessions end. Misconceptions don't. What's kept is the diagnosis, so the
> unfinished business goes first next time."

## 2:05-2:25 - None of that was about biology

A black `SECOND SUBJECT` card, then Computer Science Fundamentals. Silent -
shown, not spoken.

> "None of that was a biology feature. Same server, another subject - and I
> suspect this pair is familiar."

The student says *authorization* to "What process verifies that a user is who
they claim to be?", and the card comes back tagged `attributed to
Authorization`. Then the mirror, and `CONFUSION_DETECTED · CONTRAST_PROBE` with
`contrast: authorization vs authentication`.

Step mode stops on both. Give them a beat and say nothing over them - for this
audience the two words do the work on sight.

## 2:25-2:45 - Across a class, it stops being about one student

The final card, `CLASS_REPORT · SIMULATED COHORT`, tagged `counts, never names`
and `simulated cohort`. Silent; you read it. Say **simulated** - these are
seeded profiles, not real pupils, and the rest of this project is careful about
exactly that distinction.

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

Worth knowing, though too subtle to narrate: one of those nine confuses the
nucleus with the nucleolus, alone. It is counted and deliberately not reported,
because one student is not a pattern. The privacy floor is visible by what it
leaves out.

## 2:45-2:55 - Close

> "A wrong answer isn't a score. It's evidence about what the student believes."
