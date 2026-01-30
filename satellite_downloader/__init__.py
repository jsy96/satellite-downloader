"""
Satellite Downloader - Download satellite imagery as GeoTIFF.

A Python tool for downloading satellite imagery from multiple sources
(Google, Sentinel-2, etc.) and exporting it as georeferenced GeoTIFF files.
"""

__version__ = "1.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .cache import CacheManager
from .datasources import DataSource, DataSourceFactory, GoogleDataSource, Sentinel2DataSource
from .downloader import TileDownloader
from .geotiff import GeoTIFFWriter, create_geotiff
from .tiles import (
    lonlat_to_tile,
    tile_to_lonlat,
    tile_to_mercator,
    tile_bounds,
    calculate_zoom,
    calculate_resolution_from_zoom,
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

    # Data sources
    'DataSource',
    'DataSourceFactory',
    'GoogleDataSource',
    'Sentinel2DataSource',

    # Main functions
    'create_geotiff',

    # Tile utilities
    'lonlat_to_tile',
    'tile_to_lonlat',
    'tile_to_mercator',
    'tile_bounds',
    'calculate_zoom',
    'calculate_resolution_from_zoom',
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
