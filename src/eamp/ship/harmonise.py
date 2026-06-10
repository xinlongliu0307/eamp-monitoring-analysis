"""Harmonise Nuyina new-portal voyage CSVs into one long-format dataset.

Reads the 13 voyage CSVs, selects and renames the eight EAMP priority
variables to a clean canonical schema, attaches per-row completeness
context, and emits a tidy long-format table (one row per voyage x
timestamp x variable) suitable for analysis and plotting.

Variable handling reflects the 8 June verification:
  - air_temp, air_pressure, wind: complete across voyages
  - SST, SSS, oxygen, pH: coherent sensor-suite block, strong from
    2023-24 V2 onward, partial on early commissioning voyages
  - pCO2: present but sparse; carried with coverage flagged, never assumed
"""
import re
from pathlib import Path

import pandas as pd

from eamp.common.logging import get_logger

logger = get_logger(__name__)

FILENAME_PAT = re.compile(
    r"RSV_Nuyina_Voyage_Data_(?P<season>\d{4}-\d{2})_(?P<version>V[A-Z0-9]+)\.csv$"
)

# canonical variable name -> source column in the 99-col schema
PRIORITY_COLUMNS = {
    "sst_degC":        "sea_water_temperature",
    "sss":             "sbe45_salinity",
    "air_temp_degC":   "air_temperature_avg1min_port",
    "air_pressure_hpa": "air_pressure_avg1min",
    "wind_speed":      "wind_speed_true_avg10min_fore_1",
    "wind_dir":        "wind_from_direction_true_avg10min_fore_1",
    "pco2":            "equ_co2_concentration",
    "oxygen":          "mole_concentration_of_dissolved_molecular_oxygen_in_sea_water",
    "ph":              "sea_water_ph_external_seafet",
}
COORD_COLUMNS = {"latitude": "latitude", "longitude": "longitude"}


def parse_voyage(path: Path) -> dict:
    m = FILENAME_PAT.search(path.name)
    return {"season": m.group("season"), "version": m.group("version")} if m else {
        "season": None, "version": None}


def _find_datetime_col(cols) -> str | None:
    return next((c for c in cols if "datetime" in c.lower()), None)


def load_voyage_wide(path: Path) -> pd.DataFrame | None:
    """Load one voyage into a wide frame: time, coords, the 8 priority vars."""
    voyage = parse_voyage(path)
    head = pd.read_csv(path, nrows=0)
    cols = list(head.columns)

    dt_col = _find_datetime_col(cols)
    if dt_col is None:
        logger.warning("%s: no datetime column; skipping", path.name)
        return None

    # resolve which source columns actually exist in this voyage
    present = {canon: src for canon, src in PRIORITY_COLUMNS.items() if src in cols}
    coord_present = {c: s for c, s in COORD_COLUMNS.items() if s in cols}
    usecols = [dt_col] + list(coord_present.values()) + list(present.values())

    df = pd.read_csv(path, usecols=usecols, low_memory=False)
    if len(df) == 0:
        logger.info("%s: header-only (0 rows); skipping", path.name)
        return None

    out = pd.DataFrame()
    out["datetime"] = pd.to_datetime(df[dt_col], errors="coerce")
    for canon, src in coord_present.items():
        out[canon] = pd.to_numeric(df[src], errors="coerce")
    for canon, src in present.items():
        out[canon] = pd.to_numeric(df[src], errors="coerce")
    # any priority var absent from this voyage -> NaN column, so schema is uniform
    for canon in PRIORITY_COLUMNS:
        if canon not in out.columns:
            out[canon] = pd.NA
    
    # Treat physically-impossible zeros as missing (sentinel fill values).
    # Seawater pH, salinity, oxygen and pCO2 are never exactly 0 in valid data.
    ZERO_IS_MISSING = ["ph", "sss", "oxygen", "pco2"]
    for canon in ZERO_IS_MISSING:
        if canon in out.columns:
            n_zero = (out[canon] == 0).sum()
            if n_zero:
                logger.info("%s: %s has %d zero values -> set to NaN",
                            path.name, canon, n_zero)
                out.loc[out[canon] == 0, canon] = pd.NA

    out["season"] = voyage["season"]
    out["version"] = voyage["version"]
    out["voyage"] = f"{voyage['season']}_{voyage['version']}"
    out = out.dropna(subset=["datetime"])
    # Drop implausible timestamps (e.g. source typos like year 0025).
    # Nuyina entered service in 2021; nothing valid predates it or postdates now.
    valid_time = (out["datetime"] >= pd.Timestamp("2021-01-01")) & \
                 (out["datetime"] <= pd.Timestamp.now())
    n_bad = (~valid_time).sum()
    if n_bad:
        logger.warning("%s: dropped %d row(s) with implausible timestamps",
                       path.name, n_bad)
    out = out[valid_time].sort_values("datetime")
    logger.info("%s: %d rows loaded", path.name, len(out))
    return out


def to_long(wide: pd.DataFrame) -> pd.DataFrame:
    """Melt a wide voyage frame to long: one row per time x variable."""
    id_cols = ["voyage", "season", "version", "datetime", "latitude", "longitude"]
    id_cols = [c for c in id_cols if c in wide.columns]
    value_cols = [c for c in PRIORITY_COLUMNS if c in wide.columns]
    long = wide.melt(id_vars=id_cols, value_vars=value_cols,
                     var_name="variable", value_name="value")
    return long


def consolidate(raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load all voyages, return (long_dataset, per-voyage coverage summary)."""
    csvs = sorted(raw_dir.glob("*.csv"))
    logger.info("Found %d voyage CSVs", len(csvs))

    wides, summaries = [], []
    for path in csvs:
        wide = load_voyage_wide(path)
        if wide is None:
            continue
        wides.append(wide)
        # coverage: % non-null per priority variable for this voyage
        n = len(wide)
        row = {"voyage": wide["voyage"].iloc[0], "n_rows": n}
        for canon in PRIORITY_COLUMNS:
            nonnull = wide[canon].notna().sum() if canon in wide else 0
            row[canon] = round(100 * nonnull / n, 1) if n else 0.0
        summaries.append(row)

    if not wides:
        raise RuntimeError("No voyages loaded; check the raw directory.")

    long = pd.concat([to_long(w) for w in wides], ignore_index=True)
    coverage = pd.DataFrame(summaries)
    return long, coverage