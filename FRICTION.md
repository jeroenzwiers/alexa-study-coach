# Friction log

Product feedback on the tools used to build Study Coach: the Alexa+ MCP Toolkit
and its documentation, the MCP Python SDK 2.x, and the MCP Apps extension
(SEP-2133).

**How this was kept.** Each item was written down at the moment it cost us
something, not reconstructed afterwards, which is why some entries record a
five-minute annoyance and one records an hour.

Items 1, 2 and 7–10 were logged on 2 September 2026 while building the server,
as were the three observations in _What worked well_. Items 3 and 4 were
established on 3 September 2026 by re-reading the toolkit documentation while
designing a feature that turned out to rest on behaviour the documentation does
not describe; both quotations there were checked against the live pages that
day. Items 5, 6 and 11 were logged on 9 September 2026 while building the
server's OAuth resource-server half, which is the first thing here that required
reading the toolkit's authentication page and the MCP authorization spec against
each other.

Items are grouped by tool and ordered within each group by what they cost. The
last section is what worked well, because a log that only complains is not
feedback — and in one case the SDK already does the right thing in the code path
next door to the one that doesn't.

---

## Alexa+ MCP Toolkit — getting to a working environment

### 1. The CLI is not where the documentation implies it is

`npm install -g @alexa-ai/cli` fails with `E404` against public npm. The package
lives in a private AWS CodeArtifact repository, reachable only from an AWS
account that can assume
`arn:aws:iam::372468808636:role/AddOn3PDeveloperToolsRead`.

The environment setup page presents the install as a step in a sequence. It is
not a step; it is a gate. A developer without an AWS account, or with one that
lacks that role, cannot begin — and finds out only after following several pages
of instructions that appeared to be working.

**Cost:** this is the single largest distance between "read the docs" and "have
something running", and it is invisible until you hit it.

**Fix:** state the prerequisite in the first paragraph of the setup page, above
the first command — what the role is, how to check whether you have it, and what
to do if you don't. An `E404` from npm is the least informative possible signal
for an authorisation problem.

**And say whether the door is open at all.** Re-checked on 7 September 2026 with
the developer account available here: no `@alexa-ai/cli` on public npm (`E404`),
no local binary, no account configuration that would grant the CodeArtifact
role. What we could not determine from the documentation is whether that is a
missing step on our side or a closed gate — whether toolkit access is restricted
to selected partners, how a developer checks their own eligibility, and where
the permitted simulated path is documented. We used the hackathon's simulated
Alexa+ path: `preview/demo_server.py` is a presentation shell only and drives
the real local Streamable HTTP server.

Two things this entry does *not* claim, because an earlier draft did and both
are falsifiable in five seconds. It is not a finding that no Alexa CLI exists —
`ask-cli` is public on npm and installs fine; it is the wrong CLI for this
toolkit, which is the point. And checking three places is not a proof that no
public onboarding path exists, only that we could not find one from the
documentation we were given.

### 2. The CodeArtifact token expires in 12 hours, and the failure looks like a broken package

Once the token lapses, subsequent installs fail in a way that reads as a
packaging or registry problem rather than an expired credential. The fix — run
`aws codeartifact login` again — is not suggested by the error.

**Fix:** put the 12-hour lifetime next to the login command rather than further
down the page, and show the expired-token error text so it is searchable.

---

## Alexa+ MCP Toolkit — the contract between Alexa+ and the server

These two cost us design decisions rather than debugging time, which makes them
more expensive than they look.

### 3. The documentation does not say what a tool call actually carries

The overview explains that Alexa+ handles natural language understanding,
response generation and UI rendering, and that the server receives tool calls.
It does not say what accompanies a request:

- Is any stable user or household identity available to the server?
- Is the locale passed?
- Is `_meta` populated, and with what?
- Is anything available about the utterance beyond the transcribed arguments?

We needed the first of those, because Study Coach remembers which misconceptions
a student left unsettled and opens the next session on them. With no documented
identity, the student key had to become an ordinary tool argument — which means
the feature works only if the assistant chooses to supply it, and degrades
silently to a shared default profile if it does not.

