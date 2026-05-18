"""Inventory and metadata extraction for the downloaded AODN ship datasets.

Walks the aodn_downloads directory tree, identifies the NetCDF files for
each vessel and sub-facility, opens each file to read its metadata, and
produces a consolidated inventory suitable for the audit deliverable.
"""
import re
from pathlib import Path
from typing import Optional

import pandas as pd
import xarray as xr

from eamp.common.logging import get_logger

logger = get_logger(__name__)

# Sub-facility identifiers as embedded in the AODN file naming convention.
# The SOOP-BA, SOOP-BGC, SOOP-XBT, and SOOP-ASF tokens appear in the filename
# and identify which AODN product each file belongs to.
SUBFACILITY_TOKENS = {
    "SOOP-BA": "bioacoustics",
    "SOOP-BGC": "biogeochemical",
    "SOOP-XBT": "xbt",
    "SOOP-ASF": "asf",
}

VESSEL_TOKENS = {
    "VNAA": "Aurora Australis",
    "VNRS": "Nuyina",
    "Aurora-Australis": "Aurora Australis",
    "Nuyina": "Nuyina",
}


def parse_filename(path: Path) -> dict:
    """Extract metadata fields encoded in an AODN NetCDF filename.

    AODN file naming follows IMOS_SOOP-XX_TT_YYYYMMDDTHHMMSSZ_VESSEL_FVnn_*.
    The function returns a dictionary of best-effort parsed fields plus the
    sub-facility tag identified from the path.
    """
    name = path.name
    parts = name.split("_")

    metadata = {
        "filename": name,
        "filepath": str(path),
        "subfacility": None,
        "vessel": None,
        "start_time": None,
        "end_time": None,
        "file_version": None,
    }

    for token, label in SUBFACILITY_TOKENS.items():
        if token in name:
            metadata["subfacility"] = label
            break

    for token, vessel in VESSEL_TOKENS.items():
        if token in name:
            metadata["vessel"] = vessel
            break

    start_match = re.search(r"(\d{8}T\d{6}Z)", name)
    if start_match:
        try:
            metadata["start_time"] = pd.to_datetime(
                start_match.group(1), format="%Y%m%dT%H%M%SZ"
            )
        except ValueError:
            pass

    end_match = re.search(r"END-(\d{8}T\d{6}Z)", name)
    if end_match:
        try:
            metadata["end_time"] = pd.to_datetime(
                end_match.group(1), format="%Y%m%dT%H%M%SZ"
            )
        except ValueError:
            pass

    fv_match = re.search(r"_(FV\d{2})_", name)
    if fv_match:
        metadata["file_version"] = fv_match.group(1)

    return metadata


def read_netcdf_metadata(path: Path) -> dict:
    """Open a NetCDF file and extract a summary of its variables and dimensions.

    Returns a dictionary with the variable list, the geographic extent if
    latitude and longitude variables are present, and the temporal extent
    if a time variable is present. Returns an empty dict if the file cannot
    be opened.
    """
    metadata = {
        "variables": None,
        "n_variables": None,
        "lat_min": None,
        "lat_max": None,
        "lon_min": None,
        "lon_max": None,
        "time_min": None,
        "time_max": None,
        "n_records": None,
    }

    try:
        with xr.open_dataset(path, decode_times=True) as ds:
            metadata["variables"] = ",".join(sorted(ds.data_vars))
            metadata["n_variables"] = len(ds.data_vars)

            for lat_name in ("LATITUDE", "latitude", "lat"):
                if lat_name in ds.variables:
                    metadata["lat_min"] = float(ds[lat_name].min())
                    metadata["lat_max"] = float(ds[lat_name].max())
                    break

            for lon_name in ("LONGITUDE", "longitude", "lon"):
                if lon_name in ds.variables:
                    metadata["lon_min"] = float(ds[lon_name].min())
                    metadata["lon_max"] = float(ds[lon_name].max())
                    break

            for time_name in ("TIME", "time"):
                if time_name in ds.variables:
                    time_values = ds[time_name].values
                    metadata["time_min"] = pd.Timestamp(time_values.min())
                    metadata["time_max"] = pd.Timestamp(time_values.max())
                    metadata["n_records"] = len(time_values)
                    break
    except Exception as exc:
        logger.warning("Could not open %s: %s", path.name, exc)

    return metadata


def build_inventory(downloads_root: Path) -> pd.DataFrame:
    """Walk the aodn_downloads tree and build the consolidated inventory.

    Each row of the returned DataFrame represents one NetCDF file with the
    filename-parsed metadata and the file-internal metadata combined.
    """
    nc_files = sorted(downloads_root.rglob("*.nc"))
    logger.info("Found %d NetCDF files under %s", len(nc_files), downloads_root)

    rows = []
    for i, path in enumerate(nc_files, start=1):
        if i % 100 == 0:
            logger.info("Processed %d / %d files", i, len(nc_files))
        filename_meta = parse_filename(path)
        file_meta = read_netcdf_metadata(path)
        rows.append({**filename_meta, **file_meta,
                     "size_bytes": path.stat().st_size})

    return pd.DataFrame(rows)
