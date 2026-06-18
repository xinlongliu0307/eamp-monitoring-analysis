"""Lightweight, read-only exploration of Aurora Australis SST (TEMP).
Samples the SOOP-ASF MT files to characterise the record before any
harmonisation. Produces a quick SST-vs-time and SST-vs-latitude view.
"""
from pathlib import Path
import glob
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import xarray as xr

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
SRC = REPO / "data/raw/ship/aodn_downloads/aurora_australis_asf_met_sst_thredds"
OUT = REPO / "outputs/figures/ship"

def main():
    files = sorted(glob.glob(str(SRC / "*.nc")))
    # sample every Nth file to keep this light on a login node
    step = max(1, len(files) // 120)
    sample = files[::step]
    print(f"Total files: {len(files)}; sampling {len(sample)} (every {step})")

    recs = []
    for f in sample:
        try:
            ds = xr.open_dataset(f)
            if "TEMP" not in ds.data_vars:
                continue
            t = pd.to_datetime(ds["TIME"].values)
            temp = ds["TEMP"].values.astype(float)
            lat = ds["LATITUDE"].values.astype(float)
            # one representative (median) row per file to keep it tiny
            ok = np.isfinite(temp) & (temp > -2.5) & (temp < 30)
            if ok.sum() == 0:
                continue
            recs.append({"time": t[ok][len(t[ok])//2],
                         "sst_median": np.median(temp[ok]),
                         "sst_min": np.min(temp[ok]),
                         "sst_max": np.max(temp[ok]),
                         "lat_median": np.median(lat[np.isfinite(lat)])})
        except Exception as e:
            print(f"  skip {Path(f).name[:40]}: {e}")
    df = pd.DataFrame(recs).sort_values("time")
    print(f"Summarised {len(df)} files")
    print(f"Date span: {df['time'].min()} .. {df['time'].max()}")
    print(f"SST median range: {df['sst_median'].min():.1f} to {df['sst_median'].max():.1f} degC")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    ax1.scatter(df["time"], df["sst_median"], s=12, color="#1C7293", alpha=0.7)
    ax1.set_xlabel("Year"); ax1.set_ylabel("Median SST (\u00b0C)")
    ax1.set_title("Aurora Australis SST over time (sampled daily files)")
    ax1.grid(alpha=0.3)
    ax2.scatter(df["sst_median"], df["lat_median"], s=12, color="#065A82", alpha=0.7)
    ax2.set_xlabel("Median SST (\u00b0C)"); ax2.set_ylabel("Median latitude (\u00b0)")
    ax2.set_title("Aurora SST vs latitude (sampled)")
    ax2.grid(alpha=0.3)
    fig.suptitle("Aurora Australis SST \u2014 exploratory summary (read-only, sampled)", fontsize=14)
    fig.tight_layout(rect=[0,0,1,0.96])
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "eampB_aurora_sst_exploration.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print(f"Saved: {out}")

if __name__ == "__main__":
    main()
