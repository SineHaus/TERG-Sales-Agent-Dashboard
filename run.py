"""Start the dashboard (and the Gmail watcher, once Gmail is connected).

    python run.py            → open http://localhost:5000
"""
import logging

import config
import db
import worker
from app import app, get_gmail, gmail_ready

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

if __name__ == "__main__":
    db.init()
    worker.start_background(get_gmail)
    if not gmail_ready():
        print("Gmail not connected yet: open the dashboard and click Connect Gmail.")
    print(f"Dashboard: http://localhost:{config.PORT}")
    app.run(host="127.0.0.1", port=config.PORT, debug=False)
