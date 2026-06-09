"""Build the consolidated long-format Nuyina dataset and coverage summary."""
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import pandas as pd
from eamp.common import config
from eamp.common.logging import get_logger
from eamp.ship.harmonise import consolidate

logger = get_logger("run_ship_harmonisation")


def main():
    tag = date.today().isoformat()
    raw_dir = config.SHIP_RAW / "aadc_downloads" / "nuyina_underway_voyages"
    out_dir = config.SHIP_PROCESSED
    out_dir.mkdir(parents=True, exist_ok=True)

    long, coverage = consolidate(raw_dir)

    long_path = out_dir / f"eampB_nuyina_long_{tag}.parquet"
    cov_path = out_dir / f"eampB_nuyina_coverage_{tag}.xlsx"
    long.to_parquet(long_path, index=False)
    coverage.to_excel(cov_path, index=False, engine="openpyxl")

    logger.info("=" * 60)
    logger.info("Long dataset:    %s", long_path)
    logger.info("  rows: %d, voyages: %d, variables: %d",
                len(long), long["voyage"].nunique(), long["variable"].nunique())
    logger.info("Coverage summary: %s", cov_path)
    logger.info("=" * 60)
    print(coverage.to_string(index=False))


if __name__ == "__main__":
    main()