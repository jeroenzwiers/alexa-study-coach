# Study Coach

An Alexa+ add-on that revises with a student out loud — and when they get
something wrong, tells them _which_ idea they reached for instead, drills that
one distinction until it holds, and remembers it next week if it doesn't.

Built for the Alexa+ track of the **Build, Ship, Shape: Amazon Developer
Hackathon**. It is an MCP server implementing spec version `2025-11-25` over
Streamable HTTP.

```
ALEXA   : Question 2. Which organelle releases energy from glucose?
STUDENT : "chloroplasts"
ALEXA   : Not quite - that's the chloroplasts. Chloroplasts capture energy from
          light; mitochondria release it from food. The answer is The
          mitochondria. Question 3. Which structure gives a plant cell its
          shape and support?
...
ALEXA   : Question 5. Which organelle captures light energy in a plant cell?
STUDENT : "mitochondria"
ALEXA   : Not quite - that's the mitochondria. Let's separate those two. Which
          organelle captures light energy in a plant cell? Is it the
          chloroplasts, or the mitochondria?
STUDENT : "chloroplasts"
ALEXA   : Exactly - that's the difference. Question 7. Which organelle releases
          energy from glucose?
STUDENT : "the might o chondria"
ALEXA   : Yes - and that's the pair sorted. You had the chloroplasts and the
          mitochondria the wrong way round twice tonight, and you've just had
          them both right. That one's done.
```

Three things are happening there that a flashcard app cannot do, and each one
falls out of the same fact: **when the student is wrong, we know which wrong
thing they said.**

1. **It names the confusion.** The student did not make two unlucky mistakes;
   they have one misconception, seen from both sides.
2. **It goes looking for the other side.** After the first miss, the mirrored
   question is scheduled deliberately — whether a confusion is real should not
   be left to the shuffle.
3. **It closes.** Getting the contrast right is recognition. Getting the
   mirrored question right too is the distinction actually holding, and that is
   the one piece of good news a revision session can honestly deliver.

Then it reports it:

> _4 out of 7 on The Cell. The errors are not spread out. 3 of them are the same
> confusion: when asked about the chloroplasts, the answer given was the
> mitochondria._

…or, when the student got there:

> _6 out of 8 on The Cell. One confusion was settled during the session: the
> chloroplasts against the mitochondria, answered correctly from both sides at
> the end._

A flashcard app cannot say either sentence. It records one bit per answer.

## The problem underneath: you cannot grade speech with a similarity threshold

The obvious way to mark a spoken answer is to accept it when it is _similar
enough_ to the expected one. We measured that this cannot work.

Speech recognition mangles words phonetically, so a correct answer can arrive
badly distorted while a genuinely different answer can be spelled almost
identically:

| spoken          | expected    | letter similarity | must be |
| --------------- | ----------- | ----------------- | ------- |
| `"new clee us"` | `nucleus`   | **0.667**         | correct |
| `"nucleus"`     | `nucleolus` | **0.875**         | wrong   |

The wrong pair scores _higher_ than the right one, so no threshold on letters
separates them.

Two honest caveats, because this table used to overstate its case. The grader's
own composite metric — letters, content words and a phonetic key — does separate
*this particular* pair: 1.000 against 0.889. And the classes still overlap
elsewhere, which is the point that survives. On the shipped content the lowest
legitimate speech distortion scores **0.800** and the highest wrong answer that
must be rejected scores **0.857**. There is no threshold between them, and
`LIMITATIONS.md` §1 is what that costs.

So the grader does not ask "is this close enough?". It asks **"of every answer
that appears anywhere in this study set, which one did the student say?"** — a
nearest-neighbour attribution over a known, closed candidate set, deciding
between the best _right_ answer and the best _wrong_ one — though only on the
nearest-neighbour rung: a verbatim or whole-phrase match returns before that
comparison is reached. `nucleolus` stops
being a near-miss and becomes its own candidate.

Two things fall out of that:

