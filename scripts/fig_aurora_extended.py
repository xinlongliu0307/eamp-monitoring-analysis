"""Extended Aurora figures (1990-2020): labelled track map + SST/latitude by voyage.
Outputs PNG and vector PDF."""
from pathlib import Path
import re
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import cartopy.crs as ccrs, cartopy.feature as cfeature

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
OUT  = REPO/"outputs/figures/ship"
EXTENT = [27, 180, -72, -28]

STATIONS = [("Hobart",147.33,-42.88),("Mawson",62.87,-67.60),("Davis",77.97,-68.58),
            ("Casey",110.53,-66.28),("Macquarie Is.",158.94,-54.50),
            ("Heard Is.",73.50,-53.10),("Dumont d'Urville",140.0,-66.66),
            ("Fremantle",115.74,-32.06),("Syowa",39.59,-69.01),
            ("Molodyozhnaya",45.85,-67.67),("Burnie",145.90,-41.05)]
OFFSETS = {"Mawson":(-40,-2),"Davis":(6,-13),"Casey":(6,6),"Dumont d'Urville":(6,-13),
           "Fremantle":(6,6),"Syowa":(4,-13),"Molodyozhnaya":(6,4),"Hobart":(6,4),
           "Macquarie Is.":(6,2),"Heard Is.":(6,4),"Burnie":(-42,4)}
CONTINENTS = [("AUSTRALIA",133,-40),("ANTARCTICA",100,-70.5)]
# western features verified against the SCAR/AAD gazetteer
FEATURES = [("Princess Ragnhild Coast",30.0,-69.9),("Riiser-Larsen Pen.",34.0,-68.4),
            ("L\u00fctzow-Holm Bay",37.6,-67.7),("Amery Ice Shelf",71.0,-66.5),
            ("Shackleton Ice Shelf",96.0,-62.5),("Totten Glacier",117.0,-63.5),
            ("Mertz Glacier",145.0,-63.5),("Ross Ice Shelf",178.0,-76.5)]

