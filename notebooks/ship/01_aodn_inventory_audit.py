# %% [markdown]
# # AODN inventory audit for Workstream B
#
# This notebook analyses the consolidated AODN inventory produced by the
# ship inventory pipeline and generates summary visualisations for the
# 19 May meeting with Patricia.

# %%
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from eamp.common import config

DATE_TAG = date.today().isoformat()

# %% [markdown]
# ## 1. Load the consolidated inventory

# %%
candidates = sorted(
    config.SHIP_PROCESSED.glob("eampB_aodn_inventory_*.parquet")
)
if not candidates:
    raise FileNotFoundError(
        "No inventory Parquet files found. Run scripts/run_ship_inventory.py first."
    )
inventory_path = candidates[-1]
inv = pd.read_parquet(inventory_path)
print(f"Loaded {len(inv):,} files from {inventory_path.name}")
print(f"Columns: {list(inv.columns)}")
inv.head()

# %% [markdown]
# ## 2. Vessel and sub-facility composition

# %%
composition = (
    inv.groupby(["vessel", "subfacility"])
    .agg(
        n_files=("filename", "size"),
        total_size_mb=("size_bytes", lambda s: s.sum() / 1e6),
        earliest_obs=("start_time", "min"),
        latest_obs=("end_time", "max"),
    )
    .reset_index()
    .sort_values(["vessel", "subfacility"])
)
print(composition.to_string(index=False))

# %% [markdown]
# ## 3. Temporal coverage per vessel and sub-facility

# %%
fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True)

for ax, vessel in zip(axes, ["Aurora Australis", "Nuyina"]):
    subset = inv[inv["vessel"] == vessel].copy()
    subset = subset.dropna(subset=["start_time", "end_time"])

    subfacilities = sorted(subset["subfacility"].dropna().unique())
    colors = plt.cm.tab10.colors
    color_map = {sub: colors[i % len(colors)] for i, sub in enumerate(subfacilities)}

    for i, sub in enumerate(subfacilities):
        sub_data = subset[subset["subfacility"] == sub]
        ax.hlines(
            y=[i] * len(sub_data),
            xmin=sub_data["start_time"],
            xmax=sub_data["end_time"],
            colors=color_map[sub],
            linewidth=2.5,
            alpha=0.7,
            label=f"{sub} (n={len(sub_data)})",
        )

    ax.set_yticks(range(len(subfacilities)))
    ax.set_yticklabels(subfacilities)
    ax.set_title(f"{vessel} — AODN voyage coverage by sub-facility", fontsize=11)
    ax.grid(True, axis="x", alpha=0.3)
    ax.legend(loc="upper left", fontsize=8, frameon=True)

axes[-1].set_xlabel("Year")
axes[-1].xaxis.set_major_locator(mdates.YearLocator(2))
axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

plt.tight_layout()
config.SHIP_FIGURES.mkdir(parents=True, exist_ok=True)
temporal_path = config.SHIP_FIGURES / f"eampB_temporal_coverage_{DATE_TAG}.png"
plt.savefig(temporal_path, dpi=160, bbox_inches="tight", facecolor="white")
print(f"Temporal coverage figure saved: {temporal_path}")
plt.show()

# %% [markdown]
# ## 4. Geographic coverage map

# %%
geo = inv.dropna(subset=["lat_min", "lat_max", "lon_min", "lon_max"]).copy()
geo["lat_centroid"] = (geo["lat_min"] + geo["lat_max"]) / 2
geo["lon_centroid"] = (geo["lon_min"] + geo["lon_max"]) / 2

fig = plt.figure(figsize=(11, 11), dpi=120)
ax = plt.axes(projection=ccrs.SouthPolarStereo())
ax.set_extent([-180, 180, -90, -40], crs=ccrs.PlateCarree())

land_50m = cfeature.NaturalEarthFeature(
    category="physical", name="land", scale="50m",
    edgecolor="none", facecolor="#e8e4d8",
)
ocean_50m = cfeature.NaturalEarthFeature(
    category="physical", name="ocean", scale="50m",
    edgecolor="none", facecolor="#cfe2ef",
)
coastline_50m = cfeature.NaturalEarthFeature(
    category="physical", name="coastline", scale="50m",
    edgecolor="#5a6678", facecolor="none", linewidth=0.5,
)
ax.add_feature(land_50m)
ax.add_feature(ocean_50m)
ax.add_feature(coastline_50m)
ax.gridlines(draw_labels=False, linewidth=0.4, color="#9aa6b8",
             alpha=0.5, linestyle="--")

vessel_colors = {"Aurora Australis": "#c0392b", "Nuyina": "#2980b9"}
for vessel, color in vessel_colors.items():
    vessel_geo = geo[geo["vessel"] == vessel]
    if len(vessel_geo) > 0:
        ax.scatter(
            vessel_geo["lon_centroid"], vessel_geo["lat_centroid"],
            transform=ccrs.PlateCarree(),
            s=10, c=color, alpha=0.4, edgecolors="none",
            label=f"{vessel} (n={len(vessel_geo):,})",
        )

ax.legend(loc="lower left", fontsize=10, frameon=True, framealpha=0.95)
ax.set_title(
    "AODN Workstream B holdings — voyage centroids (2002–2026)\n"
    "Aurora Australis (decommissioned 2019) and RSV Nuyina (in service 2021–)",
    fontsize=12, pad=14,
)

geo_path = config.SHIP_FIGURES / f"eampB_geographic_coverage_{DATE_TAG}.png"
plt.savefig(geo_path, dpi=180, bbox_inches="tight", facecolor="white")
print(f"Geographic coverage figure saved: {geo_path}")
plt.show()

# %% [markdown]
# ## 5. Summary table for the 19 May meeting

# %%
meeting_summary = {
    "Total AODN files audited": f"{len(inv):,}",
    "Total disk volume": f"{inv['size_bytes'].sum() / 1e9:.2f} GB",
    "Aurora Australis files": int((inv["vessel"] == "Aurora Australis").sum()),
    "Nuyina files": int((inv["vessel"] == "Nuyina").sum()),
    "Sub-facilities covered": inv["subfacility"].nunique(),
    "Aurora Australis temporal coverage": (
        f"{inv[inv['vessel'] == 'Aurora Australis']['start_time'].min().date()} to "
        f"{inv[inv['vessel'] == 'Aurora Australis']['end_time'].max().date()}"
    ),
    "Nuyina temporal coverage": (
        f"{inv[inv['vessel'] == 'Nuyina']['start_time'].min().date()} to "
        f"{inv[inv['vessel'] == 'Nuyina']['end_time'].max().date()}"
    ),
}
for label, value in meeting_summary.items():
    print(f"  {label:<45}  {value}")
