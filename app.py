"""Dashboard: every inquiry, its conversation, the collected info, and the draft reply."""
import functools
import hmac
import logging
import uuid
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

import agent
import config
import db
import worker
from fields import FIELD_GROUPS, LABELS, missing_required

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
if config.ON_SERVER:
    if not config.DASHBOARD_PASSWORD:
        raise SystemExit("Set DASHBOARD_PASSWORD before running on a server: the dashboard shows customer data.")
    app.config.update(SESSION_COOKIE_SECURE=True, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                      PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 30)
log = logging.getLogger("app")

_gmail = None


def gmail_ready():
    return Path(config.GMAIL_TOKEN).exists()


def get_gmail():
    global _gmail
    if _gmail is None:
        from gmail_client import Gmail
        _gmail = Gmail()
    return _gmail


class OfflineGmail:
    """Stand-in used for test leads made on the Try It page: nothing touches your real inbox."""
    def get_thread(self, thread_id):
        lead = db.get_lead_by_thread(thread_id)
        return [{"gmail_id": m["gmail_id"], "direction": m["direction"]} for m in db.get_messages(lead["id"])]

    def create_draft(self, *a, **k): return None
    def delete_draft(self, *a, **k): pass


def gmail_for(lead):
    return OfflineGmail() if lead["thread_id"].startswith("test-") else get_gmail()


@app.context_processor
def globals_():
    return dict(STATUSES=db.STATUSES, LABELS=LABELS, gmail_connected=gmail_ready(),
                business=config.BUSINESS_NAME)


def login_required(view):
    @functools.wraps(view)
    def wrapped(*a, **k):
        if config.DASHBOARD_PASSWORD and not session.get("ok"):
            return redirect(url_for("login", next=request.path))
        return view(*a, **k)
    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST" and hmac.compare_digest(
            request.form.get("password", "").encode(), config.DASHBOARD_PASSWORD.encode()):
        session.permanent = True
        session["ok"] = True
        nxt = request.args.get("next", "")
        return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("index"))
    return render_template("login.html")


@app.get("/healthz")
def healthz():
    return "ok"


@app.route("/")
@login_required
def index():
    status = request.args.get("status") or None
    q = (request.args.get("q") or "").lower().strip()
    leads = db.list_leads(status)
    if not status:
        leads = [l for l in leads if l["status"] != "ignored"]
    if q:
        leads = [l for l in leads if q in " ".join(
            [l["customer_name"] or "", l["customer_email"] or "", l["subject"] or "", l["summary"] or "",
             *[v or "" for v in l["fields"].values()]]).lower()]
    return render_template("index.html", leads=leads, counts=db.status_counts(), status=status, q=q)


@app.route("/lead/<int:lead_id>")
@login_required
def lead_view(lead_id):
    lead = db.get_lead(lead_id) or abort(404)
    return render_template("lead.html", lead=lead, messages=db.get_messages(lead_id), groups=FIELD_GROUPS,
                           sheet=agent.goodshuffle_sheet(lead["fields"]),
                           is_test=lead["thread_id"].startswith("test-"),
                           missing_labels=[LABELS[k].split(" (")[0] for k in lead["missing"] if k in LABELS])


@app.post("/lead/<int:lead_id>/fields")
@login_required
def save_fields(lead_id):
    lead = db.get_lead(lead_id) or abort(404)
    fields = dict(lead["fields"])
    for _, items in FIELD_GROUPS:
        for key, _, _ in items:
            fields[key] = request.form.get(key, "").strip() or None
    missing = missing_required(fields)
    upd = dict(fields=fields, missing=missing, owner_notes=request.form.get("owner_notes", ""))
    if lead["status"] == "collecting" and not missing:
        upd["status"] = "ready_to_quote"
    db.update_lead(lead_id, **upd)
    flash("Saved.")
    return redirect(url_for("lead_view", lead_id=lead_id))


@app.post("/lead/<int:lead_id>/status")
@login_required
def set_status(lead_id):
    st = request.form["status"]
    if st not in db.STATUSES:
        abort(400)
    db.update_lead(lead_id, status=st)
    return redirect(request.referrer or url_for("lead_view", lead_id=lead_id))


