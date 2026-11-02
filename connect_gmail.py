"""One-time setup: sign in to Gmail in your browser and save token.json."""
from gmail_client import Gmail, get_service

svc = get_service(interactive=True)
print(f"Connected to Gmail as {Gmail(svc).me}. You can now run:  python run.py")
