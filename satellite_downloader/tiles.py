"""
XYZ Tile coordinate conversion utilities.

Converts between longitude/latitude and XYZ tile coordinates for various zoom levels.
Based on the Web Mercator projection used by Google Maps and similar services.
"""

import math
from typing import Tuple, List


# Google Earth tile size in pixels
TILE_SIZE = 256

# Earth circumference in meters (at equator)
EARTH_CIRCUMFERENCE = 40075016.68


def lonlat_to_tile(lon: float, lat: float, zoom: int) -> Tuple[int, int]:
    """
    Convert longitude/latitude to XYZ tile coordinates.

    Args:
        lon: Longitude in degrees (-180 to 180)
        lat: Latitude in degrees (-85.0511 to 85.0511)
        zoom: Zoom level (0 to 22+)

    Returns:
        Tuple of (x, y) tile coordinates

    Raises:
        ValueError: If coordinates are out of valid range

    Examples:
        >>> lonlat_to_tile(110, 30, 10)
        (819, 351)
    """
    # Validate input
    if not -180 <= lon <= 180:
        raise ValueError(f"Longitude must be between -180 and 180, got {lon}")
    if not -85.0511 <= lat <= 85.0511:
        raise ValueError(f"Latitude must be between -85.0511 and 85.0511, got {lat}")
    if not 0 <= zoom <= 25:
        raise ValueError(f"Zoom level must be between 0 and 25, got {zoom}")

    # Calculate tile coordinates
    n = 2 ** zoom
    x = int((lon + 180) / 360 * n)

    # Latitude calculation using Web Mercator projection
    lat_rad = math.radians(lat)
    y = int((1 - math.asinh(math.tan(lat_rad)) / math.pi) / 2 * n)

    return x, y


def tile_to_lonlat(x: int, y: int, zoom: int) -> Tuple[float, float]:
    """
    Convert XYZ tile coordinates to longitude/latitude.

    Returns the coordinates of the top-left corner of the tile.

    Args:
        x: Tile X coordinate
        y: Tile Y coordinate
        zoom: Zoom level

    Returns:
        Tuple of (longitude, latitude) in degrees

    Examples:
        >>> tile_to_lonlat(819, 351, 10)
        (109.6875, 30.35196552367773)
    """
    n = 2 ** zoom
    lon = x / n * 360 - 180

    # Reverse the Web Mercator projection
    y_rad = math.pi * (1 - 2 * y / n)
    lat = math.degrees(math.atan(math.sinh(y_rad)))

    return lon, lat


def tile_bounds(x: int, y: int, zoom: int) -> Tuple[float, float, float, float]:
    """
    Get the bounding box of a tile in longitude/latitude.

    Args:
        x: Tile X coordinate
        y: Tile Y coordinate
        zoom: Zoom level

    Returns:
        Tuple of (min_lon, min_lat, max_lon, max_lat)
    """
    min_lon, max_lat = tile_to_lonlat(x, y, zoom)
    max_lon, min_lat = tile_to_lonlat(x + 1, y + 1, zoom)
    return min_lon, min_lat, max_lon, max_lat


def calculate_zoom(resolution: float, lat: float = 0) -> int:
    """
    Calculate the appropriate zoom level for a given resolution.

    Args:
        resolution: Desired resolution in degrees
        lat: Latitude (affects meters per degree)

    Returns:
        Zoom level (integer)

    Note:
        Resolution varies with latitude due to the Mercator projection.
        At the equator, 1 degree ≈ 111.32 km.
    """
    if resolution <= 0:
        raise ValueError(f"Resolution must be positive, got {resolution}")

    # Meters per degree at the given latitude
    meters_per_degree = 111320 * math.cos(math.radians(lat))

    # Calculate required ground resolution in meters
    ground_resolution = resolution * meters_per_degree

    # Calculate zoom level
    # Formula: resolution = 2 * pi * R / (tile_size * 2^zoom)
    # Where R = Earth radius / scale factor
    # Simplified: zoom = log2(EARTH_CIRCUMFERENCE / (ground_resolution * TILE_SIZE))
    zoom = math.log2(EARTH_CIRCUMFERENCE / (ground_resolution * TILE_SIZE))

    return max(0, min(25, int(round(zoom))))


def calculate_resolution_from_zoom(zoom: int, lat: float = 0) -> float:
    """
    Calculate the resolution for a given zoom level.

    Args:
        zoom: Zoom level
        lat: Latitude (affects meters per degree)

    Returns:
        Resolution in degrees

    Note:
        This is the inverse of calculate_zoom.
        Resolution varies with latitude due to the Mercator projection.
    """
    if not 0 <= zoom <= 25:
        raise ValueError(f"Zoom level must be between 0 and 25, got {zoom}")

    # Meters per degree at the given latitude
    meters_per_degree = 111320 * math.cos(math.radians(lat))

    # Calculate ground resolution in meters for this zoom level
    # Formula: resolution = EARTH_CIRCUMFERENCE / (TILE_SIZE * 2^zoom)
    ground_resolution = EARTH_CIRCUMFERENCE / (TILE_SIZE * (2 ** zoom))

    # Convert to degrees
    resolution = ground_resolution / meters_per_degree

    return resolution


