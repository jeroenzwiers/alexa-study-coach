# Adversarial review: what a green test suite was still hiding

## What this is, and what it is not

Four simulated stakeholders were given the running MCP server and the source,
and asked to use it as themselves and then report as testers. They could message
each other, and they did: three of the four withdrew their own top finding on
someone else's evidence.

**This is an engineering review. It is not user research, and nothing in it is
evidence that any student learns better.** The participants were language models
playing a role. They are unusually good at finding defects and they cannot tell
you whether the product helps a child. Any claim of user value has to come from
people, and is reported separately.

The four:

| | who | what they were asked to judge |
| --- | --- | --- |
| student | 15, East Los Angeles, has struggled with maths since seventh grade, revises at 10pm on a shared kitchen speaker | would she keep using it, and what made her want to stop |
| teacher | secondary science, five classes of thirty, six minutes between lessons | does the class report change what she does on Monday |
| parent | father of a 13-year-old, not technical, uneasy about a listening device | does the report tell him something true he could act on |
| reviewer | Alexa+ platform evangelist judging ~60 entries | do the claims hold, and does the demo survive being run twice |

## The failure class the tests missed

Every scripted test in this repository modelled a student who eventually learns.
`test_diagnosis` drives someone who gets the pair wrong twice and then has it
right; `test_memory` drives someone who settles a confusion across sessions.
Even the check that claimed to cover the opposite — a function then named
`termination_checks`, labelled "a student who never gets it right" — was
answering most cards correctly through a lookup table of right answers.

The student this product exists for is the one who does not recover. Three of
the seven defects below appear only in that case, and no amount of running the
existing suite would have surfaced them.

The correction went into the tests first: `ceiling_checks` now drives a student
who answers **every** card with some other card's answer, varying which wrong
answer, because a fixed one concentrates every miss onto a single pair and hides
the problem.

## The seven, with evidence and the test that now holds each one

### 1. The one path that exists to refuse to guess was recording a diagnosis

`grade()` returns the nearest candidate even when it reports `ambiguous` — the
rung means "I cannot choose between these", not "there is no match". The wrong
branch read `verdict.matched` regardless, so a half-heard utterance was written
to the profile as a confusion, drilled as a contrast, probed from the other
side, and summed into the class report. The ambiguity check ran afterwards and
only suppressed what the student heard.

`"the intercept"` against the x-intercept card: score 0.947, **margin exactly
0.000** — the grader declaring it could not choose — and an x/y-intercept
confusion recorded anyway.

Found by the reviewer, reading two line numbers in order. Invisible to all four
personas until then.

*Tests:* `onbeslisbaar antwoord wijst nog wel ergens naar` · `maar legt geen
verwarring vast` · `en plant geen contrastdrill` · `en plant geen probe`

### 2. A session put down halfway wrote nothing at all

`_remember` had one call site: the turn that answers the last question. There is
no `end_session` tool and no other write path, so an abandoned session lost every
confusion found and every pair settled.

Two consequences, neither obvious. The students likeliest to stop are the ones
with the most to remember — and drilling lengthens the session for exactly the
student who keeps missing, so abandonment concentrates where the record matters
most. And `topic_map` counts a student as having practised only when `sessions`
is non-zero, a counter incremented only inside that unreachable write, so an
abandoned student vanished from the cohort entirely. "Thirteen students have
practised" meant thirteen who *finished*, and the report never said so.

*Tests:* `afgebroken sessie wordt toch bewaard` · `afgebroken sessie bewaart de
verwarring` · `afgebroken sessie telt als een sessie` · `schrijven per beurt telt
de verwarring niet dubbel`

### 3. A confusion carried from last time could never be drilled or settled

`record_confusion` refused to queue a drill for any pair already in `contested`.
A carried pair is put there when the session is seeded, before any drill has run.
So the student came back still confused, missed it again, and the mechanism built
for exactly that moment could not fire.

Measured over 20 sessions with a returning student who is still wrong: the
contrast question fired **0/20** before, 20/20 after. For a student who slips
once and then has it: settled **0/20** before, 20/20 after. It worked only for
the student who no longer needed it.

*Tests:* `terugkerende leerling die het nog fout heeft krijgt de contrastvraag` ·
`terugkerende leerling die een keer glipt kan het alsnog afsluiten`

### 4. Sessions had no ceiling

