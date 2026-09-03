# Study Coach

An Alexa+ add-on that revises with a student out loud — and when they get
something wrong, tells them *which* idea they reached for instead, drills that
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

> *4 out of 7 on The Cell. The errors are not spread out. 3 of them are the same
> confusion: when asked about the chloroplasts, the answer given was the
> mitochondria.*

…or, when the student got there:

> *6 out of 8 on The Cell. One confusion was settled during the session: the
> chloroplasts against the mitochondria, answered correctly from both sides at
> the end.*

A flashcard app cannot say either sentence. It records one bit per answer.

## The problem underneath: you cannot grade speech with a similarity threshold

The obvious way to mark a spoken answer is to accept it when it is *similar
enough* to the expected one. We measured that this cannot work.

Speech recognition mangles words phonetically, so a correct answer can arrive
badly distorted while a genuinely different answer can be spelled almost
identically:

| spoken | expected | similarity | must be |
|---|---|---|---|
| `"new clee us"` | `nucleus` | **0.750** | correct |
| `"nucleus"` | `nucleolus` | **0.875** | wrong |

The wrong pair scores *higher* than the right one. No threshold separates these
classes — not on letters, and not on phonetic keys either. The classes genuinely
overlap.

So the grader does not ask "is this close enough?". It asks **"of every answer
that appears anywhere in this study set, which one did the student say?"** — a
nearest-neighbour attribution over a known, closed candidate set, deciding
between the best *right* answer and the best *wrong* one. `nucleolus` stops
being a near-miss and becomes its own candidate.

Two things fall out of that:

1. It works. 20/20 on the hard cases in `harness/test_grading.py`, including
   distortions like `"the might o chondria"` and `"sell wall"`.
2. Being wrong is no longer one bit. We know *which* concept was reached for —
   which is what everything above and below is built on.

## It remembers the student, not the score

Sessions end. Misconceptions don't. So what survives a session is the diagnosis:

```
ALEXA   : Welcome back. Yesterday the mitochondria and the chloroplasts kept
          swapping places. Shall we settle that first? Question 1. Which
          organelle captures light energy in a plant cell?
```

That line is only available to something that kept *which two things* rather
than *how many out of ten*. The unsettled pair is not a fresh question — it is
unfinished business, so it goes first, carrying its history, and two right
answers now close it for good. A confusion that comes back after being settled
goes back on the open list rather than being quietly forgotten.

`student_progress` reads the same record across sessions: what has been settled
for good, and what is still open.

## It reads how the answer arrived, not just whether it was right

A tutor pushes when it is all going in too easily and backs off when the student
is losing heart. That needs a signal about *how* an answer arrived.

It would be convenient to read the tone of voice. **We cannot** — the Alexa+ MCP
toolkit hands a server tool arguments, and nothing in its documented contract
carries audio, prosody or affect. The server never hears the student. So the
signal is split, each half where it belongs:

| | |
|---|---|
| **observed here** | hesitation and give-up markers in the transcript, how long the answer took once Alexa's own speaking time is subtracted, and the run of right and wrong |
| **asked of Alexa+** | an optional `manner` argument on `submit_answer` — Alexa+ *did* hear the student, so the tool description invites it to say how they sounded |

`manner` is a hint that sharpens the read, never a requirement. Everything works
with it absent, the same way the screen card is additive to the voice — and
`harness/test_adaptive.py` drives the whole collapse-and-recover arc twice, once
with it and once without, requiring the session to cope either way.

There is a nice symmetry in the transcript half: the filler the grader throws
away (`"um"`, `"I guess"`) is exactly the evidence this half keeps. The same
token means *ignore me* to one part of the server and *this was effortful* to
the other.

What it does with the read:

- **struggling** → step the questions down a level and add support: first a
  hint, then two options to choose between. And say so, because an unexplained
  drop in difficulty reads as being patronised.
- **cruising** → step up. But only when the student is both accurate *and*
  comfortable: a streak scraped through slowly is not an invitation.
- **recovering** → take the support away one rung at a time, and never in the
  same breath as making the question harder.

Still no model call. It is a weighted sum over signals already in hand by the
time the answer has been graded.

## Why there is no model in the request path

Alexa+ requires a round-trip under **500 ms**. A call to a language model costs
200–800 ms on its own, so it cannot live inside the answer path.

It does not need to. Alexa+ already supplies the conversation and the reasoning;
what it cannot do is decide reliably whether a mangled utterance was the right
answer. That judgement is deterministic, explainable, and free:

| | measured |
|---|---|
| grading, median | **3.6 ms** |
| grading, p99 | **14.0 ms** — 3% of the platform budget |
| MCP round trip, median / worst | **8.9 ms** / **114.9 ms** |
| model calls while answering | **0** |

Grading is measured over 10,400 calls against the full thirteen-card set; the
round trip is what `harness/smoke_client.py` sees over Streamable HTTP, worst
case being the first call into a cold server.

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

| tool | purpose |
|---|---|
| `list_study_sets` | what this student can practise |
| `start_practice` | begin a session, return the first question |
| `submit_answer` | grade a spoken answer, adapt, return the next question |
| `explain` | one or two spoken sentences on a concept |
| `session_summary` | how the session went |
| `tutor_report` | the pattern behind the errors, for a parent or tutor |
| `student_progress` | what is settled and what is still open, across sessions |

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
```

## Layout

```
server/grading.py   attribution over a closed candidate set; all language-specific
                    parts isolated in one `Language` object
server/store.py     study sets, sessions, confusion tracking, contrast drilling,
                    resolution, and adaptive card selection
server/adaptive.py  reading how an answer arrived: strain, ease, and what to do
server/history.py   what survives a session - which confusions are open, which
                    are settled, and roughly where the student's level sits
server/app.py       the MCP server: tools, OAuth metadata, health
server/ui.py        the MCP Apps card rendered on devices with a display
content/            study sets as plain JSON - the shape a worksheet becomes
harness/            the tests that decide whether any of this is true
```

## Limitations, stated plainly

- **English only.** Alexa+ is not available in the Netherlands and the simulator
  is `en-US`. The language-specific parts are isolated in `grading.ACTIVE`, but a
  Dutch version needs a Dutch phonetic coder, which is real work and untestable
  on a platform that is not here yet.
- **`manner` is unverified against the real platform.** The tool description
  invites Alexa+ to describe how the student sounded, and Alexa+ is free to
  ignore it. That is why nothing depends on it, and why the adaptive tests run
  the whole arc without it.
- **Student profiles are JSON on disk.** Fine locally, and fenced behind
  `history.load` / `history.save` so Lambda can swap in DynamoDB on the same
  student key. Live sessions are still in memory, keyed by the MCP session id.
- **The diagnosis needs a study set with confusable answers in it.** It can only
  attribute an answer to something it knows about.
- **Difficulty is three levels, hand-labelled in the content.** Enough to move
  between, not enough to be called a model of the student.

## Licence

MIT — see `LICENSE`.