@app.post("/lead/<int:lead_id>/draft")
@login_required
def save_draft(lead_id):
    lead = db.get_lead(lead_id) or abort(404)
    body = request.form.get("draft_body", "").strip()
    action = request.form.get("action")
    is_test = lead["thread_id"].startswith("test-")

    if is_test:
        if action == "send" and body:
            db.add_message(lead_id, f"test-{uuid.uuid4()}", "outbound", config.OWNER_NAME, db.now(), body)
            db.update_lead(lead_id, draft_body=None)
            flash("Test reply recorded (nothing was emailed).")
        else:
            db.update_lead(lead_id, draft_body=body)
            flash("Draft saved.")
        return redirect(url_for("lead_view", lead_id=lead_id))

    g = get_gmail()
    msgs = g.get_thread(lead["thread_id"])
    last_in = [m for m in msgs if m["direction"] == "inbound"][-1]
    if lead["draft_id"] and g.draft_exists(lead["draft_id"]):
        g.update_draft(lead["draft_id"], lead["thread_id"], lead["customer_email"], lead["subject"] or "", body, last_in)
        draft_id = lead["draft_id"]
    else:
        draft_id = g.create_draft(lead["thread_id"], lead["customer_email"], lead["subject"] or "", body, last_in)

    if action == "send":
        g.send_draft(draft_id)
        db.update_lead(lead_id, draft_id=None, draft_body=None)
        worker.sync_thread(g, lead["thread_id"])
        flash(f"Reply sent to {lead['customer_email']}.")
    else:
        db.update_lead(lead_id, draft_id=draft_id, draft_body=body)
        flash("Draft updated in Gmail.")
    return redirect(url_for("lead_view", lead_id=lead_id))


@app.post("/lead/<int:lead_id>/regenerate")
@login_required
def regenerate(lead_id):
    lead = db.get_lead(lead_id) or abort(404)
    db.update_lead(lead_id, owner_notes=request.form.get("owner_notes", lead["owner_notes"]))
    worker.draft_reply(gmail_for(lead), lead_id)
    flash("The agent re-read the thread and wrote a new draft.")
    return redirect(url_for("lead_view", lead_id=lead_id))


# ---------- Try it without Gmail ----------
@app.route("/try", methods=["GET", "POST"])
@login_required
def try_it():
    if request.method == "POST":
        name = request.form.get("name", "").strip() or "Test Customer"
        email = request.form.get("email", "").strip() or "test@example.com"
        body = request.form["body"].strip()
        lead_id = db.create_lead(f"test-{uuid.uuid4()}", email, name,
                                 request.form.get("subject", "").strip() or "Rental inquiry")
        db.add_message(lead_id, f"test-{uuid.uuid4()}", "inbound", f"{name} <{email}>", db.now(), body)
        worker.draft_reply(OfflineGmail(), lead_id)
        return redirect(url_for("lead_view", lead_id=lead_id))
    return render_template("try.html")


@app.post("/lead/<int:lead_id>/simulate-reply")
@login_required
def simulate_reply(lead_id):
    lead = db.get_lead(lead_id) or abort(404)
    if not lead["thread_id"].startswith("test-"):
        abort(400)
    db.add_message(lead_id, f"test-{uuid.uuid4()}", "inbound", lead["customer_email"], db.now(),
                   request.form["body"].strip())
    worker.draft_reply(OfflineGmail(), lead_id)
    return redirect(url_for("lead_view", lead_id=lead_id))


@app.post("/poll")
@login_required
def poll_now():
    worker.poll_once(get_gmail())
    flash("Checked Gmail for new inquiries.")
    return redirect(url_for("index"))


@app.template_filter("when")
def when(ts):
    if not ts:
        return ""
    from datetime import datetime
    try:
        d = datetime.fromisoformat(ts).astimezone()
        return d.strftime("%b %d, %I:%M %p").replace(" 0", " ")
    except ValueError:
        return ts
