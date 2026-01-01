from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path
import sys

# Ensure repo root is importable for shared utilities
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from shared.paths import ANNOUNCEMENTS_OUTPUT_DIR
from .gmail_utils import authenticate_gmail, fetch_latest_announcement_html
from .html_parser import parse_announcements
from .ppt_generator import create_pptx_with_qr
from .summarize import summarize_text


def get_next_sunday() -> date:
    today = date.today()
    days_until_sunday = (6 - today.weekday()) % 7
    next_sunday = today + timedelta(days=days_until_sunday)
    return next_sunday


def main() -> None:
    service = authenticate_gmail()
    html_content = fetch_latest_announcement_html(
        service,
        query='from:First United Methodist Church subject:"The Latest FUMC News for You!"',
    )
    announcements = parse_announcements(html_content)

    for ann in announcements:
        if "body" in ann:
            ann["summary"] = summarize_text(ann["body"], max_chars=250)
        else:
            ann["summary"] = "No summary available."

    date_str = get_next_sunday().strftime("%Y-%m-%d")
    output_dir = ANNOUNCEMENTS_OUTPUT_DIR / date_str
    output_path = output_dir / f"weekly_announcements_{date_str}.pptx"
    os.makedirs(output_dir, exist_ok=True)
    create_pptx_with_qr(announcements, str(output_path), use_summary=True)

    # Optional: export slides to JPGs later if needed
    # jpg_folder = output_dir
    # export_pptx_to_jpg(str(output_path), str(jpg_folder))
    # print(f"  → Exported slides to JPGs in {jpg_folder}")


if __name__ == "__main__":
    main()
