"""Anomaly figures v2.
 - warm (orange) highlights for SST, pink for air temperature
 - each highlighted voyage gets a distinct colour AND line style
 - voyages with too few latitude bins drawn as markers, not misleading lines
 - reference period differs by variable (SST 1991-2020, air temp 2005-2020)
"""
from pathlib import Path
import glob
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO/"data/processed/ship"
DSET = REPO/"outputs/datasets_for_aadc"
OUT  = REPO/"outputs/figures/ship"
MIN_BINS = 8          # below this, plot markers rather than a line

# six distinguishable shades per family, cycled with line style so that
# no colour+style pair repeats until well beyond the number of voyages
WARM = ["#E65100", "#FFB300", "#BF360C", "#FF7043", "#8D4004", "#FDD835"]
PINK = ["#C2185B", "#F06292", "#7B1FA2", "#FF80AB", "#880E4F", "#CE93D8"]
STYLES = ["-", "--", "-."]

SPEC = {
    "sst":     ("Sea surface temperature", WARM, (1991, 2020), None),
    "airtemp": ("Air temperature", PINK, (2005, 2020),
                "Baseline starts in 2005: the port and starboard air sensors only agree\n"
                "closely from about that date, so earlier air temperature is less reliable."),
}
MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT/f"{name}.png", dpi=200, bbox_inches="tight")
    fig.savefig(OUT/f"{name}.pdf", bbox_inches="tight")
    print(f"  saved {name}.png + .pdf"); plt.close(fig)

def voyage_months():
    cols = ["voyage","datetime"]
    a = pd.read_parquet(PROC/"eampB_aurora_aadc_long_1990-2020.parquet", columns=cols)
    nf = sorted(glob.glob(str(DSET/"EAMP_Nuyina_underway_*.parquet")))[-1]
    n = pd.read_parquet(nf, columns=cols)
    d = pd.concat([a,n], ignore_index=True)
    d["datetime"] = pd.to_datetime(d.datetime)
    g = d.groupby("voyage").datetime.agg(["min","max"])
    return {v: (r["min"], r["max"]) for v, r in g.iterrows()}

def label_for(voy, span):
    if voy not in span: return voy
    t0, t1 = span[voy]
    m0, m1 = MONTHS[t0.month-1], MONTHS[t1.month-1]
    short = voy.split("_",1)[1] if "_" in voy else voy
    return f"{short}  ({m0}\u2013{m1} {t0.year})" if m0 != m1 else f"{short}  ({m0} {t0.year})"

def build(tag):
    label, palette, (REF0, REF1), caution = SPEC[tag]
    prof = pd.read_parquet(PROC/f"eampB_anomaly_profiles_{tag}.parquet")
    env  = pd.read_parquet(PROC/f"eampB_anomaly_envelope_{tag}.parquet")
    span = voyage_months()

    ref = prof[(prof.vessel=="Aurora Australis") & prof.season_year.between(REF0,REF1)]
    nuy = prof[prof.vessel=="RSV Nuyina"]
    last = int(nuy.season_year.max())
    hi = nuy[nuy.season_year == last]

    fig, ax = plt.subplots(figsize=(13.5, 8))

    for v, g in ref.groupby("voyage"):
        g = g.sort_values("lat_bin")
        ax.plot(g.lat_bin, g.anom, color="0.74", lw=0.6, alpha=0.6, zorder=2)

    e = env.sort_values("lat_bin")
    ax.fill_between(e.lat_bin, e.env_mean-2*e.env_sd, e.env_mean+2*e.env_sd,
                    color="0.86", alpha=0.35, zorder=1)
    ax.plot(e.lat_bin, e.env_mean+2*e.env_sd, color="black", lw=1.5, zorder=4)
    ax.plot(e.lat_bin, e.env_mean-2*e.env_sd, color="black", lw=1.5, zorder=4)
    ax.axhline(0, color="0.25", lw=1.1, zorder=3)

    handles, sparse = [], []
    for i, (v, g) in enumerate(sorted(hi.groupby("voyage"))):
        g = g.sort_values("lat_bin")
        c  = palette[i % len(palette)]
        ls = STYLES[(i // len(palette)) % len(STYLES)]
        lbl = label_for(v, span)
        if len(g) >= MIN_BINS:
            ax.plot(g.lat_bin, g.anom, color=c, lw=2.6, ls=ls, alpha=0.95, zorder=6)
            handles.append(Line2D([0],[0], color=c, lw=2.6, ls=ls, label=lbl))
        else:
            ax.plot(g.lat_bin, g.anom, "o", color=c, ms=8, alpha=0.95, zorder=6,
                    markeredgecolor="white", markeredgewidth=0.8)
            handles.append(Line2D([0],[0], color=c, marker="o", lw=0, ms=8,
                                  label=f"{lbl}  \u2014 {len(g)} bins only"))
            sparse.append(v)

    ax.set_xlabel("Latitude (\u00b0)", fontsize=13)
    ax.set_ylabel(f"{label} anomaly (\u00b0C)", fontsize=13)
    ax.invert_xaxis(); ax.grid(alpha=0.25); ax.set_axisbelow(True)

    base = [Line2D([0],[0], color="0.74", lw=1.4,
                   label=f"Aurora Australis voyages, {REF0}\u2013{REF1} ({ref.voyage.nunique()})"),
            Line2D([0],[0], color="black", lw=1.5,
                   label=f"\u00b12 standard deviations ({REF0}\u2013{REF1})")]
    ax.legend(handles=base+handles, loc="upper left", fontsize=10, framealpha=0.93,
              title=f"RSV Nuyina {last}\u2013{str(last+1)[2:]} highlighted", title_fontsize=10.5)
    ax.set_title(f"{label} anomaly relative to the Aurora Australis {REF0}\u2013{REF1} climatology\n"
                 f"Seasonal cycle removed: anomalies computed against a latitude \u00d7 month climatology",
                 fontsize=13.5)

    notes = []
    if caution: notes.append(caution)
    if sparse:
        notes.append("Voyages shown as points sampled too few latitude bands to draw as a profile.")
    notes.append("Winter months are excluded: too few reference voyages to form a climatology.")
    notes.append("Aurora Australis and RSV Nuyina are different vessels and their records do not overlap.")
    ax.text(0.99, 0.02, "\n".join(notes), transform=ax.transAxes, ha="right", va="bottom",
            fontsize=7.8, style="italic", color="0.35")

    used = [(palette[i % len(palette)], STYLES[(i // len(palette)) % len(STYLES)])
            for i in range(hi.voyage.nunique())]
    print(f"  {tag}: {ref.voyage.nunique()} reference voyages, {last} highlighted "
          f"({hi.voyage.nunique()} voyages, {len(sparse)} as points), "
          f"{len(set(used))} distinct colour+style pairs")
    save(fig, f"MEET_anomaly_{tag}_latitude_1990-2026_v2")

for tag in ["sst","airtemp"]:
    print(f"{tag}:"); build(tag)