def fmt_voyage(v):
    """'V1_1993_94' -> 'V1 1993-1994'."""
    m = re.match(r"^(.*?)[_-](\d{4})[_-](\d{2,4})$", str(v))
    if not m: return str(v).replace("_"," ")
    code, y1, y2 = m.groups(); y1 = int(y1)
    y2 = int(y2) if len(y2)==4 else (y1//100 + (1 if int(y2) < y1%100 else 0))*100 + int(y2)
    return f"{code.replace('_',' ')} {y1}-{y2}"

def save_fig(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT/f"{name}.png", dpi=200, bbox_inches="tight")
    fig.savefig(OUT/f"{name}.pdf", bbox_inches="tight")
    print(f"  Saved: {name}.png + {name}.pdf")

def base_map(ax):
    ax.set_extent(EXTENT, crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND, facecolor="0.92", zorder=0)
    try:
        ice = cfeature.NaturalEarthFeature("physical","antarctic_ice_shelves_polys","50m",
                facecolor="#DCEAF2", edgecolor="0.7", linewidth=0.3)
        ax.add_feature(ice, zorder=1)
    except Exception as e:
        print(f"  ice layer skipped ({e})")
    ax.add_feature(cfeature.COASTLINE, linewidth=0.4, edgecolor="0.5", zorder=2)
    gl = ax.gridlines(draw_labels=True, linewidth=0.3, color="0.7", alpha=0.5)
    gl.top_labels = gl.right_labels = False
    gl.xlabel_style = {"size":11}; gl.ylabel_style = {"size":11}
    for nm,lo,la in STATIONS:
        if EXTENT[0] <= lo <= EXTENT[1] and EXTENT[2] <= la <= EXTENT[3]:
            ax.plot(lo,la,marker="*",color="black",markersize=11,
                    transform=ccrs.PlateCarree(),zorder=7)
            dx,dy = OFFSETS.get(nm,(5,4))
            ax.annotate(nm,(lo,la),xytext=(dx,dy),textcoords="offset points",
                        transform=ccrs.PlateCarree(),fontsize=10.5,fontweight="bold",zorder=8)
    for nm,lo,la in CONTINENTS:
        ax.text(lo,la,nm,fontsize=14,fontweight="bold",color="0.45",ha="center",
                transform=ccrs.PlateCarree(),zorder=8)
    for nm,lo,la in FEATURES:
        if EXTENT[0] <= lo <= EXTENT[1] and EXTENT[2] <= la <= EXTENT[3]:
            ax.annotate(nm,(lo,la),xytext=(0,9),textcoords="offset points",
                        transform=ccrs.PlateCarree(),fontsize=8,color="#1a3a6b",
                        style="italic",ha="center",zorder=6)

def main():
    df = pd.read_parquet(REPO/"data/processed/ship/eampB_aurora_aadc_long_1990-2020.parquet")
    df["year"] = df.datetime.dt.year
    years = sorted(df.year.unique())
    norm = plt.Normalize(min(years), max(years))
    ycol = {y: plt.cm.viridis(norm(y)) for y in years}
    y0, y1 = min(years), max(years)

    # ---------- track map ----------
    pos = (df[df.variable=="sst_degC"][["voyage","year","datetime","latitude","longitude"]]
             .sort_values(["voyage","datetime"]))
    nv = pos.voyage.nunique(); npos = len(pos)
    fig = plt.figure(figsize=(15,9))
    ax = plt.axes(projection=ccrs.PlateCarree())
    base_map(ax)
    for (v,y), g in pos.groupby(["voyage","year"]):
        lon = g.longitude.to_numpy(float); lat = g.latitude.to_numpy(float)
        brk = np.where(np.hypot(np.diff(lon), np.diff(lat)) > 2.0)[0]
        lon = np.insert(lon, brk+1, np.nan); lat = np.insert(lat, brk+1, np.nan)
        ax.plot(lon, lat, color=ycol[y], lw=0.5, alpha=0.7,
                transform=ccrs.PlateCarree(), zorder=5)
    plt.colorbar(plt.cm.ScalarMappable(cmap="viridis", norm=norm),
                 ax=ax, shrink=0.6, pad=0.02, label="Year")
    ax.set_title(f"Aurora Australis voyage tracks, {y0}\u2013{y1}\n"
                 f"{nv} voyages  \u00b7  {npos:,} positions  \u00b7  coloured by year",
                 fontsize=15)
    save_fig(fig, "eampB_aurora_extended_tracks_1990-2020"); plt.close(fig)

    # ---------- SST vs latitude, one line per voyage ----------
    sst = df[df.variable=="sst_degC"].copy()
    sst["lat_bin"] = np.floor(sst.latitude/0.5)*0.5 + 0.25
    sst["vlabel"] = sst.voyage.map(fmt_voyage)
    nobs = len(sst); nvs = sst.voyage.nunique()
    fig, ax = plt.subplots(figsize=(13,8))
    drawn = 0
    for (v,y), g in sst.groupby(["vlabel","year"]):
        p = g.groupby("lat_bin").value.mean().sort_index()
        if len(p) > 3:
            ax.plot(p.index, p.values, color=ycol[y], lw=0.9, alpha=0.75); drawn += 1
    ax.set_xlabel("Latitude (\u00b0)", fontsize=13)
    ax.set_ylabel("Sea surface temperature (\u00b0C)", fontsize=13)
    ax.invert_xaxis(); ax.grid(alpha=0.3)
    plt.colorbar(plt.cm.ScalarMappable(cmap="viridis", norm=norm), ax=ax, label="Year")
    ax.set_title(f"Aurora Australis sea surface temperature vs latitude, by voyage\n"
                 f"{y0}\u2013{y1}  \u00b7  {nvs} voyages ({drawn} lines)  \u00b7  {nobs:,} observations",
                 fontsize=14)
    save_fig(fig, "eampB_aurora_extended_sst_latitude_1990-2020"); plt.close(fig)
    print(f"  track map: {nv} voyages, {npos:,} positions")
    print(f"  SST plot:  {nvs} voyages, {drawn} lines, {nobs:,} observations")

if __name__ == "__main__":
    main()
