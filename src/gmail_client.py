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
import re
import time
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
    """Sign out: revoke the token at Google (best effort) and delete it locally."""
    if TOKEN_PATH.exists():
        try:
            import json
            import urllib.parse
            import urllib.request
            tok = json.loads(TOKEN_PATH.read_text())
            token = tok.get("refresh_token") or tok.get("token")
            if token:
                req = urllib.request.Request(
                    "https://oauth2.googleapis.com/revoke",
                    data=urllib.parse.urlencode({"token": token}).encode(),
                    headers={"Content-Type": "application/x-www-form-urlencoded"})
                urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass  # offline or already revoked: deleting the local token still signs out
    TOKEN_PATH.unlink(missing_ok=True)


def account_email() -> str:
    """The signed-in Gmail address (gmail.readonly allows reading the profile)."""
    return _service().users().getProfile(userId="me").execute().get("emailAddress", "")


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


BATCH_SIZE = 50  # 50 gets = 250 quota units, Gmail's per-user limit per second


def _get_messages(svc, ids: list[str], retries: int = 3) -> dict:
    """Fetch full messages in batched HTTP requests (one round trip per 50).

    Requests hit by rate limiting are retried after a pause.
    """
    out: dict = {}
    pending = list(ids)
    for attempt in range(retries + 1):
        failed: list[str] = []

        def on_done(request_id, response, exception):
            if exception is None:
                out[request_id] = response
            else:
                failed.append(request_id)

        for i in range(0, len(pending), BATCH_SIZE):
            batch = svc.new_batch_http_request(callback=on_done)
            for mid in pending[i:i + BATCH_SIZE]:
                batch.add(svc.users().messages().get(userId="me", id=mid, format="full"),
                          request_id=mid)
            batch.execute()
            if i + BATCH_SIZE < len(pending):
                time.sleep(1.0)
        if not failed:
            break
        pending = failed
        time.sleep(2.0 * (attempt + 1))
    return out


def verified_domain(payload_headers: list[dict], sender: str) -> str | None:
    """The sender's domain if Gmail verified it (DMARC pass), else None.

    Only Gmail's own Authentication-Results header (added by mx.google.com) is
    trusted; a sender can insert fake ones further down.
    """
    from .rules import sender_parts
    _, domain = sender_parts(sender)
    if not domain:
        return None
    for h in payload_headers:
        if h.get("name", "").lower() != "authentication-results":
            continue
        value = h.get("value", "").strip().lower()
        if not value.startswith("mx.google.com"):
            continue
        m = re.search(r"dmarc=pass[^;]*header\.from=([\w.-]+)", value)
        return domain if m and m.group(1) == domain else None
    return None


def fetch_latest(n: int = 50, label_ids: list[str] | None = None,
                 query: str | None = None) -> list[dict]:
    """Fetch the latest n emails (paged, so n may exceed 500).

    Returns dicts: id, sender, subject, date, body, labels, mail_kind,
    verified_domain. mail_kind is "promotions" (Gmail's Promotions tab),
    "list" (other mail with a List-Unsubscribe header) or None.
    Emails are returned in memory only and never written to disk.
    """
    svc = _service()
    label_ids = label_ids or ["INBOX"]
    refs, page_token = [], None
    while len(refs) < n:
        resp = svc.users().messages().list(
            userId="me", maxResults=min(500, n - len(refs)), labelIds=label_ids,
            q=query, pageToken=page_token,
            includeSpamTrash="SPAM" in label_ids).execute()
        refs.extend(resp.get("messages", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    msgs = _get_messages(svc, [r["id"] for r in refs])
    emails = []
    for ref in refs:
        msg = msgs.get(ref["id"])
        if msg is None:  # failed even after retries; skip rather than crash
            continue
        headers = {h["name"].lower(): h["value"]
                   for h in msg.get("payload", {}).get("headers", [])}
        body = _extract_body(msg.get("payload", {})) or msg.get("snippet", "")
        emails.append({
            "id": ref["id"],
            "sender": headers.get("from", "(unknown sender)"),
            "subject": headers.get("subject", "(no subject)"),
            "date": headers.get("date", ""),
            "body": body,
            "labels": msg.get("labelIds", []),
            # promotions = Gmail's Promotions tab; list = other automated mail:
            # a List-Unsubscribe header or Gmail's Updates / Social / Forums tab
            "mail_kind": ("promotions" if "CATEGORY_PROMOTIONS" in msg.get("labelIds", [])
                          else "list" if ("list-unsubscribe" in headers or any(
                              t in msg.get("labelIds", []) for t in
                              ("CATEGORY_UPDATES", "CATEGORY_SOCIAL", "CATEGORY_FORUMS")))
                          else None),
            "verified_domain": verified_domain(msg.get("payload", {}).get("headers", []),
                                               headers.get("from", "")),
        })
    return emails
