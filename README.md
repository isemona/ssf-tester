# ssf-tester

Internal testing tool for Okta's Shared Signals Framework (SSF). Acts as
**both** a transmitter (pushes signed Security Event Tokens to Okta) and a
receiver (exposes an endpoint for Okta to push SETs to), so you can validate
an org's SSF configuration in both directions from one app.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp env.sample .env   # fill in BASE_URL / OKTA_ORG_URL once you know them
uvicorn app.main:app --reload
```

On first run it generates an RSA keypair at `app/keys/transmitter_rsa.pem`
(gitignored) and a SQLite log at `data/events.db` (gitignored).

## Running in Codespaces

This isn't a single-command start — `BASE_URL` isn't known until after the
port is public, so the first boot needs a restart once you have it:

1. Open this repo in a Codespace (devcontainer installs deps automatically).
2. `cp env.sample .env`
3. `uvicorn app.main:app --host 0.0.0.0 --reload`
4. In the Ports tab, make port 8000 public and copy the forwarded HTTPS URL.
5. Set `BASE_URL` in `.env` to that URL, then restart uvicorn so the
   transmitter's `iss`/`jwks_uri` reflect the public URL.

## Registering with Okta

- **This app as transmitter:** give Okta admin the JWKS at
  `{BASE_URL}/transmitter/jwks.json` so Okta can verify SETs you send to
  Okta's receiver endpoint (`{OKTA_ORG_URL}/security/api/v1/security-events`,
  used by default — override with `TRANSMITTER_TARGET_URL`).
- **This app as receiver:** register `{BASE_URL}/receiver/events` in Okta's
  SSF stream configuration as the push delivery endpoint.

## Endpoints

- `POST /transmitter/send` — build, sign, and push a SET.
  Body: `{"event_type": "...", "subject": "user@example.com"}`
- `GET /transmitter/jwks.json` — this app's public signing key.
- `POST /receiver/events` — push delivery endpoint Okta calls; verifies the
  SET against the issuer's JWKS and logs it.
- `GET /events` — recent send/receive history from SQLite.

## Notes

- Receiver verification discovers the issuer's JWKS via
  `{iss}/.well-known/ssf-configuration` (falling back to
  `{iss}/.well-known/jwks.json` if discovery fails) — confirm Okta exposes
  that config at your org's issuer URL before relying on it.
- `TRANSMITTER_AUDIENCE` / `RECEIVER_AUDIENCE` should match whatever
  audience value Okta expects/sends for your org's SSF registration.
- No auth gate on `/transmitter/send`, `/receiver/events`, or `/events` yet
  — fine for sandbox testing with a public Codespaces port, but add one
  (e.g. a shared-secret header) before pointing this at anything beyond a
  sandbox.
