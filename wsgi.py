"""Entry point for hosting (Render, Railway, etc.). Run with ONE gunicorn worker:

    gunicorn wsgi:app --workers 1 --threads 4

One worker matters: the Gmail watcher runs inside it, and more workers would each poll Gmail.
"""
import logging

import db
import worker
from app import app, get_gmail, gmail_ready

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
db.init()
worker.start_background(get_gmail)
if not gmail_ready():
    logging.warning("Gmail not connected yet: open the dashboard and click Connect Gmail.")
