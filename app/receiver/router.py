import json
import urllib.request

import jwt
from fastapi import APIRouter, Request, Response
from jwt import PyJWKClient
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.db import log_event

router = APIRouter(prefix="/receiver", tags=["receiver"])


def _discover_jwks_uri(issuer: str) -> str:
    """Per the SSF spec, a receiver discovers the transmitter's jwks_uri via
    its well-known configuration rather than assuming a fixed JWKS path."""
    with urllib.request.urlopen(f"{issuer}/.well-known/ssf-configuration", timeout=5) as resp:
        config = json.load(resp)
    return config["jwks_uri"]


def _verify(raw_jwt: str, issuer: str | None) -> tuple[bool, str, str | None]:
    """Blocking JWKS discovery/fetch + signature verification - run off the event loop."""
    try:
        jwks_uri = _discover_jwks_uri(issuer)
    except Exception:
        jwks_uri = f"{issuer}/.well-known/jwks.json"

    try:
        jwks_client = PyJWKClient(jwks_uri)
        signing_key = jwks_client.get_signing_key_from_jwt(raw_jwt)
        jwt.decode(
            raw_jwt,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.receiver_audience or None,
            options={"verify_aud": bool(settings.receiver_audience)},
        )
        return True, "verified", None
    except jwt.PyJWTError as exc:
        return False, "verification_failed", str(exc)


@router.post("/events")
async def receive_event(request: Request):
    raw_jwt = (await request.body()).decode("utf-8").strip()

    try:
        unverified = jwt.decode(raw_jwt, options={"verify_signature": False})
        issuer = unverified.get("iss")
        jti = unverified.get("jti")
        events = unverified.get("events", {})
        event_type = next(iter(events), None)
    except jwt.DecodeError as exc:
        log_event(
            direction="received",
            issuer=None,
            jti=None,
            event_type=None,
            subject=None,
            raw_jwt=raw_jwt,
            verified=False,
            status="malformed",
            detail=str(exc),
        )
        return Response(status_code=400, content=f"malformed SET: {exc}")

    subject = None
    if event_type:
        subject = events.get(event_type, {}).get("subject", {}).get("email")

    verified, status, detail = await run_in_threadpool(_verify, raw_jwt, issuer)

    log_event(
        direction="received",
        issuer=issuer,
        jti=jti,
        event_type=event_type,
        subject=subject,
        raw_jwt=raw_jwt,
        verified=verified,
        status=status,
        detail=detail,
    )

    if not verified:
        return Response(status_code=401, content=f"verification failed: {detail}")

    return Response(status_code=202)
