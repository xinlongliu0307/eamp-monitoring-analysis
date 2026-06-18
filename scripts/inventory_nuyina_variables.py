"""List and group all columns in the Nuyina underway schema."""
from pathlib import Path
import pandas as pd

NUYINA = Path("/g/data/gv90/xl1657/phd/eamp/data/raw/ship/aadc_downloads/nuyina_underway_voyages")

sample = sorted(NUYINA.glob("RSV_Nuyina_Voyage_Data_2024-25_V2.csv"))
if not sample:
    sample = sorted(NUYINA.glob("*.csv"))
head = pd.read_csv(sample[0], nrows=0)
cols = list(head.columns)
print(f"Source file: {sample[0].name}")
print(f"Total columns: {len(cols)}\n")

groups = {
    "Time / navigation": ["datetime", "time", "latitude", "longitude", "speed", "heading", "course", "depth_water"],
    "Meteorology (air)": ["air_temperature", "air_pressure", "humidity", "wind", "dewpoint"],
    "Radiation": ["radiation", "irradiance", "par", "shortwave", "longwave", "solar"],
    "Seawater (physical)": ["sea_water_temperature", "salinity", "conductivity", "sound_velocity"],
    "Seawater (biogeochem)": ["oxygen", "ph", "fluorescence", "chlorophyll", "turbidity"],
    "Carbon": ["co2", "pco2", "fco2", "xco2"],
}
assigned = set()
for label, keys in groups.items():
    matched = [c for c in cols if any(k in c.lower() for k in keys)]
    matched = [c for c in matched if c not in assigned]
    assigned.update(matched)
    print(f"=== {label} ({len(matched)}) ===")
    for c in matched:
        print(f"   {c}")
    print()

other = [c for c in cols if c not in assigned]
print(f"=== Other / ungrouped ({len(other)}) ===")
for c in other:
    print(f"   {c}")
