"""Settings, read from the .env file next to this script."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE = Path(__file__).parent
load_dotenv(BASE / ".env")

# Where the database and Gmail sign-in are kept. On a server, point this at a persistent disk.
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE)))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "sales_agent.db"))

# --- Your business (used in the agent's replies) ---
BUSINESS_NAME = os.getenv("BUSINESS_NAME", "Our Rental Company")
OWNER_NAME = os.getenv("OWNER_NAME", "The Team")
SERVICE_AREA = os.getenv("SERVICE_AREA", "")
# Anything else the agent should know: minimums, delivery fees policy, lead times, etc.
BUSINESS_NOTES = os.getenv("BUSINESS_NOTES", "")

# --- Gmail ---
GMAIL_CREDENTIALS = os.getenv("GMAIL_CREDENTIALS", str(BASE / "credentials.json"))
GMAIL_TOKEN = os.getenv("GMAIL_TOKEN", str(DATA_DIR / "token.json"))

# On a server there's no browser to sign in with, so paste the contents of the token.json
# made by connect_gmail.py into this variable. It's copied to disk on first start and
# refreshed there automatically after that.
_token_json = os.getenv("GMAIL_TOKEN_JSON", "").strip()
if _token_json and not Path(GMAIL_TOKEN).exists():
    Path(GMAIL_TOKEN).write_text(_token_json)
# Google OAuth client for the "Connect Gmail" button. Set these, or paste them on the
# dashboard's Gmail setup page (saved to DATA_DIR/google_client.json).
GOOGLE_CLIENT_FILE = DATA_DIR / "google_client.json"
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# Which emails count as possible inquiries. Gmail search syntax.
GMAIL_QUERY = os.getenv("GMAIL_QUERY", "in:inbox newer_than:3d -category:promotions -category:social -category:updates")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "120"))

# --- Claude ---
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
CLAUDE_EFFORT = os.getenv("CLAUDE_EFFORT", "medium")

# --- Dashboard ---
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
SECRET_KEY = os.getenv("SECRET_KEY") or DASHBOARD_PASSWORD or "local-only"
# True when running on a host (Render sets RENDER=true). Then a password is mandatory.
ON_SERVER = bool(os.getenv("RENDER") or os.getenv("ON_SERVER"))
PORT = int(os.getenv("PORT", "5000"))
