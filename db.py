"""SQLite storage for leads (one per email thread) and their messages."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id     TEXT UNIQUE NOT NULL,
    customer_email TEXT,
    customer_name TEXT,
    subject       TEXT,
    status        TEXT NOT NULL DEFAULT 'new',
    fields        TEXT NOT NULL DEFAULT '{}',
    missing       TEXT NOT NULL DEFAULT '[]',
    summary       TEXT DEFAULT '',
    owner_notes   TEXT DEFAULT '',
    draft_id      TEXT,
    draft_body    TEXT,
    last_processed_msg_id TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id     INTEGER NOT NULL REFERENCES leads(id),
    gmail_id    TEXT UNIQUE NOT NULL,
    direction   TEXT NOT NULL,          -- 'inbound' (customer) or 'outbound' (you)
    sender      TEXT,
    sent_at     TEXT,
    body        TEXT
);
"""

# Lead statuses shown in the dashboard
STATUSES = {
    "new": "New",
    "collecting": "Collecting info",
    "ready_to_quote": "Ready to quote",
    "needs_you": "Needs you",
    "quoted": "Quote sent",
    "won": "Booked",
    "lost": "Lost",
    "ignored": "Not an inquiry",
}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init():
    with connect() as c:
        c.executescript(SCHEMA)


def _lead(row):
    if row is None:
        return None
    d = dict(row)
    d["fields"] = json.loads(d["fields"] or "{}")
    d["missing"] = json.loads(d["missing"] or "[]")
    return d


def get_lead(lead_id):
    with connect() as c:
        return _lead(c.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone())


def get_lead_by_thread(thread_id):
    with connect() as c:
        return _lead(c.execute("SELECT * FROM leads WHERE thread_id=?", (thread_id,)).fetchone())


def list_leads(status=None):
    q = "SELECT * FROM leads"
    args = ()
    if status:
        q += " WHERE status=?"
        args = (status,)
    q += " ORDER BY updated_at DESC"
    with connect() as c:
        return [_lead(r) for r in c.execute(q, args).fetchall()]


def status_counts():
    with connect() as c:
        return {r["status"]: r["n"] for r in c.execute("SELECT status, COUNT(*) n FROM leads GROUP BY status")}


def create_lead(thread_id, customer_email, customer_name, subject):
    ts = now()
    with connect() as c:
        cur = c.execute(
            "INSERT INTO leads (thread_id, customer_email, customer_name, subject, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?)",
            (thread_id, customer_email, customer_name, subject, ts, ts),
        )
        return cur.lastrowid


def update_lead(lead_id, **kw):
    if not kw:
        return
    for k in ("fields", "missing"):
        if k in kw and not isinstance(kw[k], str):
            kw[k] = json.dumps(kw[k])
    kw["updated_at"] = now()
    cols = ", ".join(f"{k}=?" for k in kw)
    with connect() as c:
        c.execute(f"UPDATE leads SET {cols} WHERE id=?", (*kw.values(), lead_id))


def add_message(lead_id, gmail_id, direction, sender, sent_at, body):
    """Insert a message; returns True if it was new."""
    with connect() as c:
        cur = c.execute(
            "INSERT OR IGNORE INTO messages (lead_id, gmail_id, direction, sender, sent_at, body)"
            " VALUES (?,?,?,?,?,?)",
            (lead_id, gmail_id, direction, sender, sent_at, body),
        )
        return cur.rowcount == 1


def get_messages(lead_id):
    with connect() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM messages WHERE lead_id=? ORDER BY sent_at, id", (lead_id,)).fetchall()]
