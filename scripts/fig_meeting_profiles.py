"""Latitude profiles for SST and air temperature across three datasets:
Aurora (AADC 1990-2020), Nuyina (V8-corrected), and the combined record.
One line per voyage, coloured by departure year. Six figures, PNG + PDF."""
from pathlib import Path
import re, glob
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO/"data/processed/ship"
DSET = REPO/"outputs/datasets_for_aadc"
OUT  = REPO/"outputs/figures/ship"

VARSPEC = {
    "sst_degC":      ("Sea surface temperature (\u00b0C)",
                      "sea surface temperature", "sst",     (-2.5, 25)),
    "air_temp_degC": ("Air temperature (\u00b0C)",
                      "air temperature",         "airtemp", (-25, 32)),
}
DATASPEC = {
    "aurora":   ("Aurora Australis",              "aurora_1990-2020",   False),
    "nuyina":   ("RSV Nuyina",                    "nuyina_2021-2026",   False),
    "combined": ("Aurora Australis + RSV Nuyina", "combined_1990-2026", True),
}
GAP_NOTE = ("Note: ~21-month gap (Mar 2020 \u2013 Dec 2021) during vessel changeover;\n"
            "the two vessels are different instruments and do not overlap in time.")
AIR_NOTE = "Aurora air temperature is the mean of the port and starboard sensors."

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
    print(f"    -> {name}.png + {name}.pdf")

def load():
    a = pd.read_parquet(PROC/"eampB_aurora_aadc_long_1990-2020.parquet")
    if "vessel" not in a: a["vessel"] = "Aurora Australis"
    nf = sorted(glob.glob(str(DSET/"EAMP_Nuyina_underway_*.parquet")))[-1]
    n = pd.read_parquet(nf); print(f"Nuyina source: {Path(nf).name}")
    if "vessel" not in n: n["vessel"] = "RSV Nuyina"
    bad = (n.voyage.astype(str) == "2022-23_V8") & (n.variable == "sst_degC")
    if bad.any(): n = n[~bad]; print(f"  excluded {bad.sum():,} faulty V8 SST rows")
    cols = ["vessel","voyage","datetime","latitude","longitude","variable","value"]
    a, n = a[cols].copy(), n[cols].copy()
    for d in (a, n): d["datetime"] = pd.to_datetime(d["datetime"])
    return {"aurora": a, "nuyina": n, "combined": pd.concat([a,n], ignore_index=True)}

def profile(df, var, dkey):
    ylabel, phrase, vtag, (vmin, vmax) = VARSPEC[var]
    stub, dtag, gap = DATASPEC[dkey]
    name = f"MEET_{dtag}_{vtag}_latitude"

    s = df[df.variable == var].dropna(subset=["latitude","value"]).copy()
    if s.empty:
        print(f"    {name}: no {var} data, skipped"); return
    s = s[s.latitude.between(-72,-28) & s.value.between(vmin, vmax)]
    # colour by DEPARTURE year so a voyage crossing 1 Jan is one line, one colour
    s["season_year"] = s.groupby("voyage").datetime.transform("min").dt.year
    s["lat_bin"] = np.floor(s.latitude/0.5)*0.5 + 0.25
    years = sorted(s.season_year.unique()); y0, y1 = min(years), max(years)
    norm = plt.Normalize(y0, y1)

    fig, ax = plt.subplots(figsize=(13,8))
    plotted = []
    for v, g in s.groupby("voyage"):
        p = g.groupby("lat_bin").value.mean().sort_index()
        if len(p) > 3:
            ax.plot(p.index, p.values,
                    color=plt.cm.viridis(norm(g.season_year.iloc[0])),
                    lw=0.85, alpha=0.72)
            plotted.append(v)
    ax.set_xlabel("Latitude (\u00b0)", fontsize=13)
    ax.set_ylabel(ylabel, fontsize=13)
    ax.invert_xaxis(); ax.grid(alpha=0.3)
    plt.colorbar(plt.cm.ScalarMappable(cmap="viridis", norm=norm), ax=ax, label="Year")
    nobs = len(s[s.voyage.isin(plotted)])
    ax.set_title(f"{stub} {phrase} vs latitude, by voyage\n"
                 f"{y0}\u2013{y1}  \u00b7  {len(plotted)} voyages  \u00b7  {nobs:,} observations",
                 fontsize=14)
    notes = ([GAP_NOTE] if gap else []) + ([AIR_NOTE] if var=="air_temp_degC" else [])
    if notes:
        ax.text(0.99, 0.02, "\n".join(notes), transform=ax.transAxes,
                ha="right", va="bottom", fontsize=8, style="italic", color="0.35")
    skipped = sorted(set(s.voyage.unique()) - set(plotted))
    print(f"    {stub} | {phrase} | {len(plotted)} voyages, {nobs:,} obs"
          + (f" | too few lat bins: {skipped}" if skipped else ""))
    save_fig(fig, name); plt.close(fig)

def main():
    data = load()
    for var in ["sst_degC", "air_temp_degC"]:
        print(f"\n=== {var} ===")
        for dkey in ["aurora", "nuyina", "combined"]:
            profile(data[dkey], var, dkey)

if __name__ == "__main__":
    main()
