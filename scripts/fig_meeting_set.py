"""Full presentation set for Patricia: track maps and SST/latitude profiles for
Aurora (AADC 1990-2020), Nuyina (V8-corrected), and the combined record.
Six figures, PNG + vector PDF."""
from pathlib import Path
import re, glob
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import cartopy.crs as ccrs, cartopy.feature as cfeature

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO/"data/processed/ship"
DSET = REPO/"outputs/datasets_for_aadc"
OUT  = REPO/"outputs/figures/ship"
EXTENT = [27, 180, -72, -28]
AURORA_COL, NUYINA_COL = "#CC6677", "#332288"
TOL = ["#332288","#88CCEE","#117733","#DDCC77","#CC6677","#AA4499","#44AA99",
       "#882255","#661100","#6699CC","#AA4466","#4477AA","#228833","#CCBB44",
       "#EE7733","#009988","#BBBBBB","#EE3377"]

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
GAP_NOTE = ("Note: ~21-month gap (Mar 2020 \u2013 Dec 2021) during vessel changeover;\n"
            "the two vessels are different instruments and do not overlap in time.")

def fmt_voyage(v):
    m = re.match(r"^(.*?)[_-](\d{4})[_-](\d{2,4})$", str(v))
    if not m: return str(v).replace("_"," ")
    code,y1,y2 = m.groups(); y1 = int(y1)
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
        ax.add_feature(cfeature.NaturalEarthFeature("physical",
            "antarctic_ice_shelves_polys","50m", facecolor="#DCEAF2",
            edgecolor="0.7", linewidth=0.3), zorder=1)
    except Exception as e:
        print(f"  ice layer skipped ({e})")
    ax.add_feature(cfeature.COASTLINE, linewidth=0.4, edgecolor="0.5", zorder=2)
    gl = ax.gridlines(draw_labels=True, linewidth=0.3, color="0.7", alpha=0.5)
    gl.top_labels = gl.right_labels = False
    gl.xlabel_style = {"size":11}; gl.ylabel_style = {"size":11}
    for nm,lo,la in STATIONS:
        if EXTENT[0]<=lo<=EXTENT[1] and EXTENT[2]<=la<=EXTENT[3]:
            ax.plot(lo,la,marker="*",color="black",markersize=11,
                    transform=ccrs.PlateCarree(),zorder=7)
            dx,dy = OFFSETS.get(nm,(5,4))
            ax.annotate(nm,(lo,la),xytext=(dx,dy),textcoords="offset points",
                        transform=ccrs.PlateCarree(),fontsize=10.5,fontweight="bold",zorder=8)
    for nm,lo,la in CONTINENTS:
        ax.text(lo,la,nm,fontsize=14,fontweight="bold",color="0.45",ha="center",
                transform=ccrs.PlateCarree(),zorder=8)
    for nm,lo,la in FEATURES:
        if EXTENT[0]<=lo<=EXTENT[1] and EXTENT[2]<=la<=EXTENT[3]:
            ax.annotate(nm,(lo,la),xytext=(0,9),textcoords="offset points",
                        transform=ccrs.PlateCarree(),fontsize=8,color="#1a3a6b",
                        style="italic",ha="center",zorder=6)

def seg(g):
    lon = g.longitude.to_numpy(float); lat = g.latitude.to_numpy(float)
    brk = np.where(np.hypot(np.diff(lon), np.diff(lat)) > 2.0)[0]
    return np.insert(lon,brk+1,np.nan), np.insert(lat,brk+1,np.nan)

def load():
    a = pd.read_parquet(PROC/"eampB_aurora_aadc_long_1990-2020.parquet")
    if "vessel" not in a: a["vessel"] = "Aurora Australis"
    nf = sorted(glob.glob(str(DSET/"EAMP_Nuyina_underway_*.parquet")))[-1]
    n = pd.read_parquet(nf); print(f"  Nuyina: {Path(nf).name}")
    if "vessel" not in n: n["vessel"] = "RSV Nuyina"
    bad = (n.voyage.astype(str) == "2022-23_V8") & (n.variable=="sst_degC")
    if bad.any(): n = n[~bad]; print(f"  excluded {bad.sum():,} V8 SST rows")
    cols = ["vessel","voyage","datetime","latitude","longitude","variable","value"]
    a, n = a[cols], n[cols]
    for d in (a,n): d["datetime"] = pd.to_datetime(d["datetime"])
    return a, n, pd.concat([a,n], ignore_index=True)

