"""Inventory builder for the new AODN portal's voyage-level Nuyina downloads.

The new portal delivers data as CSV files named by voyage season and version,
following the pattern RSV_Nuyina_Voyage_Data_<season>_<version>.csv. Each
file is a self-contained voyage record with its own column structure rather
than a uniform schema across voyages.

This module walks the new_portal_nuyina directory, parses the voyage
identifier from each filename, reads each CSV to capture row count and
column structure, and produces a consolidated inventory suitable for the
audit deliverable and the progress note to Patricia.
"""
import re
from pathlib import Path

import pandas as pd

from eamp.common.logging import get_logger

logger = get_logger(__name__)

# Parameter vocabulary mapping the new portal's column-name conventions to
# the six EAMP priority variables. Each file is inspected for column names
# matching any of these tokens; matches are recorded in the inventory.
PRIORITY_VARIABLE_TOKENS = {
    "sst":   ["temperature", "sst", "sea_surface_temperature", "water_temp"],
    "sss":   ["salinity", "sss", "psal"],
    "tair":  ["air_temperature", "air_temp", "atemp", "tair"],
    "patm":  ["pressure", "air_pressure", "atmos", "patm"],
    "wind":  ["wind", "wspd", "wdir"],
    "pco2":  ["carbon", "pco2", "co2", "xco2"],
}


def parse_voyage_identifier(path: Path) -> dict:
    """Extract season and version from a new-portal voyage filename.
    
    Filenames follow the pattern RSV_Nuyina_Voyage_Data_<season>_<version>.csv
    where season is YYYY-YY and version is V<n> or VT<n><A>.
    """
    m = re.search(
        r'RSV_Nuyina_Voyage_Data_(\d{4}-\d{2})_(VT?\d+[A-Z]?)\.csv',
        path.name,
    )
    if m:
        return {"season": m.group(1), "version": m.group(2)}
    return {"season": None, "version": None}


def inspect_csv(path: Path) -> dict:
    """Read a CSV file and return summary statistics."""
    summary = {
        "n_rows": None,
        "n_columns": None,
        "columns": None,
        "priority_vars_matched": None,
        "read_status": "ok",
    }
    try:
        # Read only a small sample for column inspection; full row count
        # is obtained separately to avoid loading large files into memory.
        sample = pd.read_csv(path, nrows=5, low_memory=False)
        summary["n_columns"] = len(sample.columns)
        summary["columns"] = ";".join(sample.columns.astype(str).tolist())

        cols_lower = [str(c).lower() for c in sample.columns]
        matched = []
        for var, tokens in PRIORITY_VARIABLE_TOKENS.items():
            if any(any(t in c for t in tokens) for c in cols_lower):
                matched.append(var)
        summary["priority_vars_matched"] = ",".join(matched)

        with open(path, "r", errors="replace") as f:
            summary["n_rows"] = sum(1 for _ in f) - 1  # exclude header
    except Exception as exc:
        logger.warning("Could not inspect %s: %s", path.name, exc)
        summary["read_status"] = f"error: {exc}"
    return summary


def build_inventory(root: Path) -> pd.DataFrame:
    """Walk the directory and produce the file-level inventory."""
    csvs = sorted(root.glob("*.csv"))
    logger.info("Found %d CSV files under %s", len(csvs), root)

    rows = []
    for path in csvs:
        voyage = parse_voyage_identifier(path)
        csv_info = inspect_csv(path)
        rows.append({
            "filename": path.name,
            "season": voyage["season"],
            "version": voyage["version"],
            "size_mb": round(path.stat().st_size / 1e6, 2),
            **csv_info,
        })
    return pd.DataFrame(rows)


def summarise_by_season(inventory: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the file-level inventory into a per-season summary."""
    if inventory.empty:
        return inventory
    return (
        inventory.groupby("season", dropna=False)
        .agg(
            n_voyages=("version", "nunique"),
            n_files=("filename", "size"),
            total_size_mb=("size_mb", "sum"),
            total_rows=("n_rows", "sum"),
            priority_vars=(
                "priority_vars_matched",
                lambda s: ",".join(sorted(
                    set(v for x in s if x for v in str(x).split(",") if v)
                )),
            ),
        )
        .reset_index()
        .sort_values("season", na_position="last")
    )
