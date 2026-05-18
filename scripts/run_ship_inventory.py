"""Orchestrator script for the ship inventory analysis."""
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from eamp.common import config
from eamp.common.logging import get_logger
from eamp.ship.inventory import build_inventory

logger = get_logger("run_ship_inventory")


def main():
    date_tag = date.today().isoformat()
    downloads_root = config.SHIP_RAW / "aodn_downloads"

    logger.info("=" * 60)
    logger.info("Ship inventory analysis starting")
    logger.info("Date tag: %s", date_tag)
    logger.info("Downloads root: %s", downloads_root)
    logger.info("=" * 60)

    inventory = build_inventory(downloads_root)

    output_dir = config.SHIP_PROCESSED
    output_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = output_dir / f"eampB_aodn_inventory_{date_tag}.parquet"
    excel_path = output_dir / f"eampB_aodn_inventory_{date_tag}.xlsx"

    logger.info("Writing Parquet: %s", parquet_path)
    inventory.to_parquet(parquet_path, index=False)
    logger.info("Writing Excel: %s", excel_path)
    inventory.to_excel(excel_path, index=False, engine="openpyxl")

    logger.info("=" * 60)
    logger.info("Inventory summary")
    logger.info("  Total files: %d", len(inventory))
    logger.info("  By vessel:")
    for vessel, count in inventory["vessel"].value_counts().items():
        logger.info("    %s: %d files", vessel, count)
    logger.info("  By sub-facility:")
    for sub, count in inventory["subfacility"].value_counts().items():
        logger.info("    %s: %d files", sub, count)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
