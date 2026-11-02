"""Polls Gmail, keeps the database in sync, and has the agent draft replies."""
import logging
import threading
import time

import agent
import config
import db

log = logging.getLogger("worker")

CLOSED = {"quoted", "won", "lost"}


def sync_thread(gmail, thread_id):
    msgs = gmail.get_thread(thread_id)
    inbound = [m for m in msgs if m["direction"] == "inbound"]
    if not inbound:
        return None  # a thread you started; not an inquiry

    lead = db.get_lead_by_thread(thread_id)
    if lead is None:
        first = inbound[0]
        lead_id = db.create_lead(thread_id, first["reply_to"], first["sender_name"], first["subject"])
        lead = db.get_lead(lead_id)

    new_inbound = False
    for m in msgs:
        sender = f'{m["sender_name"]} <{m["sender"]}>' if m["sender_name"] else m["sender"]
        if db.add_message(lead["id"], m["gmail_id"], m["direction"], sender, m["sent_at"], m["body"]):
            new_inbound |= m["direction"] == "inbound"

    last = msgs[-1]

    # You replied (sent our draft or wrote your own): the draft is used up.
    if last["direction"] == "outbound":
        if lead["draft_id"] and not gmail.draft_exists(lead["draft_id"]):
            db.update_lead(lead["id"], draft_id=None, draft_body=None)
        return lead["id"]

    if last["gmail_id"] == lead["last_processed_msg_id"] or lead["status"] == "ignored" and not new_inbound:
        return lead["id"]

    if lead["status"] in CLOSED:
        # Customer wrote back after the quote went out: that's yours to handle in Goodshuffle.
        db.update_lead(lead["id"], status="needs_you", last_processed_msg_id=last["gmail_id"],
                       summary=(lead["summary"] or "") + " — Customer replied after the quote.")
        return lead["id"]

    draft_reply(gmail, lead["id"], msgs)
    return lead["id"]


def draft_reply(gmail, lead_id, msgs=None):
    """Run the agent on a lead and put its reply in Gmail Drafts."""
    lead = db.get_lead(lead_id)
    if msgs is None:
        msgs = gmail.get_thread(lead["thread_id"])
    history = db.get_messages(lead_id)

    current = dict(lead["fields"])
    current["email"] = current.get("email") or lead["customer_email"]
    current["client_name"] = current.get("client_name") or lead["customer_name"] or None

    try:
        out = agent.run(history, current, lead["owner_notes"])
    except agent.AgentError as e:
        log.error("Lead %s: %s", lead_id, e)
        db.update_lead(lead_id, status="needs_you", summary=f"Agent error: {e}")
        return

    last = msgs[-1]
    upd = dict(fields=out["fields"], missing=out["missing"], last_processed_msg_id=last["gmail_id"])

    if not out["is_inquiry"]:
        db.update_lead(lead_id, status="ignored", summary=out["summary"], **upd)
        return

    status = out["status"]
    summary = out["summary"]
    if status == "needs_you" and out.get("needs_you_reason"):
        summary = f"⚠ {out['needs_you_reason']} — {summary}"

    if lead["draft_id"]:
        gmail.delete_draft(lead["draft_id"])  # replace a stale, unsent draft
    draft_id = None
    if out["reply"]:
        draft_id = gmail.create_draft(lead["thread_id"], lead["customer_email"], lead["subject"] or "",
                                      out["reply"], last)

    db.update_lead(lead_id, status=status, summary=summary, draft_id=draft_id, draft_body=out["reply"],
                   **upd)
    log.info("Lead %s → %s (draft %s)", lead_id, status, draft_id)


def poll_once(gmail):
    for tid in gmail.search_thread_ids(config.GMAIL_QUERY):
        try:
            sync_thread(gmail, tid)
        except Exception:
            log.exception("Failed on thread %s", tid)


def start_background(gmail_factory):
    """Run the poller in a daemon thread next to the dashboard."""
    def loop():
        gmail = None
        while True:
            try:
                gmail = gmail or gmail_factory()
                poll_once(gmail)
            except Exception:
                log.exception("Poll failed")
                gmail = None
            time.sleep(config.POLL_SECONDS)

    t = threading.Thread(target=loop, daemon=True, name="gmail-poller")
    t.start()
    return t
