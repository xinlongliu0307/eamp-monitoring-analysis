"""Points 2 and 3: trend tests month by month and latitude band by latitude band.

Deliberately simple. No frontal analysis. For each cell, take the per-voyage
mean anomaly, regress on year, and report the slope with a significance test.

Reference periods follow Patricia's steer: SST from 1990, air temperature
from 2005 (when the port/starboard sensors begin to agree).

Run both with and without the longitude restriction, so the effect of
comparing like-with-like routes is visible.
"""
from pathlib import Path
import glob
import numpy as np, pandas as pd
from scipy import stats

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
PROC = REPO/"data/processed/ship"
DSET = REPO/"outputs/datasets_for_aadc"
OUT  = PROC

BANDS  = [(-72,-60,"60-72S  ice edge"), (-60,-50,"50-60S  Antarctic"),
          (-50,-40,"40-50S  frontal"),  (-40,-28,"28-40S  subtropical")]
MONTHS = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
          7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
VARSPEC = {"sst_degC":     ("sst",     1990, (-2.5,25)),
           "air_temp_degC":("airtemp", 2005, (-25,32))}
MIN_VOY = 8      # minimum voyages before a cell is tested

def load():
    cols = ["voyage","datetime","latitude","longitude","variable","value"]
    a = pd.read_parquet(PROC/"eampB_aurora_aadc_long_1990-2020.parquet", columns=cols)
    a["vessel"] = "Aurora Australis"
    nf = sorted(glob.glob(str(DSET/"EAMP_Nuyina_underway_*.parquet")))[-1]
    n = pd.read_parquet(nf, columns=cols); n["vessel"] = "RSV Nuyina"
    print(f"Nuyina source: {Path(nf).name}")
    bad = (n.voyage.astype(str) == "2022-23_V8") & (n.variable == "sst_degC")
    if bad.any(): n = n[~bad]; print(f"  excluded {bad.sum():,} faulty V8 SST rows")
    d = pd.concat([a,n], ignore_index=True)
    d["datetime"] = pd.to_datetime(d.datetime)
    d["month"] = d.datetime.dt.month
    d["season_year"] = d.groupby("voyage").datetime.transform("min").dt.year
    return d

def anomalies(d, var, y0, vmin, vmax, corridor):
    s = d[(d.variable==var) & d.value.between(vmin,vmax)].dropna(subset=["latitude","value"])
    s = s[s.latitude.between(-72,-28) & (s.season_year >= y0)]
    if corridor:
        s = s[s.longitude.between(120,150)]
    s = s.copy()
    s["lat_bin"] = np.floor(s.latitude) + 0.5
    # climatology from Aurora reference voyages only
    ref = s[(s.vessel=="Aurora Australis") & (s.season_year <= 2020)]
    cell = (ref.groupby(["lat_bin","month"])
              .agg(clim=("value","mean"), nv=("voyage","nunique")).reset_index())
    cell = cell[cell.nv >= 5]
    m = s.merge(cell[["lat_bin","month","clim"]], on=["lat_bin","month"], how="inner")
    m["anom"] = m.value - m.clim
    return m

def test_cell(g):
    v = g.groupby(["voyage","season_year"]).anom.mean().reset_index()
    if v.voyage.nunique() < MIN_VOY: return None
    sl,_,_,p,se = stats.linregress(v.season_year, v.anom)
    tau, pt = stats.kendalltau(v.season_year, v.anom)
    return dict(n=len(v), slope=sl*10, p=p, se=se*10, tau=tau, p_tau=pt)

def fdr(pvals, q=0.05):
    """Benjamini-Hochberg: which tests survive multiple-comparison correction"""
    p = np.asarray(pvals); n = len(p)
    order = np.argsort(p); ranked = p[order]
    thresh = q * (np.arange(1, n+1) / n)
    passed = ranked <= thresh
    k = np.max(np.where(passed)[0]) + 1 if passed.any() else 0
    keep = np.zeros(n, bool)
    if k: keep[order[:k]] = True
    return keep

def run(d, var, corridor):
    tag, y0, (vmin, vmax) = VARSPEC[var]
    scope = "120-150E corridor" if corridor else "all longitudes"
    print(f"\n{'='*78}\n{var}   from {y0}   ({scope})\n{'='*78}")
    m = anomalies(d, var, y0, vmin, vmax, corridor)
    if m.empty: print("  no data"); return None

    rows = []
    # by latitude band
    for lo, hi, lab in BANDS:
        r = test_cell(m[m.latitude.between(lo,hi)])
        if r: rows.append(dict(kind="band", cell=lab, month=None, **r))
    # by month
    for mo in sorted(m.month.unique()):
        r = test_cell(m[m.month==mo])
        if r: rows.append(dict(kind="month", cell=MONTHS[mo], month=mo, **r))
    # month x band
    for lo, hi, lab in BANDS:
        for mo in sorted(m.month.unique()):
            r = test_cell(m[(m.latitude.between(lo,hi)) & (m.month==mo)])
            if r: rows.append(dict(kind="month x band",
                                   cell=f"{MONTHS[mo]} / {lab.split()[0]}", month=mo, **r))
    if not rows: print("  no cells with enough voyages"); return None
    t = pd.DataFrame(rows)
    t["fdr_sig"] = fdr(t.p.values)

    for kind in ["band","month","month x band"]:
        sub = t[t.kind==kind]
        if sub.empty: continue
        print(f"\n--- by {kind} ---")
        print(f"{'cell':22s} {'n':>4} {'trend/decade':>14} {'p':>8} {'tau p':>8}  sig")
        for _, r in sub.iterrows():
            mark = "**" if r.fdr_sig else ("*" if r.p < 0.05 else "")
            print(f"{r.cell:22s} {r.n:>4} {r.slope:>+9.3f} degC {r.p:>8.3f} "
                  f"{r.p_tau:>8.3f}  {mark}")
        k = sub.p.lt(0.05).sum()
        print(f"  {k} of {len(sub)} significant at p<0.05 "
              f"(~{0.05*len(sub):.1f} expected by chance); "
              f"{sub.fdr_sig.sum()} survive FDR correction")
    t["variable"], t["corridor"] = var, corridor
    return t

def main():
    d = load()
    out = []
    for var in VARSPEC:
        for corridor in [False, True]:
            r = run(d, var, corridor)
            if r is not None: out.append(r)
    res = pd.concat(out, ignore_index=True)
    res.to_parquet(OUT/"eampB_trend_month_latitude.parquet", index=False)
    print(f"\nsaved: eampB_trend_month_latitude.parquet ({len(res)} tests)")
    print("\n* = p<0.05 uncorrected;  ** = survives Benjamini-Hochberg FDR correction")
    print("With many cells tested, some will reach p<0.05 by chance alone.")
    print("The FDR column is the honest guide to which results to believe.")

if __name__ == "__main__":
    main()
