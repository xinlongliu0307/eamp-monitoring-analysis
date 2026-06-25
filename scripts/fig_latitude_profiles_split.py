"""Latitude profiles split two ways, mirroring the track-map split:
 (1) coloured by austral season  (Okabe-Ito categorical)
 (2) coloured by season-year     (Paul Tol muted categorical)
Value (y) vs latitude (x), one line per voyage. Tasmania left, Antarctica right."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO / "data/processed/ship"
OUT = REPO / "outputs/figures/ship"

VARS = {
    "sst_degC":      ("Sea surface temperature (\u00b0C)", (-2, 20)),
    "sss":           ("Sea surface salinity",              (32.5, 35.5)),
    "air_temp_degC": ("Air temperature (\u00b0C)",          (-25, 25)),
}
LAT_BIN = 0.5

# Okabe-Ito for the four austral seasons (matches the seasonal track map)
SEASON_COLOURS = {"Summer (DJF)": "#E69F00", "Autumn (MAM)": "#009E73",
                  "Winter (JJA)": "#0072B2", "Spring (SON)": "#CC79A7"}
def austral_season(m):
    return ("Summer (DJF)" if m in (12,1,2) else "Autumn (MAM)" if m in (3,4,5)
            else "Winter (JJA)" if m in (6,7,8) else "Spring (SON)")
# Paul Tol 'muted' for season-years (matches the voyage track map)
TOL = ["#332288","#88CCEE","#117733","#DDCC77","#CC6677","#AA4499","#44AA99","#882255"]
def season_of(v): return v.split("_")[0]

def build_profiles(sub):
    sub = sub.copy()
    sub["lat_bin"] = (np.floor(sub["latitude"]/LAT_BIN)*LAT_BIN) + LAT_BIN/2
    sub["smonth"] = pd.to_datetime(sub["datetime"]).dt.month
    return sub

def main():
    src = sorted(PROC.glob("eampB_nuyina_long_*.parquet"))[-1]
    print(f"Reading: {src.name}")
    df = pd.read_parquet(src)

    for var, (label, (vmin, vmax)) in VARS.items():
        sub = df[df["variable"]==var].dropna(subset=["latitude","value","datetime"]).copy()
        if var == "sss":
            sub = sub[sub["value"] > 1]
        sub = sub[(sub["value"]>vmin-5)&(sub["value"]<vmax+10)]
        sub = sub[(sub["latitude"]>-72)&(sub["latitude"]<-38)]
        if sub.empty:
            print(f"{var}: no data"); continue
        sub = build_profiles(sub)
        voyages = sorted(sub["voyage"].unique())
        seasons = sorted({season_of(v) for v in voyages})
        tol_col = {s: TOL[i % len(TOL)] for i, s in enumerate(seasons)}

        # ---- (1) coloured by AUSTRAL SEASON ----
        fig, ax = plt.subplots(figsize=(13, 8))
        for voyage in voyages:
            g = sub[sub["voyage"]==voyage]
            prof = g.groupby("lat_bin")["value"].mean()
            if len(prof) < 3: continue
            # season of this voyage = modal month's season
            seas = austral_season(int(g["smonth"].mode().iloc[0]))
            prof = prof.sort_index()
            ax.plot(prof.index, prof.values, color=SEASON_COLOURS[seas],
                    linewidth=1.3, alpha=0.8)
        ax.set_xlabel("Latitude (\u00b0)", fontsize=13); ax.set_ylabel(label, fontsize=13)
        ax.set_ylim(vmin, vmax); ax.invert_xaxis(); ax.grid(alpha=0.3)
        ax.set_title(f"RSV Nuyina {label} vs latitude \u2014 by austral season\n"
                     "Each line = one voyage; colour = season (colourblind-safe)", fontsize=14)
        handles = [Line2D([0],[0], color=c, lw=2.5, label=s) for s,c in SEASON_COLOURS.items()]
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01,1.0),
                  fontsize=10, title="Austral season", title_fontsize=11)
        fig.tight_layout()
        o1 = OUT / f"eampB_nuyina_latprofile_{var}_seasonal.png"
        fig.savefig(o1, dpi=200, bbox_inches="tight"); print(f"Saved: {o1}"); plt.close(fig)

        # ---- (2) coloured by SEASON-YEAR ----
        fig, ax = plt.subplots(figsize=(13, 8))
        seen = set()
        for voyage in voyages:
            g = sub[sub["voyage"]==voyage]
            prof = g.groupby("lat_bin")["value"].mean()
            if len(prof) < 3: continue
            s = season_of(voyage); prof = prof.sort_index()
            ax.plot(prof.index, prof.values, color=tol_col[s], linewidth=1.3, alpha=0.8,
                    label=s if s not in seen else None); seen.add(s)
        ax.set_xlabel("Latitude (\u00b0)", fontsize=13); ax.set_ylabel(label, fontsize=13)
        ax.set_ylim(vmin, vmax); ax.invert_xaxis(); ax.grid(alpha=0.3)
        ax.set_title(f"RSV Nuyina {label} vs latitude \u2014 by season-year\n"
                     "Each line = one voyage; colour = year (between-line spread = variability)", fontsize=14)
        handles = [Line2D([0],[0], color=tol_col[s], lw=2.5, label=s) for s in seasons]
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01,1.0),
                  fontsize=10, title="Season-year", title_fontsize=11)
        fig.tight_layout()
        o2 = OUT / f"eampB_nuyina_latprofile_{var}_byyear.png"
        fig.savefig(o2, dpi=200, bbox_inches="tight"); print(f"Saved: {o2}"); plt.close(fig)

if __name__ == "__main__":
    main()
