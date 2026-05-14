"""Column-name and value harmonisation for the colony observation sheets."""
import re
from typing import Optional

import pandas as pd


COLUMN_RENAMES = {
    "date": "observation_date",
    "lat": "latitude",
    "long": "longitude",
    "surface": "surface_type",
    "open water distance (km)": "open_water_distance_km",
    "comments": "comments",
}

DISTANCE_FROM_LAST_VARIANTS = {
    "distance from last (km)",
    "km from previous",
    "dist since last (km)",
}

NON_STANDARD_SHEETS = {"16. Shackelton Ice Shelf"}

SURFACE_TYPE_CANONICAL = {
    "fast ice": "fast_ice",
    "fastice": "fast_ice",
    "fast-ice": "fast_ice",
    "ice tongue": "ice_tongue",
    "icetongue": "ice_tongue",
    "iceberg": "iceberg",
    "berg": "iceberg",
    "open water": "open_water",
    "ow": "open_water",
    "land": "land",
    "ice shelf": "ice_shelf",
}


def parse_colony_name(sheet_name: str) -> tuple[int, str]:
    match = re.match(r"^\s*(\d+)\.\s+(.+?)\s*$", sheet_name)
    if not match:
        raise ValueError(f"Unrecognised sheet name format: {sheet_name!r}")
    return int(match.group(1)), match.group(2).strip()


def parse_surface_type(value) -> Optional[str]:
    if pd.isna(value):
        return None
    text = str(value).strip().lower()
    return SURFACE_TYPE_CANONICAL.get(text, text)


def harmonise_columns(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    normalised_lookup = {col: str(col).strip().lower() for col in df.columns}

    rename_map = {}
    drop_cols = []
    for raw_col, normalised in normalised_lookup.items():
        if normalised in COLUMN_RENAMES:
            rename_map[raw_col] = COLUMN_RENAMES[normalised]
        elif normalised in DISTANCE_FROM_LAST_VARIANTS:
            drop_cols.append(raw_col)

    df = df.rename(columns=rename_map)
    if drop_cols:
        df = df.drop(columns=drop_cols)

    required = {"observation_date", "latitude", "longitude", "surface_type"}
    if not required.issubset(df.columns):
        return None

    for canonical_col in COLUMN_RENAMES.values():
        if canonical_col not in df.columns:
            df[canonical_col] = pd.NA

    df["observation_date"] = pd.to_datetime(df["observation_date"], errors="coerce")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["open_water_distance_km"] = pd.to_numeric(
        df["open_water_distance_km"], errors="coerce"
    )
    df["surface_type"] = df["surface_type"].apply(parse_surface_type)
    df["comments"] = df["comments"].astype("string").fillna("")

    return df[list(COLUMN_RENAMES.values())]
