"""Thin wrapper around the Gmail API: read threads, create/update/send draft replies."""
import base64
import html
import re
from email.mime.text import MIMEText
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config

# Read mail, create drafts, and send drafts you approve.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def get_service(interactive=False):
    creds = None
    if Path(config.GMAIL_TOKEN).exists():
        creds = Credentials.from_authorized_user_file(config.GMAIL_TOKEN, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not interactive:
            raise RuntimeError("Gmail isn't connected yet. Run:  python connect_gmail.py")
        flow = InstalledAppFlow.from_client_secrets_file(config.GMAIL_CREDENTIALS, SCOPES)
        creds = flow.run_local_server(port=0, open_browser=True)
    Path(config.GMAIL_TOKEN).write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


class Gmail:
    def __init__(self, service=None):
        self.svc = service or get_service()
        self.me = self.svc.users().getProfile(userId="me").execute()["emailAddress"].lower()

    # ---------- reading ----------
    def search_thread_ids(self, query, limit=50):
        res = self.svc.users().threads().list(userId="me", q=query, maxResults=limit).execute()
        return [t["id"] for t in res.get("threads", [])]

    def get_thread(self, thread_id):
        t = self.svc.users().threads().get(userId="me", id=thread_id, format="full").execute()
        return [self._parse(m) for m in t.get("messages", []) if "DRAFT" not in m.get("labelIds", [])]

    def _parse(self, m):
        headers = {h["name"].lower(): h["value"] for h in m["payload"].get("headers", [])}
        name, addr = parseaddr(headers.get("from", ""))
        outbound = "SENT" in m.get("labelIds", []) or addr.lower() == self.me
        try:
            sent_at = parsedate_to_datetime(headers["date"]).isoformat()
        except Exception:
            sent_at = None
        return {
            "gmail_id": m["id"],
            "direction": "outbound" if outbound else "inbound",
            "sender_name": name,
            "sender": addr.lower(),
            "reply_to": parseaddr(headers.get("reply-to", ""))[1].lower() or addr.lower(),
            "subject": headers.get("subject", ""),
            "message_id": headers.get("message-id", ""),
            "references": headers.get("references", ""),
            "sent_at": sent_at,
            "body": strip_quoted(extract_body(m["payload"])),
        }

    # ---------- drafts ----------
    def _raw_reply(self, to, subject, body, last_msg):
        msg = MIMEText(body, "plain", "utf-8")
        msg["To"] = to
        msg["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
        if last_msg.get("message_id"):
            msg["In-Reply-To"] = last_msg["message_id"]
            msg["References"] = (last_msg.get("references", "") + " " + last_msg["message_id"]).strip()
        return base64.urlsafe_b64encode(msg.as_bytes()).decode()

    def create_draft(self, thread_id, to, subject, body, last_msg):
        raw = self._raw_reply(to, subject, body, last_msg)
        d = self.svc.users().drafts().create(
            userId="me", body={"message": {"raw": raw, "threadId": thread_id}}).execute()
        return d["id"]

    def update_draft(self, draft_id, thread_id, to, subject, body, last_msg):
        raw = self._raw_reply(to, subject, body, last_msg)
        self.svc.users().drafts().update(
            userId="me", id=draft_id, body={"message": {"raw": raw, "threadId": thread_id}}).execute()

    def delete_draft(self, draft_id):
        try:
            self.svc.users().drafts().delete(userId="me", id=draft_id).execute()
        except HttpError as e:
            if e.resp.status != 404:
                raise

    def draft_exists(self, draft_id):
        try:
            self.svc.users().drafts().get(userId="me", id=draft_id, format="minimal").execute()
            return True
        except HttpError as e:
            if e.resp.status == 404:
                return False
            raise

    def send_draft(self, draft_id):
        return self.svc.users().drafts().send(userId="me", body={"id": draft_id}).execute()


# ---------- body helpers ----------
def _decode(data):
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", errors="replace")


def extract_body(payload):
    plain, htm = [], []

    def walk(p):
        mime = p.get("mimeType", "")
        data = p.get("body", {}).get("data")
        if data and mime == "text/plain":
            plain.append(_decode(data))
        elif data and mime == "text/html":
            htm.append(_decode(data))
        for sub in p.get("parts", []) or []:
            walk(sub)

    walk(payload)
    if plain:
        return "\n".join(plain)
    if htm:
        text = re.sub(r"(?is)<(script|style).*?</\1>", "", "\n".join(htm))
        text = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        return html.unescape(text)
    return ""


_QUOTE_MARKERS = [
    re.compile(r"^On .{5,200}wrote:\s*$", re.M | re.S),
    re.compile(r"^-{2,}\s*Original Message\s*-{2,}", re.M | re.I),
    re.compile(r"^From: .+\nSent: ", re.M),
]


def strip_quoted(text):
    """Drop the quoted history Gmail/Outlook append to replies (we store each message separately)."""
    cut = len(text)
    for rx in _QUOTE_MARKERS:
        m = rx.search(text)
        if m:
            cut = min(cut, m.start())
    lines = [ln for ln in text[:cut].splitlines() if not ln.startswith(">")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
