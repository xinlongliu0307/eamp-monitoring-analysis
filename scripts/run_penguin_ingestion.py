"""Orchestrator script for the penguin ingestion pipeline.

Composes the ingest module's entry points (load, overlay, consolidate, write)
and adds the standing quality-audit checks. The overlay step incorporates
Barb's supplementary corrections (received 2026-05-18) for the Umebosi and
Shackleton Ice Shelf colonies.
"""
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from eamp.common import config
from eamp.common.logging import get_logger
from eamp.penguin.ingest import (
    load_observations_workbook,
    overlay_supplementary_sheets,
    consolidate_observations,
    write_processed,
)
from eamp.penguin.quality_audit import write_quality_audit_report

logger = get_logger("run_penguin_ingestion")

# Barb's 2026-05-18 supplementary workbooks supersede the corresponding sheets
# in the main observational workbook. The Umebosi supplement contains the
# corrected latitude (-68.04, previously mis-recorded as -64.04) plus the
# missing 2025 observations. The Shackleton supplement adds the previously
# non-standard ice-shelf colony in a structure compatible with the canonical
# sheet schema.
SUPPLEMENTS_DIR = config.PENGUIN_RAW / "barb_2026-05-18"
SUPPLEMENTS = {
    "1. Umebosi": SUPPLEMENTS_DIR / "Umebosi_updated_20260518.xlsx",
    "16. Shackelton Ice Shelf": SUPPLEMENTS_DIR / "Shackleton_20260518.xlsx",
}
SUPPLEMENT_SHEET_NAMES = {
    "1. Umebosi": "1.Umebosi",
    "16. Shackelton Ice Shelf": "16.Shackleton",
}

# Shackleton can now be ingested as a standard sheet, so the skip list is
# empty. If future audits reveal a new non-standard sheet, add it here.
NON_STANDARD_SHEETS: list[str] = []


def main():
    date_tag = date.today().isoformat()

    logger.info("=" * 60)
    logger.info("Penguin ingestion starting (date tag: %s)", date_tag)
    logger.info("=" * 60)

    source_path = config.PENGUIN_RAW / config.PENGUIN_OBSERVATIONS_FILE
    sheets = load_observations_workbook(source_path)

    # Overlay Barb's supplementary corrections
    sheets = overlay_supplementary_sheets(
        sheets, SUPPLEMENTS, name_mapping=SUPPLEMENT_SHEET_NAMES
    )

    observations, skipped = consolidate_observations(
        sheets, skip_sheets=NON_STANDARD_SHEETS
    )
    logger.info("Consolidated %d observations across %d sheets",
                len(observations), len(sheets) - len(skipped))
    if skipped:
        logger.info("Skipped sheets: %s", ", ".join(skipped))

    output_dir = config.PENGUIN_PROCESSED
    parquet_path, excel_path = write_processed(observations, output_dir, date_tag)
    logger.info("Wrote Parquet: %s", parquet_path)
    logger.info("Wrote Excel:   %s", excel_path)

    audit_path = output_dir / f"eampA_quality_audit_{date_tag}.xlsx"
    write_quality_audit_report(observations, audit_path)
    logger.info("Wrote audit:   %s", audit_path)

    logger.info("=" * 60)
    logger.info("Ingestion summary")
    logger.info("  Total observations: %d", len(observations))
    logger.info("  Distinct colonies:  %d", observations["colony_name"].nunique())
    logger.info("  Date range:         %s to %s",
                observations["observation_date"].min().date(),
                observations["observation_date"].max().date())
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
