# planning_center_api.py
"""
Thin wrapper around the Planning Center Services API (JSON-API spec).
Handles authentication via Personal Access Token (PAT) and provides
helpers to fetch a plan by date and pull out song lyrics attachments.

Prerequisites
-------------
export PCO_TOKEN="your_personal_access_token"

pip install requests
"""

import os
import sys
import requests
from pathlib import Path
from urllib.parse import urlencode
from datetime import datetime
import json

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared import config

BASE_URL = "https://api.planningcenteronline.com/services/v2"


class PlanningCenterClient:
    def __init__(self,
                 app_id: str | None = None,
                 secret: str | None = None,
                 timeout: int = 15):
        """
        Authenticate via Basic Auth using your PAT’s Application ID and Secret.

        Expects either:
          - app_id & secret passed in here, _or_
          - PCO_APP_ID & PCO_SECRET set in your environment.
        """
        self.app_id = config.client_id or os.getenv("PCO_APP_ID")
        self.secret = config.secret or os.getenv("PCO_SECRET")
        if not (self.app_id and self.secret):
            raise RuntimeError(
                "You must set PCO_APP_ID and PCO_SECRET env vars (or pass them in)."
            )
        self.session = requests.Session()
        # Basic Auth: username=Application ID, password=Secret
        self.session.auth = (self.app_id, self.secret)
        self.timeout = timeout

    def _get(self, path: str, params: dict | None = None) -> dict:
        """Low-level GET against the Services API."""
        url = f"{BASE_URL}{path}"
        if params:
            url += "?" + urlencode(params)
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def get_plan(self, service_type_id: int, plan_id: int, expand: bool = True) -> dict:
        """
        Fetch the full JSON for a single plan.
        If expand=True, includes items, notes, attachments, and song arrangements in one request.
        """
        params = {}
        if expand:
            params["include"] = "items,item_notes,item_attachments,items.arrangement"
        return self._get(f"/service_types/{service_type_id}/plans/{plan_id}", params)

    def find_plan_by_date(self, service_type_id: int, target_date: str) -> tuple[int, dict]:
        """
        List plans for a service_type and return the one matching target_date (YYYY-MM-DD).
        Returns (plan_id, plan_meta_dict) or raises ValueError if not found.
        """
        resp = self._get(f"/service_types/{service_type_id}/plans", {'filter':'future'})
        for plan in resp["data"]:
            # sort_date is ISO8601, e.g. "2025-07-20T14:00:00Z"
            iso = plan["attributes"]["sort_date"].replace("Z", "+00:00")
            plan_date = datetime.fromisoformat(iso).date().isoformat() 
            if plan_date == target_date:
                return int(plan["id"]), plan
        raise ValueError(f"No plan on {target_date} for service_type {service_type_id}")

    def get_item_lyrics(self, arrangement_id: int) -> str | None:
        """
        Fetch plain-text lyrics for a given arrangement_id, if a .txt or .lyrics
        attachment is present. Otherwise returns None.
        """
        resp = self._get(f"/arrangements/{arrangement_id}/attachments")
        for att in resp["data"]:
            fn = att["attributes"]["filename"].lower()
            if fn.endswith((".txt", ".lyrics")):
                download_url = att["attributes"]["download_url"]
                return self.session.get(download_url, timeout=self.timeout).text
        return None
    

    def upload_item_attachment(
        self,
        service_type_id: int,
        plan_id: int,
        item_id: int,
        file_path: str,
        content_type: str = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    ) -> dict:
        """
        POST the file at `file_path` as a new attachment on the given item.
        Adheres to JSON:API spec; uses lowercase 'attachments' resource type.
        """
        url = (
            f"{BASE_URL}/service_types/{service_type_id}"
            f"/plans/{plan_id}/items/{item_id}/attachments"
        )
        filename = os.path.basename(file_path)

        # JSON:API metadata describing the attachment (lowercase type)
        metadata = {
            "data": {
                "type": "attachments",
                "attributes": {
                    "filename": filename,
                    "content_type": content_type
                }
            }
        }

        with open(file_path, "rb") as fp:
            files = {
                "file": (filename, fp, content_type),
                # 'data' form-field with JSON metadata
                "data": (None, json.dumps(metadata), "application/json")
            }
            resp = self.session.post(url, files=files, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()


    def upload_media(
        self,
        file_path: str,
        content_type: str = "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        title: str | None = None
    ) -> dict:
        """
        Upload a file into the global Media library.
        - Uses the singular, capitalized JSON:API type "Media".
        - Attributes must include `title` and `media_type`.
        Returns the created Media JSON.
        """
        url = f"{BASE_URL}/media"
        filename = os.path.basename(file_path)
        # If you want a custom title, pass it; otherwise default to filename (minus extension)
        media_title = title or os.path.splitext(filename)[0]

        # JSON:API metadata
        metadata = {
            "data": {
                "type": "Media",
                "attributes": {
                    "title": media_title,
                    "media_type": "powerpoint"
                }
            }
        }
        print(metadata)

        with open(file_path, "rb") as fp:
            files = {
                # binary payload
                "file": (filename, fp, content_type),
                # metadata payload (must be application/vnd.api+json)
                "data": (None, json.dumps(metadata), "application/vnd.api+json"),
            }
            resp = self.session.post(url, files=files, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()


    def attach_media_to_item(
        self,
        service_type_id: int,
        plan_id: int,
        item_id: int,
        media_id: str
    ) -> dict:
        """
        Link an existing Media record to a specific plan item.
        Posts to the JSON:API relationships endpoint.
        """
        url = (
            f"{BASE_URL}/service_types/{service_type_id}"
            f"/plans/{plan_id}/items/{item_id}/relationships/media"
        )
        payload = {
            "data": [
                { "type": "Media", "id": media_id }
            ]
        }
        resp = self.session.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()



# Optional quick test / example usage
if __name__ == "__main__":
    # Simple demo: fetch the next Sunday’s plan for a given service_type_id
    from datetime import date, timedelta

    def get_upcoming_sunday() -> str:
        today = date.today()
        days_ahead = (6 - today.weekday()) % 7
        return (today + timedelta(days=days_ahead)).isoformat()

    import argparse

    parser = argparse.ArgumentParser(description="Fetch a PCO plan JSON for the upcoming Sunday")
    parser.add_argument("service_type_id", type=int, help="Planning Center service_type_id")
    args = parser.parse_args()

    client = PlanningCenterClient()
    sunday = get_upcoming_sunday()
    plan_id, meta = client.find_plan_by_date(args.service_type_id, sunday)
    full_plan = client.get_plan(args.service_type_id, plan_id)
    print(f"Plan for {sunday} (ID {plan_id}):")
    print(full_plan)