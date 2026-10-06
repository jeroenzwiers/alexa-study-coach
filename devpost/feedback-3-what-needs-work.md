Alexa+ MCP Toolkit - documentation, two gaps that changed the product rather
than costing us an afternoon.

Nothing states what a tool invocation actually delivers to the server. We
designed a feature around reading the student's tone of voice before
establishing that no audio, prosody or affect reaches a server at all. The
feature survived only because we could redesign it around observable behaviour
reported by Alexa+ instead. Workaround: read the contract off the SDK's types
and assume nothing beyond them. Severity: high.

Two different latency figures live on two different pages, and neither says what
the measurement covers - server processing, the full round trip, or the whole
turn including speech. We budgeted against the strictest reading. Severity:
medium.

Alexa+ MCP Toolkit - the CLI is not where the documentation implies it is. It is
not on public npm; it lives in a private AWS CodeArtifact repository behind an
IAM role we could not be granted, and nothing says so before the first command
fails. There is no workaround. We continued only because the submission rules do
not require a deployed add-on. Severity: critical for anyone whose goal is a
deployed add-on.

Alexa+ MCP Toolkit - the CodeArtifact token expires after twelve hours and the
failure then looks like a broken package rather than an expired credential.
Workaround: re-run the login command whenever an install starts failing for no
reason. Severity: low, but it costs the same twenty minutes every time.

Alexa+ MCP Toolkit - the authentication page and the quickstart disagree about
which well-known document is the Protected Resource Metadata one. The quickstart
names /.well-known/oauth-authorization-server; RFC 9728 puts it at
/.well-known/oauth-protected-resource. Workaround: serve both, correctly.
Severity: low, but only because we read the specification and the quickstart
against each other.

MCP Python SDK 2.x - WWW-Authenticate on a 401 is unsupported, and the MCP
authorization specification asks for it. Without the header, a client has to
know in advance where to authenticate, which defeats the purpose of the metadata
documents the same specification requires. No workaround available to us.
Severity: medium.

MCP Python SDK 2.x - tools registered after the server is constructed vanish
with no error. They are simply absent from the list. The SDK performs exactly
this class of validation one path over, where binding a tool to an unregistered
ui:// resource raises an explicit error naming the missing URI. Workaround:
register everything before construction. Severity: medium, entirely because of
the silence.

MCP Python SDK 2.x - a tool annotated to return dict silently produces no output
schema. Workaround: annotate a concrete model. Severity: low, same cause -
silence rather than an error.

MCP Python SDK 2.x - the 1.x to 2.x migration renames things across unrelated
types, repeatedly camelCase to snake_case, and streamablehttp_client became
streamable_http_client with a changed arity. The error messages were helpful
every time, which is the only reason this is a nuisance rather than an
afternoon. Severity: low.

MCP Python SDK 2.x - sending a single header means constructing a client. A
one-header request is more ceremony than it should be. Severity: low.

MCP Apps extension (SEP-2133) - the thing we most wanted to know is not written
down anywhere we could find: what a real Alexa+ device does with a card it does
not recognise. We designed defensively, making the card strictly additive so
that a device which ignores it loses only the picture. That is the right design
anyway, but we chose it without being able to check. Severity: medium, and it
will matter more as more clients implement the extension.