`planned` gated only the drawing of fresh cards. Forced contrast questions and
probes bypassed it, so a student who kept missing could be held indefinitely.
Measured: sessions of up to **366 questions** against a requested length of 12,
and closed loops repeating the same six questions verbatim.

The parent put it better than the bug report: *nobody's thirteen-year-old should
be trapped in a quiz that won't let them leave because they can't answer it.*

*Tests:* `sessie eindigt ook als ALLES fout gaat (25 shuffles)` · `sessie blijft
binnen het plafond van twee keer de lengte`

### 5. The parent's report counted last week's mistakes as tonight's

A carried confusion arrives with its counter seeded so the drill treats it as
ripe. `history.remember` correctly subtracted that seed on the way to disk;
`tutor_report` printed the raw total. A returning student with seven misses in a
fifteen-question session was reported as **"14 of them are the same confusion"** —
more errors than questions asked.

*Test:* `rapport claimt nooit meer fouten dan er gemaakt zijn (20x)`

### 6. Containing an answer is not saying it

The grader's fast path accepted any utterance containing an accepted phrasing,
which is right for `"I think it's the mitochondria"` and wrong for
`"authentication token"`, `"a cache miss"`, `"mitochondrion wall"` — where the
extra word is not padding but the thing naming a different concept. Those came
back `exact`, score 1.0, marked correct.

The answer must now be the last thing of substance said, and the veto applies to
the whole card: vetoing only the phrasing leaves `"mitochondrion wall"` to drop
out of the fast path and then win against the sibling phrasing `mitochondria` on
similarity alone. The reviewer, who had proposed the per-phrasing version, said
she had not seen that.

*Tests:* `mitochondrion wall` and `cell membrane protein` in
`harness/test_grading.py`

### 7. Self-correction was thrown away

A leading `"no"` was read as a semantic negation, so `"no wait, the median"` was
discarded whole — 0 of 12 cards, rung `negated`. Filler was stripped first, so a
clean correct answer was assembled and *then* binned. And because a discarded
turn is unattributable, no confusion could ever be diagnosed from one either: the
commonest shape a hesitant answer takes switched the product's core feature off
silently.

*Tests:* `no wait the mitochondria` · `no, the nucleus` · `nope um the cell wall`
· and `no its not the nucleus`, which must still be refused

## The finding that changed how the content is checked

The teacher's contribution was not a defect but a mechanism. The misattribution
in §1 is **deterministic**, so it is correlated across students: thirty children
saying the same taught synonym snap to the same wrong card, and the class report
renders that as a clean lopsided pattern indistinguishable from a real finding.
The two-thirds direction test does not filter it — it certifies it, because a
deterministic error is maximally lopsided.

`verify_study_set.py` could not see this by construction: every check asked
whether a phrasing **in** a set lands on the right card, and a word that is not
in the set is exactly what both grader failures are made of. Cards now declare
`near_misses`, the checker requires them, and 458 such checks run across four
sets.

*Tests:* `checker vangt: geen enkele near-miss gedeclareerd` · `checker vangt:
near-miss wordt juist goedgerekend`

## What the review confirmed sound

Recorded because a review that lists only faults is its own kind of dishonesty,
and because two of these were checked by someone who arrived intending to
complain.

- The stored profile is card ids, counts, a date and a score. No transcript, no
  audio, no timestamps beyond a date. The parent went looking to be angry and
  was not.
- `manner` is consumed as three booleans inside the turn and never persisted.
  Fourteen emotion labels produced an adjustment identical to passing nothing.
- The screen card escapes every interpolated value; `_safe_id` closes path
  traversal; prompt injection grades as ambiguous.
- Zero model calls in the request path — `anthropic` appears once in the whole
  repository, in an offline tool.
- The phonetic matching understood a bilingual student first try, every time:
  `"um the medium"`, `"the co-efficient"`, `"multiple-o"`, `"the perimetro"`,
  `"el promedio, um, the average"`. This is why the grader thresholds were left
  alone: any threshold that rejects `vesicle` rejects these too. Measured — the
  lowest legitimate distortion scores 0.800, the highest false accept 0.857.

## What this review cannot tell you

Whether the confusions it detects are the ones a teacher would call meaningful.
Whether a student who uses it revises differently. Whether any of it helps.

Those need people, one modest question, and a separate document.
