"""
Generate service leader guide PDF from Planning Center Online service.

The leader guide contains all service items (names, descriptions, details) in order,
with attached PDFs (lyrics, sheet music) embedded for easy reference during worship.

Usage:
    python -m bulletins_app.make_service_leader_guide
    # or via console script
    make-service-leader-guide
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from pypco.pco import PCO

try:
    from church_automation_shared.paths import (
        LEADER_GUIDE_OUTPUT_DIR,
        SLIDES_SLIDES_CONFIG,
    )
    from church_automation_shared import config
except ModuleNotFoundError:
    _REPO_ROOT = Path(__file__).resolve().parents[3]
    _SHARED_PARENT = _REPO_ROOT / "packages" / "shared"
    if str(_SHARED_PARENT) not in sys.path:
        sys.path.insert(0, str(_SHARED_PARENT))
    try:
        from church_automation_shared.paths import (
            LEADER_GUIDE_OUTPUT_DIR,
            SLIDES_SLIDES_CONFIG,
        )
        from church_automation_shared import config
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "church_automation_shared not found. Install packages with:\n"
            "  uv sync --all-extras"
        ) from e

# Import renderer with fallback for direct script execution
try:
    from bulletins_app.leader_guide_renderer import LeaderGuideRenderer
except ModuleNotFoundError:
    from leader_guide_renderer import LeaderGuideRenderer

# Configuration
CONFIG_PATH = os.getenv("SLIDES_CONFIG", str(SLIDES_SLIDES_CONFIG))
OUTPUT_DIR = LEADER_GUIDE_OUTPUT_DIR


def load_config(path: str) -> dict:
    """Load configuration from JSON file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_slug(value: str) -> str:
    """Convert string to safe filename."""
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value.strip())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "service"


def format_human_date(date_str: str) -> str:
    """Format date string as human-readable."""
    # Handle various date formats
    for fmt in ["%Y-%m-%d", "%B %d, %Y", "%B %#d, %Y", "%B %-d, %Y"]:
        try:
            dt = datetime.strptime(date_str, fmt)
            # Try Windows format first, fall back to standard
            try:
                return dt.strftime("%B %#d, %Y")
            except:
                return dt.strftime("%B %-d, %Y")
        except ValueError:
            continue
    # If all else fails, return the original string
    return date_str


def remove_highlighted_text(soup: BeautifulSoup) -> None:
    """Remove highlighted/marked text from HTML."""
    for tag in soup.find_all(["mark"]):
        tag.decompose()
    for span in soup.find_all("span"):
        if not isinstance(span, Tag) or span.attrs is None:
            continue
        style = (span.get("style") or "").lower()
        cls = " ".join(span.get("class") or []).lower()
        if "background" in style or "highlight" in style or "marker" in cls:
            span.decompose()


def remove_red_text(soup: BeautifulSoup) -> None:
    """Remove red-colored text from HTML."""
    def is_red_style(style: str) -> bool:
        return bool(
            re.search(
                r"color\s*:\s*(red|#f00\b|#ff0000\b|#ff0000ff\b|rgba?\s*\(\s*255\s*,\s*0\s*,\s*0(?:\s*,\s*[0-9.]+)?\s*\))",
                style,
                re.IGNORECASE,
            )
        )

    for tag in soup.find_all(True):
        if not isinstance(tag, Tag):
            continue
        if tag.attrs is None:
            continue
        style = tag.get("style") or ""
        color_attr = tag.get("color") or ""
        if is_red_style(style) or re.search(r"^red$", color_attr, re.IGNORECASE):
            tag.decompose()


