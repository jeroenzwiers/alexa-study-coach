MCP specification 2025-11-25 and Streamable HTTP - worked first time. Version
negotiation was clean and a single endpoint serving both POST and GET behaved
exactly as specified. We are recording this precisely because it is the part
most likely to have gone wrong, and it cost us nothing. (Friction item 14.)

MCP Python SDK 2.x - error messages are consistently helpful wherever the SDK
raises at all. Across three separate mistakes of ours it pointed somewhere
useful: the migration guide, the correct field name, the right symbol. The gap
in this SDK is not message quality; it is the two places where it stays silent
instead. (Item 15.)

MCP Python SDK, UI resource binding - binding a tool to a ui:// resource that
has not been registered raises an explicit, solvable error naming the missing
URI. That is exactly the validation we wanted one path over, and the SDK already
knows how to do it. (Item 13.)

MCP Apps extension (SEP-2133) - the additive model is right, and worth saying
out loud. A card is an addition to spoken text, never a replacement for it, so a
speaker with no display loses only the picture. That single decision is what let
us design one product for both kinds of device instead of two. (Item 12.)

Alexa+ MCP Toolkit, the authentication requirements - demanding a real OAuth 2.1
resource server rather than a shared secret pushed us to build bearer
validation, audience and scope checks and Origin validation properly, early,
when it was still cheap. The requirement was stricter than we would have been
with ourselves.

pydantic, uvicorn and jellyfish - no friction to report. Each did what it says
and never appeared in our log.

Setup time, measured honestly: everything above was running within a day. Every
item in our friction log concerns documentation or silence, not defects - which
is itself the summary judgement on these tools.
