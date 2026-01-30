"""
Satellite Downloader - Download Google satellite imagery as GeoTIFF.

A Python tool for downloading satellite imagery from Google's XYZ tile service
and exporting it as georeferenced GeoTIFF files with EPSG:4326 support.
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .cache import CacheManager
from .downloader import TileDownloader
from .geotiff import GeoTIFFWriter, create_geotiff
from .tiles import (
    lonlat_to_tile,
    tile_to_lonlat,
    tile_bounds,
    calculate_zoom,
    get_tiles_in_bbox,
    estimate_tile_count,
    parse_extent,
    parse_bbox
)
from .utils import (
    validate_bbox,
    validate_resolution,
    validate_zoom,
    format_bytes,
    print_summary
)

__all__ = [
    # Version info
    '__version__',
    '__author__',
    '__email__',

    # Main classes
    'CacheManager',
    'TileDownloader',
    'GeoTIFFWriter',

    # Main functions
    'create_geotiff',

    # Tile utilities
    'lonlat_to_tile',
    'tile_to_lonlat',
    'tile_bounds',
    'calculate_zoom',
    'get_tiles_in_bbox',
    'estimate_tile_count',
    'parse_extent',
    'parse_bbox',

    # Utility functions
    'validate_bbox',
    'validate_resolution',
    'validate_zoom',
    'format_bytes',
    'print_summary',
]
