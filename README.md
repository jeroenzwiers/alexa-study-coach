# Study Coach

An Alexa+ add-on that revises with a student out loud — and when they get
something wrong, tells them *which* idea they reached for instead.

Built for the Alexa+ track of the **Build, Ship, Shape: Amazon Developer
Hackathon**. It is an MCP server implementing spec version `2025-11-25` over
Streamable HTTP.

```
ALEXA   : Question 5. Which organelle releases energy from glucose?
STUDENT : "chloroplasts"
ALEXA   : Not quite - that's the chloroplasts. Chloroplasts capture energy from
          light; mitochondria release it from food. The answer is The
          mitochondria. Question 6. Which organelle captures light energy?
STUDENT : "mitochondria"
ALEXA   : Not quite - that's the mitochondria. Let's separate those two. Which
          organelle captures light energy in a plant cell? Is it the
          mitochondria, or the chloroplasts?
```

That third turn is the point. The student did not make two unlucky mistakes;
they have one misconception, seen from both sides. The session notices, stops
drawing random cards, and drills the distinction — then reports it:

> *4 out of 7 on The Cell. The errors are not spread out. 3 of them are the same
> confusion: when asked about the chloroplasts, the answer given was the
> mitochondria.*

A flashcard app cannot say that sentence. It records one bit per answer.

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
   which is what the whole diagnosis above is built on.

## Why there is no model in the request path

Alexa+ requires a round-trip under **500 ms**. A call to a language model costs
200–800 ms on its own, so it cannot live inside the answer path.

It does not need to. Alexa+ already supplies the conversation and the reasoning;
what it cannot do is decide reliably whether a mangled utterance was the right
answer. That judgement is deterministic, explainable, and free:

| | measured |
|---|---|
| grading, p99 | **10.3 ms** — 2% of the platform budget |
| MCP round trip, median | **9.8 ms** |
| model calls while answering | **0** |

## On a screen, it shows the one thing voice cannot

Devices with a display get a card through the **MCP Apps extension**
(`io.modelcontextprotocol/ui`). It does not transcribe the conversation —
repeating spoken words on screen adds nothing. It shows the progress, the
verdict, and, when a confusion keeps recurring, **the two confused concepts side
by side**, which is exactly the thing a voice cannot put next to each other.

Per SEP-2133 the extension is additive: `start_practice` and `submit_answer`
carry `_meta.ui.resourceUri`, and every tool still returns full spoken text, so a
speaker with no display loses only the picture. The other four tools have no UI
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

`start_practice` and `submit_answer` are bound to `ui://study-coach/practice.html`.

## Running it

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # POSIX: .venv/bin/pip
.venv/Scripts/python server/app.py                 # serves /mcp on :8080
```

Then, in another shell:

```bash
.venv/Scripts/python harness/smoke_client.py       # full session over MCP
.venv/Scripts/python harness/test_grading.py       # 20 hard spoken answers
.venv/Scripts/python harness/test_diagnosis.py     # does it diagnose, or only score?
```

## Layout

```
server/grading.py   attribution over a closed candidate set; all language-specific
                    parts isolated in one `Language` object
server/store.py     study sets, sessions, confusion tracking, contrast drilling
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
- **Sessions live in memory.** Fine locally; on Lambda they belong in DynamoDB,
  keyed by the MCP session id.
- **The diagnosis needs a study set with confusable answers in it.** It can only
  attribute an answer to something it knows about.

## Licence

MIT — see `LICENSE`.
