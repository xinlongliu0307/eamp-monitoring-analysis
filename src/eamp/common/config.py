"""Path resolution and shared configuration for the eamp package."""
from pathlib import Path
import os

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(REPO_ROOT / ".env")


def _resolve_path(env_var: str, default_subpath: str) -> Path:
    raw = os.environ.get(env_var)
    if raw:
        return Path(raw).expanduser().resolve()
    return (REPO_ROOT / default_subpath).resolve()


DATA_RAW = _resolve_path("EAMP_DATA_RAW", "data/raw")
DATA_INTERIM = _resolve_path("EAMP_DATA_INTERIM", "data/interim")
DATA_PROCESSED = _resolve_path("EAMP_DATA_PROCESSED", "data/processed")
OUTPUTS = _resolve_path("EAMP_OUTPUTS", "outputs")

PENGUIN_RAW = DATA_RAW / "penguin"
PENGUIN_INTERIM = DATA_INTERIM / "penguin"
PENGUIN_PROCESSED = DATA_PROCESSED / "penguin"
PENGUIN_FIGURES = OUTPUTS / "figures" / "penguin"

SHIP_RAW = DATA_RAW / "ship"
SHIP_INTERIM = DATA_INTERIM / "ship"
SHIP_PROCESSED = DATA_PROCESSED / "ship"
SHIP_FIGURES = OUTPUTS / "figures" / "ship"

PENGUIN_OBSERVATIONS_FILE = "eampA_colony_observations_eastant_2018-2025_v1.xlsx"
PENGUIN_INVENTORY_FILE = "eampA_colony_inventory_circumpolar_2025_v1.xlsx"
