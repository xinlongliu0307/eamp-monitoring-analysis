"""Tests for the penguin harmonisation module."""
import pandas as pd
import pytest

from eamp.penguin.harmonise import (
    harmonise_columns,
    parse_colony_name,
    parse_surface_type,
)


class TestParseColonyName:
    def test_standard_format(self):
        assert parse_colony_name("7. Auster") == (7, "Auster")

    def test_double_space_after_dot(self):
        assert parse_colony_name("2.  Casey Bay") == (2, "Casey Bay")

    def test_two_digit_id(self):
        assert parse_colony_name("25. Ninnis Bank") == (25, "Ninnis Bank")

    def test_compound_name(self):
        assert parse_colony_name("8. Flutter (Cape Darnley)") == (
            8,
            "Flutter (Cape Darnley)",
        )

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_colony_name("Not a numbered sheet")


class TestParseSurfaceType:
    def test_fast_ice(self):
        assert parse_surface_type("Fast ice") == "fast_ice"

    def test_fastice_no_space(self):
        assert parse_surface_type("fastice") == "fast_ice"

    def test_berg_to_iceberg(self):
        assert parse_surface_type("berg") == "iceberg"

    def test_open_water(self):
        assert parse_surface_type("Open water") == "open_water"

    def test_nan_returns_none(self):
        assert parse_surface_type(pd.NA) is None

    def test_unknown_passes_through_lowercased(self):
        assert parse_surface_type("Unknown surface") == "unknown surface"


class TestHarmoniseColumns:
    def test_trailing_space_in_date_column(self):
        df = pd.DataFrame(
            {
                "Date ": ["2024-01-01"],
                "Lat": [-67.0],
                "Long": [60.0],
                "Surface": ["fast ice"],
                "Open water distance (km)": [12.5],
                "Comments": ["test entry"],
            }
        )
        result = harmonise_columns(df)
        assert result is not None
        assert "observation_date" in result.columns
        assert "latitude" in result.columns
        assert result["surface_type"].iloc[0] == "fast_ice"

    def test_drops_distance_from_last_variant(self):
        df = pd.DataFrame(
            {
                "Date": ["2024-01-01"],
                "Lat": [-67.0],
                "Long": [60.0],
                "Distance from last (km)": [5.0],
                "Surface": ["open water"],
                "Open water distance (km)": [0.0],
                "Comments": [""],
            }
        )
        result = harmonise_columns(df)
        assert result is not None
        assert "Distance from last (km)" not in result.columns

    def test_returns_none_when_required_columns_missing(self):
        df = pd.DataFrame({"Colony 1": [1], "Colony 2": [2]})
        result = harmonise_columns(df)
        assert result is None
