"""Combined Aurora Australis (AADC 1990-2020) + RSV Nuyina (2021-2026):
labelled track map and SST/latitude by voyage. PNG + vector PDF.
NOTE: uses the AADC Aurora record only; it supersedes the older AODN file."""
from pathlib import Path
import re, glob
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import cartopy.crs as ccrs, cartopy.feature as cfeature

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO/"data/processed/ship"
OUT  = REPO/"outputs/figures/ship"
EXTENT = [27, 180, -72, -28]
AURORA_COL, NUYINA_COL = "#CC6677", "#332288"

STATIONS = [("Hobart",147.33,-42.88),("Mawson",62.87,-67.60),("Davis",77.97,-68.58),
            ("Casey",110.53,-66.28),("Macquarie Is.",158.94,-54.50),
            ("Heard Is.",73.50,-53.10),("Dumont d'Urville",140.0,-66.66),
            ("Fremantle",115.74,-32.06),("Syowa",39.59,-69.01),
            ("Molodyozhnaya",45.85,-67.67),("Burnie",145.90,-41.05)]
OFFSETS = {"Mawson":(-40,-2),"Davis":(6,-13),"Casey":(6,6),"Dumont d'Urville":(6,-13),
           "Fremantle":(6,6),"Syowa":(4,-13),"Molodyozhnaya":(6,4),"Hobart":(6,4),
           "Macquarie Is.":(6,2),"Heard Is.":(6,4),"Burnie":(-42,4)}
CONTINENTS = [("AUSTRALIA",133,-40),("ANTARCTICA",100,-70.5)]
FEATURES = [("Princess Ragnhild Coast",30.0,-69.9),("Riiser-Larsen Pen.",34.0,-68.4),
            ("L\u00fctzow-Holm Bay",37.6,-67.7),("Amery Ice Shelf",71.0,-66.5),
            ("Shackleton Ice Shelf",96.0,-62.5),("Totten Glacier",117.0,-63.5),
            ("Mertz Glacier",145.0,-63.5),("Ross Ice Shelf",178.0,-76.5)]

def fmt_voyage(v):
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

def load():
    a = pd.read_parquet(PROC/"eampB_aurora_aadc_long_1990-2020.parquet")
    if "vessel" not in a: a["vessel"] = "Aurora Australis"
    cand = sorted(glob.glob(str(REPO/"outputs/datasets_for_aadc/EAMP_Nuyina_underway_*.parquet"))) \
        or sorted(glob.glob(str(PROC/"eampB_nuyina_long_*with_v2*.parquet")))
    n = pd.read_parquet(cand[-1])
    print(f"  Nuyina from: {Path(cand[-1]).name}")
    if "vessel" not in n: n["vessel"] = "RSV Nuyina"
    if "source" not in n: n["source"] = "AADC"
    cols = ["vessel","voyage","datetime","latitude","longitude","variable","value","source"]
    df = pd.concat([a[cols], n[cols]], ignore_index=True)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["year"] = df.datetime.dt.year
    return df

def main():
    df = load()
    print(f"combined rows: {len(df):,}")
    print(df.groupby("vessel").agg(n=("value","size"),
          start=("datetime","min"), end=("datetime","max")).to_string())
    years = sorted(df.year.unique()); y0, y1 = min(years), max(years)
    norm = plt.Normalize(y0, y1)

    # ---------- combined track map: one colour per vessel ----------
    pos = (df[df.variable=="sst_degC"][["vessel","voyage","datetime","latitude","longitude"]]
             .sort_values(["vessel","voyage","datetime"]))
    nv = pos.groupby("vessel").voyage.nunique()
    fig = plt.figure(figsize=(15,9))
    ax = plt.axes(projection=ccrs.PlateCarree()); base_map(ax)
    for ves, col in [("Aurora Australis",AURORA_COL), ("RSV Nuyina",NUYINA_COL)]:
        for v, g in pos[pos.vessel==ves].groupby("voyage"):
            lon = g.longitude.to_numpy(float); lat = g.latitude.to_numpy(float)
            brk = np.where(np.hypot(np.diff(lon), np.diff(lat)) > 2.0)[0]
            lon = np.insert(lon, brk+1, np.nan); lat = np.insert(lat, brk+1, np.nan)
            ax.plot(lon, lat, color=col, lw=0.45, alpha=0.55,
                    transform=ccrs.PlateCarree(), zorder=5)
    handles = [Line2D([0],[0],color=AURORA_COL,lw=2.5,
                      label=f"Aurora Australis 1990\u20132020 ({nv.get('Aurora Australis',0)} voyages)"),
               Line2D([0],[0],color=NUYINA_COL,lw=2.5,
                      label=f"RSV Nuyina 2021\u20132026 ({nv.get('RSV Nuyina',0)} voyages)")]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02,1.0),
              fontsize=11, title="Vessel", title_fontsize=12)
    ax.set_title(f"Aurora Australis + RSV Nuyina voyage tracks, {y0}\u2013{y1}\n"
                 f"{int(nv.sum())} voyages  \u00b7  {len(pos):,} positions  \u00b7  one colour per vessel",
                 fontsize=15)
    save_fig(fig, "eampB_combined_extended_tracks_1990-2026"); plt.close(fig)

    # ---------- combined SST vs latitude, one line per voyage, coloured by year ----------
    sst = df[df.variable=="sst_degC"].copy()
    sst["lat_bin"] = np.floor(sst.latitude/0.5)*0.5 + 0.25
    sst["vlabel"] = sst.voyage.map(fmt_voyage)
    fig, ax = plt.subplots(figsize=(13,8))
    drawn = 0
    for (ves, v, y), g in sst.groupby(["vessel","vlabel","year"]):
        p = g.groupby("lat_bin").value.mean().sort_index()
        if len(p) > 3:
            ax.plot(p.index, p.values, color=plt.cm.viridis(norm(y)),
                    lw=0.85, alpha=0.72); drawn += 1
    ax.set_xlabel("Latitude (\u00b0)", fontsize=13)
    ax.set_ylabel("Sea surface temperature (\u00b0C)", fontsize=13)
    ax.invert_xaxis(); ax.grid(alpha=0.3)
    plt.colorbar(plt.cm.ScalarMappable(cmap="viridis", norm=norm), ax=ax, label="Year")
    nvs = sst.groupby("vessel").voyage.nunique().sum()
    ax.set_title(f"Aurora Australis + RSV Nuyina sea surface temperature vs latitude, by voyage\n"
                 f"{y0}\u2013{y1}  \u00b7  {nvs} voyages ({drawn} lines)  \u00b7  {len(sst):,} observations",
                 fontsize=14)
    ax.text(0.99,0.02,"Note: ~21-month gap (Mar 2020 \u2013 Dec 2021) during vessel changeover;\n"
            "the two vessels are different instruments and do not overlap in time.",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=8,
            style="italic", color="0.35")
    save_fig(fig, "eampB_combined_extended_sst_latitude_1990-2026"); plt.close(fig)

if __name__ == "__main__":
    main()
