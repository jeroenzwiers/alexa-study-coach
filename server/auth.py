"""The OAuth 2.1 resource-server half of this MCP server.

Alexa+ will not talk to an add-on that accepts unauthenticated requests, and the
MCP specification version we implement (2025-11-25) puts this server in the role
of an OAuth 2.1 *resource server*: it validates access tokens and never issues
them. Issuing belongs to an authorization server - Cognito in deployment, and
nothing at all on a laptop.

There is deliberately no flag that switches authentication off. The version of
this file that this one replaces advertised an authorization server that did not
exist, and the lesson taken from that was not "advertise less" but "never let the
running server and the document disagree". So:

  - with MCP_AUTH_ISSUER set, this is a real resource server in front of a real
    authorization server, and the discovery documents point at it;
  - without it, the server runs in development mode against a signing secret
    that is a literal in this file. Anyone reading the repository can mint a
    token against such a server. It says so on every start, and it serves no
    authorization-server metadata, because in that mode there is no
    authorization server to describe.

Development mode is what keeps `python server/app.py` working out of the box,
and it is why the harness exercises the authenticated path rather than a bypass
around it.
"""

from __future__ import annotations

import contextlib
import json
import os
import time

import jwt

# --- Configuration ----------------------------------------------------------
#
# The resource URI is this server's own identity as an OAuth resource: the value
# a client puts in the `resource` parameter (RFC 8707) and the value we require
# to come back in the token. Getting this wrong in deployment is the difference
# between validating a token issued *for us* and accepting any token the issuer
# ever signed, so it is read from the environment and never guessed.

RESOURCE_URI = os.environ.get("MCP_RESOURCE_URI", "http://127.0.0.1:8421/mcp")
ISSUER = os.environ.get("MCP_AUTH_ISSUER", "").rstrip("/")
JWKS_URL = os.environ.get("MCP_AUTH_JWKS_URL", "")

DEV_ISSUER = "https://study-coach.invalid/dev"
DEV_SECRET = os.environ.get(
    "MCP_DEV_SECRET",
    # Public on purpose. A secret in a public repository is not a secret, and
    # pretending otherwise is how a development mode ends up in production.
    "development-only-secret-do-not-deploy",
)

DEV_MODE = not ISSUER

# Alexa+ defines these three. `mcp:service` is what a client_credentials grant
# gets; the other two come from an authorization_code grant on behalf of a user.
SCOPE_SERVICE = "mcp:service"
SCOPE_TOOLS = "mcp:tools"
SCOPE_RESOURCES = "mcp:resources"
SCOPES_SUPPORTED = [SCOPE_SERVICE, SCOPE_TOOLS, SCOPE_RESOURCES]

# Reaching the MCP endpoint at all takes one of these. Finer-grained checks per
# tool are not done here and LIMITATIONS.md says so: a token that can ask a
# question can also read `student_progress`.
SCOPES_REQUIRED = {SCOPE_SERVICE, SCOPE_TOOLS}

_ALLOWED_ORIGINS = tuple(
    o.strip().rstrip("/")
    for o in os.environ.get("MCP_ALLOWED_ORIGINS", "").split(",")
    if o.strip()
)

# A browser page on another origin must not be able to drive the tools of a
# server bound to a loopback address - that is the DNS-rebinding case the MCP
# transport section asks servers to close. A request with no Origin header at
# all is not a browser and is left alone.
_LOOPBACK_ORIGINS = (
    "http://localhost",
    "http://127.0.0.1",
    "https://localhost",
    "https://127.0.0.1",
)


class AuthError(Exception):
    """An OAuth 2.0 error, in the shape RFC 6749 section 5.2 asks for."""

    def __init__(self, status: int, error: str, description: str) -> None:
        super().__init__(f"{error}: {description}")
        self.status = status
        self.error = error
        self.description = description

    def body(self) -> bytes:
        return json.dumps(
            {"error": self.error, "error_description": self.description}
        ).encode("utf-8")


