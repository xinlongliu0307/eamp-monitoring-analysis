"""Orchestrator for the new AODN portal Nuyina inventory."""
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
    root = config.SHIP_RAW / "aodn_downloads" / "new_portal_nuyina"

    logger.info("=" * 60)
    logger.info("New AODN portal Nuyina inventory (date tag: %s)", date_tag)
    logger.info("Root: %s", root)
    logger.info("=" * 60)

    if not root.exists():
        logger.error("Expected directory not found: %s", root)
        sys.exit(1)

    file_inv = build_inventory(root)
    season_summary = summarise_by_season(file_inv)

    output_dir = config.SHIP_PROCESSED
    output_dir.mkdir(parents=True, exist_ok=True)
    excel_path = output_dir / f"eampB_aodn_new_portal_nuyina_inventory_{date_tag}.xlsx"

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
    logger.info("  Seasons represented: %d",
                file_inv["season"].nunique(dropna=True))
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
