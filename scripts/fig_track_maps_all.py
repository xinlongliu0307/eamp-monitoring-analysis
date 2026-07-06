"""Track maps for Patricia's matrix:
 - Aurora: full extent + Australia-Antarctica focus
 - Nuyina: Australia-Antarctica focus
 - Combined: one colour per vessel
Single-vessel maps coloured by year (Paul Tol muted, colourblind-safe);
combined map uses one colour per vessel. Rich Antarctic labelling."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.lines import Line2D
import cartopy.crs as ccrs
import cartopy.feature as cfeature

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO / "data/processed/ship"
OUT = REPO / "outputs/figures/ship"

def save_fig(fig, name):
    """Save a figure as both PNG (raster, 200 dpi) and PDF (vector) in OUT.
    `name` is the base filename without extension."""
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.png", dpi=200, bbox_inches="tight")
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    print(f"  Saved: {name}.png + {name}.pdf")

FOCUS = [35, 165, -72, -38]          # Australia-Antarctica corridor
FULL  = [35, 180, -72, -28]          # Patricia crop: W of Syowa tracks to 180E, N past Perth        # whole extent (for Aurora full map)
TOL = ["#332288","#88CCEE","#117733","#DDCC77","#CC6677","#AA4499","#44AA99",
       "#882255","#661100","#6699CC","#AA4466","#4477AA","#228833","#CCBB44"]

STATIONS = [("Hobart",147.33,-42.88),("Mawson",62.87,-67.60),("Davis",77.97,-68.58),
            ("Casey",110.53,-66.28),("Macquarie Is.",158.94,-54.50),
            ("Heard Is.",73.50,-53.10),("Dumont d'Urville",140.0,-66.66),
            ("Fremantle",115.74,-32.06),
            ("Syowa",39.59,-69.01)]
CONTINENTS = [("AUSTRALIA",133,-40),("ANTARCTICA",95,-70.5)]
FEATURES = [("Amery Ice Shelf",71.0,-66.5),("Shackleton Ice Shelf",96.0,-62.5),
            ("Totten Glacier",117.0,-63.5),("Mertz Glacier",145.0,-63.5),
            ("Ross Ice Shelf",178.0,-76.5)]

def add_north_arrow(ax):
    ax.annotate("N", xy=(0.97, 0.92), xytext=(0.97, 0.83),
                arrowprops=dict(facecolor="black", width=4, headwidth=12),
                ha="center", va="center", fontsize=13, fontweight="bold",
                xycoords=ax.transAxes)

def add_scale_bar(ax, extent, km=1000):
    # approximate scale bar at the given latitude (degrees of lon per km varies)
    lat_mid = (extent[2]+extent[3])/2
    km_per_deg = 111.32 * np.cos(np.radians(lat_mid))
    deg = km / km_per_deg
    x0 = extent[0] + (extent[1]-extent[0])*0.06
    y0 = extent[2] + (extent[3]-extent[2])*0.08
    ax.plot([x0, x0+deg], [y0, y0], color="black", linewidth=3,
            transform=ccrs.PlateCarree(), zorder=9)
    ax.text(x0+deg/2, y0+ (extent[3]-extent[2])*0.02, f"{km} km",
            ha="center", fontsize=9, transform=ccrs.PlateCarree(), zorder=9)

def base_map(ax, extent, rich=True):
    ax.set_extent(extent, crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND, facecolor="0.92", zorder=0)
    try:
        ice = cfeature.NaturalEarthFeature("physical","antarctic_ice_shelves_polys",
                "50m", facecolor="#DCEAF2", edgecolor="0.7", linewidth=0.3)
        ax.add_feature(ice, zorder=1)
    except Exception as e:
        print(f"  ice layer skipped ({e})")
    ax.add_feature(cfeature.COASTLINE, linewidth=0.4, edgecolor="0.5", zorder=2)
    gl = ax.gridlines(draw_labels=True, linewidth=0.3, color="0.7", alpha=0.5)
    gl.top_labels = gl.right_labels = False
    gl.xlabel_style = {"size": 11}; gl.ylabel_style = {"size": 11}
    # per-station label offsets to avoid collisions (dx,dy in points)
    OFFSETS = {"Mawson":(-38,-2),"Davis":(6,-12),"Casey":(6,6),
               "Dumont d'Urville":(6,-12),"Fremantle":(6,6),"Syowa":(6,6),
               "Hobart":(6,4),"Macquarie Is.":(6,2),"Heard Is.":(6,4)}
    for nm,lo,la in STATIONS:
        if extent[0] <= lo <= extent[1] and extent[2] <= la <= extent[3]:
            ax.plot(lo,la,marker="*",color="black",markersize=11,
                    transform=ccrs.PlateCarree(),zorder=7)
            dx,dy = OFFSETS.get(nm,(5,4))
            ax.annotate(nm,(lo,la),xytext=(dx,dy),textcoords="offset points",
                        transform=ccrs.PlateCarree(),fontsize=11,fontweight="bold",zorder=8)
    for nm,lo,la in CONTINENTS:
        if extent[0] <= lo <= extent[1] and extent[2] <= la <= extent[3]:
            ax.text(lo,la,nm,fontsize=14,fontweight="bold",color="0.45",
                    ha="center",transform=ccrs.PlateCarree(),zorder=8)
    if rich:
        for nm,lo,la in FEATURES:
            if extent[0] <= lo <= extent[1] and extent[2] <= la <= extent[3]:
                ax.annotate(nm,(lo,la),xytext=(0,10),textcoords="offset points",
                            transform=ccrs.PlateCarree(),fontsize=8,
                            color="#1a3a6b",style="italic",ha="center",zorder=6,
                            bbox=dict(boxstyle="round,pad=0.1",fc="white",ec="none",alpha=0.6))

def load(which):
    f = sorted(PROC.glob(f"eampB_{which}_long_*.parquet"))[-1]
    df = pd.read_parquet(f, columns=["voyage","datetime","latitude","longitude"])
    df = df.drop_duplicates(["voyage","datetime"]).dropna(subset=["latitude","longitude"])
    df["year"] = pd.to_datetime(df["datetime"]).dt.year
    return df.sort_values(["voyage","datetime"])

def draw_tracks_by_year(ax, df):
    years = sorted(df["year"].unique())
    ycol = {y: TOL[i % len(TOL)] for i,y in enumerate(years)}
    for (voyage,yr), g in df.groupby(["voyage","year"]):
        lon,lat = g["longitude"].to_numpy(float), g["latitude"].to_numpy(float)
        brk = np.where(np.hypot(np.diff(lon),np.diff(lat))>2.0)[0]
        lon,lat = np.insert(lon,brk+1,np.nan), np.insert(lat,brk+1,np.nan)
        ax.plot(lon,lat,color=ycol[yr],linewidth=0.9,alpha=0.8,
                transform=ccrs.PlateCarree(),zorder=5)
    return [Line2D([0],[0],color=ycol[y],lw=2.5,label=str(y)) for y in years]

def one_map_voyages(df, extent, title, outname, rich=True):
    """Like one_map but legend lists each voyage (with year), coloured by year."""
    fig = plt.figure(figsize=(15,11))
    ax = plt.axes(projection=ccrs.PlateCarree())
    base_map(ax, extent, rich=rich)
    years = sorted(df["year"].unique())
    ycol = {y: TOL[i % len(TOL)] for i,y in enumerate(years)}
    handles = []
    for (voyage,yr), g in df.groupby(["voyage","year"]):
        lon,lat = g["longitude"].to_numpy(float), g["latitude"].to_numpy(float)
        brk = np.where(np.hypot(np.diff(lon),np.diff(lat))>2.0)[0]
        lon,lat = np.insert(lon,brk+1,np.nan), np.insert(lat,brk+1,np.nan)
        ax.plot(lon,lat,color=ycol[yr],linewidth=0.9,alpha=0.8,
                transform=ccrs.PlateCarree(),zorder=5)
        vid = str(voyage); vlabel = vid.split("_",1)[1] if "_" in vid else vid
        handles.append(Line2D([0],[0],color=ycol[yr],lw=2.0,label=f"{vlabel} ({yr})"))
    ncol = 1 if len(handles) <= 16 else 2
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.14,1.0),
              fontsize=7.5, title="Voyage (year)", title_fontsize=10, ncol=ncol)
    ax.text(0.02, 0.04, f"{df['voyage'].nunique()} voyages", transform=ax.transAxes,
            fontsize=10, style="italic", color="0.3",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="0.7", alpha=0.85))
    ax.set_title(title, fontsize=15)
    OUT.mkdir(parents=True, exist_ok=True)
    save_fig(fig, outname.replace(".png",""))
    plt.close(fig)

def one_map(df, extent, title, outname, rich=True):
    fig = plt.figure(figsize=(15,11))
    ax = plt.axes(projection=ccrs.PlateCarree())
    base_map(ax, extent, rich=rich)
    handles = draw_tracks_by_year(ax, df)
    ncol = 1 if len(handles) <= 14 else 2
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.14,1.0),
              fontsize=9, title="Year", title_fontsize=11, ncol=ncol)
    ax.text(0.02, 0.04, f"{df['voyage'].nunique()} voyages", transform=ax.transAxes,
            fontsize=10, style="italic", color="0.3",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="0.7", alpha=0.85))
    ax.set_title(title, fontsize=15)
    OUT.mkdir(parents=True, exist_ok=True)
    save_fig(fig, outname.replace(".png",""))
    plt.close(fig)

def main():
    aurora = load("aurora"); nuyina = load("nuyina")

    print("Aurora full extent:")
    one_map(aurora, FULL, "Aurora Australis voyage tracks (2008\u20132020) \u2014 East Antarctic\u2013Australian sector\nColoured by year", "eampB_aurora_track_full_byyear.png", rich=True)
    print("Aurora focus:")
    one_map(aurora, FOCUS, "Aurora Australis voyage tracks (2008\u20132020)\nAustralia\u2013Antarctica; coloured by year", "eampB_aurora_track_focus_byyear.png")
    print("Nuyina focus (voyage legend):")
    one_map_voyages(nuyina, FOCUS, "RSV Nuyina voyage tracks (2021\u20132025)\nAustralia\u2013Antarctica; coloured by year, labelled by voyage", "eampB_nuyina_track_focus_byyear.png")

    # combined: one colour per vessel
    print("Combined (by vessel):")
    fig = plt.figure(figsize=(15,11))
    ax = plt.axes(projection=ccrs.PlateCarree())
    base_map(ax, FOCUS, rich=True)
    for df, col, name in [(aurora,"#CC6677","Aurora Australis (2008\u201320)"),
                          (nuyina,"#332288","RSV Nuyina (2021\u201325)")]:
        for (voyage,yr), g in df.groupby(["voyage","year"]):
            lon,lat = g["longitude"].to_numpy(float), g["latitude"].to_numpy(float)
            brk = np.where(np.hypot(np.diff(lon),np.diff(lat))>2.0)[0]
            lon,lat = np.insert(lon,brk+1,np.nan), np.insert(lat,brk+1,np.nan)
            ax.plot(lon,lat,color=col,linewidth=0.7,alpha=0.6,
                    transform=ccrs.PlateCarree(),zorder=5)
    handles = [Line2D([0],[0],color="#CC6677",lw=2.5,label="Aurora Australis (2008\u201320)"),
               Line2D([0],[0],color="#332288",lw=2.5,label="RSV Nuyina (2021\u201325)")]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.14,1.0),
              fontsize=11, title="Vessel", title_fontsize=12)
    ax.set_title("Aurora Australis + RSV Nuyina voyage tracks\nAustralia\u2013Antarctica; one colour per vessel", fontsize=15)
    save_fig(fig, "eampB_combined_track_byvessel")
    print("  Saved: eampB_combined_track_byvessel.png"); plt.close(fig)

    # combined map, full circumpolar extent (same boundaries as Aurora full map)
    print("Combined (full extent, by vessel):")
    fig = plt.figure(figsize=(16,10))
    ax = plt.axes(projection=ccrs.PlateCarree())
    base_map(ax, FULL, rich=False)
    for df, col in [(aurora,"#CC6677"), (nuyina,"#332288")]:
        for (voyage,yr), g in df.groupby(["voyage","year"]):
            lon,lat = g["longitude"].to_numpy(float), g["latitude"].to_numpy(float)
            brk = np.where(np.hypot(np.diff(lon),np.diff(lat))>2.0)[0]
            lon,lat = np.insert(lon,brk+1,np.nan), np.insert(lat,brk+1,np.nan)
            ax.plot(lon,lat,color=col,linewidth=0.7,alpha=0.6,
                    transform=ccrs.PlateCarree(),zorder=5)
    handles = [Line2D([0],[0],color="#CC6677",lw=2.5,label="Aurora Australis (2008\u201320)"),
               Line2D([0],[0],color="#332288",lw=2.5,label="RSV Nuyina (2021\u201325)")]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.14,1.0),
              fontsize=11, title="Vessel", title_fontsize=12)
    ax.set_title("Aurora Australis + RSV Nuyina voyage tracks\nFull circumpolar extent; one colour per vessel", fontsize=15)
    save_fig(fig, "eampB_combined_track_full_byvessel")
    print("  Saved: eampB_combined_track_full_byvessel.png"); plt.close(fig)

if __name__ == "__main__":
    main()
