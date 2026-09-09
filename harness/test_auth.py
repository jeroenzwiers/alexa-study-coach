"""The resource-server checks, against the running server and in isolation.

Every case here is a request Alexa+ or an attacker actually makes. The two that
matter most are the ones a green suite would never notice: a token signed by the
right issuer but issued for a *different* resource, and a token with a valid
signature whose scopes do not cover this endpoint. Both are accepted by a naive
`jwt.decode`, and both are the whole point of the audience section of the spec.
"""

from __future__ import annotations

import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

import jwt

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

import auth

BASE = "http://127.0.0.1:8421"
MCP = f"{BASE}/mcp"

# A minimal well-formed MCP request. What comes back does not matter here - only
# whether the request was let through at all.
INITIALIZE = json.dumps(
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "test_auth", "version": "0"},
        },
    }
).encode()


def call(token: str | None = None, origin: str | None = None, body: bytes = INITIALIZE):
    """POST to /mcp and return (status, parsed body, response headers)."""
    request = urllib.request.Request(MCP, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Accept", "application/json, text/event-stream")
    request.add_header("MCP-Protocol-Version", "2025-11-25")
    if token is not None:
        request.add_header("Authorization", f"Bearer {token}")
    if origin is not None:
        request.add_header("Origin", origin)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read(), response.headers
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw), exc.headers
        except ValueError:
            return exc.code, raw, exc.headers


def get(path: str):
    try:
        with urllib.request.urlopen(f"{BASE}{path}", timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read())
        except ValueError:
            return exc.code, None


def signed(**overrides) -> str:
    """A token the development issuer would have signed, with fields replaced."""
    now = int(time.time())
    claims = {
        "iss": auth.DEV_ISSUER,
        "sub": "test",
        "aud": auth.RESOURCE_URI,
        "scope": f"{auth.SCOPE_SERVICE} {auth.SCOPE_TOOLS}",
        "iat": now,
        "exp": now + 3600,
    }
    claims.update(overrides)
    return jwt.encode(claims, auth.DEV_SECRET, algorithm="HS256")


def main() -> int:
    checks: dict[str, bool] = {}

    # --- Refusals -----------------------------------------------------------

    status, body, headers = call(token=None)
    checks["geen token -> 401"] = status == 401
    checks["401 draagt een RFC 6749-foutbody"] = (
        isinstance(body, dict) and body.get("error") == "invalid_request"
    )
    # Alexa+ documents that it does not support this header; the MCP spec asks
    # for the header *or* a well-known document, and we serve the document.
    checks["401 draagt geen WWW-Authenticate"] = (
        headers.get("WWW-Authenticate") is None
    )

    status, *_ = call(token="not-a-jwt")
    checks["onzin-token -> 401"] = status == 401

    status, *_ = call(token=signed(exp=int(time.time()) - 60))
    checks["verlopen token -> 401"] = status == 401

    status, *_ = call(
        token=jwt.encode({"iss": auth.DEV_ISSUER}, "a-key-that-is-not-ours-x" * 2, algorithm="HS256")
    )
    checks["verkeerde sleutel -> 401"] = status == 401

    status, *_ = call(token=signed(iss="https://somewhere.else/"))
    checks["andere uitgever -> 401"] = status == 401

    # The one a naive implementation gets wrong: our issuer really did sign
    # this, for someone else's server.
    status, body, _ = call(token=signed(aud="https://another-mcp-server.example/mcp"))
    checks["token voor een andere resource -> 401"] = status == 401
    checks["... en zegt dat het om het publiek gaat"] = (
        isinstance(body, dict) and "not issued for" in body.get("error_description", "")
    )

    # Signature fine, issuer fine, audience fine - scopes wrong.
    status, body, _ = call(token=signed(scope="mcp:resources"))
    checks["te smalle scope -> 403"] = status == 403
    checks["... met insufficient_scope"] = (
        isinstance(body, dict) and body.get("error") == "insufficient_scope"
    )

    # --- Origin, the DNS-rebinding case -------------------------------------

    status, body, _ = call(token=signed(), origin="https://evil.example")
    checks["vreemde Origin -> 403"] = status == 403
    status, *_ = call(token=signed(), origin="http://localhost:8430")
    checks["Origin van de demo-shell mag door"] = status == 200

    # --- The path that must still work --------------------------------------

    status, *_ = call(token=signed())
    checks["geldig token -> 200"] = status == 200
    status, *_ = call(token=auth.mint_dev_token())
    checks["mint_dev_token komt langs de deur"] = status == 200

    # --- Discovery ----------------------------------------------------------

    status, doc = get("/.well-known/oauth-protected-resource")
    doc = doc if isinstance(doc, dict) else {}
    checks["protected-resource document bestaat"] = status == 200
    checks["... noemt onze resource"] = doc.get("resource") == auth.RESOURCE_URI
    checks["... noemt de scopes"] = auth.SCOPE_TOOLS in doc.get("scopes_supported", [])

    status, doc = get("/.well-known/oauth-authorization-server")
    doc = doc if isinstance(doc, dict) else {}
    if auth.DEV_MODE:
        # The point of the whole exercise: in development there is no
        # authorization server, so this must not describe one.
        checks["zonder issuer: geen AS-document verzonnen"] = status == 404
        checks["... en het zegt waarom"] = "MCP_AUTH_ISSUER" in doc.get(
            "error_description", ""
        )
        _, resource_doc = get("/.well-known/oauth-protected-resource")
        checks["... en authorization_servers blijft leeg"] = (
            isinstance(resource_doc, dict)
            and resource_doc.get("authorization_servers") == []
        )
    else:
        checks["met issuer: AS-document wijst door"] = status in (200, 307)

    # /healthz stays open - a load balancer has no token.
    status, _ = get("/healthz")
    checks["healthz blijft open"] = status == 200

    # --- Origin logic in isolation ------------------------------------------

    checks["allowlist leeg: loopback mag"] = auth.origin_allowed("http://127.0.0.1:8430")
    checks["allowlist leeg: vreemde origin mag niet"] = not auth.origin_allowed(
        "https://evil.example"
    )

    for label, ok in checks.items():
        print(f"  {'OK  ' if ok else 'FOUT'} {label}")
    failed = [k for k, v in checks.items() if not v]
    print(f"\n{len(checks) - len(failed)}/{len(checks)}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
