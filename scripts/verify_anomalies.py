"""Verification for Patricia's points 1 and 5:
 (1) confirm the seasonal cycle really is removed
 (2) diagnose the near-straight Nuyina line in the SST anomaly figure"""
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

PROC = Path("/g/data/gv90/xl1657/phd/eamp/data/processed/ship")

for tag, label in [("sst","SEA SURFACE TEMPERATURE"), ("airtemp","AIR TEMPERATURE")]:
    print(f"\n{'='*72}\n{label}\n{'='*72}")
    prof = pd.read_parquet(PROC/f"eampB_anomaly_profiles_{tag}.parquet")
    print(f"profiles: {len(prof):,} voyage-latitude points, "
          f"{prof.voyage.nunique()} voyages, "
          f"{prof.vessel.nunique()} vessels")
    print(f"anomaly mean {prof.anom.mean():+.4f}, sd {prof.anom.std():.3f}")
    print("  (mean should be near zero by construction if the climatology is right)")

print(f"\n{'='*72}\nSEASONAL REMOVAL TEST\n{'='*72}")
print("If the seasonal cycle is removed, mean anomaly by month should be ~0.")
print("If it is NOT removed, months will show systematic offsets.\n")

import glob
cols = ["voyage","datetime","latitude","variable","value"]
a = pd.read_parquet(PROC/"eampB_aurora_aadc_long_1990-2020.parquet", columns=cols)
a["vessel"] = "Aurora Australis"
nf = sorted(glob.glob(str(Path("/g/data/gv90/xl1657/phd/eamp/outputs/datasets_for_aadc")
                            /"EAMP_Nuyina_underway_*.parquet")))[-1]
n = pd.read_parquet(nf, columns=cols); n["vessel"] = "RSV Nuyina"
df = pd.concat([a,n], ignore_index=True)
df["datetime"] = pd.to_datetime(df.datetime)
df["month"] = df.datetime.dt.month
df["season_year"] = df.groupby("voyage").datetime.transform("min").dt.year
df["lat_bin"] = np.floor(df.latitude/1.0)*1.0 + 0.5

for var, tag, lo, hi in [("sst_degC","sst",-2.5,25), ("air_temp_degC","airtemp",-25,32)]:
    d = df[(df.variable==var) & df.value.between(lo,hi)].dropna(subset=["latitude","value"])
    d = d[d.latitude.between(-72,-28)]
    ref = d[(d.vessel=="Aurora Australis") & d.season_year.between(1991,2020)]

    # RAW values by month (should show a strong seasonal cycle)
    raw_m = ref.groupby("month").value.mean()
    # ANOMALY by month, using the lat x month climatology
    cell = (ref.groupby(["lat_bin","month"])
              .agg(clim=("value","mean"), nv=("voyage","nunique")).reset_index())
    cell = cell[cell.nv >= 5]
    m = ref.merge(cell[["lat_bin","month","clim"]], on=["lat_bin","month"], how="inner")
    m["anom"] = m.value - m.clim
    an_m = m.groupby("month").anom.mean()

    # a latitude-only climatology, for comparison (seasonal cycle NOT removed)
    cell2 = ref.groupby("lat_bin").value.mean().rename("clim2").reset_index()
    m2 = ref.merge(cell2, on="lat_bin", how="inner")
    m2["anom2"] = m2.value - m2.clim2
    an2_m = m2.groupby("month").anom2.mean()

    print(f"\n--- {var} ---")
    print(f"{'month':>6} {'raw mean':>10} {'lat-only anom':>15} {'lat x month anom':>18}")
    for mth in range(1,13):
        r = raw_m.get(mth, np.nan); a1 = an2_m.get(mth, np.nan); a2 = an_m.get(mth, np.nan)
        print(f"{mth:>6} {r:>10.2f} {a1:>15.3f} {a2:>18.3f}")
    print(f"{'spread':>6} {raw_m.max()-raw_m.min():>10.2f} "
          f"{an2_m.max()-an2_m.min():>15.3f} {an_m.max()-an_m.min():>18.3f}")
    print("  Column 3 keeps the seasonal cycle; column 4 should be much flatter.")

print(f"\n{'='*72}\nPOINT 5: the straight Nuyina line in the SST figure\n{'='*72}")
prof = pd.read_parquet(PROC/"eampB_anomaly_profiles_sst.parquet")
nuy = prof[prof.vessel=="RSV Nuyina"]
print(f"{'voyage':18s} {'year':>5} {'bins':>5} {'lat range':>16} "
      f"{'anom range':>13} {'linearity r':>12}")
for v, g in nuy.groupby("voyage"):
    g = g.sort_values("lat_bin")
    if len(g) < 3: 
        print(f"{v:18s} {int(g.season_year.iloc[0]):>5} {len(g):>5}  (too few bins)")
        continue
    r = stats.linregress(g.lat_bin, g.anom).rvalue
    print(f"{v:18s} {int(g.season_year.iloc[0]):>5} {len(g):>5} "
          f"{g.lat_bin.min():>7.1f} to {g.lat_bin.max():<6.1f} "
          f"{g.anom.min():>+6.2f} to {g.anom.max():<+6.2f} {r:>+12.2f}")
print("\n  |r| near 1 with few bins = a near-straight line, likely sparse sampling")
print("  spanning a wide latitude range with little data in between.")
