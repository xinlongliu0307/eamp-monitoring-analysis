"""Figures B and C: specification curve and instrument diagnostic."""
from pathlib import Path
import numpy as np, pandas as pd, glob
from scipy import stats
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path("outputs/figures/ship"); OUT.mkdir(parents=True, exist_ok=True)

def save(fig, name):
    fig.savefig(OUT/f"{name}.png", dpi=200, bbox_inches="tight")
    fig.savefig(OUT/f"{name}.pdf", bbox_inches="tight")
    print(f"  saved {name}"); plt.close(fig)

# ---- Figure B: specification curve (values from the analysis) ----
spec = [
    ("Raw, all latitudes\n(no controls)",              0.064, 0.066, 139),
    ("Seasonal climatology\n40-50S, all longitudes",   0.226, 0.096, 118),
    ("Restricted to 120-150E\ncorridor",               0.062, 0.083, 127),
    ("Front-relative\ncoordinates",                   -0.070, 0.073, 119),
    ("Stable-instrument era\n2005-2020",              -0.049, 0.155,  69),
]
fig, ax = plt.subplots(figsize=(11,6))
y = np.arange(len(spec))[::-1]
for i,(lab,est,se,n) in enumerate(spec):
    yy = y[i]; lo, hi = est-1.96*se, est+1.96*se
    sig = lo > 0 or hi < 0
    col = "#C1666B" if sig else "#4C6E8A"
    ax.plot([lo,hi],[yy,yy], color=col, lw=2.5, solid_capstyle="round")
    ax.plot(est, yy, "o", color=col, ms=9, zorder=3)
    ax.text(hi+0.03, yy, f"n={n}", va="center", fontsize=9, color="0.4")
ax.axvline(0, color="0.3", lw=1.2, ls="--")
ax.set_yticks(y); ax.set_yticklabels([s[0] for s in spec], fontsize=10)
ax.set_xlabel("SST trend (\u00b0C per decade), 95% confidence interval", fontsize=12)
ax.set_title("Aurora Australis sea surface temperature trend, 1990\u20132020\n"
             "The apparent trend disappears as sampling confounds are controlled",
             fontsize=13)
ax.grid(axis="x", alpha=0.3); ax.set_axisbelow(True)
ax.text(0.99,0.02,"Red = significant at 95%.  Blue = not distinguishable from zero.",
        transform=ax.transAxes, ha="right", fontsize=8.5, style="italic", color="0.35")
fig.tight_layout(); save(fig, "MEET_trend_specification_curve")

# ---- Figure C: instrument diagnostic ----
rows=[]
for f in sorted(glob.glob("data/raw/ship/aadc_downloads/aurora_full/*.csv")):
    try:
        c = pd.read_csv(f, usecols=["date_time_utc","temp_air_port_degc",
              "temp_air_strbrd_degc"], low_memory=False).dropna()
        if len(c) < 500: continue
        yr = pd.to_datetime(c.date_time_utc, errors="coerce").dt.year.median()
        d = c.temp_air_port_degc - c.temp_air_strbrd_degc
        rows.append((yr, d.mean(), d.std()))
    except Exception: pass
d = pd.DataFrame(rows, columns=["year","mean","sd"]).dropna().sort_values("year")

fig, axes = plt.subplots(1, 2, figsize=(13,5))
axes[0].scatter(d.year, d["mean"], s=26, color="#4C6E8A", alpha=0.75)
axes[0].axhline(0, color="0.3", lw=1, ls="--")
axes[0].set_ylabel("Port minus starboard (\u00b0C)", fontsize=11)
axes[0].set_title("Mean disagreement between the two air sensors", fontsize=12)
axes[1].scatter(d.year, d.sd, s=26, color="#C1666B", alpha=0.75)
axes[1].set_yscale("log")
axes[1].set_ylabel("Within-voyage scatter, SD (\u00b0C, log scale)", fontsize=11)
axes[1].set_title("Scatter between the two sensors", fontsize=12)
for a in axes:
    a.set_xlabel("Year", fontsize=11); a.grid(alpha=0.3); a.set_axisbelow(True)
fig.suptitle("Two air-temperature sensors on the same ship, measuring the same air\n"
             "Their agreement improves ~30-fold over the record: instrument change, not climate",
             fontsize=13)
fig.tight_layout(); save(fig, "MEET_air_sensor_diagnostic")
