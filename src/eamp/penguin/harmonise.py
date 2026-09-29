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

# Surface vocabulary. Keys are raw values after lower-casing and collapsing
# whitespace; values are snake_case codes. Only spelling variants are merged;
# distinct descriptions keep distinct codes, and "a/b" compounds become
# "a_and_b". Any value not listed passes through lower-cased (see
# is_known_surface_type). See docs/decisions/2026-09-29-surface-vocabulary.md.
SURFACE_TYPE_CANONICAL = {
    "fast ice": "fast_ice",
    "fastice": "fast_ice",
    "fast-ice": "fast_ice",
    "fasr ice": "fast_ice",
    "iceberg": "iceberg",
    "ice berg": "iceberg",
    "berg": "iceberg",
    "sm iceberg": "iceberg",
    "floe": "ice_floe",
    "ice floe": "ice_floe",
    "large floe": "ice_floe",
    "glacier ice": "glacier_ice",
    "on glacier ice": "glacier_ice",
    "ice shelf": "ice_shelf",
    "ice tongue": "ice_tongue",
    "icetongue": "ice_tongue",
    "ice slope": "ice_slope",
    "ice ramp": "ice_ramp",
    "ice ramp?": "ice_ramp",
    "thin ice": "thin_ice",
    "new ice": "new_ice",
    "ice": "ice",
    "land": "land",
    "land ice": "land_ice",
    "rock": "rock",
    "gully": "gully",
    "open water": "open_water",
    "ow": "open_water",
    "iceberg/fast ice": "iceberg_and_fast_ice",
    "iceberg/fastice": "iceberg_and_fast_ice",
    "fast ice/iceberg": "iceberg_and_fast_ice",
    "land/ice": "land_and_ice",
    "rock/ice": "rock_and_ice",
}
SURFACE_TYPE_CODES = frozenset(SURFACE_TYPE_CANONICAL.values())


def parse_colony_name(sheet_name: str) -> tuple[int, str]:
    match = re.match(r"^\s*(\d+)\.\s+(.+?)\s*$", sheet_name)
    if not match:
        raise ValueError(f"Unrecognised sheet name format: {sheet_name!r}")
    return int(match.group(1)), match.group(2).strip()


def _surface_key(value) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().lower()


def parse_surface_type(value) -> Optional[str]:
    """Return the snake_case surface code, or the lower-cased value if unknown."""
    if pd.isna(value) or str(value).strip() == "":
        return None
    key = _surface_key(value)
    return SURFACE_TYPE_CANONICAL.get(key, key)


def is_known_surface_type(value) -> bool:
    """True if the raw value maps to a code in the controlled vocabulary."""
    if pd.isna(value) or str(value).strip() == "":
        return True
    return _surface_key(value) in SURFACE_TYPE_CANONICAL


def surface_label(code: Optional[str]) -> Optional[str]:
    """Readable label for a surface code: 'fast_ice' -> 'fast ice',
    'iceberg_and_fast_ice' -> 'iceberg/fast ice'."""
    if code is None:
        return None
    return code.replace("_and_", "/").replace("_", " ")


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
