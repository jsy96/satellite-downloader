"""
Tests for tile coordinate conversion utilities.
"""

import pytest

from satellite_downloader.tiles import (
    lonlat_to_tile,
    tile_to_lonlat,
    tile_bounds,
    calculate_zoom,
    get_tiles_in_bbox,
    parse_extent,
    parse_bbox
)


class TestLonLatToTile:
    """Tests for lonlat_to_tile function."""

    def test_basic_conversion(self):
        """Test basic longitude/latitude to tile conversion."""
        x, y = lonlat_to_tile(0, 0, 0)
        assert x == 0
        assert y == 0

    def test_specific_location(self):
        """Test conversion at specific location."""
        # London area
        x, y = lonlat_to_tile(-0.1276, 51.5074, 10)
        assert isinstance(x, int)
        assert isinstance(y, int)

    def test_invalid_longitude(self):
        """Test with invalid longitude."""
        with pytest.raises(ValueError):
            lonlat_to_tile(181, 0, 10)

    def test_invalid_latitude(self):
        """Test with invalid latitude."""
        with pytest.raises(ValueError):
            lonlat_to_tile(0, 91, 10)

    def test_invalid_zoom(self):
        """Test with invalid zoom level."""
        with pytest.raises(ValueError):
            lonlat_to_tile(0, 0, 30)


class TestTileToLonLat:
    """Tests for tile_to_lonlat function."""

    def test_basic_conversion(self):
        """Test basic tile to longitude/latitude conversion."""
        lon, lat = tile_to_lonlat(0, 0, 0)
        assert -180 <= lon <= 180
        assert -90 <= lat <= 90

    def test_roundtrip(self):
        """Test roundtrip conversion."""
        original_lon, original_lat = 110.5, 30.5

        x, y = lonlat_to_tile(original_lon, original_lat, 15)
        result_lon, result_lat = tile_to_lonlat(x, y, 15)

        # Allow small difference due to tile quantization
        assert abs(original_lon - result_lon) < 0.1
        assert abs(original_lat - result_lat) < 0.1


class TestCalculateZoom:
    """Tests for calculate_zoom function."""

    def test_high_resolution(self):
        """Test with high resolution (small value)."""
        zoom = calculate_zoom(0.0001, 30)
        assert zoom >= 17  # Should be around 18-20

    def test_low_resolution(self):
        """Test with low resolution (large value)."""
        zoom = calculate_zoom(0.1, 0)
        assert zoom <= 16  # Should be around 14

    def test_invalid_resolution(self):
        """Test with invalid resolution."""
        with pytest.raises(ValueError):
            calculate_zoom(0, 0)
        with pytest.raises(ValueError):
            calculate_zoom(-0.001, 0)


class TestParseExtent:
    """Tests for parse_extent function."""

    def test_valid_extent(self):
        """Test parsing valid extent string."""
        min_lon, min_lat, max_lon, max_lat = parse_extent("E110-E110.1,N30-N30.1")
        assert min_lon == 110.0
        assert min_lat == 30.0
        assert max_lon == 110.1
        assert max_lat == 30.1

    def test_extent_with_spaces(self):
        """Test parsing extent with spaces."""
        result = parse_extent("E 110 - E 110.1 , N 30 - N 30.1")
        # Should handle spaces with strip
        assert len(result) == 4

    def test_invalid_format(self):
        """Test with invalid format."""
        with pytest.raises(ValueError):
            parse_extent("invalid")

    def test_missing_direction(self):
        """Test with missing direction prefix."""
        with pytest.raises(ValueError):
            parse_extent("110-110.1,30-30.1")


class TestParseBbox:
    """Tests for parse_bbox function."""

    def test_valid_bbox(self):
        """Test parsing valid bbox string."""
        min_lon, min_lat, max_lon, max_lat = parse_bbox("110,30,110.1,30.1")
        assert min_lon == 110.0
        assert min_lat == 30.0
        assert max_lon == 110.1
        assert max_lat == 30.1

    def test_invalid_format(self):
        """Test with invalid format."""
        with pytest.raises(ValueError):
            parse_bbox("invalid")

    def test_wrong_number_of_values(self):
        """Test with wrong number of values."""
        with pytest.raises(ValueError):
            parse_bbox("110,30,110.1")


class TestGetTilesInBbox:
    """Tests for get_tiles_in_bbox function."""

    def test_small_area(self):
        """Test with small area."""
        tiles, (x_min, y_min, x_max, y_max) = get_tiles_in_bbox(
            110, 30, 110.01, 30.01, 15
        )
        assert len(tiles) > 0
        assert isinstance(x_min, int)
        assert isinstance(y_min, int)

    def test_tile_coordinates(self):
        """Test that tile coordinates are valid."""
        tiles, bounds = get_tiles_in_bbox(0, 0, 0.1, 0.1, 10)
        for x, y in tiles:
            assert isinstance(x, int)
            assert isinstance(y, int)
            assert x >= 0
            assert y >= 0