1. It works on distortion. 28/28 on the hard cases in `harness/test_grading.py`
   — `"the might o chondria"`, `"sell wall"`, `"no wait the median"`. Read that
   number for what it is: that file grades against a deck that includes the
   near-misses as cards. Replayed against the content this repo actually ships,
   which does not, it does worse — see `LIMITATIONS.md` §1.
2. Being wrong is no longer one bit. We know _which_ concept was reached for —
   which is what everything above and below is built on.

## Where the questions come from, and why that is the same problem

The closed candidate set is what makes the diagnosis possible, and it is also
the thing a badly built study set destroys. If a student answers _chloroplasts_
and no card in the set has _chloroplasts_ as an answer, there is nothing to
attribute it to — and what happens then is worse than nothing happening. The
answer does not come back `ambiguous`. It is attributed to the nearest card
anyway and usually marked **correct**: of 27 plausible wrong answers, 24 were.
The questions look fine, no confusion is ever recorded, and the class report is
silently missing the very patterns it exists to find. `LIMITATIONS.md` §1 has
the measurements and why the fix is content-side rather than a threshold.

So `tools/build_study_set.py` does not generate twenty questions. It is asked to
build the set **around the confusions** — which concepts students actually swap,
and in which direction — and to put both halves of every pair in the set. The
confusion graph is the artefact; the questions are how it is delivered. It runs
offline against `claude-opus-5`, never in the request path.

And then the model's work is checked by the code that has to live with it.
`tools/verify_study_set.py` runs every set through the **real `grading.grade`**
that serves live traffic:

| check                 | what it catches                                                                                                                                                                                                    |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| own phrasings         | a card whose own answer does not attribute to it — an unanswerable question                                                                                                                                        |
| **cross-attribution** | saying card A's answer to card B's question must still be attributed to A. This is the diagnosis in one assertion: it is how the coach knows the student said _chloroplasts_ rather than merely _not mitochondria_ |
| collisions            | two cards accepting the same words, which makes attribution a coin flip                                                                                                                                            |
| structure             | difficulty out of range, a missing misconception line, a distractor label pointing nowhere                                                                                                                         |

A generated set that fails is reported and not written. The model proposes; the
grader decides.

The hand-written set that ships passes the same gate — 42 accepted phrasings and
**504 cross-attributions, all landing on the right card** — and
`harness/test_content.py` keeps it that way, using deliberately broken sets to
prove the checker still fires.

## It remembers the student, not the score

Sessions end. Misconceptions don't. So what survives a session is the diagnosis:

```
ALEXA   : Welcome back. Yesterday the mitochondria and the chloroplasts kept
          swapping places. Shall we settle that first? Question 1. Which
          organelle captures light energy in a plant cell?
```

That line is only available to something that kept _which two things_ rather
than _how many out of ten_. The unsettled pair is not a fresh question — it is
unfinished business, so it goes first, carrying its history, and two right
answers now close it for good. A confusion that comes back after being settled
goes back on the open list rather than being quietly forgotten.

`student_progress` reads the same record across sessions: what has been settled
for good, and what is still open.

## The same confusion, across students, is a fact about the topic

One student mixing osmosis up with diffusion is a fact about that student. Nine
students doing it is a fact about the material:

> _Nine students have practised The Cell. One confusion stands out: osmosis and
> diffusion, seven students. Six of them go the same way: asked about osmosis,
> they answer diffusion. Three have since settled it._

That last-but-one sentence is the useful one. "They confuse these two" tells a
teacher to revise both. "Six of them answer diffusion when asked about osmosis"
tells them **which half of the distinction is missing** — and no marking
produces it, because marking records that an answer was wrong, not which other
idea was reached for.

It is aggregate by construction. `class_report` counts students per confusion
and never carries an identity out of `history.py`.

That is true of the code and **not true of the system**, and the difference
matters enough to say here rather than in a footnote. A teacher who runs the
report twice — default arguments, thirty-five minutes apart, one child
practising in between — reads the identity off the deltas: twelve students to
thirteen, that pair three to four. Identity re-enters through *when* the call is
made. `LIMITATIONS.md` §3 has the reproduction and what closing it would take.

