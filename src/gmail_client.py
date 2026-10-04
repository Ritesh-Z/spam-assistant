"""Read only Gmail access.

Uses the gmail.readonly scope, so the app can never send, change or delete mail.
The sign-in token is stored locally in data/token.json and removed on disconnect.

Setup (one time, see README):
  1. Create a Google Cloud project and enable the Gmail API.
  2. Configure the OAuth consent screen (External, add yourself as a test user).
  3. Create an OAuth client ID of type "Desktop app".
  4. Download it as credentials.json into the project root.
"""
from __future__ import annotations

import base64
from pathlib import Path

from .preprocess import strip_html

ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_PATH = ROOT / "credentials.json"   # keep out of git
TOKEN_PATH = ROOT / "data" / "token.json"      # keep out of git
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailSetupError(RuntimeError):
    pass


def is_connected() -> bool:
    return TOKEN_PATH.exists()


def _get_credentials(interactive: bool = True):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not interactive:
            raise GmailSetupError("Not connected to Gmail.")
        if not CREDENTIALS_PATH.exists():
            raise GmailSetupError(
                "credentials.json not found in the project root. "
                "Follow the Gmail setup steps in the README.")
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
        creds = flow.run_local_server(port=0)  # opens Google's own sign-in page
    TOKEN_PATH.parent.mkdir(exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())
    return creds


def connect() -> None:
    """Run the Google sign-in flow and store the token."""
    _get_credentials(interactive=True)


def disconnect() -> None:
    TOKEN_PATH.unlink(missing_ok=True)


def _service():
    from googleapiclient.discovery import build
    return build("gmail", "v1", credentials=_get_credentials(interactive=False),
                 cache_discovery=False)


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode()).decode("utf-8", errors="replace")


def _extract_body(payload: dict) -> str:
    """Prefer text/plain; fall back to text/html with tags removed."""
    plain, html = [], []

    def walk(part: dict) -> None:
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        if data and mime == "text/plain":
            plain.append(_decode(data))
        elif data and mime == "text/html":
            html.append(_decode(data))
        for sub in part.get("parts", []) or []:
            walk(sub)

    walk(payload)
    if plain:
        return "\n".join(plain)
    if html:
        return strip_html("\n".join(html))
    return ""


def fetch_latest(n: int = 50, label_ids: list[str] | None = None) -> list[dict]:
    """Fetch the latest n emails. Returns dicts: id, sender, subject, date, body.

    Emails are returned in memory only and never written to disk.
    """
    svc = _service()
    resp = svc.users().messages().list(
        userId="me", maxResults=n, labelIds=label_ids or ["INBOX"]).execute()
    emails = []
    for ref in resp.get("messages", []):
        msg = svc.users().messages().get(userId="me", id=ref["id"], format="full").execute()
        headers = {h["name"].lower(): h["value"]
                   for h in msg.get("payload", {}).get("headers", [])}
        body = _extract_body(msg.get("payload", {})) or msg.get("snippet", "")
        emails.append({
            "id": ref["id"],
            "sender": headers.get("from", "(unknown sender)"),
            "subject": headers.get("subject", "(no subject)"),
            "date": headers.get("date", ""),
            "body": body,
        })
    return emails
