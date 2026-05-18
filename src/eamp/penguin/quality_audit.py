"""Standing quality-audit checks for the penguin ingestion pipeline.

These functions are intended to run as part of every ingestion run, surfacing
data-quality anomalies in the consolidated dataset before they reach the
analytical or visualisation stages. Each check returns a pandas DataFrame of
flagged records with sufficient context for a human reviewer to assess the
finding without re-running the source.

The current checks are:

- coast_distance_audit: flag colonies sitting more than a threshold distance
  from the nearest 50 m Natural Earth coastline, which surfaces coordinate
  transposition errors and inventory entries on dynamic ice features.
- date_range_audit: flag observations outside a configurable realistic
  window, which surfaces date-entry typos.
- surface_type_audit: flag observations whose surface_type value is not in
  the canonical priority categories, which surfaces vocabulary drift.
"""
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import cartopy.io.shapereader as shpreader
from shapely.geometry import Point
from shapely.ops import unary_union, nearest_points

from eamp.common.logging import get_logger

logger = get_logger(__name__)


COAST_DISTANCE_THRESHOLD_KM = 25.0
ANTARCTIC_BOUNDS_SOUTH_LIMIT = -60.0
EARTH_RADIUS_KM = 6371.0


def _haversine_km(lat1, lon1, lat2, lon2):
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a = (np.sin(dphi / 2) ** 2
         + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def _load_antarctic_coastline(resolution: str = "50m"):
    """Load and union all Natural Earth land polygons extending south of 60 S."""
    shp_path = shpreader.natural_earth(
        resolution=resolution, category="physical", name="land"
    )
    reader = shpreader.Reader(shp_path)
    antarctic_polys = [
        g for g in reader.geometries()
        if g.bounds[1] < ANTARCTIC_BOUNDS_SOUTH_LIMIT
    ]
    logger.info(
        "Loaded %d Antarctic coastline polygons at %s resolution",
        len(antarctic_polys), resolution,
    )
    return unary_union(antarctic_polys)


def coast_distance_audit(
    df: pd.DataFrame,
    threshold_km: float = COAST_DISTANCE_THRESHOLD_KM,
    resolution: str = "50m",
) -> pd.DataFrame:
    """Flag colonies more than `threshold_km` from the nearest coastline.

    Parameters
    ----------
    df
        DataFrame with columns including colony_name, latitude, longitude.
    threshold_km
        Maximum acceptable distance to coast before flagging.
    resolution
        Natural Earth coastline resolution. Default 50 m matches the
        production visualisation.

    Returns
    -------
    pd.DataFrame
        One row per unique colony, with columns colony_name, stored_lat,
        stored_lon, nearest_coast_lat, nearest_coast_lon, distance_km, and
        flagged (True if distance_km > threshold_km).
    """
    coords = (
        df.dropna(subset=["latitude", "longitude"])
        .groupby("colony_name")
        .agg(stored_lat=("latitude", "mean"),
             stored_lon=("longitude", "mean"))
        .reset_index()
    )
    if coords.empty:
        logger.warning("coast_distance_audit: no coordinates to audit")
        return pd.DataFrame(columns=[
            "colony_name", "stored_lat", "stored_lon",
            "nearest_coast_lat", "nearest_coast_lon",
            "distance_km", "flagged",
        ])

    antarctica = _load_antarctic_coastline(resolution=resolution)

    rows = []
    for _, r in coords.iterrows():
        pt = Point(r["stored_lon"], r["stored_lat"])
        nearest = nearest_points(pt, antarctica)[1]
        d = _haversine_km(
            r["stored_lat"], r["stored_lon"], nearest.y, nearest.x
        )
        rows.append({
            "colony_name": r["colony_name"],
            "stored_lat": r["stored_lat"],
            "stored_lon": r["stored_lon"],
            "nearest_coast_lat": nearest.y,
            "nearest_coast_lon": nearest.x,
            "distance_km": d,
            "flagged": d > threshold_km,
        })

    audit = (
        pd.DataFrame(rows)
        .sort_values("distance_km", ascending=False)
        .reset_index(drop=True)
    )
    n_flagged = int(audit["flagged"].sum())
    logger.info(
        "coast_distance_audit: %d of %d colonies > %.1f km from coast",
        n_flagged, len(audit), threshold_km,
    )
    return audit


def date_range_audit(
    df: pd.DataFrame,
    start: pd.Timestamp = pd.Timestamp("2018-01-01"),
    end: Optional[pd.Timestamp] = None,
) -> pd.DataFrame:
    """Flag observations outside the realistic date window."""
    if end is None:
        end = pd.Timestamp.today().normalize()
    mask = (df["observation_date"] < start) | (df["observation_date"] > end)
    flagged = df.loc[mask, ["colony_name", "observation_date", "source_sheet"]].copy()
    flagged["audit_window_start"] = start
    flagged["audit_window_end"] = end
    logger.info(
        "date_range_audit: %d observations outside %s to %s",
        len(flagged), start.date(), end.date(),
    )
    return flagged


def write_quality_audit_report(
    df: pd.DataFrame,
    output_path: Path,
) -> None:
    """Write a multi-sheet Excel report consolidating all quality audits."""
    coast = coast_distance_audit(df)
    dates = date_range_audit(df)
    consistency = coordinate_consistency_audit(df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        coast.to_excel(writer, sheet_name="coast_distance", index=False)
        dates.to_excel(writer, sheet_name="date_range", index=False)
        consistency.to_excel(writer, sheet_name="coord_consistency", index=False)
    logger.info("Quality audit report written: %s", output_path)


COORDINATE_DIVERGENCE_THRESHOLD_KM = 5.0


def coordinate_consistency_audit(
    df: pd.DataFrame,
    threshold_km: float = COORDINATE_DIVERGENCE_THRESHOLD_KM,
) -> pd.DataFrame:
    """Flag colonies whose mean and median coordinates diverge meaningfully.

    Under normal circumstances the mean and median of a colony's per-observation
    coordinates differ by only a few hundred metres. A divergence of more than
    `threshold_km` indicates that one or more outlier observations are pulling
    the mean away from the median, which is the signature of a coordinate
    transposition, missing sign, or magnitude entry error.
    """
    grouped = (
        df.dropna(subset=["latitude", "longitude"])
        .groupby("colony_name")
        .agg(
            n_observations=("latitude", "size"),
            lat_mean=("latitude", "mean"),
            lat_median=("latitude", "median"),
            lon_mean=("longitude", "mean"),
            lon_median=("longitude", "median"),
        )
        .reset_index()
    )

    if grouped.empty:
        logger.warning("coordinate_consistency_audit: no coordinates to audit")
        return pd.DataFrame(columns=[
            "colony_name", "n_observations",
            "lat_mean", "lat_median", "lon_mean", "lon_median",
            "divergence_km", "flagged",
        ])

    grouped["divergence_km"] = _haversine_km(
        grouped["lat_mean"], grouped["lon_mean"],
        grouped["lat_median"], grouped["lon_median"],
    )
    grouped["flagged"] = grouped["divergence_km"] > threshold_km

    grouped = grouped.sort_values("divergence_km", ascending=False).reset_index(drop=True)
    n_flagged = int(grouped["flagged"].sum())
    logger.info(
        "coordinate_consistency_audit: %d of %d colonies with mean-median divergence > %.1f km",
        n_flagged, len(grouped), threshold_km,
    )
    return grouped