What does hold: a confusion held by one student alone is counted but never
reported as a pattern, and no student's name reaches the report. For a product
whose users are children, that is a design constraint rather than a feature —
which is exactly why the part that does not hold is written above it rather than
underneath it.

## It reads how the answer arrived, not just whether it was right

A tutor pushes when it is all going in too easily and backs off when the student
is losing heart. That needs a signal about _how_ an answer arrived.

It would be convenient to read the tone of voice. **We cannot** — the Alexa+ MCP
toolkit hands a server tool arguments, and nothing in its documented contract
carries audio, prosody or affect. The server never hears the student. So the
signal is split, each half where it belongs:

|                     |                                                                                                                                                                                                                               |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **observed here**   | hesitation and give-up markers in the transcript, how long the answer took once Alexa's own speaking time is subtracted, and the run of right and wrong                                                                       |
| **asked of Alexa+** | an optional `manner` argument on `submit_answer` — Alexa+ _did_ hear the student, so the tool description invites it to report what the student **did**: "long pause before answering", "asked to stop", "answered instantly" |

`manner` carries **observable behaviour, never an emotion label** — and the
server acts on an allowlist of behavioural phrases, so an emotion word handed
over willingly matches nothing and produces no signal. It is not detected and
refused; it is simply inert. Fourteen emotion labels produced an adjustment
identical to passing nothing at all. That is
a deliberate line, for two reasons.

It works better. "Paused for eight seconds, then asked to move on" is something
the platform can actually observe. "Frustrated" is a guess about an inner state,
and Recital 44 of the EU AI Act is blunt about how well those guesses
generalise.

It stays inside the law. Article 5(1)(f) prohibits AI systems that infer a
person's emotions in the workplace or in education, in force since 2 February
2025, with only medical and safety exceptions. A revision coach sits squarely in
that domain. Reading what a student _did_ is not inferring what they _felt_, and
keeping the two apart is what lets this feature exist at all.

`manner` is a hint that sharpens the read, never a requirement. Everything works
with it absent, the same way the screen card is additive to the voice — and
`harness/test_adaptive.py` drives the whole collapse-and-recover arc twice, once
with it and once without, requiring the session to cope either way.

There is a nice symmetry in the transcript half: the filler the grader throws
away (`"um"`, `"I guess"`) is exactly the evidence this half keeps. The same
token means _ignore me_ to one part of the server and _this was effortful_ to
the other.

What it does with the read:

- **struggling** → step the questions down a level and add support: first a
  hint, then two options to choose between. And say so, because an unexplained
  drop in difficulty reads as being patronised.
- **cruising** → step up. But only when the student is both accurate _and_
  comfortable: a streak scraped through slowly is not an invitation.
- **recovering** → take the support away one rung at a time, and never in the
  same breath as making the question harder.

Still no model call. It is a weighted sum over signals already in hand by the
time the answer has been graded.

## Why there is no model in the request path

The Alexa+ MCP quickstart requires a round-trip under **500 ms**. A call to a
language model costs
200–800 ms on its own, so it cannot live inside the answer path.

It does not need to. Alexa+ already supplies the conversation and the reasoning;
what it cannot do is decide reliably whether a mangled utterance was the right
answer. That judgement is deterministic, explainable, and free:

|                                | measured                                 |
| ------------------------------ | ---------------------------------------- |
| grading, median                | **11.3 ms**                               |
| grading, p99                   | **49.6 ms** — 10% of the platform budget  |
| MCP round trip, median / worst | **14–20 ms** / **169–239 ms**             |
| model calls while answering    | **0**                                     |

Every figure here is measured on an otherwise idle laptop, and that qualifier is
load-bearing rather than polite. Running the presentation shell alongside the
server moves grading p99 from 49.6 ms to 119.3 ms and the round-trip worst case
from 239 ms to 912 ms — through the budget. Nothing about the code changed; the
machine was busy. Read these as what the work costs, not as a guarantee about
the box it runs on.

