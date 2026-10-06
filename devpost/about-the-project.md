## Inspiration

A revision app marks an answer right or wrong, and throws away the only
interesting thing it knows. When a child says *chloroplasts* and the answer was
*mitochondria*, "wrong" is one bit. **Which** wrong thing they said is the whole
diagnosis, and no flashcard app keeps it.

Keep it, and a revision session can say things it otherwise cannot:

> *"Not quite — you said the chloroplasts. Chloroplasts capture energy from
> light; mitochondria release it from food."*

…and then, two questions later:

> *"You had the chloroplasts and the mitochondria the wrong way round twice
> tonight, and you've just had them both right. That one's done."*

That second sentence is why the project exists. It is the one piece of good news
a revision session can honestly deliver, and marking cannot produce it.

## What it does

Study Coach is an Alexa+ add-on that revises with a student out loud. Three
things fall out of knowing which idea they reached for:

1. **It names the confusion.** Two misses on the same pair are not two unlucky
   mistakes; they are one misconception seen from both sides.
2. **It goes looking for the other side.** After the first miss, the mirrored
   question is scheduled deliberately — whether a confusion is real should not be
   left to the shuffle.
3. **It closes.** Getting the contrast right is recognition. Getting the
   mirrored question right too is the distinction actually holding.

Built on top of that:

- **It remembers.** An unsettled confusion is carried into next week's session
  and re-probed; a settled one is retired. Session state is written *during* the
  session, so a child who puts the speaker down halfway keeps their evening.
- **It reports the pattern, not the score.** `tutor_report` for a parent, and
  `class_report` for a teacher: *"Nine students have practised The Cell. One
  confusion stands out: osmosis and diffusion, seven students. Six of them go the
  same way: asked about osmosis, they answer diffusion. Three have since settled
  it."* The useful sentence is the second-to-last. Not "they confuse these two"
  but **which half of the distinction is missing** — and no marking scheme
  produces it.
- **On a screen it shows what voice cannot.** The MCP Apps extension (SEP-2133,
  `io.modelcontextprotocol/ui`) renders a card that does not transcribe the
  conversation. It holds the two confused concepts side by side, and the moment
  the pair is finally told apart. Voice says that once and it is gone. The
  extension is additive: every tool still returns full spoken text, so a speaker
  with no display loses only the picture.

### It reads how the answer arrived — and stops exactly where the law does

A tutor pushes when it is all going in too easily and backs off when the student
is losing heart. That needs a signal about *how* an answer arrived. It would be
convenient to read tone of voice, and we cannot: nothing in the Alexa+ MCP tool
contract carries audio, prosody or affect, and the server never hears the
student.

So the signal is split. The server reads hesitation markers, time-to-answer with
Alexa's own speaking time subtracted, and the run of right and wrong. And
`submit_answer` takes an optional `manner` argument that asks Alexa+ — which
*did* hear the student — for what the student **did**: "long pause before
answering", "asked to stop", "answered instantly".

`manner` carries observable behaviour and **never an emotion label**. The server
matches it against an allowlist of behavioural phrases, so an emotion word handed
over willingly matches nothing: it is not detected and refused, it is simply
inert. Fourteen emotion labels produced an adjustment identical to passing
nothing at all.

That is a legal line, not a stylistic one. **Article 5(1)(f) of the EU AI Act
prohibits AI systems that infer a person's emotions in education**, in force
since 2 February 2025, with only medical and safety exceptions. A revision coach
sits squarely in that domain. Reading what a student *did* is not inferring what
they *felt*, and keeping the two apart is what lets the feature exist at all.

## How we built it

**The core decision: grading is attribution, not similarity.** The obvious way to
mark a spoken answer is to accept it when it is similar enough to the expected
one. We measured that this cannot work. Speech recognition mangles words
phonetically, so a correct answer arrives distorted while a genuinely different
answer is spelled almost identically:

- `"new clee us"` against **nucleus** — letter similarity **0.667** — must be correct
- `"nucleus"` against **nucleolus** — letter similarity **0.875** — must be wrong

The wrong pair scores higher than the right one. On the content this repo ships,
the lowest legitimate speech distortion scores 0.800 and the highest wrong answer
that must be rejected scores 0.857. The classes overlap, so no threshold
separates them.

So the grader never asks "is this close enough?". It asks **"of every answer that
appears anywhere in this study set, which one did the student say?"** —
nearest-neighbour attribution over a known, closed candidate set, deciding
between the best right answer and the best wrong one. `nucleolus` stops being a
near-miss and becomes its own candidate. That one decision is what produces the
diagnosis: you cannot name a misconception unless grading tells you which concept
was reached for, and a threshold never can.

**Zero model calls in the answer path.** The Alexa+ MCP quickstart requires a
round trip under 500 ms. A language model call costs 200–800 ms on its own, so it
cannot live there. It does not need to: Alexa+ supplies the conversation and the
reasoning, and what it cannot do reliably is decide whether a mangled utterance
was the right answer.

