"""Two demo figures on the extended 1990-2020 Aurora record."""
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import cartopy.crs as ccrs, cartopy.feature as cfeature

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
df = pd.read_parquet(REPO/"data/processed/ship/eampB_aurora_aadc_long_1990-2020.parquet")
df["year"] = df.datetime.dt.year
OUT = REPO/"outputs/figures/ship"; OUT.mkdir(parents=True, exist_ok=True)
years = sorted(df.year.unique())
cmap = plt.cm.viridis(np.linspace(0,1,len(years)))
ycol = dict(zip(years, cmap))

# --- 1. track map, full period ---
pos = df[df.variable=="sst_degC"][["voyage","year","latitude","longitude"]]
fig = plt.figure(figsize=(15,9))
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent([35,180,-72,-28], crs=ccrs.PlateCarree())
ax.add_feature(cfeature.LAND, facecolor="0.92")
ax.add_feature(cfeature.COASTLINE, linewidth=0.4, edgecolor="0.5")
gl = ax.gridlines(draw_labels=True, linewidth=0.3, color="0.7", alpha=0.5)
gl.top_labels = gl.right_labels = False
for (v,y), g in pos.groupby(["voyage","year"]):
    ax.plot(g.longitude, g.latitude, color=ycol[y], lw=0.5, alpha=0.7,
            transform=ccrs.PlateCarree())
sm = plt.cm.ScalarMappable(cmap="viridis",
        norm=plt.Normalize(min(years), max(years)))
plt.colorbar(sm, ax=ax, shrink=0.6, label="Year")
ax.set_title(f"Aurora Australis voyage tracks ({min(years)}\u2013{max(years)})", fontsize=15)
fig.savefig(OUT/"DEMO_aurora_tracks_1990_2020.png", dpi=180, bbox_inches="tight")
plt.close(fig); print("saved track map")

# --- 2. SST vs latitude, coloured by year ---
sst = df[df.variable=="sst_degC"].copy()
sst["lat_bin"] = np.floor(sst.latitude/0.5)*0.5 + 0.25
fig, ax = plt.subplots(figsize=(13,8))
for y, g in sst.groupby("year"):
    p = g.groupby("lat_bin").value.mean().sort_index()
    if len(p) > 3: ax.plot(p.index, p.values, color=ycol[y], lw=1.1, alpha=0.85)
ax.set_xlabel("Latitude (\u00b0)", fontsize=13)
ax.set_ylabel("Sea surface temperature (\u00b0C)", fontsize=13)
ax.invert_xaxis(); ax.grid(alpha=0.3)
sm = plt.cm.ScalarMappable(cmap="viridis", norm=plt.Normalize(min(years), max(years)))
plt.colorbar(sm, ax=ax, label="Year")
ax.set_title(f"Aurora Australis sea surface temperature vs latitude, by year ({min(years)}\u2013{max(years)})",
             fontsize=14)
fig.savefig(OUT/"DEMO_aurora_sst_latitude_by_year.png", dpi=180, bbox_inches="tight")
plt.close(fig); print("saved SST/latitude figure")