The fourth question shaped a feature outright. We wanted to adapt when a student
is struggling. Since nothing documented carries audio or affect, we split the
signal: the server reads the transcript and the timing, and asks Alexa+ for an
optional note describing observable behaviour. That is a defensible design, and
we would have reached it faster — and with more confidence — if a reference page
had simply said what arrives.

**Fix:** one page listing exactly what a tool invocation delivers to the server,
marking each field guaranteed or best-effort. For a protocol whose whole promise
is a clean contract, this is the page most conspicuously missing.

### 4. Two different latency figures live on two different pages, and neither says where it is measured

The binding number is in the **quickstart**, under Performance:

> "Your MCP server must meet a round-trip query response latency of less than
> 500 ms."

The **functional requirements** page — the page whose name promises to hold the
requirements — does not mention 500 ms at all. What it says about timing is:

> "Return results within 3 seconds. If processing takes longer, surface an
> interim message so the customer knows the system is working."

So a developer who reads the requirements page for requirements comes away with
a budget six times larger than the real one, and a suggestion to emit interim
messages that the stricter figure leaves no room for. We only found the 500 ms
because we read the quickstart after having already read the requirements.

Neither figure says what is being measured. Between the student finishing
speaking and Alexa beginning to reply there is ASR, Alexa's own reasoning, DNS,
TLS, the network hop, possibly a Lambda cold start, and finally the handler.
Which of those are inside the window?

We engineered far inside it — 8.9 ms median round trip, 3.6 ms median for
grading — precisely because we could not tell how much of the budget was ours to
spend. That worked out, but it is a consequence of this project's shape rather
than something the documentation enabled.

**Fix:** put the 500 ms figure on the functional requirements page, reconcile it
with the 3-second guidance or scope that guidance explicitly, and state what is
timed and from where to where. A developer who knows they own 400 ms builds
differently from one who assumes they own 50 — and differently again from one
who thinks they have three seconds.

---

### 5. The authentication page and the quickstart disagree about which well-known document to serve

The quickstart says to host "a Protected Resource Metadata document" at
`/.well-known/oauth-authorization-server`. Those are two different documents at
two different paths. Protected Resource Metadata is RFC 9728 and lives at
`/.well-known/oauth-protected-resource`; `/.well-known/oauth-authorization-server`
is RFC 8414 and describes the *authorization server*, which for most add-ons is
somebody else's deployment entirely. An implementer who follows the sentence
literally serves a document describing a server they do not run.

We serve the RFC 9728 document, which is ours to make claims in, and redirect the
RFC 8414 path to the configured issuer — and 404 it, with a reason, when no
issuer is configured.

**Fix:** name the document by its RFC and put it at that RFC's path. If the
intent really is that the add-on proxies the authorization server's metadata,
say so, because that is a surprising thing to ask for and nothing on the page
suggests it.

---

### 6. `WWW-Authenticate` on a 401 is unsupported, and the MCP spec asks for it

The toolkit documents that it does not support `WWW-Authenticate` headers on 401
responses. The MCP authorization spec's example 401 is a `WWW-Authenticate`
header, and it is listed first of the two discovery mechanisms a server may
implement.

There is no actual conflict — the spec says *one of* the two, and serving the
well-known document satisfies it — but working that out took a careful reading of
both documents, on the question of whether the platform was asking us to violate
the specification it names.

**Fix:** one clause. "Serve the well-known document instead; the specification
permits either." It converts a contradiction into a choice.

---

## MCP Python SDK 2.x

### 7. Tools registered after the server is constructed vanish without an error

`MCPServer(extensions=[...])` reads the extension **eagerly** in the
constructor. `@apps.tool` decorators that run afterwards therefore register into
an object the server has already copied from. The tools do not appear in
`tools/list`. There is no exception, no warning, and no log line.

The required order — register the UI resource, then the tools, then construct
the server — is not stated in the `Apps` docstring. It is implicit in
`_apply_extension`, which is private, so the answer is only reachable by reading
source you have no reason to open.

**Cost:** about an hour, most of it spent doubting the transport, because a
short `tools/list` looks like a protocol problem rather than an ordering one.

