from __future__ import annotations
import sys
from typing import Optional

try:
    from church_automation_shared import config
except ModuleNotFoundError:
    # Fallback to local shared package path when running from repo root
    from pathlib import Path
    _REPO_ROOT = Path(__file__).resolve().parents[1]
    _SHARED_PARENT = _REPO_ROOT / "packages" / "shared"
    if str(_SHARED_PARENT) not in sys.path:
        sys.path.insert(0, str(_SHARED_PARENT))
    from church_automation_shared import config  # type: ignore

from pypco.pco import PCO


def main() -> None:
    pco = PCO(application_id=config.client_id, secret=config.secret)
    print("Listing Planning Center People Lists:\n")
    try:
        for lst in pco.iterate("/people/v2/lists"):
            lid = lst["id"]
            name = lst.get("attributes", {}).get("name", "")
            last_run = lst.get("attributes", {}).get("last_run_at")
            print(f"- {name} (id={lid}) last_run={last_run}")
    except Exception as exc:
        print(f"Error fetching lists: {exc}")


if __name__ == "__main__":
    main()
