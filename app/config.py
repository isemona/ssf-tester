import os

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _codespaces_base_url() -> str | None:
    """Derive the forwarded HTTPS URL for port 8000 from Codespaces' own
    env vars, so BASE_URL doesn't need to be hand-set after making the port public."""
    name = os.environ.get("CODESPACE_NAME")
    domain = os.environ.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN")
    if name and domain:
        return f"https://{name}-8000.{domain}"
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Public base URL of this app once exposed (e.g. via Codespaces port forwarding).
    # Used as the `iss` claim when this app acts as transmitter, and to build its jwks_uri.
    base_url: str = "http://localhost:8000"

    @model_validator(mode="after")
    def _default_base_url_from_codespaces(self):
        # Only kick in when nothing explicitly set base_url (still at its
        # hardcoded default) - an explicit .env/env var value always wins.
        if self.base_url == "http://localhost:8000":
            derived = _codespaces_base_url()
            if derived:
                self.base_url = derived
        return self

    # Okta org this tool talks to.
    okta_org_url: str = "https://your-org.okta.com"

    # Where the transmitter POSTs signed SETs. Defaults to Okta's SSF receiver endpoint.
    transmitter_target_url: str = ""

    # `aud` claim to put on outbound SETs. Okta expects this to match what you registered
    # for the transmitter in the Okta admin console.
    transmitter_audience: str = ""

    # This app's own receiver identity - used as the expected `aud` on inbound SETs.
    receiver_audience: str = ""

    db_path: str = "data/events.db"
    private_key_path: str = "app/keys/transmitter_rsa.pem"
    key_id: str = "ssf-tester-key-1"

    @property
    def resolved_transmitter_target_url(self) -> str:
        return self.transmitter_target_url or f"{self.okta_org_url}/security/api/v1/security-events"


settings = Settings()