**Fix:** either capture extension tools lazily at first use, or raise when a tool
is added to an extension already bound to a server. This is the most expensive
item in this log and among the cheapest to fix. See item 13 — the SDK already
does exactly this, correctly, one code path over.

### 8. A tool annotated `-> dict` silently produces no output schema

Returning a plain `dict` from a tool yields no `outputSchema` and no structured
content. Nothing warns you. You discover it when the client receives text and
nothing else, and then have to work out that an explicit pydantic model is
required.

This is not documented where you need it — on the `@tool` decorator — and the
failure is silent in the same way as item 7.

**Fix:** warn at registration time when a tool's return annotation cannot produce
a schema, and say so on the decorator's own docstring.

### 9. camelCase to snake_case, repeatedly, across unrelated types

`serverInfo` → `server_info`, `protocolVersion` → `protocol_version`,
`structuredContent` → `structured_content`, and later `Resource.mimeType` →
`mime_type`.

The individual error messages are genuinely good — `Did you mean: 'mime_type'?`
is exactly right — but the pattern re-appears on each new type you touch, and
each appearance costs another edit-run cycle. Knowing the rule does not help,
because you cannot tell which types you have not yet hit.

**Fix:** a single table in the 2.x migration notes listing every renamed field,
not only the renamed classes. One page would have collapsed four separate
discoveries into one read.

### 10. `streamablehttp_client` → `streamable_http_client`, and the arity changed with it

The rename is discoverable from the error. The accompanying change — the
transport now yields a 2-tuple where it previously yielded 3 — is not: it
surfaces as an unpacking error about values, which says nothing about the
transport contract having changed.

**Fix:** mention the shape change alongside the rename in the migration notes.
A renamed symbol is a five-second fix; a silently re-shaped return value is not.

---

### 11. Sending a header means constructing a client

`streamable_http_client` takes no `headers` argument. To put an `Authorization`
header on a connection you construct an `httpx2.AsyncClient` with default
headers and pass it as `http_client`, then own its lifetime.

This is fine once you know it, but a bearer token is the single most common thing
anyone needs to add to an MCP connection — it is what the authorization spec
requires on every request — and the parameter that used to carry it is gone with
no note in the migration guide. The signature gives no hint: `http_client` reads
like an optimisation for connection pooling, not like the way you authenticate.

**Fix:** either keep a `headers` argument that forwards, or say in the migration
notes that headers now go through `http_client`. One line in the docstring would
have saved the search.

---

## MCP Apps extension (SEP-2133)

### 12. The additive model is right, and worth saying out loud

Binding `start_practice` and `submit_answer` to a `ui://` resource via
`_meta.ui.resourceUri` while leaving every tool's spoken text intact meant a
speaker with no display needed no special-casing anywhere in our code. The
degradation is structural rather than something we had to remember to maintain.

This deserves to be stated more prominently in the extension's own
documentation. It is the property that makes the extension safe to adopt for a
voice-first product, and it is currently something you infer rather than
something you are told.

---

## What worked well

### 13. The validation in item 7, done correctly, one path over

Binding a tool to a `ui://` resource that has not been registered raises an
explicit, solvable error naming the missing URI. It is precisely the behaviour
item 7 is missing, in adjacent code. The SDK already knows how to catch this
class of mistake; the extension-ordering path just doesn't.

### 14. Streamable HTTP and version negotiation worked first time

`2025-11-25` negotiated cleanly, and a single endpoint serving both POST and GET
behaved as specified. No friction to report, which is worth recording precisely
because it is the part most likely to have gone wrong.

### 15. Error messages are consistently helpful where they exist

Across items 8, 9 and 10, wherever the SDK raised at all, the message pointed
somewhere useful — the migration guide, the correct field name, the right
symbol. The gap in this SDK is not message quality. It is the two places where
it stays silent.

---

## If we could ask for one thing

A single reference page describing what a tool invocation delivers to the
server, and what the 500 ms budget covers. Items 3 and 4 are the only two
entries here that changed the shape of the product rather than costing us an
afternoon, and both are documentation gaps rather than defects.
