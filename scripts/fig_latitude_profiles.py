"""Latitude profiles per variable: value (y) vs latitude (x), one line per
voyage, coloured by season-year. This is the latitude-controlled trend view
Patricia sketched - latitude on the x-axis so between-line spread shows the
year-to-year and seasonal variation."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO / "data/processed/ship"
OUT = REPO / "outputs/figures/ship"

VARS = {
    "sst_degC":      ("Sea surface temperature (\u00b0C)", (-2, 20)),
    "sss":           ("Sea surface salinity",              (32.5, 35.5)),
    "air_temp_degC": ("Air temperature (\u00b0C)",          (-25, 25)),
}
LAT_BIN = 0.5   # degrees

def season_of(v): return v.split("_")[0]

def main():
    src = sorted(PROC.glob("eampB_nuyina_long_*.parquet"))[-1]
    print(f"Reading: {src.name}")
    df = pd.read_parquet(src)

    for var, (label, (vmin, vmax)) in VARS.items():
        sub = df[df["variable"] == var].dropna(subset=["latitude","value"]).copy()
        if var == "sss":
            sub = sub[sub["value"] > 1]          # drop sentinel zeros
        sub = sub[(sub["value"] > vmin-5) & (sub["value"] < vmax+10)]
        sub = sub[(sub["latitude"] > -72) & (sub["latitude"] < -38)]
        if sub.empty:
            print(f"{var}: no data"); continue

        # bin latitude, average value per voyage per bin
        sub["lat_bin"] = (np.floor(sub["latitude"]/LAT_BIN)*LAT_BIN) + LAT_BIN/2
        prof = (sub.groupby(["voyage","lat_bin"])["value"].mean().reset_index())

        voyages = sorted(sub["voyage"].unique())
        seasons = sorted({season_of(v) for v in voyages})
        # colour by season-year; line style cycles within a season for separation
        seas_col = {s: c for s, c in zip(seasons, cm.viridis(np.linspace(0.05,0.85,len(seasons))))}

        fig, ax = plt.subplots(figsize=(13, 8))
        for voyage in voyages:
            g = prof[prof["voyage"]==voyage].sort_values("lat_bin")
            if len(g) < 3:
                continue
            s = season_of(voyage)
            ax.plot(g["lat_bin"], g["value"], color=seas_col[s], linewidth=1.3,
                    alpha=0.85, label=voyage.split("_",1)[1] + f"  {s}")
        ax.set_xlabel("Latitude (\u00b0)", fontsize=13)
        ax.set_ylabel(label, fontsize=13)
        ax.set_ylim(vmin, vmax)
        ax.invert_xaxis()  # Tasmania (~-42) on the left, Antarctica (~-70) on the right
        ax.grid(alpha=0.3)
        ax.set_title(f"RSV Nuyina {label} vs latitude, by voyage\n"
                     "Each line = one voyage; colour = season-year "
                     "(between-line spread shows year-to-year variation)", fontsize=14)
        ax.legend(loc="upper left", bbox_to_anchor=(1.01,1.0), fontsize=7.5,
                  title="Voyage \u00b7 season", title_fontsize=9, ncol=1)
        fig.tight_layout()
        OUT.mkdir(parents=True, exist_ok=True)
        out = OUT / f"eampB_nuyina_latprofile_{var}.png"
        fig.savefig(out, dpi=200, bbox_inches="tight")
        print(f"Saved: {out}")
        plt.close(fig)

if __name__ == "__main__":
    main()
