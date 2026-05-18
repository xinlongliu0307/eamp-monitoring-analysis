"""Diagnostic script for the northeastern coastal anomaly Patricia flagged.

Identifies colonies whose stored coordinates plot a long way from the nearest
coastline polygon at 50m Natural Earth resolution. Each candidate colony is
reported with its stored coordinates, the distance to the nearest coast in
kilometres, and the coordinates of the closest coast point, so the reason for
the offshore appearance can be diagnosed concretely.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np
import pandas as pd
import cartopy.io.shapereader as shpreader
from shapely.geometry import Point, MultiPolygon
from shapely.ops import unary_union, nearest_points

from eamp.common import config


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def main():
    # Load both datasets
    obs_candidates = sorted(
        config.PENGUIN_PROCESSED.glob("eampA_colony_observations_long_*.parquet")
    )
    obs = pd.read_parquet(obs_candidates[-1])
    obs_summary = (
        obs.groupby("colony_name")
        .agg(latitude=("latitude", "mean"), longitude=("longitude", "mean"))
        .reset_index()
    )
    obs_summary["source"] = "observational"

    inventory_path = config.PENGUIN_RAW / config.PENGUIN_INVENTORY_FILE
    inventory = pd.read_excel(inventory_path, sheet_name=0, header=1, engine="openpyxl")
    inventory = inventory.rename(
        columns={"Colony": "colony_name", "Lat": "latitude", "Long": "longitude"}
    )
    inventory = inventory.dropna(subset=["latitude", "longitude"])
    inventory["source"] = "inventory"
    inventory = inventory[["colony_name", "latitude", "longitude", "source"]]

    all_colonies = pd.concat([obs_summary, inventory], ignore_index=True)

    # Sanity audit on the coordinate fields themselves
    print("=== Coordinate range audit ===")
    print(f"  Latitude  min/max: {all_colonies['latitude'].min():.3f} / "
          f"{all_colonies['latitude'].max():.3f}")
    print(f"  Longitude min/max: {all_colonies['longitude'].min():.3f} / "
          f"{all_colonies['longitude'].max():.3f}")
    suspect_lat = all_colonies[
        (all_colonies["latitude"] > -50) | (all_colonies["latitude"] < -85)
    ]
    suspect_lon = all_colonies[
        (all_colonies["longitude"] < -180) | (all_colonies["longitude"] > 180)
    ]
    print(f"  Colonies with suspect latitude (outside -85 to -50): {len(suspect_lat)}")
    print(f"  Colonies with suspect longitude (outside -180 to 180): {len(suspect_lon)}")
    if len(suspect_lat) > 0:
        print(suspect_lat.to_string(index=False))
    if len(suspect_lon) > 0:
        print(suspect_lon.to_string(index=False))

    # Load 50m coastline as a single multipolygon
    print("\n=== Loading 50m Antarctic coastline ===")
    shp_path = shpreader.natural_earth(
        resolution="50m", category="physical", name="land"
    )
    reader = shpreader.Reader(shp_path)
    antarctic_polys = [
        g for g in reader.geometries()
        if g.bounds[1] < -60  # any polygon extending south of 60S
    ]
    antarctica = unary_union(antarctic_polys)
    print(f"  Loaded {len(antarctic_polys)} polygons south of 60S")

    # Compute distance to coast for each colony
    print("\n=== Distance to nearest coast (50m) for each colony ===")
    distances = []
    for _, row in all_colonies.iterrows():
        pt = Point(row["longitude"], row["latitude"])
        nearest_on_land = nearest_points(pt, antarctica)[1]
        d_km = haversine_km(
            row["latitude"], row["longitude"],
            nearest_on_land.y, nearest_on_land.x,
        )
        distances.append({
            "colony_name": row["colony_name"],
            "source": row["source"],
            "stored_lat": row["latitude"],
            "stored_lon": row["longitude"],
            "nearest_coast_lat": nearest_on_land.y,
            "nearest_coast_lon": nearest_on_land.x,
            "distance_km": d_km,
        })
    dist_df = pd.DataFrame(distances).sort_values("distance_km", ascending=False)

    # Report colonies more than 20 km from the nearest coast
    print(f"\n  Total colonies: {len(dist_df)}")
    print(f"  Mean distance to coast: {dist_df['distance_km'].mean():.1f} km")
    print(f"  Median: {dist_df['distance_km'].median():.1f} km")
    print(f"  Maximum: {dist_df['distance_km'].max():.1f} km")
    print()
    print("=== Colonies > 20 km from coast (candidates for Patricia's flagged point) ===")
    far_offshore = dist_df[dist_df["distance_km"] > 20]
    print(far_offshore.to_string(index=False))

    # Save full diagnostic
    output_path = config.PENGUIN_PROCESSED / "eampA_colony_coast_distance_diagnostic.xlsx"
    dist_df.to_excel(output_path, index=False, engine="openpyxl")
    print(f"\nFull diagnostic saved: {output_path}")


if __name__ == "__main__":
    main()