def origin_allowed(origin: str) -> bool:
    origin = origin.rstrip("/")
    if origin in _ALLOWED_ORIGINS:
        return True
    if _ALLOWED_ORIGINS:
        # An explicit allowlist is exactly that. Loopback is only waved through
        # when nobody has said which origins are expected.
        return False
    return any(
        origin == o or origin.startswith(o + ":") for o in _LOOPBACK_ORIGINS
    )


# --- Token validation -------------------------------------------------------

_jwk_client = None


def _signing_key(token: str):
    """The key to verify with, and the algorithms it may have been signed by."""
    global _jwk_client
    if DEV_MODE:
        return DEV_SECRET, ["HS256"]
    if not JWKS_URL:
        raise AuthError(
            500,
            "server_error",
            "MCP_AUTH_ISSUER is set but MCP_AUTH_JWKS_URL is not, so no token "
            "can be verified.",
        )
    if _jwk_client is None:
        # PyJWKClient caches the key set and refetches on an unknown kid, which
        # is what a rotating issuer like Cognito needs.
        _jwk_client = jwt.PyJWKClient(JWKS_URL, cache_keys=True)
    try:
        return _jwk_client.get_signing_key_from_jwt(token).key, ["RS256", "ES256"]
    except Exception as exc:  # network, unknown kid, malformed header
        raise AuthError(401, "invalid_token", f"Signing key unavailable: {exc}")


def _audience_ok(claims: dict) -> bool:
    """Was this token issued for us?

    RFC 8707 puts the answer in `aud`. Cognito's client-credentials tokens carry
    the same fact in `client_id`/`resource` depending on how the resource server
    is registered, so both shapes are accepted - but one of them must be there.
    Accepting a token merely because our issuer signed it is the audience
    confusion the spec spends a whole section on.
    """
    aud = claims.get("aud")
    if isinstance(aud, str) and aud == RESOURCE_URI:
        return True
    if isinstance(aud, (list, tuple)) and RESOURCE_URI in aud:
        return True
    return claims.get("resource") == RESOURCE_URI


def _scopes(claims: dict) -> set[str]:
    raw = claims.get("scope") or claims.get("scp") or ""
    if isinstance(raw, str):
        return set(raw.split())
    return set(raw)


def validate(token: str) -> dict:
    """Return the claims of a token that may be used against this server."""
    key, algorithms = _signing_key(token)
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            issuer=DEV_ISSUER if DEV_MODE else ISSUER,
            # Checked below, because two claim shapes carry the answer.
            options={"verify_aud": False, "require": ["exp", "iss"]},
        )
    except jwt.ExpiredSignatureError:
        raise AuthError(401, "invalid_token", "The access token has expired.")
    except jwt.InvalidIssuerError:
        raise AuthError(401, "invalid_token", "The token was issued elsewhere.")
    except jwt.InvalidTokenError as exc:
        raise AuthError(401, "invalid_token", f"The access token is not valid: {exc}")

    if not _audience_ok(claims):
        raise AuthError(
            401,
            "invalid_token",
            f"The token was not issued for {RESOURCE_URI}.",
        )

    granted = _scopes(claims)
    if not (granted & SCOPES_REQUIRED):
        raise AuthError(
            403,
            "insufficient_scope",
            f"This endpoint needs one of {' or '.join(sorted(SCOPES_REQUIRED))}.",
        )
    return claims


def token_from_header(value: str) -> str:
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise AuthError(
            401, "invalid_request", "Expected an `Authorization: Bearer` header."
        )
    return token.strip()


def mint_dev_token(
    scopes: str = f"{SCOPE_SERVICE} {SCOPE_TOOLS} {SCOPE_RESOURCES}",
    lifetime: int = 3600,
    subject: str = "harness",
    audience: str | None = None,
) -> str:
    """A token the development issuer would have issued, had it existed.

    Only meaningful against a server in development mode - the harness and the
    demo use it so that every scripted run goes through the same check a real
    request does.
    """
    now = int(time.time())
    return jwt.encode(
        {
            "iss": DEV_ISSUER,
            "sub": subject,
            "aud": audience or RESOURCE_URI,
            "scope": scopes,
            "iat": now,
            "exp": now + lifetime,
        },
        DEV_SECRET,
        algorithm="HS256",
    )


