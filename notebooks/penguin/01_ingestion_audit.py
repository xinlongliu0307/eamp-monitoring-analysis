# %% [markdown]
# # Ingestion audit and first-pass visualisation
#
# This notebook audits the consolidated colony observations dataset produced
# by the ingestion pipeline, quantifies the two data-quality findings recorded
# in the decisions directory, and generates the first-pass circumpolar map
# combining the 26-colony observational record with the 71-colony 2025
# circumpolar inventory.

# %%
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from eamp.common import config

DATE_TAG = date.today().isoformat()
TODAY = pd.Timestamp.today().normalize()
REALISTIC_START = pd.Timestamp("2018-01-01")
REALISTIC_END = TODAY

# %% [markdown]
# ## 1. Load the most recent consolidated dataset

# %%
candidates = sorted(
    config.PENGUIN_PROCESSED.glob("eampA_colony_observations_long_*.parquet")
)
if not candidates:
    raise FileNotFoundError(
        f"No processed Parquet files found in {config.PENGUIN_PROCESSED}. "
        f"Run scripts/run_penguin_ingestion.py first."
    )
parquet_path = candidates[-1]
obs_all = pd.read_parquet(parquet_path)
print(f"Loaded {len(obs_all):,} observations from {parquet_path.name}")
print(f"Columns: {list(obs_all.columns)}")
obs_all.head()

# %% [markdown]
# ## 2. Apply temporal filter to exclude out-of-range dates

# %%
in_range_mask = (
    (obs_all["observation_date"] >= REALISTIC_START)
    & (obs_all["observation_date"] <= REALISTIC_END)
)
obs = obs_all.loc[in_range_mask].copy()
out_of_range = obs_all.loc[~in_range_mask].copy()

print(f"Realistic window: {REALISTIC_START.date()} to {REALISTIC_END.date()}")
print(f"  Observations within window:  {len(obs):,}")
print(f"  Observations outside window: {len(out_of_range)}")
print(f"  Filtered dataset date range: "
      f"{obs['observation_date'].min().date()} to "
      f"{obs['observation_date'].max().date()}")

# %% [markdown]
# ## 3. Load the circumpolar 2025 inventory

# %%
inventory_path = config.PENGUIN_RAW / config.PENGUIN_INVENTORY_FILE
inventory = pd.read_excel(
    inventory_path, sheet_name=0, header=1, engine="openpyxl"
)
inventory = inventory.rename(
    columns={"Colony": "colony_name", "Date": "observation_date",
             "Lat": "latitude", "Long": "longitude"}
)
inventory["observation_date"] = pd.to_datetime(
    inventory["observation_date"], errors="coerce"
)
inventory = inventory.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)
print(f"Loaded {len(inventory)} circumpolar colony locations from inventory")
inventory.head()

# %% [markdown]
# ## 4. Observations per colony (filtered dataset)

# %%
per_colony = (
    obs.groupby("colony_name")
    .agg(
        n_observations=("observation_date", "size"),
        first_observation=("observation_date", "min"),
        last_observation=("observation_date", "max"),
    )
    .sort_values("n_observations", ascending=False)
)
per_colony["record_duration_years"] = (
    per_colony["last_observation"] - per_colony["first_observation"]
).dt.days / 365.25
print(per_colony.to_string())

# %% [markdown]
# ## 5. Out-of-range date audit

# %%
print(f"Rows with dates outside the expected window: {len(out_of_range)}")
print()
print(out_of_range[["colony_name", "observation_date", "source_sheet"]].to_string())

# %% [markdown]
# ## 6. Surface type frequency

# %%
PRIORITY_CATEGORIES = {
    "fast_ice": "Fast ice (seasonal sea ice attached to shore)",
    "ice_floe": "Floating ice floe (free-floating sea ice)",
    "iceberg": "Iceberg (grounded or drifting freshwater ice)",
    "glacier_ice": "Glacier ice or ice tongue (floating glacier extension)",
    "ice_shelf": "Ice shelf (permanent floating ice extension of inland ice)",
}

surface_counts = obs["surface_type"].value_counts(dropna=False)
priority_mask = surface_counts.index.isin(PRIORITY_CATEGORIES.keys())

print("=== Priority categories ===")
for cat, description in PRIORITY_CATEGORIES.items():
    count = surface_counts.get(cat, 0)
    print(f"  {cat:>15}  {count:>5}  {description}")

print()
print("=== Other observed values (frequency >= 5) ===")
others = surface_counts[~priority_mask].sort_values(ascending=False)
for value, count in others.items():
    if count >= 5:
        print(f"  {str(value):>20}  {count:>5}")

print()
print(f"Total observations covered by priority categories: "
      f"{surface_counts[priority_mask].sum():,}")
print(f"Total observations in 'other' or null categories: "
      f"{surface_counts[~priority_mask].sum():,}")

# %% [markdown]
# ## 7. Circumpolar visualisation