def get_tiles_in_bbox(min_lon: float, min_lat: float, max_lon: float, max_lat: float,
                      zoom: int) -> List[Tuple[int, int]]:
    """
    Get all tiles that intersect with the given bounding box.

    Args:
        min_lon: Minimum longitude
        min_lat: Minimum latitude
        max_lon: Maximum longitude
        max_lat: Maximum latitude
        zoom: Zoom level

    Returns:
        List of (x, y) tile coordinates
    """
    # Get tile range
    x_min, y_max = lonlat_to_tile(min_lon, max_lat, zoom)
    x_max, y_min = lonlat_to_tile(max_lon, min_lat, zoom)

    tiles = []
    for x in range(x_min, x_max + 1):
        # Note: y_max <= y_min in tile coordinates (Y increases downward)
        for y in range(y_max, y_min + 1):
            tiles.append((x, y))

    return tiles, (x_min, y_min, x_max, y_max)


def estimate_tile_count(min_lon: float, min_lat: float, max_lon: float, max_lat: float,
                        zoom: int) -> int:
    """
    Estimate the number of tiles needed for a bounding box.

    Args:
        min_lon: Minimum longitude
        min_lat: Minimum latitude
        max_lon: Maximum longitude
        max_lat: Maximum latitude
        zoom: Zoom level

    Returns:
        Estimated number of tiles
    """
    tiles, _ = get_tiles_in_bbox(min_lon, min_lat, max_lon, max_lat, zoom)
    return len(tiles)


def parse_extent(extent_str: str) -> Tuple[float, float, float, float]:
    """
    Parse extent string in format "E{min}-E{max},N{min}-N{max}".

    Args:
        extent_str: Extent string like "E110-E110.1,N30-N30.1"

    Returns:
        Tuple of (min_lon, min_lat, max_lon, max_lat)

    Raises:
        ValueError: If format is invalid

    Examples:
        >>> parse_extent("E110-E110.1,N30-N30.1")
        (110.0, 30.0, 110.1, 30.1)
    """
    try:
        parts = extent_str.split(',')
        if len(parts) != 2:
            raise ValueError("Extent must have 2 parts separated by comma")

        # Parse longitude part: "E110-E110.1"
        lon_part = parts[0].strip().upper()
        if not lon_part.startswith('E'):
            raise ValueError("Longitude part must start with 'E'")
        lon_values = lon_part[1:].split('-')
        if len(lon_values) != 2:
            raise ValueError("Longitude must have 2 values")
        min_lon = float(lon_values[0])
        max_lon = float(lon_values[1])

        # Parse latitude part: "N30-N30.1"
        lat_part = parts[1].strip().upper()
        if not lat_part.startswith('N'):
            raise ValueError("Latitude part must start with 'N'")
        lat_values = lat_part[1:].split('-')
        if len(lat_values) != 2:
            raise ValueError("Latitude must have 2 values")
        min_lat = float(lat_values[0])
        max_lat = float(lat_values[1])

        # Validate order
        if min_lon > max_lon:
            raise ValueError(f"min_lon ({min_lon}) must be <= max_lon ({max_lon})")
        if min_lat > max_lat:
            raise ValueError(f"min_lat ({min_lat}) must be <= max_lat ({max_lat})")

        return min_lon, min_lat, max_lon, max_lat

    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid extent format: {extent_str}. Expected format: 'E110-E110.1,N30-N30.1'. Error: {e}")


def tile_to_mercator(x: int, y: int, zoom: int) -> Tuple[float, float]:
    """
    Convert XYZ tile coordinates to Web Mercator (EPSG:3857) coordinates.

    Returns the coordinates of the top-left corner of the tile in meters.

    Args:
        x: Tile X coordinate
        y: Tile Y coordinate
        zoom: Zoom level

    Returns:
        Tuple of (easting, northing) in meters

    Examples:
        >>> tile_to_mercator(819, 351, 10)
        (12225416.24, 3522174.51)
    """
    n = 2 ** zoom
    # Tile size in meters at this zoom level
    tile_size_meters = EARTH_CIRCUMFERENCE / n

    # Calculate easting (x coordinate in meters)
    # x=0 corresponds to -180° = -EARTH_CIRCUMFERENCE/2
    easting = x * tile_size_meters - EARTH_CIRCUMFERENCE / 2

    # Calculate northing (y coordinate in meters)
    # y=0 corresponds to max latitude (≈85.05°)
    northing = EARTH_CIRCUMFERENCE / 2 - y * tile_size_meters

    return easting, northing


def parse_bbox(bbox_str: str) -> Tuple[float, float, float, float]:
    """
    Parse bbox string in format "min_lon,min_lat,max_lon,max_lat".

    Args:
        bbox_str: Bbox string like "110,30,110.1,30.1"

    Returns:
        Tuple of (min_lon, min_lat, max_lon, max_lat)

    Raises:
        ValueError: If format is invalid

    Examples:
        >>> parse_bbox("110,30,110.1,30.1")
        (110.0, 30.0, 110.1, 30.1)
    """
    try:
        values = bbox_str.split(',')
        if len(values) != 4:
            raise ValueError("Bbox must have 4 values")

        min_lon = float(values[0])
        min_lat = float(values[1])
        max_lon = float(values[2])
        max_lat = float(values[3])

        # Validate order
        if min_lon > max_lon:
            raise ValueError(f"min_lon ({min_lon}) must be <= max_lon ({max_lon})")
        if min_lat > max_lat:
            raise ValueError(f"min_lat ({min_lat}) must be <= max_lat ({max_lat})")

        return min_lon, min_lat, max_lon, max_lat

    except ValueError as e:
        raise ValueError(f"Invalid bbox format: {bbox_str}. Expected format: 'min_lon,min_lat,max_lon,max_lat'. Error: {e}")