# --- Discovery documents ----------------------------------------------------


def protected_resource_metadata() -> dict:
    """RFC 9728. This one is ours to serve and is true in both modes."""
    return {
        "resource": RESOURCE_URI,
        "authorization_servers": [ISSUER] if ISSUER else [],
        "scopes_supported": SCOPES_SUPPORTED,
        "bearer_methods_supported": ["header"],
    }


def authorization_server_metadata_url() -> str | None:
    """Where the *authorization server's* own metadata lives, if there is one.

    The Alexa+ quickstart tells clients to look for this document on the add-on
    server. It describes an authorization server, so serving a copy of it from
    here would be this file claiming to be something it is not. In deployment we
    redirect to the issuer that really publishes it; in development there is no
    authorization server, so the path 404s and says why.
    """
    if not ISSUER:
        return None
    return f"{ISSUER}/.well-known/oauth-authorization-server"


# --- ASGI middleware --------------------------------------------------------


class AuthMiddleware:
    """Bearer validation and Origin validation in front of the MCP endpoint.

    Written against the raw ASGI interface rather than Starlette's
    BaseHTTPMiddleware, which buffers the response body and would sit in the
    way of a streaming transport.
    """

    def __init__(self, app, protected: tuple[str, ...] = ("/mcp",)) -> None:
        self.app = app
        self.protected = protected

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not any(path == p or path.startswith(p + "/") for p in self.protected):
            await self.app(scope, receive, send)
            return

        headers = {
            k.decode("latin-1").lower(): v.decode("latin-1")
            for k, v in scope.get("headers", [])
        }

        origin = headers.get("origin")
        if origin is not None and not origin_allowed(origin):
            await _refuse(
                send,
                AuthError(403, "invalid_request", f"Origin {origin} is not allowed."),
            )
            return

        try:
            claims = validate(token_from_header(headers.get("authorization", "")))
        except AuthError as exc:
            await _refuse(send, exc)
            return

        # Available to anything downstream that wants to know who is asking.
        scope.setdefault("state", {})["auth"] = claims
        await self.app(scope, receive, send)


async def _refuse(send, error: AuthError) -> None:
    body = error.body()
    # No WWW-Authenticate header: the Alexa+ toolkit documents that it does not
    # support one, and the MCP spec asks for either that header or a well-known
    # discovery document. We serve the document, so omitting the header stays
    # within both.
    await send(
        {
            "type": "http.response.start",
            "status": error.status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                (b"cache-control", b"no-store"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


def startup_banner() -> str:
    if DEV_MODE:
        return (
            "WARNING: authentication is running against the development secret "
            "published in server/auth.py. Anyone who can read this repository "
            "can mint a token for this server. Set MCP_AUTH_ISSUER and "
            "MCP_AUTH_JWKS_URL before exposing it to a network."
        )
    return f"Authenticating against {ISSUER} for resource {RESOURCE_URI}."


def client():
    """An HTTP client that carries a token, for anything driving this server.

    The harness, the smoke client and the demo shell all need one. In
    development it mints its own; against a deployed server, export
    MCP_ACCESS_TOKEN and the same code paths run unchanged.
    """
    import httpx2

    token = os.environ.get("MCP_ACCESS_TOKEN") or mint_dev_token()
    return httpx2.AsyncClient(headers={"Authorization": f"Bearer {token}"})


@contextlib.asynccontextmanager
async def connect(url: str):
    """Open an authenticated MCP transport to `url`.

    The 2.x transport takes an http_client rather than headers, so a bearer
    token means constructing and closing one of these around every connection.
    Doing it in one place keeps the three scripted drivers honest: they go
    through the same check Alexa+ will.
    """
    from mcp.client.streamable_http import streamable_http_client

    async with client() as http:
        async with streamable_http_client(url, http_client=http) as streams:
            yield streams
