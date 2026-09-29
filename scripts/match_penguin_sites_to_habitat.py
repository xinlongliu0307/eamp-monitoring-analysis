"""Match the observation sites to the 71-colony 2025 habitat dataset.

Workstream A (penguin). Links the 27 sites (28 colonies, Shackleton has two) in
the combined observation CSV built by build_penguin_observations_csv.py to the
circumpolar 2025 colony list with Barb Wienecke's four habitat labels, so that
Julie McInnes can join the two datasets.

Matching is by name, not by position: each site is matched to a habitat-table
colony through a normalised name plus a short explicit alias table for the
spellings that differ between the two sources. Position is then used only as
an independent check: the distance between the site's 2025 median position
and the habitat-table position is reported, and any match further apart than
CHECK_KM is flagged for review rather than silently accepted.

Habitat dataset: the 2026-06-22 version is the confirmed one. It is identical
to the 2026-06-03 version except for three corrected colony names
(Dawson-Lambton Ice Tongue, Stancomb-Wills Ice Tongue, Riiser-Larsen Ice
Shelf), none of which are observation sites.

Usage (from the repo root):
    python scripts/match_penguin_sites_to_habitat.py
    python scripts/match_penguin_sites_to_habitat.py --observations <csv> --habitat <xlsx>

Default inputs:
    data/processed/penguin/eampA_colony_observations_combined_<latest>.csv
    data/raw/penguin/Emperor_colony_locations_2025_habitat_20260622.xlsx
Outputs (data/processed/penguin/):
    eampA_site_habitat_crosswalk_<date>.csv       one row per site/colony
    eampA_colony_observations_with_habitat_<date>.csv   observations + habitat
"""
import argparse
import math
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import pandas as pd  # noqa: E402

from eamp.common import config  # noqa: E402
from eamp.common.logging import get_logger  # noqa: E402

logger = get_logger("match_penguin_sites_to_habitat")

DEFAULT_HABITAT = config.PENGUIN_RAW / "Emperor_colony_locations_2025_habitat_20260622.xlsx"
HABITAT_SHEET = "EMPE colonies 2025"

# Observation-site spellings that differ from the habitat table after
# normalisation. Keys and values are the names exactly as they appear.
ALIASES = {
    "Flutter (Cape Darnley)": "Flutter/Cape Darnley",
    "Barrier Bay": "Barrier Bay (extinct)",
    "Bowman": "Bowman Island",
    "Pointe Geologie": "Point Géologie",
}

CHECK_KM = 25.0  # position check threshold, same as the colony outlier rule


def normalise(name: str) -> str:
    """Lower-case, strip accents, drop '(extinct)' and punctuation."""
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = s.replace("(extinct)", "")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def latest_observations_csv() -> Path:
    files = sorted(config.PENGUIN_PROCESSED.glob("eampA_colony_observations_combined_*.csv"))
    if not files:
        raise SystemExit("No combined observations CSV found; run "
                         "scripts/build_penguin_observations_csv.py first.")
    return files[-1]


def load_habitat(path: Path) -> pd.DataFrame:
    hab = pd.read_excel(path, sheet_name=HABITAT_SHEET)
    hab = hab.dropna(how="all").dropna(axis=1, how="all")
    hab = hab.rename(columns={"Colony": "habitat_colony", "Date": "habitat_date",
                              "Lat": "habitat_lat", "Long": "habitat_long",
                              "Habitat": "habitat"})
    hab["extinct"] = hab["habitat_colony"].str.contains("(extinct)", regex=False)
    hab["key"] = hab["habitat_colony"].map(normalise)
    if hab["key"].duplicated().any():
        raise SystemExit(f"Duplicate colony names in {path.name}")
    logger.info(f"Habitat table: {len(hab)} colonies ({hab['extinct'].sum()} extinct) "
                f"from {path.name}")
    return hab


