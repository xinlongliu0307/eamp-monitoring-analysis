"""Tests for the penguin harmonisation module."""
import pandas as pd
import pytest

from eamp.penguin.harmonise import (
    SURFACE_TYPE_CODES,
    harmonise_columns,
    is_known_surface_type,
    parse_colony_name,
    parse_surface_type,
    surface_label,
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

    def test_whitespace_and_typo_variants(self):
        assert parse_surface_type(" fast  ice") == "fast_ice"
        assert parse_surface_type("fasr ice") == "fast_ice"
        assert parse_surface_type(" ice berg") == "iceberg"

    def test_floe_variants(self):
        for raw in ["floe", "ice floe", "large floe"]:
            assert parse_surface_type(raw) == "ice_floe"

    def test_compound_order_independent(self):
        assert parse_surface_type("fast ice/iceberg") == "iceberg_and_fast_ice"
        assert parse_surface_type("iceberg/fastice") == "iceberg_and_fast_ice"

    def test_distinct_categories_not_merged(self):
        assert parse_surface_type("land ice") != parse_surface_type("land/ice")
        assert parse_surface_type("rock") != parse_surface_type("rock/ice")

    def test_blank_returns_none(self):
        assert parse_surface_type("  ") is None

    def test_known_flag(self):
        assert is_known_surface_type("Fast ice")
        assert is_known_surface_type(None)
        assert not is_known_surface_type("Unknown surface")


class TestSurfaceLabel:
    def test_simple(self):
        assert surface_label("fast_ice") == "fast ice"

    def test_compound(self):
        assert surface_label("iceberg_and_fast_ice") == "iceberg/fast ice"

    def test_none(self):
        assert surface_label(None) is None

    def test_labels_round_trip(self):
        for code in SURFACE_TYPE_CODES:
            assert parse_surface_type(surface_label(code)) == code, code


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
