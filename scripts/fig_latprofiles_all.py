"""Latitude profiles (value vs latitude, one line per voyage, coloured by year)
for SST, air temperature, and salinity, across three categories:
Aurora, Nuyina, and combined. Paul Tol muted palette by year."""
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
LAT_BIN = 0.5
TOL = ["#332288","#88CCEE","#117733","#DDCC77","#CC6677","#AA4499","#44AA99",
       "#882255","#661100","#6699CC","#AA4466","#4477AA","#228833","#CCBB44"]

VARS = {
    "sst_degC":      ("Sea surface temperature (\u00b0C)", (-2, 20)),
    "air_temp_degC": ("Air temperature (\u00b0C)",          (-25, 25)),
    "sss":           ("Sea surface salinity",              (32.5, 35.5)),
}

def load(which):
    if which == "nuyina":
        f = sorted(PROC.glob("eampB_nuyina_long_*.parquet"))[-1]
    else:
        f = sorted(PROC.glob("eampB_aurora_long_*.parquet"))[-1]
    df = pd.read_parquet(f)
    df["year"] = pd.to_datetime(df["datetime"]).dt.year
    # SST quality control:
    # (1) Voyage 2022-23 V8 SST is faulty throughout (recorded 16.8C at 54.6S,
    #     physically impossible) - exclude its SST entirely, not just outliers.
    # (2) A generous latitude-dependent band as a backstop for any other
    #     grossly-implausible warm values.
    is_sst = df["variable"] == "sst_degC"
    v8_sst = is_sst & (df["voyage"].astype(str) == "2022-23_V8")
    df = df[~v8_sst]
    is_sst = df["variable"] == "sst_degC"   # recompute after the drop
    max_ok = 0.636 * df["latitude"] + 51.35
    df = df[~(is_sst & (df["value"] > max_ok))]
    # voyage-year key: Nuyina has season-year in 'voyage'; Aurora uses YYYYMM
    df["vkey"] = df["voyage"].astype(str) + "_" + df["year"].astype(str)
    return df

def plot_profiles(df, var, label, vmin, vmax, title, outname):
    sub = df[df["variable"]==var].dropna(subset=["latitude","value"]).copy()
    if var == "sss":
        sub = sub[sub["value"] > 1]
    sub = sub[(sub["value"]>vmin-5)&(sub["value"]<vmax+10)]
    sub = sub[(sub["latitude"]>-72)&(sub["latitude"]<-38)]
    if sub.empty:
        print(f"  {outname}: no data, skipped"); return
    sub["lat_bin"] = (np.floor(sub["latitude"]/LAT_BIN)*LAT_BIN) + LAT_BIN/2
    years = sorted(sub["year"].unique())
    ycol = {y: TOL[i % len(TOL)] for i, y in enumerate(years)}

    fig, ax = plt.subplots(figsize=(13.5, 8.5))
    legend_handles = []
    for vkey, g in sub.groupby("vkey"):
        prof = g.groupby("lat_bin")["value"].mean().sort_index()
        if len(prof) < 3: continue
        yr = int(g["year"].iloc[0])
        # voyage label: Nuyina has a real voyage id in 'voyage' (e.g. 2021-22_V2);
        # take the part after the underscore if present, else the raw voyage id
        vid = str(g["voyage"].iloc[0])
        vlabel = vid.split("_",1)[1] if "_" in vid else vid
        ax.plot(prof.index, prof.values, color=ycol[yr], linewidth=1.2, alpha=0.8)
        legend_handles.append(Line2D([0],[0], color=ycol[yr], lw=2.0,
                              label=f"{vlabel}  ({yr})"))
    ax.set_xlabel("Latitude (\u00b0)", fontsize=13); ax.set_ylabel(label, fontsize=13)
    ax.set_ylim(vmin, vmax); ax.invert_xaxis(); ax.grid(alpha=0.3)
    ax.set_title(title, fontsize=14)
    # legend lists every voyage with its year; multi-column if many
    ncol = 1 if len(legend_handles) <= 16 else 2
    ax.legend(handles=legend_handles, loc="upper left", bbox_to_anchor=(1.01,1.0),
              fontsize=7, title="Voyage (year)", title_fontsize=10, ncol=ncol)
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / outname
    fig.savefig(out, dpi=200, bbox_inches="tight"); print(f"  Saved: {out}"); plt.close(fig)

def main():
    nuyina = load("nuyina"); nuyina["vessel"] = "Nuyina"
    aurora = load("aurora"); aurora["vessel"] = "Aurora"
    combined = pd.concat([aurora, nuyina], ignore_index=True)

    cats = {"aurora": aurora, "nuyina": nuyina, "combined": combined}
    for var, (label, (vmin, vmax)) in VARS.items():
        for cat, df in cats.items():
            title = f"{cat.capitalize()} {label} vs latitude, by voyage and year"
            outname = f"eampB_{cat}_latprofile_{var}_byyear.png"
            print(f"{cat}/{var}:")
            plot_profiles(df, var, label, vmin, vmax, title, outname)

if __name__ == "__main__":
    main()
