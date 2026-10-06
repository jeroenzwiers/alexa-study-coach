Yes.

The reason is specific rather than polite. Building an add-on as an MCP server
meant we spent our time on the thing that is actually hard - deciding, from a
mangled spoken answer, which concept the student reached for - and almost none
on conversation management, speech, or turn-taking. Alexa+ supplies those, and
supplies them better than we would have. The division of labour is the right one
and it is what let a project this size have a real idea in it at all.

Three things we would keep: the specification negotiated first time and never
bothered us again; the 500 ms budget is a demanding constraint that made the
product better, because it forced the grading decision out of a language model
and into deterministic code we can measure and explain; and the additive model
in the Apps extension let us design one product for devices with and without a
screen instead of two.

One qualification, and it is the whole of our reservation. We would build with
the specification again tomorrow. We cannot say we would build an add-on again,
because we never managed to deploy one - the CLI is behind an AWS role we could
not obtain, and we only discovered that after following the setup guide in
order. Everything we know about this platform, we know from the documentation
and the specification, not from watching it run on a device. Fix the first
command of the quickstart and the answer loses its asterisk.