def parse_html_detail(html: str) -> List[Dict[str, object]]:
    """Parse HTML details into structured paragraphs with style info."""
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    remove_highlighted_text(soup)
    # Note: Keep red text for leader guide (unlike bulletins which remove it)

    def iter_text_with_style(node: Tag, bold: bool = False):
        for child in node.children:
            if isinstance(child, NavigableString):
                yield str(child), bold
            elif isinstance(child, Tag):
                name = child.name.lower()
                if name == "br":
                    yield "\n", bold
                else:
                    child_bold = bold or name in {"strong", "b"}
                    yield from iter_text_with_style(child, child_bold)

    paragraphs: List[Dict[str, object]] = []
    block_tags = {"p", "div", "li"}

    for node in soup.find_all(block_tags):
        if node.find_parent(block_tags):
            continue
        pieces = list(iter_text_with_style(node))
        buffer: List[Tuple[str, bool]] = []
        for text, is_bold in pieces:
            parts = text.split("\n")
            for idx, part in enumerate(parts):
                if part:
                    buffer.append((part, is_bold))
                if idx < len(parts) - 1:
                    if buffer:
                        line_text = " ".join(t.strip() for t, _ in buffer if t.strip())
                        line_bold = any(b for _, b in buffer)
                        if line_text:
                            prefix = "- " if node.name == "li" else ""
                            paragraphs.append({
                                "text": f"{prefix}{line_text}",
                                "bold": line_bold,
                                "paragraph_end": False,
                                "break_kind": "br",
                            })
                    buffer = []
        if buffer:
            line_text = " ".join(t.strip() for t, _ in buffer if t.strip())
            line_bold = any(b for _, b in buffer)
            if line_text:
                prefix = "- " if node.name == "li" else ""
                paragraphs.append({
                    "text": f"{prefix}{line_text}",
                    "bold": line_bold,
                    "paragraph_end": True,
                    "break_kind": "p",
                })

    if not paragraphs:
        flat = soup.get_text("\n", strip=True)
        for ln in flat.split("\n"):
            if ln.strip():
                paragraphs.append({"text": ln.strip(), "bold": False, "break_kind": "p"})

    cleaned: List[Dict[str, object]] = []
    for p in paragraphs:
        txt = (p.get("text") or "").strip()
        if txt:
            cleaned.append({
                "text": txt,
                "bold": bool(p.get("bold")),
                "paragraph_end": bool(p.get("paragraph_end")),
                "break_kind": p.get("break_kind", "p"),
            })

    deduped: List[Dict[str, object]] = []
    last_key: Optional[Tuple[str, bool, str]] = None
    for entry in cleaned:
        key = (entry["text"], entry["bold"], entry["break_kind"])
        if key != last_key:
            deduped.append(entry)
            last_key = key

    return deduped


def fetch_first_attachment_id(
    pco: PCO,
    item_obj: Dict[str, object],
    service_type_id: int,
    plan_id: str,
    included: Optional[List[Dict[str, object]]] = None,
) -> Optional[str]:
    """Retrieve the first attachment ID for an item using multiple fallback strategies."""
    item_id = str(item_obj.get("id", ""))

    # 1) included attachments
    if included:
        for inc in included:
            if inc.get("type") != "Attachment":
                continue
            rel = inc.get("relationships") or {}
            attachable = (rel.get("attachable") or {}).get("data") or {}
            if str(attachable.get("id")) == item_id:
                att_id = str(inc.get("id"))
                return att_id

    # 2) relationships data
    rel = (item_obj.get("relationships") or {}).get("attachments", {})
    data = rel.get("data") or []
    if data:
        att_id = str(data[0].get("id"))
        return att_id

    # 3) attachments link
    links = item_obj.get("links") or {}
    attach_url = links.get("attachments")
    if attach_url:
        resp = pco.get(attach_url)
        data = resp.get("data") or []
        if data:
            att_id = str(data[0].get("id"))
            return att_id

    # 4) explicit endpoint fallback
    direct_url = (
        f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/items/{item_id}/attachments"
    )
    resp = pco.get(direct_url)
    data = resp.get("data") or []
    if data:
        att_id = str(data[0].get("id"))
        return att_id

    return None


def download_attachment(
    pco: PCO,
    attachment_obj: Dict[str, object],
    service_type_id: int,
    plan_id: str,
    item_id: str,
) -> Optional[bytes]:
    """Download attachment and return bytes."""
    try:
        att_id = str(attachment_obj.get("id", ""))
        att_attrs = attachment_obj.get("attributes", {})
        filename = att_attrs.get("filename", "attachment")

        # Open the attachment to get download URL
        open_url = (
            f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/items/{item_id}/attachments/{att_id}/open"
        )
        open_resp = pco.post(open_url)
        if not open_resp:
            return None

        attachment_url = open_resp.get("data", {}).get("attributes", {}).get("attachment_url")
        if not attachment_url:
            print(f"  ⚠ Could not resolve download URL for {filename}")
            return None

        # Download the file
        file_resp = requests.get(attachment_url, timeout=10)
        file_resp.raise_for_status()
        
        return file_resp.content
    except Exception as e:
        print(f"  ⚠ Failed to download attachment: {e}")

    return None


def get_next_seven_day_window() -> Tuple[str, str]:
    """Get date range for next 7 days."""
    today = date.today()
    end = today + timedelta(days=7)
    return today.isoformat(), end.isoformat()


def fetch_service_name(pco: PCO, service_type_id: int) -> str:
    """Fetch service type name from PCO."""
    try:
        resp = pco.get(f"/services/v2/service_types/{service_type_id}")
        if resp and resp.get("data"):
            return resp["data"].get("attributes", {}).get("name", "Service")
    except Exception:
        pass
    return "Service"


def find_plans_in_range(
    pco: PCO, service_type_id: int, start_date: str, end_date: str
) -> List[Dict[str, object]]:
    """Find service plans in date range."""
    try:
        url = f"/services/v2/service_types/{service_type_id}/plans"
        resp = pco.get(url, where={"from": start_date, "to": end_date}, filter="future")
        plans = resp.get("data", [])
        results = []
        for plan in plans:
            # Extract ISO date from the dates field (format: YYYY-MM-DDTHH:MM:SS)
            plan_date_str = plan.get("attributes", {}).get("dates", "")
            if plan_date_str:
                # Take only the date part (before 'T')
                iso_date = plan_date_str.split("T")[0]
                results.append({"plan": plan, "plan_date": iso_date})
        return results
    except Exception as e:
        print(f"  ⚠ Error fetching plans: {e}")
        return []


