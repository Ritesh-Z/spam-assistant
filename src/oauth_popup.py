"""Google sign-in in a popup window, without leaving the app.

How it works (OAuth 2.0 for desktop apps, loopback redirect + PKCE):
  1. start() builds Google's sign-in URL whose redirect points at a tiny
     HTTP listener on 127.0.0.1:<free port>, started in a background thread.
  2. The page opens that URL in a popup (ui/assets/signin.js).
  3. After the user signs in, Google redirects the popup to the listener,
     which exchanges the code for a token, saves data/token.json and shows
     a "you can close this window" page that closes itself.
  4. Meanwhile the page polls the listener's /status endpoint; when it says
     "done" it closes the popup and tells Python to load the inbox.

Only one sign-in attempt runs at a time and it expires after 10 minutes.
"""
from __future__ import annotations

import json
import secrets
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .gmail_client import CREDENTIALS_PATH, SCOPES, TOKEN_PATH, GmailSetupError

TIMEOUT_S = 600

_DONE_PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>Signed in</title>
<style>body{margin:0;height:100vh;display:grid;place-items:center;background:#E9E9EB;
font:15px Inter,system-ui,sans-serif;color:#141416}div{text-align:center}
b{display:block;font-size:20px;margin-bottom:8px}span{color:#4A4A50}</style></head>
<body><div><b>%s</b><span>%s</span></div>
<script>setTimeout(function(){window.close()},900)</script></body></html>"""


def _later(seconds: float, fn) -> None:
    t = threading.Timer(seconds, fn)
    t.daemon = True        # never keeps the process alive on exit
    t.start()


class _Attempt:
    def __init__(self) -> None:
        from google_auth_oauthlib.flow import Flow

        if not CREDENTIALS_PATH.exists():
            raise GmailSetupError("credentials.json not found in the project root. "
                                  "Follow the Gmail setup steps in the README.")
        with socket.socket() as s:            # pick a free loopback port
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.redirect_uri = f"http://127.0.0.1:{self.port}/"
        self.flow = Flow.from_client_secrets_file(
            str(CREDENTIALS_PATH), SCOPES, redirect_uri=self.redirect_uri)
        self.state = secrets.token_urlsafe(24)
        self.auth_url, _ = self.flow.authorization_url(
            access_type="offline", prompt="select_account consent", state=self.state)
        self.status = "waiting"               # waiting | done | error
        self.error = ""
        self.created = time.time()
        self.server = ThreadingHTTPServer(("127.0.0.1", self.port), self._handler())
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        _later(TIMEOUT_S, self.close)

    @property
    def status_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/status"

    @property
    def expired(self) -> bool:
        return time.time() - self.created > TIMEOUT_S - 30

    def close(self) -> None:
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def _finish(self, query: dict) -> tuple[str, str]:
        if query.get("state", [""])[0] != self.state:
            return "Sign-in failed", "The response did not match this sign-in attempt."
        if "error" in query:
            self.status, self.error = "error", query["error"][0]
            return "Sign-in cancelled", "You can close this window and try again."
        try:
            self.flow.fetch_token(code=query["code"][0])
            TOKEN_PATH.parent.mkdir(exist_ok=True)
            TOKEN_PATH.write_text(self.flow.credentials.to_json())
            self.status = "done"
            return "Signed in", "You can close this window. Your inbox is loading."
        except Exception as e:  # network problems, reused code, ...
            self.status, self.error = "error", str(e)
            return "Sign-in failed", "You can close this window and try again."

    def _handler(self):
        attempt = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):     # keep the console quiet
                pass

            def _send(self, code: int, body: str, ctype: str) -> None:
                data = body.encode()
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                # the app page (another localhost port) polls /status
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                url = urlparse(self.path)
                if url.path == "/status":
                    self._send(200, json.dumps({"status": attempt.status, "error": attempt.error}),
                               "application/json")
                elif url.path == "/":
                    title, text = attempt._finish(parse_qs(url.query))
                    self._send(200, _DONE_PAGE % (title, text), "text/html; charset=utf-8")
                    if attempt.status == "done":
                        _later(5, attempt.close)
                else:
                    self._send(404, "not found", "text/plain")

        return Handler


_lock = threading.Lock()
_current: _Attempt | None = None


def start() -> dict:
    """Return {auth_url, status_url} for the current sign-in attempt (reused across reruns)."""
    global _current
    with _lock:
        if _current is None or _current.expired or _current.status != "waiting":
            if _current is not None:
                _current.close()
            _current = _Attempt()
        return {"auth_url": _current.auth_url, "status_url": _current.status_url}
