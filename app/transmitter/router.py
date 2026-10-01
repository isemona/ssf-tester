import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings
from app.db import log_event
from app.keys import jwks, sign_set

router = APIRouter(prefix="/transmitter", tags=["transmitter"])

# Hosted at the issuer's root, not under /transmitter: SSF discovery assumes
# a transmitter's config lives at {iss}/.well-known/ssf-configuration.
wellknown_router = APIRouter(tags=["transmitter"])


class SendEventRequest(BaseModel):
    event_type: str
    subject: str
    target_url: str | None = None
    audience: str | None = None
    extra_event_claims: dict = {}


@wellknown_router.get("/.well-known/ssf-configuration")
def ssf_configuration():
    return {
        "issuer": settings.base_url,
        "jwks_uri": f"{settings.base_url}/transmitter/jwks.json",
        "delivery_methods_supported": ["urn:ietf:rfc:8935"],
        "spec_version": "1_0-ID2",
    }


@router.get("/jwks.json")
def transmitter_jwks():
    return jwks()


@router.post("/send")
def send_event(req: SendEventRequest):
    jti = str(uuid.uuid4())
    payload = {
        "iss": settings.base_url,
        "jti": jti,
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "aud": req.audience or settings.transmitter_audience,
        "events": {
            req.event_type: {
                "subject": {"format": "email", "email": req.subject},
                **req.extra_event_claims,
            }
        },
    }
    signed = sign_set(payload)
    target_url = req.target_url or settings.resolved_transmitter_target_url

    try:
        response = httpx.post(
            target_url,
            content=signed,
            headers={"Content-Type": "application/secevent+jwt"},
            timeout=10.0,
        )
        status = f"http_{response.status_code}"
        detail = response.text
        ok = response.is_success
    except httpx.HTTPError as exc:
        status = "request_failed"
        detail = str(exc)
        ok = False

    log_event(
        direction="sent",
        issuer=settings.base_url,
        jti=jti,
        event_type=req.event_type,
        subject=req.subject,
        raw_jwt=signed,
        verified=None,
        status=status,
        detail=detail,
    )

    return {
        "jti": jti,
        "target_url": target_url,
        "status": status,
        "ok": ok,
        "response_body": detail,
        "signed_set": signed,
    }
