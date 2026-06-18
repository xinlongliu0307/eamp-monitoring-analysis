"""All-variable completeness diagnostic for the Nuyina underway schema.

Computes per-voyage non-null completeness across all measurement columns,
grouped by instrument domain, and renders a grouped heatmap. Status/flag
columns are reported separately (they are health flags, not measurements).
Zeros are treated as missing only where zero is physically impossible.
"""
from datetime import date
from pathlib import Path
import re

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path("/g/data/gv90/xl1657/phd/eamp")
NUYINA = REPO / "data/raw/ship/aadc_downloads/nuyina_underway_voyages"
OUT = REPO / "outputs/figures/ship"

FILENAME_PAT = re.compile(
    r"RSV_Nuyina_Voyage_Data_(?P<season>\d{4}-\d{2})_(?P<version>V[A-Z0-9]+)\.csv$")

# explicit grouping built from the actual 99 columns
GROUPS = {
    "Navigation": [
        "latitude", "longitude", "platform_course_true", "platform_speed_wrt_ground",
        "platform_heading_true", "platform_heave_down", "platform_pitch_fore_up",
        "platform_roll_starboard_down", "surface_current_speed", "surface_current_direction_to"],
    "Wind": [
        "wind_speed_true_avg10min_fore_1", "wind_speed_relative_fore_1", "wind_speed_true_fore_1",
        "wind_speed_true_gust10min_fore_1", "wind_speed_true_fore_2", "wind_speed_true_avg10min_fore_2",
        "wind_speed_true_gust10min_fore_2", "wind_speed_relative_fore_2", "wind_speed_true_aft",
        "wind_speed_true_avg10minute_aft", "wind_speed_true_gust10minute_aft", "wind_speed_relative_aft",
        "wind_from_direction_true_avg10min_fore_1", "fore_wind_from_direction_relative",
        "wind_from_direction_true_fore_1", "wind_from_direction_true_fore_2",
        "wind_from_direction_true_avg10min_fore_2", "wind_from_direction_relative_fore_2",
        "wind_from_direction_true_aft", "wind_from_direction_true_avg10minute_aft",
        "wind_from_direction_relative_aft"],
    "Meteorology": [
        "air_pressure_avg1min", "air_pressure_tend3h", "air_pressure_trend3h",
        "air_temperature_avg1min_port", "air_temperature_avg1min_stbd",
        "relative_humidity_avg1min_port", "relative_humidity_avg1min_stbd",
        "dew_point_temperature_avg1min_port", "dew_point_temperature_avg1min_stbd",
        "precipitation_accumulation_1hr", "precipitation_rate_avg1min", "present_weather",
        "present_weather_avg15min", "snow_accumulation_1min", "visibility_in_air_avg1min",
        "visibility_in_air_avg10min", "cloud_cover_1", "cloud_cover_2", "cloud_cover_3",
        "cloud_cover_4", "cloud_cover_5", "cloud_height_1", "cloud_height_2", "cloud_height_3",
        "cloud_height_4", "cloud_height_5"],
    "Radiation": [
        "longwave_irradiance_avg1min_port", "longwave_irradiance_avg1min_stbd",
        "photosynthetically_active_radiation_avg1min_port",
        "photosynthetically_active_radiation_avg1min_stbd", "solar_irradiance_avg1min_port",
        "solar_irradiance_avg1min_stbd", "uvb_irradiation_avg1min_port",
        "uvb_irradiation_avg1min_stbd", "uv_irradiance_avg1min_port", "uv_irradiance_avg1min_stbd"],
    "Waves": [
        "significant_wave_height", "maximum_wave_height", "mean_wave_length"],
    "SW physical": [
        "sea_water_temperature", "sbe45_salinity", "sea_water_electrical_conductivity_sbe45"],
    "SW biogeochem": [
        "mole_concentration_of_dissolved_molecular_oxygen_in_sea_water", "sea_water_turbidity_ecoflu",
        "mass_concentration_of_chlorophyll_a_in_sea_water_ecoflu", "sea_water_ph_external_seafet",
        "sea_water_ph_internal_seafet", "yield_fluorescence_in_sea_water_phytoflash",
        "particle_size_lisst", "particle_concentration_lisst"],
    "Carbon": ["equ_co2_concentration"],
    "Flow": ["water_flow_oceanpack", "water_pressure_oceanpack"],
}
# zero is physically impossible for these -> treat 0 as missing
ZERO_IS_MISSING = {
    "sbe45_salinity", "sea_water_ph_external_seafet", "sea_water_ph_internal_seafet",
    "mole_concentration_of_dissolved_molecular_oxygen_in_sea_water", "equ_co2_concentration",
    "sea_water_electrical_conductivity_sbe45"}

