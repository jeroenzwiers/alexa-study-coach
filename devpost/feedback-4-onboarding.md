The honest summary: zero to hello world was a day for the server, and never for
the add-on.

MCP Python SDK 2.x and Streamable HTTP - good. A server answering on the
2025-11-25 specification, with version negotiation and a single endpoint serving
both POST and GET, was running the same day we started. Nothing in that path
surprised us, which is worth saying because it is the part most likely to have
gone wrong. The friction we did hit came afterwards, during the 1.x to 2.x
migration, and the error messages pointed somewhere useful every time.

Alexa+ MCP Toolkit, the documentation - good enough to build against. The
requirements are stated plainly: Streamable HTTP, a latency budget, 401 on
unauthenticated requests, Origin validation, the session header. We could work
from them directly. What is missing is not instruction but description: what a
tool call delivers, and what the latency figure measures.

Alexa+ MCP Toolkit, the CLI - we never reached hello world. The first command in
the setup guide installs a package that is not on public npm. It lives in a
private AWS CodeArtifact repository reachable only through an IAM role we could
not be granted, and nothing earlier in the guide says who can get that role.
From a standing start, the documented path produced an authentication failure
rather than a running add-on, and no amount of care on our side would have
changed that.

What saved the project was reading the submission rules rather than the setup
guide: a deployed add-on is not required, so we built the server the track
specifies and demonstrated it against a presentation shell driving the real
thing. A developer who follows the quickstart in order, though, concludes the
platform is closed to them - and stops. One sentence at the top of that page
about who can obtain the CLI, and what can be built without it, would change
that experience completely.

MCP Apps extension (SEP-2133) - straightforward to adopt. The additive model
meant we could add a card without restructuring anything, and the SDK raises a
clear error if a tool is bound to a ui:// resource that has not been registered.
The gap is at the other end: no way to see what a real device does with it.

Everything else - pydantic, uvicorn, jellyfish, PyJWT - was ordinary. Installed,
read the documentation once, worked.
