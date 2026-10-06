Alexa+ MCP Toolkit (documentation, quickstart, authentication pages) - the
contract we built against: transport, latency budget, authentication and the
shape of a tool invocation.

MCP specification 2025-11-25 - the protocol itself. Streamable HTTP, one
endpoint serving POST and GET, session identifiers and version negotiation.

MCP Python SDK 2.x (mcp==2.1.1) - the server: transport, tool registration,
session handling, discovery documents.

MCP Apps extension, SEP-2133 (io.modelcontextprotocol/ui) - the card shown on
devices with a display. Two of our eight tools are bound to a ui:// resource and
carry _meta.ui.resourceUri; the other six have no UI at all.

PyJWT with cryptography - bearer token validation in our OAuth 2.1 resource
server: signature, audience and scope checks.

uvicorn - the ASGI server underneath.

pydantic - tool argument models and validation.

jellyfish - phonetic keys inside the grader, alongside our own content-word and
letter comparison.

Claude (claude-opus-5) - offline only, never in the request path. It turns a
worksheet into a study set built around the confusions, and nothing it produces
is trusted until our own verifier re-checks it with the live grader.

puppeteer-core with headless Chrome - driving the presentation shell to record
the demo video deterministically rather than with a screen recorder.

ffmpeg - cutting a long speech render into per-line clips, and laying those
clips back against the recorded frames at the millisecond each one played.

ElevenLabs - pre-rendering the 33 spoken lines of the demo.

AWS CodeArtifact and the alexa-ai CLI - attempted, never obtained. The CLI is
not on public npm; it lives in a private CodeArtifact repository behind an IAM
role we could not be granted. See friction items 1 and 2.