# %%
obs_summary = (
    obs.groupby("colony_name")
    .agg(
        latitude=("latitude", "mean"),
        longitude=("longitude", "mean"),
        n_observations=("observation_date", "size"),
        first_observation=("observation_date", "min"),
        last_observation=("observation_date", "max"),
    )
    .reset_index()
)
obs_summary["record_duration_years"] = (
    obs_summary["last_observation"] - obs_summary["first_observation"]
).dt.days / 365.25

obs_names = set(obs_summary["colony_name"].str.lower().str.strip())
inventory["_match_key"] = inventory["colony_name"].str.lower().str.strip()
inventory_only = inventory[~inventory["_match_key"].isin(obs_names)].copy()

print(f"Observational colonies: {len(obs_summary)}")
print(f"Inventory-only colonies: {len(inventory_only)}")
print(f"Record duration range: "
      f"{obs_summary['record_duration_years'].min():.1f} to "
      f"{obs_summary['record_duration_years'].max():.1f} years")

# %%
fig = plt.figure(figsize=(11, 11), dpi=120)
ax = plt.axes(projection=ccrs.SouthPolarStereo())
ax.set_extent([-180, 180, -90, -55], crs=ccrs.PlateCarree())

ax.add_feature(cfeature.LAND, facecolor="#e8e4d8", edgecolor="none")
ax.add_feature(cfeature.OCEAN, facecolor="#cfe2ef", edgecolor="none")
ax.add_feature(cfeature.COASTLINE, linewidth=0.6, edgecolor="#5a6678")
ax.gridlines(
    draw_labels=False, linewidth=0.4, color="#9aa6b8",
    alpha=0.5, linestyle="--",
)

ax.scatter(
    inventory_only["longitude"], inventory_only["latitude"],
    transform=ccrs.PlateCarree(),
    s=28, marker="o", facecolors="none",
    edgecolors="#6a7a8c", linewidths=0.9,
    label=f"Inventory-only colonies (n={len(inventory_only)})",
    zorder=4,
)

size_min, size_max = 50, 280
sizes = np.interp(
    obs_summary["n_observations"],
    (obs_summary["n_observations"].min(), obs_summary["n_observations"].max()),
    (size_min, size_max),
)

sc = ax.scatter(
    obs_summary["longitude"], obs_summary["latitude"],
    transform=ccrs.PlateCarree(),
    s=sizes, c=obs_summary["record_duration_years"],
    cmap="viridis",
    vmin=obs_summary["record_duration_years"].min(),
    vmax=obs_summary["record_duration_years"].max(),
    edgecolors="#1f3a5f", linewidths=0.6,
    alpha=0.9, zorder=5,
    label=f"Observational colonies (n={len(obs_summary)})",
)

cbar = plt.colorbar(sc, ax=ax, orientation="horizontal", pad=0.05, shrink=0.7)
cbar.set_label("Record duration (years between first and last observation)", fontsize=10)

size_legend_values = [
    int(obs_summary["n_observations"].min()),
    int(obs_summary["n_observations"].median()),
    int(obs_summary["n_observations"].max()),
]
size_legend_sizes = np.interp(
    size_legend_values,
    (obs_summary["n_observations"].min(), obs_summary["n_observations"].max()),
    (size_min, size_max),
)
for val, sz in zip(size_legend_values, size_legend_sizes):
    ax.scatter(
        [], [], s=sz, c="grey", edgecolors="#1f3a5f", linewidths=0.6,
        alpha=0.9, label=f"  {val:,} observations",
    )

ax.legend(
    loc="lower left", fontsize=9, frameon=True, framealpha=0.95,
    title="Legend (point size = observation count)",
    title_fontsize=10,
)

ax.set_title(
    "Emperor penguin colonies — East Antarctic observational record (2018–2025)\n"
    "with the all-Antarctic circumpolar inventory (2025 snapshot) for context",
    fontsize=13, pad=14,
)

config.PENGUIN_FIGURES.mkdir(parents=True, exist_ok=True)
figure_path = (
    config.PENGUIN_FIGURES / f"eampA_circumpolar_overview_{DATE_TAG}.png"
)
plt.savefig(figure_path, dpi=180, bbox_inches="tight", facecolor="white")
print(f"Figure saved: {figure_path}")
plt.show()

# %% [markdown]
# ## 8. Summary export for the Wednesday email

# %%
summary = {
    "Total observations (raw)": f"{len(obs_all):,}",
    "Observations within realistic window": f"{len(obs):,}",
    "Out-of-range observations (excluded from visualisation)": len(out_of_range),
    "Colonies in observational record": obs["colony_name"].nunique(),
    "Colonies in 2025 circumpolar inventory": len(inventory),
    "Surface types observed (distinct, filtered)": obs["surface_type"].nunique(dropna=False),
    "Observations in 5 priority surface categories": int(
        surface_counts[priority_mask].sum()
    ),
    "Date range (filtered observational record)": (
        f"{obs['observation_date'].min().date()} to "
        f"{obs['observation_date'].max().date()}"
    ),
    "Record duration range (years)": (
        f"{obs_summary['record_duration_years'].min():.1f} to "
        f"{obs_summary['record_duration_years'].max():.1f}"
    ),
}
for label, value in summary.items():
    print(f"  {label:<55}  {value}")
