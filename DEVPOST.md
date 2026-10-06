# Devpost submission — Study Coach

Everything on this page is text to be pasted into the Devpost form, field by
field. It is kept in the repo so the submitted wording and the code it describes
stay in one place, and so every number in it can be traced to the file that
produced it.

Status of the two things the form needs that are not text:

- **Demo video** — <https://youtu.be/QTodUEiRStI>, 2:53, English. Must be set to
  **Public**; the rules ask for a publicly visible video and Unlisted is not
  demonstrably that.
- **Public repository** — not yet. The MIT licence is already in place; the repo
  has to be flipped from private, and the resulting URL then goes into the
  YouTube description as well as here.

---

## Short fields

**Project name**

```
Study Coach
```

**Tagline**

```
A revision coach for Alexa+ that doesn't mark the answer wrong - it names the idea the student reached for instead.
```

**Track**

```
Alexa+
```

**Mini-challenges**

```
Open Source ($5,000) - MIT, public repository, and the whole thing: the server, the test harness, the content tooling and the friction log.
```

AWS Builder is deliberately **not** claimed. Nothing in this project runs on
AWS: the server is self-hosted, and the one AWS dependency we met — the private
CodeArtifact repository the `alexa-ai` CLI lives in — we never got access to
(friction log items 1 and 2). Claiming it would be a claim the code cannot show,
and the rules allow one mini-prize anyway.

**Built with**

```
python, mcp, model-context-protocol, streamable-http, oauth2, jwt, uvicorn, pydantic, jellyfish, mcp-apps, claude, javascript, puppeteer, ffmpeg
```

**Try it out**

```
https://github.com/jeroenzwiers/alexa-study-coach    (clone and run - the README has the commands)
https://youtu.be/QTodUEiRStI                          (2:53 demo)
```

There is no hosted URL on purpose. The Alexa+ track asks for a server on the MCP
specification; the rules point judges at the repository and the video, not at a
running endpoint, and a tunnel from a laptop would have been a weaker claim than
a server anyone can start themselves.

---

## About the project

### The sentence a flashcard app cannot say

> _"Not quite — you said the chloroplasts. Chloroplasts capture energy from
> light; mitochondria release it from food."_

…and then, two questions later:

> _"You had the chloroplasts and the mitochondria the wrong way round twice
> tonight, and you've just had them both right. That one's done."_

Marking is one bit per answer: right, wrong. Everything a revision session could
usefully tell a child is in the bit it throws away — **which** wrong thing they
said. Study Coach keeps it, and the whole product falls out of that one fact.

1. **It names the confusion.** Two misses on the same pair are not two unlucky
   mistakes; they are one misconception seen from both sides.
2. **It goes looking for the other side.** After the first miss, the mirrored
   question is scheduled deliberately — whether a confusion is real should not
   be left to the shuffle.
3. **It closes.** Getting the contrast right is recognition. Getting the
   mirrored question right too is the distinction actually holding, and that is
   the one piece of good news a revision session can honestly deliver.

### The problem underneath: you cannot grade speech with a threshold

The obvious way to mark a spoken answer is to accept it when it is similar
enough to the expected one. We measured that this cannot work. Speech
recognition mangles words phonetically, so a correct answer arrives distorted
while a genuinely different answer is spelled almost identically:

| spoken        | expected  | letter similarity | must be |
| ------------- | --------- | ----------------- | ------- |
| "new clee us" | nucleus   | 0.667             | correct |
| "nucleus"     | nucleolus | 0.875             | wrong   |

The wrong pair scores higher than the right one. On the content this repo ships,
the lowest legitimate speech distortion scores 0.800 and the highest wrong
answer that must be rejected scores 0.857 — the classes overlap, so no threshold
separates them.

So the grader never asks "is this close enough?". It asks **"of every answer
that appears anywhere in this study set, which one did the student say?"** —
nearest-neighbour attribution over a known, closed candidate set, deciding
between the best right answer and the best wrong one. `nucleolus` stops being a
near-miss and becomes its own candidate.