def voyage_label(name):
    m = FILENAME_PAT.search(name)
    return f"{m.group('season')}_{m.group('version')}" if m else name

def main():
    csvs = sorted(NUYINA.glob("*.csv"))
    all_vars = [c for g in GROUPS.values() for c in g]

    rows = {}
    for path in csvs:
        df = pd.read_csv(path, low_memory=False)
        if len(df) == 0:
            continue
        label = voyage_label(path.name)
        n = len(df)
        comp = {}
        for v in all_vars:
            if v not in df.columns:
                comp[v] = np.nan  # variable absent from this voyage
                continue
            s = pd.to_numeric(df[v], errors="coerce")
            if v in ZERO_IS_MISSING:
                s = s.where(s != 0)
            comp[v] = 100 * s.notna().mean()
        rows[label] = comp
        print(f"{label}: {n} rows")

    M = pd.DataFrame(rows)  # rows=variables, cols=voyages
    M = M.reindex(all_vars)

    # ordered row labels with group dividers
    ordered_vars, group_bounds, y = [], [], 0
    for gname, gvars in GROUPS.items():
        present = [v for v in gvars if v in M.index]
        ordered_vars.extend(present)
        group_bounds.append((gname, y, y + len(present)))
        y += len(present)
    M = M.reindex(ordered_vars)

    fig, ax = plt.subplots(figsize=(13, 22))
    im = ax.imshow(M.values, aspect="auto", cmap="viridis", vmin=0, vmax=100)
    ax.set_xticks(range(len(M.columns)))
    ax.set_xticklabels(M.columns, rotation=90, fontsize=8)
    ax.set_yticks(range(len(M.index)))
    ax.set_yticklabels([v[:42] for v in M.index], fontsize=6.5)

    # group dividers + labels (labels on the RIGHT, clear of the colorbar)
    # font scales down for small groups so long names do not overflow/overlap
    n_cols = M.shape[1]
    for gname, y0, y1 in group_bounds:
        if y0 > 0:
            ax.axhline(y0 - 0.5, color="black", linewidth=1.2)
        span = y1 - y0
        fs = 9 if span >= 6 else (7.5 if span >= 3 else 6)
        ax.text(n_cols - 0.3, (y0 + y1)/2 - 0.5, gname, rotation=90,
                ha="left", va="center", fontsize=fs, fontweight="bold",
                color="#21295C", clip_on=False)

    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.06)
    cbar.set_label("Completeness (% non-null)", fontsize=11)
    ax.set_title("RSV Nuyina underway data completeness \u2014 all measured variables\n"
                 "Grouped by instrument domain; zeros treated as missing where physically impossible",
                 fontsize=13)
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"eampB_nuyina_all_variable_completeness_{date.today().isoformat()}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"\nSaved: {out}")

    # also save the numeric table for the meeting
    xlsx = REPO / "data/processed/ship" / f"eampB_nuyina_all_variable_completeness_{date.today().isoformat()}.xlsx"
    M.to_excel(xlsx, engine="openpyxl")
    print(f"Saved: {xlsx}")

if __name__ == "__main__":
    main()
