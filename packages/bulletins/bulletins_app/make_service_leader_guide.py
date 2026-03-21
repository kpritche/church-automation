"""
Generate service leader guide PDFs from a Planning Center Online service.

Each service produces multiple leader guide variants with the same base item content
but different song attachment rules.

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
UPLOAD_TO_PCO = os.getenv("LEADER_GUIDE_UPLOAD_TO_PCO", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}

LEADER_GUIDE_VARIANTS: List[Dict[str, object]] = [
    {
        "key": "sheet_music",
        "label": "sheet music",
        "fallback_order": ("sheet_music", "chord_chart", "lyrics"),
    },
    {
        "key": "chord_charts",
        "label": "chord charts",
        "fallback_order": ("chord_chart", "lyrics"),
    },
]


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
    # Keep all text for leader guides, including highlighted and red content.

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


def attachment_filename(attachment_obj: Dict[str, object]) -> str:
    """Return lowercase filename for an attachment."""
    attrs = attachment_obj.get("attributes") or {}
    return str(attrs.get("filename") or "").lower()


def attachment_content_type(attachment_obj: Dict[str, object]) -> str:
    """Return lowercase content type for an attachment."""
    attrs = attachment_obj.get("attributes") or {}
    return str(attrs.get("content_type") or "").lower()


def is_pdf_attachment(attachment_obj: Dict[str, object]) -> bool:
    """Return whether an attachment is a PDF."""
    filename = attachment_filename(attachment_obj)
    content_type = attachment_content_type(attachment_obj)
    return filename.endswith(".pdf") or "pdf" in content_type


def classify_song_attachment(attachment_obj: Dict[str, object]) -> Optional[str]:
    """Classify a song PDF attachment for variant-specific fallback selection."""
    if not is_pdf_attachment(attachment_obj):
        return None

    filename = attachment_filename(attachment_obj)

    if "lyric" in filename:
        return "lyrics"

    if any(keyword in filename for keyword in ["chart", "chord", "chords"]):
        return "chord_chart"

    return "sheet_music"


def song_attachment_priority(attachment_obj: Dict[str, object], attachment_kind: str) -> Tuple[int, str]:
    """Return a sort key for attachment selection within a song attachment class."""
    filename = attachment_filename(attachment_obj)

    if attachment_kind == "sheet_music":
        if "vocal" in filename:
            return (0, filename)
        if "lead" in filename:
            return (1, filename)
        return (2, filename)

    if attachment_kind == "chord_chart":
        if "chord" in filename:
            return (0, filename)
        if "chart" in filename:
            return (1, filename)
        return (2, filename)

    return (0, filename)


def choose_song_attachment(
    attachments: List[Dict[str, object]],
    fallback_order: Tuple[str, ...],
) -> Tuple[Optional[Dict[str, object]], Optional[str]]:
    """Choose a single song attachment using the variant fallback order."""
    attachments_by_kind: Dict[str, List[Dict[str, object]]] = {
        "sheet_music": [],
        "chord_chart": [],
        "lyrics": [],
    }

    for attachment in attachments:
        kind = classify_song_attachment(attachment)
        if kind:
            attachments_by_kind[kind].append(attachment)

    for kind in fallback_order:
        candidates = attachments_by_kind.get(kind) or []
        if candidates:
            selected = sorted(candidates, key=lambda att: song_attachment_priority(att, kind))[0]
            return selected, kind

    return None, None


def fetch_item_attachments(
    pco: PCO,
    service_type_id: int,
    plan_id: str,
    item_id: str,
    title: str,
) -> List[Dict[str, object]]:
    """Fetch attachments for a single service item."""
    attachments_url = (
        f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/items/{item_id}/attachments"
    )
    try:
        attachments_resp = pco.get(attachments_url)
        return attachments_resp.get("data", [])
    except Exception as e:
        print(f"  ⚠ Could not fetch attachments for '{title}': {e}")
        return []


def extract_leader_name(person_obj: Dict[str, object]) -> Optional[str]:
    """Extract the preferred leader display name from a Person payload."""
    attributes = person_obj.get("attributes") or {}
    first_name = str(attributes.get("first_name") or "").strip()
    last_name = str(attributes.get("last_name") or "").strip()
    if first_name and last_name:
        return f"{first_name} {last_name}"

    full_name = str(attributes.get("full_name") or "").strip()
    if full_name:
        return full_name

    if first_name:
        return first_name
    if last_name:
        return last_name

    return None


def fetch_item_leaders(
    pco: PCO,
    service_type_id: int,
    plan_id: str,
    item_id: str,
    title: str,
) -> List[str]:
    """Fetch assigned leader first names for a single service item."""
    endpoint = (
        f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/items/{item_id}/item_assignments"
    )

    try:
        resp = pco.get(endpoint, include="assignable")
    except Exception as e:
        print(f"  ⚠ Could not fetch item assignments for '{title}': {e}")
        return []

    included = resp.get("included") or []
    people_by_id: Dict[str, Dict[str, object]] = {
        str(person.get("id")): person
        for person in included
        if person.get("type") == "Person"
    }

    leaders: List[str] = []
    seen: set[str] = set()

    for assignment in resp.get("data") or []:
        relationships = assignment.get("relationships") or {}
        assignable = (relationships.get("assignable") or {}).get("data") or {}
        if assignable.get("type") != "Person":
            continue

        person_id = str(assignable.get("id") or "")
        person_obj = people_by_id.get(person_id)
        if person_obj is None:
            related_url = (relationships.get("assignable") or {}).get("links", {}).get("related")
            if related_url:
                try:
                    person_resp = pco.get(related_url)
                    person_obj = person_resp.get("data")
                except Exception:
                    person_obj = None

        if not person_obj:
            continue

        leader_name = extract_leader_name(person_obj)
        if leader_name and leader_name not in seen:
            seen.add(leader_name)
            leaders.append(leader_name)

    return leaders


def prepare_item_entries(
    pco: PCO,
    service_type_id: int,
    plan_id: str,
    items: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    """Prepare item metadata and attachments once for all leader guide variants."""
    prepared_items: List[Dict[str, object]] = []

    for item_obj in items:
        item_attrs = item_obj.get("attributes", {})
        item_id = str(item_obj.get("id", ""))
        title = item_attrs.get("title", "Untitled")
        description = item_attrs.get("description")
        html_details = parse_html_detail(item_attrs.get("html_details", ""))
        item_type = str(item_attrs.get("item_type") or "").lower()

        prepared_items.append(
            {
                "item_id": item_id,
                "title": title,
                "description": description,
                "html_details": html_details,
                "should_skip_details": title in {"Bulletin Cover", "Bulletin cover"},
                "is_song": item_type == "song",
                "leaders": fetch_item_leaders(
                    pco,
                    service_type_id=service_type_id,
                    plan_id=plan_id,
                    item_id=item_id,
                    title=title,
                ),
                "attachments": fetch_item_attachments(
                    pco,
                    service_type_id=service_type_id,
                    plan_id=plan_id,
                    item_id=item_id,
                    title=title,
                ),
            }
        )

    return prepared_items


def get_attachment_bytes(
    pco: PCO,
    attachment_obj: Dict[str, object],
    service_type_id: int,
    plan_id: str,
    item_id: str,
    cache: Dict[str, bytes],
) -> Optional[bytes]:
    """Download attachment bytes with a simple in-memory cache."""
    attachment_id = str(attachment_obj.get("id") or "")
    if attachment_id in cache:
        return cache[attachment_id]

    attachment_bytes = download_attachment(
        pco,
        attachment_obj,
        service_type_id=service_type_id,
        plan_id=plan_id,
        item_id=item_id,
    )
    if attachment_bytes:
        cache[attachment_id] = attachment_bytes
    return attachment_bytes


def upload_leader_guide_to_plan(
    pco: PCO,
    service_type_id: int,
    plan_id: str,
    file_path: Path,
) -> bool:
    """Upload a generated leader guide PDF as a plan attachment in PCO."""
    try:
        upload_resp = pco.upload(str(file_path))
        upload_id = upload_resp["data"][0]["id"]

        attach_payload = {
            "data": {
                "attributes": {
                    "file_upload_identifier": upload_id,
                    "filename": file_path.name,
                }
            }
        }

        pco.post(
            f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/attachments",
            payload=attach_payload,
        )
        print(f"  [OK] Uploaded leader guide to plan: {file_path.name}")
        return True
    except Exception as e:
        print(f"  ⚠ Failed to upload leader guide to plan '{plan_id}': {e}")
        return False


def render_leader_guide_variant(
    pco: PCO,
    service_type_id: int,
    plan_id: str,
    plan_date: str,
    service_name: str,
    prepared_items: List[Dict[str, object]],
    variant: Dict[str, object],
    attachment_cache: Dict[str, bytes],
) -> None:
    """Render one leader guide variant for a service."""
    renderer = LeaderGuideRenderer()
    variant_label = str(variant["label"])
    fallback_order = tuple(variant["fallback_order"])

    print(
        f"[INFO] Rendering {variant_label} leader guide for {service_name} on {plan_date}"
    )

    for item in prepared_items:
        title = str(item["title"])
        item_id = str(item["item_id"])

        if not item["should_skip_details"]:
            renderer.draw_item(
                title,
                item.get("description"),
                item.get("html_details"),
                item.get("leaders"),
            )

        selected_attachments: List[Tuple[Dict[str, object], Optional[str]]] = []

        if item["is_song"]:
            selected_attachment, selected_kind = choose_song_attachment(
                item["attachments"],
                fallback_order=fallback_order,
            )
            if selected_attachment:
                selected_attachments.append((selected_attachment, selected_kind))
        else:
            for attachment in item["attachments"]:
                if is_pdf_attachment(attachment):
                    selected_attachments.append((attachment, None))

        for attachment_obj, selected_kind in selected_attachments:
            attachment_bytes = get_attachment_bytes(
                pco,
                attachment_obj,
                service_type_id=service_type_id,
                plan_id=plan_id,
                item_id=item_id,
                cache=attachment_cache,
            )
            if not attachment_bytes:
                continue

            filename = (attachment_obj.get("attributes", {}) or {}).get("filename", "attachment")
            renderer.add_attachment_pdf(attachment_bytes)
            if selected_kind:
                print(f"  [OK] Added {selected_kind} for '{title}': {filename}")
            else:
                print(f"  [OK] Added PDF for '{title}': {filename}")

    safe_service = safe_slug(service_name)
    variant_key = str(variant["key"])
    filename = f"{safe_service}_{plan_date}_leader_guide_{variant_key}.pdf"
    output_path = Path(OUTPUT_DIR) / filename

    renderer.save(output_path)
    print(f"  [OK] {variant_label.title()} leader guide saved to {output_path}")
    if UPLOAD_TO_PCO:
        upload_leader_guide_to_plan(
            pco,
            service_type_id=service_type_id,
            plan_id=plan_id,
            file_path=output_path,
        )
    else:
        print(f"  [OK] Skipped PCO upload for local test: {output_path.name}")


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
    """Generate all leader guide PDF variants for a service plan."""
    print(f"[INFO] Generating leader guide variants for {service_name} on {plan_date}")

    # Fetch all items
    items_resp = pco.get(
        f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/items",
        include="attachments",
    )
    items = items_resp.get("data", [])

    if not items:
        print(f"  ⚠ No items found for plan {plan_id}; skipping")
        return

    # Sort items by position
    sorted_items = sorted(
        items, key=lambda x: x.get("attributes", {}).get("item_position_order", 999)
    )

    prepared_items = prepare_item_entries(
        pco,
        service_type_id=service_type_id,
        plan_id=plan_id,
        items=sorted_items,
    )
    attachment_cache: Dict[str, bytes] = {}

    for variant in LEADER_GUIDE_VARIANTS:
        render_leader_guide_variant(
            pco,
            service_type_id=service_type_id,
            plan_id=plan_id,
            plan_date=plan_date,
            service_name=service_name,
            prepared_items=prepared_items,
            variant=variant,
            attachment_cache=attachment_cache,
        )


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
