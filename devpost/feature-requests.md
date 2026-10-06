1. A reference page for what a tool invocation delivers, and what the 500 ms
budget covers. CRITICAL.

Nothing we could find states what arrives at the server when Alexa+ calls a
tool, or which part of the round trip the 500 ms figure measures. Why it matters
to us: these are the only two gaps that changed the shape of our product rather
than costing us an afternoon. We designed a feature around hearing the student's
tone of voice before establishing that no audio, prosody or affect reaches the
server at all, and we budgeted against a latency figure whose boundaries we had
to infer. Both are documentation gaps, not defects, which is why one page fixes
them. (Friction items 3 and 4.)

2. A documented way to obtain the alexa-ai CLI, or a statement that it is not
needed. CRITICAL.

The CLI is not on public npm. It lives in a private AWS CodeArtifact repository
behind an IAM role we could not be granted, and nothing says so before the first
command fails. Why it matters: a developer who reads the quickstart in order
concludes the platform is closed to them. We only continued because the
submission rules turned out not to require a deployed add-on. One sentence at
the top of the setup page - who can get this, and what you can build without it
- would have saved the afternoon and, for some people, the project. (Items 1
and 2.)

3. Support WWW-Authenticate on a 401. IMPORTANT.

The MCP authorization specification asks a resource server to return the header
on an unauthenticated request so the client can discover where to authenticate.
We could not set it. Why it matters: without it, discovery depends on the client
already knowing where to look, which defeats the purpose of the metadata
documents the same specification requires. (Item 6.)

4. Raise when a tool is registered after the server is constructed. IMPORTANT.

Tools registered too late vanish with no error at all - they simply are not in
the list. Why it matters: silence turns a one-line ordering mistake into a
debugging session. The SDK already does exactly this validation one path over,
where binding a tool to an unregistered ui:// resource raises an explicit error
naming the missing URI. (Items 7 and 13.)

5. Agree with the MCP specification on which well-known document is the
Protected Resource Metadata one. NICE-TO-HAVE.

The quickstart calls /.well-known/oauth-authorization-server a Protected
Resource Metadata document; RFC 9728 puts that at
/.well-known/oauth-protected-resource. Why it matters: we serve both, correctly,
which costs little - but we only knew to do that because we read the
specification and the quickstart against each other. (Item 5.)