- grading, median — **11.3 ms**
- grading, p99 — **49.6 ms**, 10% of the platform budget
- MCP round trip, median / worst — 14–20 ms / 169–239 ms
- model calls while the student is waiting — **0**

Reproduce it with `harness/bench_grading.py`: 10,400 calls against the full
thirteen-card set, each on an utterance the grader has not seen before. That last
part is the methodology, because warming a cache on the student's own words would
report a grader that never does any work — an earlier version of this table was
measured that way and read three times faster than the truth. These figures are
from an otherwise idle laptop, and that qualifier is load-bearing: running the
presentation shell alongside the server moves p99 to 119.3 ms and the worst round
trip to 912 ms.

**A model is used — offline.** `tools/build_study_set.py` turns a worksheet into
a study set built *around the confusions*, with both halves of every pair
present. `tools/verify_study_set.py` then checks the model's work with the real
`grading.grade` that serves live traffic, including the assertion the whole
product rests on: saying card A's answer to card B's question must still be
attributed to A.

**The server.** Self-hosted MCP on spec `2025-11-25` over Streamable HTTP
(`mcp==2.1.1`, uvicorn), fronted by an OAuth 2.1 resource server of our own:
bearer validation, audience and scope checks, `Origin` validation against DNS
rebinding, `401` on unauthenticated requests, and both
`/.well-known/oauth-authorization-server` and RFC 9728
`/.well-known/oauth-protected-resource`, because the quickstart conflates the
two. Eight tools, two of them UI-bound.

**The video is built by the repository**, not by a screen recorder. `preview/`
runs the presentation shell against the real server, `tools/record_demo.mjs`
drives it in headless Chrome and writes a still each time something visibly
changes — with the page stamping its own change times, because timing a frame by
when the recorder noticed put every card three seconds behind its own line — and
`tools/mux_demo.py` lays 43 pre-rendered speech clips back at the exact
millisecond each one played. Both halves came off the same clock, so nothing is
stretched or nudged.

## Challenges we ran into

The honest list is `FRICTION.md` in the repository: fifteen numbered items with
reproductions, each written down when it cost us something rather than
reconstructed afterwards. The short version:

- **The `alexa-ai` CLI is not on public npm.** It lives in a private AWS
  CodeArtifact repository behind an IAM role we could not be granted, so the
  documented path to a deployed add-on was closed from the first command. The
  submission requirements do not require a deployed add-on, which is the only
  reason this project exists at all.
- **The toolkit and the MCP specification disagree** in places, most sharply on
  which well-known document is the "Protected Resource Metadata" one. We serve
  both.
- **The MCP Apps extension is young** enough that the thing we most wanted to
  know — what a real Alexa+ device does with a card it does not recognise — is
  not written down anywhere we could find.

The hardest *engineering* problem was none of those. In a real speech render, the
pauses inside a sentence measure 0.40–0.46 s and the pauses between sentences
0.46–0.57 s. Overlapping classes, no threshold between them — which is exactly
the shape of the problem this product exists to solve. It got the same answer:
stop classifying the gaps and attribute instead. Cut finely, then group the
pieces by what each line's character count says it should weigh.

## Accomplishments that we're proud of

Not a feature. It is that the repository contains the measurements that make our
own claims smaller.

`LIMITATIONS.md` opens with the case where grading against the content we
actually ship does *worse* than the number in the test file, explains why, and
says the fix is content-side rather than a threshold. The class report's own
section states that it is aggregate in the code and **not** in the system: a
teacher who runs it twice, thirty-five minutes apart with one child practising in
between, reads the identity off the deltas. We wrote that above the good news
rather than underneath it.

For a product whose users are children, that is the part we would want a judge to
check first.

## What we learned

Everything measurable here was verified automatically — and four defects in the
finished demo were found by a human watching it: a verdict that read as
agreement, a question whose subject was never named, a card that appeared before
its line was spoken, and a clip that said "That's right" twice.

We could verify placement and timing. We could not verify meaning. For anything
that will be listened to rather than executed, that gap is the thing to plan for.

## What's next for Study Coach

Content coverage is the honest bottleneck. The diagnosis is only as good as the
closed candidate set, and a set that omits the wrong answers students actually
give is silently useless rather than visibly broken — it attributes the answer to
the nearest card anyway and usually marks it correct.

Then a real deployment behind Cognito — the server is already a resource server,
so that is configuration rather than construction — and the `class_report` timing
leak, which needs k-anonymity over a fixed window rather than counting on call.

### What this submission does not claim

- **No child has used it.** The class report is demonstrated against generated
  profiles, and the demo video's learner answers are scripted so the run repeats.
  Every verdict, question, diagnosis and report in the video came back from the
  real server; the voices are synthesised and none of them is Amazon's.
- **It is not deployed in Alexa+.** It is a server on the track's specification,
  runnable by anyone who clones it.
- **The latency figures are from one idle laptop**, and the section that gives
  them also gives the numbers under load.
