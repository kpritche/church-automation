from __future__ import annotations

import pickle
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from church_automation_shared.paths import ANNOUNCEMENTS_CREDENTIALS_PATH, ANNOUNCEMENTS_TOKEN_PATH

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _load_creds_from_cache(token_path: Path) -> Optional[object]:
    if token_path.exists():
        with open(token_path, "rb") as token:
            return pickle.load(token)
    return None


def authenticate_gmail():
    """Authenticate with Gmail API, caching refreshed tokens under announcements/."""
    creds = _load_creds_from_cache(ANNOUNCEMENTS_TOKEN_PATH)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not ANNOUNCEMENTS_CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"Gmail credentials file missing at {ANNOUNCEMENTS_CREDENTIALS_PATH}."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(ANNOUNCEMENTS_CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)

        ANNOUNCEMENTS_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ANNOUNCEMENTS_TOKEN_PATH, "wb") as token:
            pickle.dump(creds, token)

    return build("gmail", "v1", credentials=creds)


def fetch_latest_announcement_html(service, query: str) -> str:
    results = service.users().messages().list(userId="me", q=query).execute()
    msg_id = results["messages"][0]["id"]
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    parts = msg["payload"].get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/html":
            data = part.get("body", {}).get("data")
            if data:
                return (  # defer import to avoid top-level dependency for tests
                    __import__("base64").urlsafe_b64decode(data).decode()
                )
    return ""
