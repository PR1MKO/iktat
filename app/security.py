import secrets

from flask import g


def csp_nonce():
    if not hasattr(g, "csp_nonce"):
        g.csp_nonce = secrets.token_urlsafe(16)
    return g.csp_nonce


def csp_header(resp):
    nonce = getattr(g, "csp_nonce", "")
    policy = (
        "default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}' 'strict-dynamic'; "
        "style-src 'self'; img-src 'self' data:; connect-src 'self'; "
        "base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
        "upgrade-insecure-requests"
    )
    resp.headers["Content-Security-Policy"] = policy
    return resp