def track_map(df, name, title_stub, mode):
    # positions from ALL variables: a failed thermometer does not invalidate the GPS
    pos = (df[["vessel","voyage","datetime","latitude","longitude"]]
             .drop_duplicates(["vessel","voyage","datetime"])
             .sort_values(["vessel","voyage","datetime"]))
    pos["year"] = pos.datetime.dt.year
    years = sorted(pos.year.unique()); y0,y1 = min(years), max(years)
    norm = plt.Normalize(y0,y1)
    fig = plt.figure(figsize=(15,9)); ax = plt.axes(projection=ccrs.PlateCarree()); base_map(ax)
    if mode == "vessel":
        for ves,col in [("Aurora Australis",AURORA_COL),("RSV Nuyina",NUYINA_COL)]:
            for v,g in pos[pos.vessel==ves].groupby("voyage"):
                lo,la = seg(g); ax.plot(lo,la,color=col,lw=0.45,alpha=0.55,
                                        transform=ccrs.PlateCarree(),zorder=5)
        nv = pos.groupby("vessel").voyage.nunique()
        ax.legend(handles=[
            Line2D([0],[0],color=AURORA_COL,lw=2.5,
                   label=f"Aurora Australis 1990\u20132020 ({nv.get('Aurora Australis',0)} voyages)"),
            Line2D([0],[0],color=NUYINA_COL,lw=2.5,
                   label=f"RSV Nuyina 2021\u20132026 ({nv.get('RSV Nuyina',0)} voyages)")],
            loc="upper left", bbox_to_anchor=(1.02,1.0), fontsize=11,
            title="Vessel", title_fontsize=12)
        extra = "one colour per vessel"
    elif mode == "voyage":
        vs = sorted(pos.voyage.unique()); cmap = {v:TOL[i%len(TOL)] for i,v in enumerate(vs)}
        for v,g in pos.groupby("voyage"):
            lo,la = seg(g); ax.plot(lo,la,color=cmap[v],lw=0.9,alpha=0.85,
                                    transform=ccrs.PlateCarree(),zorder=5)
        ncol = 1 if len(vs)<=16 else 2
        ax.legend(handles=[Line2D([0],[0],color=cmap[v],lw=2.2,label=fmt_voyage(v)) for v in vs],
                  loc="upper left", bbox_to_anchor=(1.02,1.0), fontsize=8,
                  title="Voyage", title_fontsize=11, ncol=ncol)
        extra = "coloured by voyage"
    else:
        for (v,y),g in pos.groupby(["voyage","year"]):
            lo,la = seg(g); ax.plot(lo,la,color=plt.cm.viridis(norm(y)),lw=0.5,alpha=0.7,
                                    transform=ccrs.PlateCarree(),zorder=5)
        plt.colorbar(plt.cm.ScalarMappable(cmap="viridis",norm=norm),
                     ax=ax, shrink=0.6, pad=0.02, label="Year")
        extra = "coloured by year"
    ax.set_title(f"{title_stub} voyage tracks, {y0}\u2013{y1}\n"
                 f"{pos.voyage.nunique()} voyages  \u00b7  {len(pos):,} positions  \u00b7  {extra}",
                 fontsize=15)
    save_fig(fig, name); plt.close(fig)

def sst_profile(df, name, title_stub, gap=False):
    s = df[df.variable=="sst_degC"].dropna(subset=["latitude","value"]).copy()
    s = s[s.latitude.between(-72,-28) & s.value.between(-2.5,25)]
    s["year"] = s.datetime.dt.year
    s["lat_bin"] = np.floor(s.latitude/0.5)*0.5 + 0.25
    s["vlabel"] = s.voyage.map(fmt_voyage)
    years = sorted(s.year.unique()); y0,y1 = min(years), max(years)
    norm = plt.Normalize(y0,y1)
    fig, ax = plt.subplots(figsize=(13,8)); drawn = 0
    for (v,y),g in s.groupby(["vlabel","year"]):
        p = g.groupby("lat_bin").value.mean().sort_index()
        if len(p) > 3:
            ax.plot(p.index,p.values,color=plt.cm.viridis(norm(y)),lw=0.85,alpha=0.72); drawn+=1
    ax.set_xlabel("Latitude (\u00b0)",fontsize=13)
    ax.set_ylabel("Sea surface temperature (\u00b0C)",fontsize=13)
    ax.invert_xaxis(); ax.grid(alpha=0.3)
    plt.colorbar(plt.cm.ScalarMappable(cmap="viridis",norm=norm), ax=ax, label="Year")
    ax.set_title(f"{title_stub} sea surface temperature vs latitude, by voyage\n"
                 f"{y0}\u2013{y1}  \u00b7  {s.voyage.nunique()} voyages ({drawn} lines)  \u00b7  "
                 f"{len(s):,} observations", fontsize=14)
    if gap:
        ax.text(0.99,0.02,GAP_NOTE,transform=ax.transAxes,ha="right",va="bottom",
                fontsize=8,style="italic",color="0.35")
    save_fig(fig, name); plt.close(fig)

def main():
    aurora, nuyina, combined = load()
    print("\nAurora:");   track_map(aurora,"MEET_aurora_tracks_1990-2020","Aurora Australis","year")
    # SST profiles now come solely from fig_meeting_profiles.py
    print("Nuyina:");     track_map(nuyina,"MEET_nuyina_tracks_2021-2026","RSV Nuyina","voyage")

    print("Combined:");   track_map(combined,"MEET_combined_tracks_1990-2026",
                                    "Aurora Australis + RSV Nuyina","vessel")


if __name__ == "__main__":
    main()
