"""Ingestion of emperor penguin colony observation spreadsheets."""
from pathlib import Path
from typing import Optional

import pandas as pd

from eamp.common.logging import get_logger
from eamp.penguin.harmonise import (
    harmonise_columns,
    parse_colony_name,
)

logger = get_logger(__name__)


def load_observations_workbook(path: Path) -> dict[str, pd.DataFrame]:
    logger.info("Reading observations workbook: %s", path)
    sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    logger.info("Read %d sheets", len(sheets))
    return sheets


def consolidate_observations(
    sheets: dict[str, pd.DataFrame],
    skip_sheets: Optional[list[str]] = None,
) -> tuple[pd.DataFrame, list[str]]:
    skip_sheets = skip_sheets or []
    frames = []
    skipped = []

    for sheet_name, df in sheets.items():
        if sheet_name in skip_sheets:
            logger.info("Skipping non-standard sheet: %s", sheet_name)
            skipped.append(sheet_name)
            continue

        try:
            colony_id, colony_name = parse_colony_name(sheet_name)
        except ValueError as exc:
            logger.warning("Could not parse sheet name %r: %s", sheet_name, exc)
            skipped.append(sheet_name)
            continue

        harmonised = harmonise_columns(df)
        if harmonised is None:
            logger.warning(
                "Sheet %r lacks required columns; skipping", sheet_name
            )
            skipped.append(sheet_name)
            continue

        harmonised["colony_id"] = colony_id
        harmonised["colony_name"] = colony_name
        harmonised["source_sheet"] = sheet_name
        frames.append(harmonised)
        logger.info(
            "Sheet %r harmonised: %d observations", sheet_name, len(harmonised)
        )

    consolidated = pd.concat(frames, ignore_index=True)
    column_order = [
        "colony_id",
        "colony_name",
        "observation_date",
        "latitude",
        "longitude",
        "surface_type",
        "open_water_distance_km",
        "comments",
        "source_sheet",
    ]
    return consolidated[column_order], skipped


def write_processed(
    df: pd.DataFrame,
    output_dir: Path,
    date_tag: str,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = output_dir / f"eampA_colony_observations_long_{date_tag}.parquet"
    excel_path = output_dir / f"eampA_colony_observations_long_{date_tag}.xlsx"

    logger.info("Writing Parquet: %s", parquet_path)
    df.to_parquet(parquet_path, index=False)

    logger.info("Writing Excel: %s", excel_path)
    df.to_excel(excel_path, index=False, engine="openpyxl")

    return parquet_path, excel_path
