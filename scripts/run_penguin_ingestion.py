"""Orchestrator script for the penguin ingestion pipeline."""
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from eamp.common import config
from eamp.common.logging import get_logger
from eamp.penguin.harmonise import NON_STANDARD_SHEETS
from eamp.penguin.ingest import (
    consolidate_observations,
    load_observations_workbook,
    write_processed,
)

logger = get_logger("run_penguin_ingestion")


def main():
    date_tag = date.today().isoformat()
    input_path = config.PENGUIN_RAW / config.PENGUIN_OBSERVATIONS_FILE

    logger.info("=" * 60)
    logger.info("Penguin ingestion pipeline starting")
    logger.info("Date tag: %s", date_tag)
    logger.info("Input: %s", input_path)
    logger.info("Output dir: %s", config.PENGUIN_PROCESSED)
    logger.info("=" * 60)

    sheets = load_observations_workbook(input_path)
    df, skipped = consolidate_observations(
        sheets, skip_sheets=list(NON_STANDARD_SHEETS)
    )

    logger.info("=" * 60)
    logger.info("Consolidation summary")
    logger.info("  Total observations: %d", len(df))
    logger.info("  Colonies represented: %d", df["colony_name"].nunique())
    logger.info(
        "  Date range: %s to %s",
        df["observation_date"].min().date(),
        df["observation_date"].max().date(),
    )
    logger.info(
        "  Surface types observed: %s",
        sorted(s for s in df["surface_type"].dropna().unique()),
    )
    logger.info("  Skipped sheets: %s", skipped)
    logger.info("=" * 60)

    parquet_path, excel_path = write_processed(
        df, config.PENGUIN_PROCESSED, date_tag
    )
    logger.info("Outputs written:")
    logger.info("  %s", parquet_path)
    logger.info("  %s", excel_path)


if __name__ == "__main__":
    main()
