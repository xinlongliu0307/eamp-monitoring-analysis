"""Orchestrator for new AODN portal inventory across one or more vessels.

Usage:
    python scripts/run_new_portal_inventory.py [vessel_subdir]

If vessel_subdir is provided (e.g., 'new_portal_nuyina' or
'new_portal_aurora_australis'), the inventory covers only that directory.
If omitted, the script walks all new_portal_* directories under
aodn_downloads and produces a consolidated inventory covering both vessels.
"""
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import pandas as pd

from eamp.common import config
from eamp.common.logging import get_logger
from eamp.ship.new_portal_inventory import (
    build_inventory,
    summarise_by_season,
)

logger = get_logger("run_new_portal_inventory")


def main():
    date_tag = date.today().isoformat()
    aodn_root = config.SHIP_RAW / "aodn_downloads"

    # Determine which directories to inventory
    if len(sys.argv) > 1:
        targets = [aodn_root / sys.argv[1]]
        scope = sys.argv[1]
    else:
        targets = sorted(aodn_root.glob("new_portal_*"))
        scope = "all_new_portal"

    logger.info("=" * 60)
    logger.info("New AODN portal inventory (date tag: %s)", date_tag)
    logger.info("Scope: %s", scope)
    logger.info("Target directories: %s", [str(t.name) for t in targets])
    logger.info("=" * 60)

    if not targets:
        logger.error("No new_portal_* directories found under %s", aodn_root)
        sys.exit(1)

    frames = []
    for target in targets:
        if not target.exists():
            logger.warning("Directory does not exist: %s", target)
            continue
        logger.info("Building inventory for: %s", target.name)
        frames.append(build_inventory(target))

    if not frames:
        logger.error("No files inventoried; exiting")
        sys.exit(1)

    file_inv = pd.concat(frames, ignore_index=True)
    season_summary = summarise_by_season(file_inv)

    output_dir = config.SHIP_PROCESSED
    output_dir.mkdir(parents=True, exist_ok=True)
    excel_path = output_dir / f"eampB_aodn_new_portal_{scope}_inventory_{date_tag}.xlsx"

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        file_inv.to_excel(writer, sheet_name="files", index=False)
        season_summary.to_excel(writer, sheet_name="season_summary", index=False)

    logger.info("Inventory written: %s", excel_path)
    logger.info("=" * 60)
    logger.info("Summary")
    logger.info("  Total files: %d", len(file_inv))
    logger.info("  Total rows across all files: %s",
                f"{int(file_inv['n_rows'].sum()):,}"
                if file_inv["n_rows"].notna().any() else "n/a")
    logger.info("  Total volume: %.1f MB", file_inv["size_mb"].sum())
    logger.info("  Vessels represented: %s",
                ", ".join(sorted(file_inv["vessel"].dropna().unique())))
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