def generate_leader_guide(
    pco: PCO,
    service_type_id: int,
    plan_id: str,
    plan_date: str,
    service_name: str,
) -> None:
    """Generate leader guide PDF for a service plan."""
    print(f"[INFO] Generating leader guide for {service_name} on {plan_date}")

    # Fetch all items
    items_resp = pco.get(
        f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/items",
        include="attachments",
    )
    items = items_resp.get("data", [])

    if not items:
        print(f"  ⚠ No items found for plan {plan_id}; skipping")
        return

    # Initialize renderer
    renderer = LeaderGuideRenderer()

    # Draw title - commented out per user preference
    # title = f"{service_name}\n{format_human_date(plan_date)}"
    # renderer.draw_title(title)

    # Sort items by position
    sorted_items = sorted(
        items, key=lambda x: x.get("attributes", {}).get("item_position_order", 999)
    )

    # Process each item
    for item_obj in sorted_items:
        item_attrs = item_obj.get("attributes", {})
        item_id = item_obj.get("id", "")

        title = item_attrs.get("title", "Untitled")
        
        # Skip drawing item details for Bulletin Cover, but still process attachments
        skip_details_titles = {"Bulletin Cover", "Bulletin cover"}
        should_skip_details = title in skip_details_titles
        
        description = item_attrs.get("description")
        html_details_str = item_attrs.get("html_details", "")

        # Parse HTML details
        html_details = parse_html_detail(html_details_str)

        # Draw item (unless skipped)
        if not should_skip_details:
            renderer.draw_item(title, description, html_details)

        # Fetch attachments for this item
        attachments_url = (
            f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/items/{item_id}/attachments"
        )
        try:
            attachments_resp = pco.get(attachments_url)
            attachments = attachments_resp.get("data", [])
        except Exception as e:
            print(f"  ⚠ Could not fetch attachments for '{title}': {e}")
            attachments = []

        # Download and add attachments
        for att_obj in attachments:
            att_id = att_obj.get("id")
            att_attrs = att_obj.get("attributes", {})
            filename = att_attrs.get("filename", "attachment")

            # Determine file type - check content_type first, fall back to filename extension
            content_type = (att_attrs.get("content_type", "") or "").lower()
            filename_lower = filename.lower()
            
            is_pdf = "pdf" in content_type or filename_lower.endswith(".pdf")
            is_image = "image" in content_type
            
            if not is_pdf and not is_image:
                continue

            att_bytes = download_attachment(
                pco, att_obj, service_type_id, plan_id, item_id
            )
            if att_bytes:
                if is_pdf:
                    renderer.add_attachment_pdf(att_bytes)
                    print(f"  [OK] Added PDF: {filename}")

    # Save to output directory
    safe_service = safe_slug(service_name)
    filename = f"{safe_service}_{plan_date}_leader_guide.pdf"
    output_path = Path(OUTPUT_DIR) / filename

    renderer.save(output_path)
    print(f"  [OK] Leader guide saved to {output_path}")


def main() -> None:
    """Main entry point."""
    try:
        cfg = load_config(CONFIG_PATH)
    except FileNotFoundError:
        print(f"[ERROR] Configuration file not found: {CONFIG_PATH}")
        print("  Please set SLIDES_CONFIG environment variable or create slides_config.json")
        return

    service_type_ids = cfg.get("service_type_ids", [])
    if not service_type_ids:
        print(
            "[ERROR] No service_type_ids configured. "
            "Add this to your slides_config.json:\n"
            '  "service_type_ids": [123, 456, ...]'
        )
        return

    start_date, end_date = get_next_seven_day_window()

    pco = PCO(application_id=config.client_id, secret=config.secret)

    # Find the first upcoming service date across all service types
    next_service_date = None
    
    for stid in service_type_ids:
        plans = find_plans_in_range(pco, stid, start_date, end_date)
        if plans:
            next_service_date = plans[0]["plan_date"]
            break
    
    if not next_service_date:
        print("[ERROR] No upcoming services found in the next 7 days")
        return

    print(f"[INFO] Generating leader guides for all services on {next_service_date}")

    # Process all services on that date
    for stid in service_type_ids:
        service_name = fetch_service_name(pco, stid)
        plans = find_plans_in_range(pco, stid, start_date, end_date)

        # Filter to only plans on the next_service_date
        plans_on_date = [p for p in plans if p["plan_date"] == next_service_date]

        for plan_entry in plans_on_date:
            plan_obj = plan_entry["plan"]
            plan_date = plan_entry["plan_date"]
            plan_id = plan_obj["id"]

            generate_leader_guide(pco, stid, plan_id, plan_date, service_name)


if __name__ == "__main__":
    main()
