"""Figure A: NSIDC-style anomaly plot.
All reference voyages in grey, +/-2 SD envelope in black, most recent
Nuyina season highlighted. Built for SST (primary) and air temperature
(secondary, flagged as instrumentally compromised)."""
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO/"data/processed/ship"
OUT  = REPO/"outputs/figures/ship"
REF0, REF1 = 1991, 2020

SPEC = {
    "sst":     ("Sea surface temperature", "#0B3C5D", None),
    "airtemp": ("Air temperature", "#7A4E7E",
                "Caution: the two air sensors diverge by ~1 \u00b0C across the record.\n"
                "This variable is not suitable for trend interpretation."),
}

def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT/f"{name}.png", dpi=200, bbox_inches="tight")
    fig.savefig(OUT/f"{name}.pdf", bbox_inches="tight")
    print(f"  saved {name}.png + .pdf"); plt.close(fig)

def build(tag):
    label, hi_col, caution = SPEC[tag]
    prof = pd.read_parquet(PROC/f"eampB_anomaly_profiles_{tag}.parquet")
    env  = pd.read_parquet(PROC/f"eampB_anomaly_envelope_{tag}.parquet")

    ref = prof[(prof.vessel == "Aurora Australis") &
               prof.season_year.between(REF0, REF1)]
    nuy = prof[prof.vessel == "RSV Nuyina"]
    if nuy.empty:
        print(f"  {tag}: no Nuyina profiles"); return
    last = int(nuy.season_year.max())
    hi = nuy[nuy.season_year == last]

    fig, ax = plt.subplots(figsize=(13, 8))

    for v, g in ref.groupby("voyage"):
        g = g.sort_values("lat_bin")
        ax.plot(g.lat_bin, g.anom, color="0.72", lw=0.6, alpha=0.65, zorder=2)

    e = env.sort_values("lat_bin")
    ax.plot(e.lat_bin, e.env_mean + 2*e.env_sd, color="black", lw=1.6, zorder=4)
    ax.plot(e.lat_bin, e.env_mean - 2*e.env_sd, color="black", lw=1.6, zorder=4)
    ax.fill_between(e.lat_bin, e.env_mean - 2*e.env_sd, e.env_mean + 2*e.env_sd,
                    color="0.85", alpha=0.25, zorder=1)
    ax.axhline(0, color="0.25", lw=1.1, zorder=3)

    for v, g in hi.groupby("voyage"):
        g = g.sort_values("lat_bin")
        ax.plot(g.lat_bin, g.anom, color=hi_col, lw=2.4, alpha=0.9, zorder=5)

    ax.set_xlabel("Latitude (\u00b0)", fontsize=13)
    ax.set_ylabel(f"{label} anomaly (\u00b0C)", fontsize=13)
    ax.invert_xaxis(); ax.grid(alpha=0.25); ax.set_axisbelow(True)

    handles = [
        Line2D([0],[0], color="0.72", lw=1.4,
               label=f"Aurora Australis voyages, {REF0}\u2013{REF1} ({ref.voyage.nunique()})"),
        Line2D([0],[0], color="black", lw=1.6,
               label=f"\u00b12 standard deviations ({REF0}\u2013{REF1})"),
        Line2D([0],[0], color=hi_col, lw=2.4,
               label=f"RSV Nuyina {last}\u2013{str(last+1)[2:]} ({hi.voyage.nunique()} voyages)"),
    ]
    ax.legend(handles=handles, loc="upper left", fontsize=10.5, framealpha=0.92)
    ax.set_title(f"{label} anomaly relative to the Aurora Australis {REF0}\u2013{REF1} climatology\n"
                 f"Anomalies computed against a latitude \u00d7 month climatology, "
                 f"so the seasonal cycle is removed", fontsize=13.5)

    note = ("Aurora Australis and RSV Nuyina are different vessels with different instruments,\n"
            "and their records do not overlap, so they cannot be cross-calibrated directly.")
    if caution: note = caution + "\n" + note
    ax.text(0.99, 0.02, note, transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8, style="italic", color="0.35")

    inside = ((hi.anom.abs() < 2*e.env_sd.median()).mean())*100
    print(f"  {tag}: {ref.voyage.nunique()} reference voyages, "
          f"highlighting {last} ({hi.voyage.nunique()} voyages), "
          f"{inside:.0f}% of highlighted points within \u00b12 SD")
    save(fig, f"MEET_anomaly_{tag}_latitude_1990-2026")

for tag in ["sst", "airtemp"]:
    print(f"{tag}:"); build(tag)