That one decision is what produces the diagnosis. You cannot name a
misconception unless grading tells you which concept was reached for, and a
threshold never can.

### Zero model calls in the answer path

The Alexa+ MCP quickstart requires a round trip under 500 ms. A language model
call costs 200–800 ms on its own, so it cannot live there. It does not need to:
Alexa+ supplies the conversation and the reasoning, and what it cannot do
reliably is decide whether a mangled utterance was the right answer. That
judgement is deterministic, explainable and free.

| | measured |
| --- | --- |
| grading, median | **11.3 ms** |
| grading, p99 | **49.6 ms** — 10% of the platform budget |
| MCP round trip, median / worst | 14–20 ms / 169–239 ms |
| model calls while answering | **0** |

Reproduce it with `harness/bench_grading.py`: 10,400 calls against the full
thirteen-card set, each on an utterance the grader has not seen before. That
last part is the methodology, because warming a cache on the student's own words
would report a grader that never does any work — an earlier version of this
table was measured that way and read three times faster than the truth.

These figures are from an otherwise idle laptop, and that qualifier is
load-bearing: running the presentation shell alongside the server moves p99 from
49.6 ms to 119.3 ms and the worst round trip from 239 ms to 912 ms. Read them as
what the work costs, not as a guarantee about the box it runs on.

A model *is* used — offline. `tools/build_study_set.py` turns a worksheet into a
study set built **around the confusions**, with both halves of every pair
present, and `tools/verify_study_set.py` then checks the model's work with the
real `grading.grade` that serves live traffic, including the assertion the whole
product rests on: saying card A's answer to card B's question must still be
attributed to A.

### What gets built on top of the diagnosis

- **It remembers.** An unsettled confusion is carried into next week's session
  and re-probed; a settled one is retired. Session state is written *during* the
  session, so a child who puts the speaker down halfway keeps their evening.
- **It reads how the answer arrived.** Hesitation markers, time-to-answer with
  Alexa's own speaking time subtracted, and the run of right and wrong feed a
  weighted sum that steps difficulty down with support, or up — but only when
  the student is both accurate *and* comfortable. A streak scraped through
  slowly is not an invitation.
- **It reports the pattern, not the score.** `tutor_report` for a parent;
  `class_report` for a teacher, which is the claim the video had no room for:
  _"Nine students have practised The Cell. One confusion stands out: osmosis and
  diffusion, seven students. Six of them go the same way: asked about osmosis,
  they answer diffusion. Three have since settled it."_ The useful sentence is
  the second-to-last: not "they confuse these two" but **which half of the
  distinction is missing**. No marking scheme produces it.
- **On a screen it shows what voice cannot.** The MCP Apps extension (SEP-2133,
  `io.modelcontextprotocol/ui`) renders a card that does not transcribe the
  conversation — it holds the two confused concepts side by side, and the moment
  the pair is finally told apart. Voice says that once and it is gone. The
  extension is additive: every tool still returns full spoken text, so a speaker
  with no display loses only the picture.

### A line drawn in the law, not just in the design

It would be convenient to read tone of voice. We cannot — nothing in the Alexa+
MCP tool contract carries audio, prosody or affect, and the server never hears
the student. So `submit_answer` takes an optional `manner` argument and asks
Alexa+ for what the student **did**: "long pause before answering", "asked to
stop", "answered instantly".

`manner` carries observable behaviour and **never an emotion label**. The server
matches it against an allowlist of behavioural phrases, so an emotion word
handed over willingly matches nothing: it is not detected and refused, it is
simply inert. Fourteen emotion labels produced an adjustment identical to
passing nothing at all (`harness/test_adaptive.py`).

That is a legal line, not a stylistic one. **Article 5(1)(f) of the EU AI Act
prohibits AI systems that infer a person's emotions in education**, in force
since 2 February 2025, with only medical and safety exceptions. A revision coach
sits squarely in that domain. Reading what a student *did* is not inferring what
they *felt*, and keeping the two apart is what lets the feature exist at all.

### How we built it