Reproduce the grading figures with `harness/bench_grading.py`: 10,400 calls
against the full thirteen-card set, each on an utterance the grader has not seen
before. That last part is the whole methodology. The candidate phrasings are
cached because they repeat on every call all day, which is the real workload;
repeating the *student's* utterances too would warm a cache that is always cold
in production and report a grader that never does any work. An earlier version
of this table was measured that way and read about three times faster than the
truth.

The round trip is what `harness/smoke_client.py` sees over Streamable HTTP. The
worst case is the first tool call of a new MCP session, and it is worth being
exact about which "first" that is: not the first call into a cold process, but
the first call of each session, still 551 ms against a server that had been up
for an hour and served hundreds of calls. Every call after it in the same
session lands between 10 and 37 ms. Something is initialised lazily per session
and has not been chased down. It was re-measured over
three runs after bearer validation went in front of every request and did not
move out of its own run-to-run spread (medians 12.7 / 15.1 / 19.8 ms), which is
what verifying an HMAC signature should cost. A deployment validating RS256
against a remote key set will pay more on the first request of a key's life and
nothing after it, and that figure is not measured here because there is no
authorization server to measure against yet.

Both figures have risen, and both rises were bought deliberately. Grading scales
with the size of the closed candidate set, and teaching the sets the vocabulary
a classroom actually uses — both the synonyms that mean the right answer and the
concepts that do not — grew The Cell from 42 candidate phrasings to 68. The
round trip rose when session state started being written during the session
rather than only at the end, so a child who puts the speaker down halfway keeps
their evening. Neither is free and neither is close to the budget.

## On a screen, it shows the one thing voice cannot

Devices with a display get a card through the **MCP Apps extension**
(`io.modelcontextprotocol/ui`). It does not transcribe the conversation —
repeating spoken words on screen adds nothing. It shows the progress, the
verdict, **the two confused concepts side by side** when a confusion keeps
recurring, and the moment that pair is finally told apart. Voice says that once
and it is gone; on screen it stays. A row of pips carries the current level, so
a step up or down is visible without speech having to keep announcing it.

Per SEP-2133 the extension is additive: `start_practice` and `submit_answer`
carry `_meta.ui.resourceUri`, and every tool still returns full spoken text, so a
speaker with no display loses only the picture. The other five tools have no UI
at all.

## Tools

| tool               | purpose                                                       |
| ------------------ | ------------------------------------------------------------- |
| `list_study_sets`  | what this student can practise                                |
| `start_practice`   | begin a session, return the first question                    |
| `submit_answer`    | grade a spoken answer, adapt, return the next question        |
| `explain`          | one or two spoken sentences on a concept                      |
| `session_summary`  | how the session went                                          |
| `tutor_report`     | the pattern behind the errors, for a parent or tutor          |
| `student_progress` | what is settled and what is still open, across sessions       |
| `class_report`     | which confusions recur across every student who studied a set |

`start_practice` and `submit_answer` are bound to `ui://study-coach/practice.html`.

## Running it

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # POSIX: .venv/bin/pip
.venv/Scripts/python server/app.py                 # serves /mcp on :8421
```

Then, in another shell:

```bash
.venv/Scripts/python harness/smoke_client.py       # full session over MCP
.venv/Scripts/python harness/test_grading.py       # 20 hard spoken answers
.venv/Scripts/python harness/test_diagnosis.py     # does it diagnose, and settle?
.venv/Scripts/python harness/test_memory.py        # does it remember across sessions?
.venv/Scripts/python harness/test_adaptive.py      # does it read the student?
.venv/Scripts/python harness/test_topic_map.py     # a synthetic class of nine
.venv/Scripts/python harness/test_content.py       # is the study set itself sound?
.venv/Scripts/python harness/test_auth.py          # does it refuse the wrong token?
```

The server requires a bearer token on `/mcp` and refuses without one. On a
laptop it runs in development mode: tokens are signed with a secret that is a
literal in `server/auth.py`, the server says so on every start, and the harness
mints its own, so every scripted run goes through the same check Alexa+ will.
Point it at a real authorization server with `MCP_AUTH_ISSUER` and
`MCP_AUTH_JWKS_URL`; set `MCP_RESOURCE_URI` to the server's public URL, because
that is the audience a token has to name.

For a judge-facing Alexa+-style proof backed by the real MCP server, start the
server and the presentation shell in two shells:

```bash
.venv/bin/python server/app.py
.venv/bin/python preview/demo_server.py
```

Open `http://127.0.0.1:8430`. The shell is presentation only: every question,
grade, confusion, resolution, and persisted-progress result comes from live
Streamable HTTP MCP calls to the server on port 8421.

