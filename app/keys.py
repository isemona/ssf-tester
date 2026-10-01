import json
import os

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from app.config import settings


def _generate_and_save_key(path: str) -> rsa.RSAPrivateKey:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(pem)
    return key


def load_or_create_private_key() -> rsa.RSAPrivateKey:
    path = settings.private_key_path
    if os.path.exists(path):
        with open(path, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)
    return _generate_and_save_key(path)


PRIVATE_KEY = load_or_create_private_key()
_ALGO = RSAAlgorithm(RSAAlgorithm.SHA256)


def public_jwk() -> dict:
    jwk = json.loads(_ALGO.to_jwk(PRIVATE_KEY.public_key()))
    jwk["kid"] = settings.key_id
    jwk["use"] = "sig"
    jwk["alg"] = "RS256"
    return jwk


def jwks() -> dict:
    return {"keys": [public_jwk()]}


def sign_set(payload: dict) -> str:
    return jwt.encode(
        payload,
        PRIVATE_KEY,
        algorithm="RS256",
        headers={"typ": "secevent+jwt", "kid": settings.key_id},
    )
