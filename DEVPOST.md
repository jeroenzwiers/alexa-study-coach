# Devpost submission — Study Coach

Everything on this page is text to be pasted into the Devpost form, field by
field. It is kept in the repo so the submitted wording and the code it describes
stay in one place, and so every number in it can be traced to the file that
produced it.

The **About the project** section below uses Devpost's own seven headings in
Devpost's own order, so it goes into that box whole. The two tables are written
as lists on purpose: the box is Markdown, but pipe tables are not reliably
rendered there and a collapsed table reads worse than no table.

Status of the parts that are not text:

- **Demo video** — <https://youtu.be/QTodUEiRStI>, 2:53, English, Public
  (verified anonymously: `isUnlisted: false`, `isPrivate: false`).
- **Public repository** — <https://github.com/jeroenzwiers/alexa-study-coach>,
  MIT, reachable without signing in, and linked from the video description.
- **Thumbnail** — `preview/devpost-thumbnail.jpg`, 1200×800, the 3:2 the form
  asks for. Not a logo: a frame of the running thing, carrying the whole arc on
  one screen — a wrong answer attributed to a named concept, the contrast
  question chosen rather than shuffled, and the pair closed.
- **Image gallery** — `preview/gallery/`, five images at the same 3:2, cut from
  the same recorded frames and named in the order they should be uploaded:

  1. `1-the-claim.jpg` — the opening screen and what to watch for
  2. `2-real-server.jpg` — the MCP connection: spec 2025-11-25, Streamable HTTP,
     eight tools, no model on this path, grading 11 ms median
  3. `3-confusion-named.jpg` — a wrong answer attributed to a named concept, and
     the contrast question scheduled to settle the pair
  4. `4-pair-closed.jpg` — the pair closed from both sides, and the handover to
     a second subject
  5. `5-second-subject.jpg` — the same machinery on authorization against
     authentication, with all three watch-for items ticked

---

## Short fields

**Project name**

```
Study Coach
```

**Elevator pitch** (200 characters; this is 170)

```
It doesn't mark the answer wrong. It names the idea the student reached for instead, drills that one distinction until it holds, and remembers it next week if it doesn't.
```

**Built with** (15 of the 25 allowed)

```
python, mcp, model-context-protocol, streamable-http, oauth2, jwt, uvicorn, pydantic, jellyfish, mcp-apps, claude, javascript, puppeteer, ffmpeg, alexa
```

**Try it out links**

```
https://github.com/jeroenzwiers/alexa-study-coach
https://youtu.be/QTodUEiRStI
```

**Video demo link**

```
https://youtu.be/QTodUEiRStI
```

**Track**

```
Alexa+
```

**Mini-challenges**

```
Open Source ($5,000) - MIT, public repository, and the whole thing: the server, the test harness, the content tooling and the friction log.
```

**Open Source Mini Challenge — the required write-up**

Paste **`devpost/open-source.md`**, not this file. The field takes the write-up
and nothing else; it is quoted below only so this page stays readable.

> A new MIT-licensed repository, created inside the hackathon window:
> <https://github.com/jeroenzwiers/alexa-study-coach>, 59 commits between
> 2 September and 6 October 2026.
>
> **What it is.** A self-hosted MCP server on spec 2025-11-25 over Streamable
> HTTP that revises with a student by voice and, when they are wrong, names the
> concept they reached for instead of the right one.
>
> **How it works.** Grading is nearest-neighbour attribution over the closed set
> of answers in a study set, not a similarity threshold. We measured that no
> threshold can work: a correct answer distorted by speech recognition scores
> lower than a genuinely wrong one that happens to be spelled alike. Knowing
> *which* wrong answer was given is what lets the server name a confusion,
> deliberately schedule the mirrored question, and close the pair when both
> sides come back right.
>
> **Why it matters as open source.** Everything a reader would need in order to
> disbelieve us is in the repository. `LIMITATIONS.md` documents where the
> grader does worse than its own test file reports and why the fix is
> content-side. `FRICTION.md` is fifteen logged problems with the tools, written
> down as they cost us something. The harness reproduces every figure in the
> README. Three parts are reusable on their own: the OAuth 2.1 resource server,
> the study-set verifier that checks generated content with the live grader, and
> the audio-splitting tool that groups speech by expected length instead of
> thresholding the pauses.

**Contribution URL** and **Project Repository URL** are the same here, because
the contribution *is* the new repository the rules allow:
`https://github.com/jeroenzwiers/alexa-study-coach`. **GitHub username**:
`jeroenzwiers`.

AWS Builder is deliberately **not** claimed. Nothing in this project runs on
AWS: the server is self-hosted, and the one AWS dependency we met — the private
CodeArtifact repository the `alexa-ai` CLI lives in — we never got access to
(friction log items 1 and 2). Verified rather than assumed: nothing in
`server/`, `tools/`, `harness/` or the dependency list imports or calls an AWS
service — no boto3, no Bedrock, no SageMaker. Claiming it would be a claim the
code cannot show, and the rules allow one mini-prize anyway.

There is no hosted URL on purpose. The Alexa+ track asks for a server on the MCP
specification; the rules point judges at the repository and the video, not at a
running endpoint, and a tunnel from a laptop would have been a weaker claim than
a server anyone can start themselves.

---

## About the project

**Do not paste this file.** It carries the text of every field at once, so
pasting it into any one box puts all the others in there too — which is exactly
what happened, twice. Every box that takes prose has its own file in
**`devpost/`**; open it, select all, paste:

| Devpost field | file |
| --- | --- |
| About the project | `devpost/about-the-project.md` |
| Open Source mini challenge, description | `devpost/open-source.md` |
| [Optional] Feature Requests | `devpost/feature-requests.md` |
| Feedback 1: which tools did you use | `devpost/feedback-1-what-we-used.md` |
| Feedback 2: what worked well | `devpost/feedback-2-what-worked.md` |
| Feedback 3: what needs work | `devpost/feedback-3-what-needs-work.md` |
| Feedback 4: onboarding | `devpost/feedback-4-onboarding.md` |
| Feedback 5: would you build again | `devpost/feedback-5-again.md` |
| [Optional] Friction Log | a URL, not text: <https://github.com/jeroenzwiers/alexa-study-coach/blob/main/FRICTION.md> |

`devpost/about-the-project.md` is cut from the story below by this command, so
the two cannot drift apart:

```
python -c "import pathlib; s=pathlib.Path('DEVPOST.md').read_text(encoding='utf-8');   pathlib.Path('devpost/about-the-project.md').write_text(s[s.index('## Inspiration'):s.index(chr(10)+'---'+chr(10)+chr(10)+'*End of the')].rstrip()+chr(10), encoding='utf-8')"
```

---

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

---

*End of the "About the project" box.*
