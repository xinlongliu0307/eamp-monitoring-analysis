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


def overlay_supplementary_sheets(
    sheets: dict[str, pd.DataFrame],
    supplements: dict[str, Path],
    name_mapping: Optional[dict[str, str]] = None,
) -> dict[str, pd.DataFrame]:
    """Overlay supplementary single-sheet workbooks onto the main sheets dict.

    Each supplementary file is read and its sheet replaces the corresponding
    entry in the main dictionary. The optional name_mapping handles the case
    where the supplementary sheet name differs from the canonical sheet name
    in the main workbook (e.g. '1.Umebosi' in the supplement vs '1. Umebosi'
    in the original).

    Parameters
    ----------
    sheets
        The dictionary returned by load_observations_workbook.
    supplements
        Mapping of canonical sheet name (as used in the main workbook) to the
        path of the supplementary single-sheet workbook providing the
        replacement data.
    name_mapping
        Optional mapping from the canonical sheet name (key in supplements)
        to the actual sheet name inside the supplementary file, when the two
        differ.

    Returns
    -------
    dict[str, pd.DataFrame]
        The updated sheets dictionary with supplementary content overlaid.
    """
    name_mapping = name_mapping or {}
    updated = dict(sheets)
    for canonical_name, supp_path in supplements.items():
        supp_sheet_name = name_mapping.get(canonical_name, canonical_name)
        logger.info(
            "Overlaying supplement %s -> sheet %r from %s",
            canonical_name, supp_sheet_name, supp_path.name,
        )
        supp = pd.read_excel(
            supp_path, sheet_name=supp_sheet_name, engine="openpyxl"
        )
        updated[canonical_name] = supp
    return updated