def build_crosswalk(obs: pd.DataFrame, hab: pd.DataFrame) -> pd.DataFrame:
    pos = obs[obs["has_position"]].copy()
    pos["date"] = pd.to_datetime(pos["date"])

    rows = []
    for (site_id, site, colony), g in pos.groupby(["site_id", "site", "colony"],
                                                  dropna=False, sort=True):
        # Reference position: median of the most recent year with positions,
        # comparable with the 2025 date of the habitat table.
        last_year = g["date"].dt.year.max()
        ref = g[g["date"].dt.year == last_year]
        lat, lon = ref["lat"].median(), ref["long"].median()

        target = ALIASES.get(site, site)
        method = "alias" if site in ALIASES else "name"
        hit = hab[hab["key"] == normalise(target)]
        row = {"site_id": site_id, "site": site, "colony": colony,
               "obs_ref_year": int(last_year), "obs_ref_n": len(ref),
               "obs_ref_lat": round(lat, 5), "obs_ref_long": round(lon, 5)}
        if hit.empty:
            row.update(match_method="unmatched", check="NO MATCH")
        else:
            h = hit.iloc[0]
            d = haversine_km(lat, lon, h["habitat_lat"], h["habitat_long"])
            row.update(match_method=method, habitat_colony=h["habitat_colony"],
                       habitat=h["habitat"], habitat_date=h["habitat_date"].date(),
                       habitat_lat=h["habitat_lat"], habitat_long=h["habitat_long"],
                       extinct=bool(h["extinct"]), distance_km=round(d, 2),
                       check="ok" if d <= CHECK_KM else f"REVIEW: {d:.0f} km apart")
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--observations", type=Path, default=None,
                        help="combined observations CSV (default: latest in data/processed/penguin)")
    parser.add_argument("--habitat", type=Path, default=DEFAULT_HABITAT,
                        help="habitat workbook (default: 20260622 version)")
    parser.add_argument("--outdir", type=Path, default=config.PENGUIN_PROCESSED)
    args = parser.parse_args()

    obs_path = args.observations or latest_observations_csv()
    obs = pd.read_csv(obs_path, low_memory=False)
    logger.info(f"Observations: {len(obs):,} rows from {obs_path.name}")
    hab = load_habitat(args.habitat)

    xwalk = build_crosswalk(obs, hab)
    n_site = xwalk["site"].nunique()
    unmatched = xwalk[xwalk["match_method"] == "unmatched"]
    review = xwalk[xwalk["check"].str.startswith("REVIEW")]

    # Join habitat fields onto every observation row (site-level join; both
    # Shackleton colonies map to the single Shackleton Ice Shelf entry).
    site_map = xwalk.drop_duplicates("site")[["site", "habitat_colony", "habitat", "extinct"]]
    joined = obs.merge(site_map, on="site", how="left", validate="many_to_one")
    assert len(joined) == len(obs)

    args.outdir.mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()
    xw_path = args.outdir / f"eampA_site_habitat_crosswalk_{stamp}.csv"
    jn_path = args.outdir / f"eampA_colony_observations_with_habitat_{stamp}.csv"
    xwalk.to_csv(xw_path, index=False)
    joined.to_csv(jn_path, index=False)

    logger.info(f"Matched {n_site - unmatched['site'].nunique()}/{n_site} sites "
                f"({(xwalk['match_method'] == 'alias').sum()} via alias); "
                f"{len(review)} flagged by the {CHECK_KM:.0f} km position check")
    for _, r in unmatched.iterrows():
        logger.warning(f"UNMATCHED: {r['site']}")
    for _, r in review.iterrows():
        logger.warning(f"{r['site']}: obs {r['obs_ref_year']} median "
                       f"({r['obs_ref_lat']}, {r['obs_ref_long']}) vs habitat "
                       f"({r['habitat_lat']}, {r['habitat_long']}) = {r['distance_km']} km")
    counts = joined.drop_duplicates("site")["habitat"].value_counts(dropna=False)
    logger.info("Sites per habitat: " + ", ".join(f"{k}: {v}" for k, v in counts.items()))
    logger.info(f"Wrote crosswalk: {xw_path}")
    logger.info(f"Wrote joined CSV: {jn_path}")


if __name__ == "__main__":
    main()