A self-hosted MCP server on spec version `2025-11-25` over Streamable HTTP
(`mcp==2.1.1`, uvicorn), fronted by an OAuth 2.1 resource server of our own
(`server/auth.py`): bearer validation, audience and scope checks, `Origin`
validation against DNS rebinding, `401` on unauthenticated requests, and both
`/.well-known/oauth-authorization-server` and RFC 9728
`/.well-known/oauth-protected-resource`, because the quickstart conflates the
two (friction item 5). Eight tools, two of them UI-bound.

The grader is `jellyfish` phonetics plus content-word and letter comparison
inside a single `Language` object, so the language-specific parts sit in one
place rather than sprinkled through the logic.

The demo video is built by the repository, not by a screen recorder: `preview/`
runs the presentation shell against the real server, `tools/record_demo.mjs`
drives it in headless Chrome and writes a still each time something visibly
changes — with the page stamping its own change times, because timing a frame by
when the recorder noticed put every card three seconds behind its own line — and
`tools/mux_demo.py` lays 43 pre-rendered speech clips back at the exact
millisecond each one played. Both halves came off the same clock, so nothing is
stretched or nudged.

### Challenges

The honest list is in **[`FRICTION.md`](FRICTION.md)** — fifteen numbered items
with reproductions, each written down when it cost us something rather than
reconstructed afterwards. It is also our product feedback, and the last four
items are what worked well, because a log that only complains is not feedback.
The short version:

- The `alexa-ai` CLI is not on public npm. It lives in a private AWS
  CodeArtifact repository behind an IAM role we could not be granted, so the
  documented path to a deployed add-on was closed from the first command. The
  submission requirements do not require a deployed add-on, which is the only
  reason this project exists at all.
- The toolkit's stated requirements and the MCP specification disagree in
  places, most sharply on which well-known document is the "Protected Resource
  Metadata" one. We serve both.
- The MCP Apps extension is young enough that the thing we most wanted to know —
  what a real Alexa+ device does with a card it does not recognise — is not
  written down anywhere we could find.

The hardest *engineering* problem was none of those. In a real speech render,
the pauses inside a sentence measure 0.40–0.46 s and the pauses between
sentences 0.46–0.57 s. Overlapping classes, no threshold between them. That is
the same shape as the problem this product exists to solve, and it got the same
answer: stop classifying the gaps and attribute instead — cut finely, then group
the pieces by what each line's character count says it should weigh.

### What we're proud of

Not a feature. It is that the repository contains the measurements that make the
claims smaller. `LIMITATIONS.md` opens with the case where grading against the
content we actually ship does *worse* than the number in the test file, explains
why, and says the fix is content-side rather than a threshold. The class
report's own section states that it is aggregate in the code and **not** in the
system: a teacher who runs it twice, thirty-five minutes apart with one child
practising in between, reads the identity off the deltas. We wrote that above
the good news rather than underneath it.

### What we learned

Everything measurable here was verified automatically, and four defects in the
finished demo were found by a human watching it: a verdict that read as
agreement, a question whose subject was never named, a card that appeared before
its line was spoken, and a clip that said "That's right" twice. We could verify
placement and timing. We could not verify meaning. That is worth knowing about
this kind of work.

### What's next

Content coverage is the honest bottleneck: the diagnosis is only as good as the
closed candidate set, and a set that omits the wrong answers students actually
give is silently useless rather than visibly broken (`LIMITATIONS.md` §1). Then
a real deployment behind Cognito — the server is already a resource server, so
that is configuration rather than construction — and the `class_report` timing
leak, which needs k-anonymity over a fixed window rather than counting on call.

---

## What this submission does not claim

- **No child has used it.** The class report is demonstrated against generated
  profiles, and the demo video's learner answers are scripted so the run
  repeats. Every verdict, question, diagnosis and report in the video came back
  from the real server; the voices are synthesised and none of them is Amazon's.
- **It is not deployed in Alexa+.** It is a server on the track's
  specification, runnable by anyone who clones it. Friction items 1 and 2 are
  why, and the submission rules are why that is admissible.
- **The latency figures are from one idle laptop**, and the section that gives
  them also gives the numbers under load.