## Layout

```
server/grading.py   attribution over a closed candidate set; all language-specific
                    parts isolated in one `Language` object
server/store.py     study sets, sessions, confusion tracking, contrast drilling,
                    resolution, and adaptive card selection
server/adaptive.py  reading how an answer arrived: strain, ease, and what to do
server/history.py   what survives a session - which confusions are open, which
                    are settled, where the student's level sits, and the same
                    confusions summed across every student who studied a set
server/app.py       the MCP server: tools, discovery documents, health
server/auth.py      the OAuth 2.1 resource server: bearer validation, audience
                    and scope checks, Origin validation
server/ui.py        the MCP Apps card rendered on devices with a display
content/            study sets as plain JSON - the shape a worksheet becomes
tools/              build_study_set.py   worksheet or topic -> a study set, built
                                         around the confusions, offline
                    verify_study_set.py  checks any set with the live grader
harness/            the tests that decide whether any of this is true
data/students/      one profile per real student (gitignored)
data/scratch/       the same, for students whose id is marked synthetic - the
                    harness and the demo. Never counted in a class report, and
                    emptied when the server starts
```

## Limitations, stated plainly

**[`LIMITATIONS.md`](LIMITATIONS.md) is the full account**, and
**[`ADVERSARIAL_REVIEW.md`](ADVERSARIAL_REVIEW.md)** is how most of it was
found: four simulated stakeholders driving the running server, who between them
surfaced seven defects a green test suite was hiding — because every test in
this repository modelled a student who eventually learns, and this product is
for the one who does not. That review is engineering evidence and explicitly not
evidence that anyone learns better. Both are worth
reading before the code. It covers the three ways the grader can be wrong and
which one invents a record; what authentication does and does not cover; how a
teacher who
runs the class report twice can identify one student; why the report describes a
narrower population than "the class"; and what we checked and found sound. Four
people stress-tested this build — a student, a teacher, a parent and a platform
reviewer — and most of what is in that file, they found.

The short version:

- **English only.** Alexa+ is not available in the Netherlands and the simulator
  is `en-US`. The language-specific parts are isolated in `grading.ACTIVE`, but a
  Dutch version needs a Dutch phonetic coder, which is real work and untestable
  on a platform that is not here yet.
- **`manner` is unverified against the real platform.** The tool description
  invites Alexa+ to describe what the student did, and Alexa+ is free to ignore
  it, or to send an emotion label anyway — which the server drops. That is why
  nothing depends on it, and why the adaptive tests run the whole arc without it.
- **Student profiles are JSON on disk.** Fine locally, and fenced behind
  `history.load` / `history.save` so Lambda can swap in DynamoDB on the same
  student key. Live sessions are still in memory, keyed by the MCP session id.
- **The diagnosis needs a study set with confusable answers in it.** It can only
  attribute an answer to something it knows about.
- **Difficulty is three levels, hand-labelled in the content.** Enough to move
  between, not enough to be called a model of the student.
- **The generator has not been run against the live API from this checkout.**
  Its request shape, prompt and pydantic schema are exercised offline, and the
  verification half runs on every set in `content/` — but the set that ships was
  written by hand, and no generated set has been produced end to end yet. The
  first real run needs an `ANTHROPIC_API_KEY`.

## Friction log

Product feedback on the Alexa+ MCP Toolkit, the MCP Python SDK and the MCP Apps
extension, kept at the moment each thing cost us something: [`FRICTION.md`](FRICTION.md).

## Licence

MIT — see `LICENSE`.
