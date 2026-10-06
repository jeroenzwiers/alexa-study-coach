A new MIT-licensed repository, created inside the hackathon window:
https://github.com/jeroenzwiers/alexa-study-coach, 59 commits between
2 September and 6 October 2026.

**What it is.** A self-hosted MCP server on spec 2025-11-25 over Streamable HTTP
that revises with a student by voice and, when they are wrong, names the concept
they reached for instead of the right one.

**How it works.** Grading is nearest-neighbour attribution over the closed set of
answers in a study set, not a similarity threshold. We measured that no threshold
can work: a correct answer distorted by speech recognition scores lower than a
genuinely wrong one that happens to be spelled alike. Knowing *which* wrong
answer was given is what lets the server name a confusion, deliberately schedule
the mirrored question, and close the pair when both sides come back right.

**Why it matters as open source.** Everything a reader would need in order to
disbelieve us is in the repository. LIMITATIONS.md documents where the grader
does worse than its own test file reports, and why the fix is content-side rather
than a threshold. FRICTION.md is fifteen logged problems with the tools, written
down as they cost us something. The harness reproduces every figure in the
README. Three parts are reusable on their own: the OAuth 2.1 resource server, the
study-set verifier that checks generated content with the live grader, and the
audio-splitting tool that groups speech by expected length instead of
thresholding the pauses.
