"""Aurora latitude x month climatology (1991-2020) and per-voyage anomaly profiles.
Anomalies are computed per observation against the climatological cell mean,
then averaged per voyage and latitude bin, so voyages crossing months are handled."""
from pathlib import Path
import glob
import numpy as np, pandas as pd

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO/"data/processed/ship"; DSET = REPO/"outputs/datasets_for_aadc"
OUT  = PROC
REF0, REF1 = 1991, 2020        # WMO 30-year normal
MIN_VOY    = 5                 # minimum voyages per climatology cell
LATBIN     = 1.0               # degrees

def load():
    cols = ["voyage","datetime","latitude","variable","value"]
    a = pd.read_parquet(PROC/"eampB_aurora_aadc_long_1990-2020.parquet", columns=cols)
    a["vessel"] = "Aurora Australis"
    nf = sorted(glob.glob(str(DSET/"EAMP_Nuyina_underway_*.parquet")))[-1]
    n = pd.read_parquet(nf, columns=cols); n["vessel"] = "RSV Nuyina"
    print(f"Nuyina source: {Path(nf).name}")
    bad = n.voyage.astype(str).str.contains("V8") & (n.variable=="sst_degC")
    if bad.any(): n = n[~bad]; print(f"  excluded {bad.sum():,} faulty V8 SST rows")
    df = pd.concat([a,n], ignore_index=True)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df

def prep(df, var, vmin, vmax):
    d = df[df.variable==var].dropna(subset=["latitude","value"]).copy()
    d = d[d.latitude.between(-72,-28) & d.value.between(vmin,vmax)]
    d["month"]   = d.datetime.dt.month
    d["lat_bin"] = np.floor(d.latitude/LATBIN)*LATBIN + LATBIN/2
    d["season_year"] = d.groupby("voyage").datetime.transform("min").dt.year
    return d

def run(df, var, vmin, vmax, tag):
    print(f"\n{'='*62}\n{var}\n{'='*62}")
    d = prep(df, var, vmin, vmax)

    # --- climatology from Aurora reference period only ---
    ref = d[(d.vessel=="Aurora Australis") & d.season_year.between(REF0, REF1)]
    print(f"reference: Aurora {REF0}-{REF1}, {ref.voyage.nunique()} voyages, {len(ref):,} obs")
    cell = ref.groupby(["lat_bin","month"]).agg(
        clim=("value","mean"), n_obs=("value","size"), n_voy=("voyage","nunique")).reset_index()
    good = cell[cell.n_voy >= MIN_VOY].copy()
    print(f"cells: {len(cell)} occupied, {len(good)} with >={MIN_VOY} voyages "
          f"({100*len(good)/len(cell):.0f}%)")

    # --- per-observation anomaly ---
    d = d.merge(good[["lat_bin","month","clim","n_voy"]], on=["lat_bin","month"], how="left")
    valid = d.clim.notna()
    for ves in d.vessel.unique():
        m = d.vessel==ves
        print(f"  {ves}: {100*valid[m].mean():.1f}% of obs fall in valid climatology cells")
    d = d[valid].copy()
    d["anom"] = d.value - d.clim

    # --- voyage anomaly profiles (mean anomaly per voyage per latitude bin) ---
    prof = (d.groupby(["vessel","voyage","season_year","lat_bin"])
              .agg(anom=("anom","mean"), n=("anom","size")).reset_index())
    prof = prof[prof.n >= 20]                       # drop thinly-sampled bins
    print(f"anomaly profiles: {prof.voyage.nunique()} voyages, {len(prof):,} voyage-latitude points")

    # --- +/-2 SD envelope from reference-period Aurora voyages ---
    rp = prof[(prof.vessel=="Aurora Australis") & prof.season_year.between(REF0,REF1)]
    env = (rp.groupby("lat_bin").anom.agg(["mean","std","count"])
             .rename(columns={"mean":"env_mean","std":"env_sd","count":"n_voy"}).reset_index())
    env = env[env.n_voy >= MIN_VOY]
    print(f"envelope: {len(env)} latitude bins, "
          f"median SD {env.env_sd.median():.2f} degC, "
          f"latitudes {env.lat_bin.min():.1f} to {env.lat_bin.max():.1f}")

    good.to_parquet(OUT/f"eampB_climatology_{tag}.parquet", index=False)
    prof.to_parquet(OUT/f"eampB_anomaly_profiles_{tag}.parquet", index=False)
    env.to_parquet(OUT/f"eampB_anomaly_envelope_{tag}.parquet", index=False)
    print(f"saved: climatology / profiles / envelope for {tag}")

    # sanity: recent years vs envelope
    print("\n  mean anomaly by season-year (last 12):")
    s = prof.groupby(["vessel","season_year"]).anom.mean().reset_index().tail(12)
    for _,r in s.iterrows():
        print(f"    {r.season_year}  {r.vessel[:16]:16s} {r.anom:+.3f} degC")

def main():
    df = load()
    run(df, "sst_degC",      -2.5, 25, "sst")
    run(df, "air_temp_degC", -25,  32, "airtemp")

if __name__ == "__main__":
    main()
